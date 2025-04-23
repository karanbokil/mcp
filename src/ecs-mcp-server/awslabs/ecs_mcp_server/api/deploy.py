"""
API for deploying containerized applications to AWS ECS.
"""

import logging
import os
import json
import time
from typing import Dict, List, Optional, Any

import boto3

from awslabs.ecs_mcp_server.api.containerize import containerize_app
from awslabs.ecs_mcp_server.api.infrastructure import create_infrastructure
from awslabs.ecs_mcp_server.utils.aws import get_aws_client, get_aws_account_id
from awslabs.ecs_mcp_server.utils.docker import build_and_push_image

logger = logging.getLogger(__name__)


async def deploy_to_ecs(
    app_path: str,
    app_name: str,
    container_port: int,
    vpc_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    cpu: Optional[int] = None,
    memory: Optional[int] = None,
    environment_vars: Optional[Dict[str, str]] = None,
    health_check_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deploys a containerized application to AWS ECS with Fargate and ALB.

    Args:
        app_path: Path to the web application directory
        app_name: Name of the application
        container_port: Port the container listens on
        vpc_id: VPC ID for deployment (optional)
        subnet_ids: List of subnet IDs for deployment (optional)
        cpu: CPU units for the task (optional)
        memory: Memory (MB) for the task (optional)
        environment_vars: Environment variables as a dictionary (optional)
        health_check_path: Path for ALB health checks (optional)

    Returns:
        Dict containing deployment results
    """
    logger.info(f"Deploying {app_name} to ECS from {app_path}")

    # Step 1: Containerize the application
    containerization_result = await containerize_app(
        app_path=app_path, port=container_port, environment_vars=environment_vars
    )

    # Step 2: Create ECS infrastructure
    infrastructure_result = await create_infrastructure(
        app_name=app_name, vpc_id=vpc_id, subnet_ids=subnet_ids, cpu=cpu, memory=memory
    )

    # Step 3: Build and push Docker image to ECR
    account_id = await get_aws_account_id()
    region = os.environ.get("AWS_REGION", "us-east-1")
    repository_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{app_name}-repo"

    image_tag = await build_and_push_image(
        app_path=app_path, repository_uri=repository_uri, tag="latest"
    )

    # Step 4: Update ECS task definition with the new image
    task_definition = await _update_task_definition(
        app_name=app_name,
        image_uri=f"{repository_uri}:{image_tag}",
        container_port=container_port,
        cpu=cpu or 256,
        memory=memory or 512,
        environment_vars=environment_vars or {},
    )

    # Step 5: Update ECS service with the new task definition
    service = await _update_ecs_service(
        app_name=app_name,
        task_definition=task_definition["taskDefinitionArn"],
        health_check_path=health_check_path or "/",
    )

    # Step 6: Wait for service to stabilize and get the ALB URL
    alb_url = await _get_alb_url(app_name)

    return {
        "app_name": app_name,
        "repository_uri": repository_uri,
        "image_tag": image_tag,
        "task_definition_arn": task_definition["taskDefinitionArn"],
        "service_arn": service["serviceArn"],
        "alb_url": alb_url,
        "status": "DEPLOYING",
        "message": f"Application {app_name} is being deployed. Check status with get_deployment_status tool.",
    }


async def _update_task_definition(
    app_name: str,
    image_uri: str,
    container_port: int,
    cpu: int,
    memory: int,
    environment_vars: Dict[str, str],
) -> Dict[str, Any]:
    """Updates the ECS task definition with the new image."""
    ecs_client = await get_aws_client("ecs")

    # Convert environment variables to ECS format
    environment = [{"name": k, "value": v} for k, v in environment_vars.items()]

    # Register new task definition
    response = ecs_client.register_task_definition(
        family=f"{app_name}-task",
        executionRoleArn=f"arn:aws:iam::{await get_aws_account_id()}:role/{app_name}-ecs-execution-role",
        taskRoleArn=f"arn:aws:iam::{await get_aws_account_id()}:role/{app_name}-ecs-task-role",
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu=str(cpu),
        memory=str(memory),
        containerDefinitions=[
            {
                "name": f"{app_name}-container",
                "image": image_uri,
                "essential": True,
                "portMappings": [
                    {"containerPort": container_port, "hostPort": container_port, "protocol": "tcp"}
                ],
                "environment": environment,
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": f"/ecs/{app_name}",
                        "awslogs-region": os.environ.get("AWS_REGION", "us-east-1"),
                        "awslogs-stream-prefix": "ecs",
                    },
                },
            }
        ],
    )

    return response["taskDefinition"]


async def _update_ecs_service(
    app_name: str, task_definition: str, health_check_path: str
) -> Dict[str, Any]:
    """Updates the ECS service with the new task definition."""
    ecs_client = await get_aws_client("ecs")

    # Check if service exists
    try:
        response = ecs_client.describe_services(
            cluster=f"{app_name}-cluster", services=[f"{app_name}-service"]
        )

        if response["services"] and response["services"][0]["status"] != "INACTIVE":
            # Update existing service
            response = ecs_client.update_service(
                cluster=f"{app_name}-cluster",
                service=f"{app_name}-service",
                taskDefinition=task_definition,
                forceNewDeployment=True,
            )
            return response["service"]
    except Exception as e:
        logger.warning(f"Error checking service status: {e}")

    # Create new service if it doesn't exist or is inactive
    try:
        # Get target group ARN
        elbv2_client = await get_aws_client("elbv2")
        target_groups = elbv2_client.describe_target_groups(Names=[f"{app_name}-target-group"])
        target_group_arn = target_groups["TargetGroups"][0]["TargetGroupArn"]

        # Create service
        response = ecs_client.create_service(
            cluster=f"{app_name}-cluster",
            serviceName=f"{app_name}-service",
            taskDefinition=task_definition,
            desiredCount=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": await _get_subnet_ids(app_name),
                    "securityGroups": [await _get_security_group_id(app_name)],
                    "assignPublicIp": "ENABLED",
                }
            },
            loadBalancers=[
                {
                    "targetGroupArn": target_group_arn,
                    "containerName": f"{app_name}-container",
                    "containerPort": 80,  # This should match the container port
                }
            ],
        )
        return response["service"]
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise


async def _get_subnet_ids(app_name: str) -> List[str]:
    """Gets subnet IDs from CloudFormation outputs."""
    cloudformation = await get_aws_client("cloudformation")

    try:
        response = cloudformation.describe_stacks(StackName=f"{app_name}-ecs-infrastructure")

        for output in response["Stacks"][0]["Outputs"]:
            if output["OutputKey"] == "SubnetIds":
                return output["OutputValue"].split(",")
    except Exception as e:
        logger.error(f"Error getting subnet IDs: {e}")

    # Fallback to default VPC subnets
    ec2 = await get_aws_client("ec2")
    response = ec2.describe_subnets(Filters=[{"Name": "default-for-az", "Values": ["true"]}])
    return [subnet["SubnetId"] for subnet in response["Subnets"][:2]]


async def _get_security_group_id(app_name: str) -> str:
    """Gets security group ID from CloudFormation outputs."""
    cloudformation = await get_aws_client("cloudformation")

    try:
        response = cloudformation.describe_stacks(StackName=f"{app_name}-ecs-infrastructure")

        for output in response["Stacks"][0]["Outputs"]:
            if output["OutputKey"] == "ContainerSecurityGroup":
                return output["OutputValue"]
    except Exception as e:
        logger.error(f"Error getting security group ID: {e}")

    # Fallback to default VPC security group
    ec2 = await get_aws_client("ec2")
    response = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": ["default"]}])
    return response["SecurityGroups"][0]["GroupId"]


async def _get_alb_url(app_name: str) -> str:
    """Gets the ALB URL from CloudFormation outputs."""
    cloudformation = await get_aws_client("cloudformation")

    try:
        response = cloudformation.describe_stacks(StackName=f"{app_name}-ecs-infrastructure")

        for output in response["Stacks"][0]["Outputs"]:
            if output["OutputKey"] == "LoadBalancerDNS":
                return f"http://{output['OutputValue']}"
    except Exception as e:
        logger.error(f"Error getting ALB URL: {e}")
        return "ALB URL not available yet. Check status later with get_deployment_status tool."
