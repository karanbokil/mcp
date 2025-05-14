"""
API for creating ECS infrastructure using CloudFormation/CDK.
"""

import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

import boto3
from jinja2 import Environment, FileSystemLoader

from awslabs.ecs_mcp_server.utils.aws import (
    get_aws_account_id,
    get_aws_client,
    get_default_vpc_and_subnets,
)
from awslabs.ecs_mcp_server.utils.templates import get_templates_dir

logger = logging.getLogger(__name__)

async def create_infrastructure(
    app_name: str,
    app_path: str,
    vpc_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    cpu: Optional[int] = None,
    memory: Optional[int] = None,
    desired_count: Optional[int] = None,
    enable_auto_scaling: Optional[bool] = None,
    container_port: Optional[int] = None,
    environment_vars: Optional[Dict[str, str]] = None,
    health_check_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates complete ECS infrastructure using CloudFormation.
    This method combines the creation of ECR and ECS infrastructure.
    It will also build and push the Docker image.

    Args:
        app_name: Name of the application
        app_path: Path to the application directory (required for building and pushing Docker image)
        vpc_id: VPC ID for deployment (optional, will create new if not provided)
        subnet_ids: List of subnet IDs for deployment (optional)
        cpu: CPU units for the task (optional, default: 256)
        memory: Memory (MB) for the task (optional, default: 512)
        desired_count: Desired number of tasks (optional, default: 1)
        enable_auto_scaling: Enable auto-scaling for the service (optional, default: False)
        container_port: Port the container listens on (optional, will be detected from app)
        environment_vars: Environment variables as a dictionary (optional)
        health_check_path: Path for ALB health checks (optional, default: "/")

    Returns:
        Dict containing infrastructure creation results
    """
    logger.info(f"Creating complete infrastructure for {app_name}")
    
    # Step 1: Create ECR infrastructure
    ecr_result = await create_ecr_infrastructure(app_name=app_name)
    
    # Get the ECR repository URI
    ecr_repo_uri = ecr_result["resources"]["ecr_repository_uri"]
    
    # Step 2: Build and push Docker image
    try:
        from awslabs.ecs_mcp_server.utils.docker import build_and_push_image
        logger.info(f"Building and pushing Docker image for {app_name} from {app_path}")
        
        image_tag = await build_and_push_image(
            app_path=app_path, repository_uri=ecr_repo_uri, tag="latest"
        )
        logger.info(f"Image successfully built and pushed with tag: {image_tag}")
        image_uri = f"{ecr_repo_uri}:{image_tag}"
    except Exception as e:
        logger.error(f"Error building and pushing Docker image: {e}")
        # Return partial result with just ECR info if image build fails
        return {
            "stack_name": f"{app_name}-ecr-infrastructure",
            "operation": "create",
            "resources": {
                "ecr_repository": f"{app_name}-repo",
                "ecr_repository_uri": ecr_repo_uri,
            },
            "message": f"Created ECR repository, but Docker image build failed: {str(e)}"
        }
    
    # Step 3: Create ECS infrastructure with the image URI
    try:
        ecs_result = await create_ecs_infrastructure(
            app_name=app_name,
            image_uri=image_uri,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            cpu=cpu,
            memory=memory,
            desired_count=desired_count,
            enable_auto_scaling=enable_auto_scaling,
            container_port=container_port,
            health_check_path=health_check_path if health_check_path else "/"
        )
    except Exception as e:
        logger.error(f"Error creating ECS infrastructure: {e}")
        # Return partial result with just ECR info if ECS creation fails
        return {
            "stack_name": f"{app_name}-ecr-infrastructure",
            "operation": "create",
            "resources": {
                "ecr_repository": f"{app_name}-repo",
                "ecr_repository_uri": ecr_repo_uri,
            },
            "message": f"Created ECR repository, but ECS infrastructure creation failed: {str(e)}"
        }
    
    # Combine results
    combined_result = {
        "stack_name": ecs_result["stack_name"],
        "stack_id": ecs_result["stack_id"],
        "operation": ecs_result["operation"],
        "template_path": ecs_result["template_path"],
        "vpc_id": ecs_result["vpc_id"],
        "subnet_ids": ecs_result["subnet_ids"],
        "resources": {
            **ecs_result["resources"],
            "ecr_repository": ecr_result["resources"]["ecr_repository"],
            "ecr_repository_uri": ecr_repo_uri,
        },
        "image_uri": image_uri
    }
    
    return combined_result

async def create_ecr_infrastructure(
    app_name: str,
) -> Dict[str, Any]:
    """
    Creates ECR repository infrastructure using CloudFormation.

    Args:
        app_name: Name of the application

    Returns:
        Dict containing infrastructure creation results
    """
    logger.info(f"Creating ECR infrastructure for {app_name}")

    # Get AWS account ID
    account_id = await get_aws_account_id()

    # Generate CloudFormation template
    cf_template = await _generate_cloudformation_template(
        template_name="ecr_infrastructure.json.j2",
        app_name=app_name,
        account_id=account_id,
    )

    # Create a temporary file for the CloudFormation template
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(cf_template.encode("utf-8"))

    try:
        # Deploy the CloudFormation stack
        cloudformation = await get_aws_client("cloudformation")
        stack_name = f"{app_name}-ecr-infrastructure"

        # Check if stack already exists
        try:
            cloudformation.describe_stacks(StackName=stack_name)
            stack_exists = True
        except cloudformation.exceptions.ClientError:
            stack_exists = False

        if stack_exists:
            # Update existing stack
            response = cloudformation.update_stack(
                StackName=stack_name,
                TemplateBody=cf_template,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {"ParameterKey": "AppName", "ParameterValue": app_name},
                ],
            )
            operation = "update"
        else:
            # Create new stack
            response = cloudformation.create_stack(
                StackName=stack_name,
                TemplateBody=cf_template,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {"ParameterKey": "AppName", "ParameterValue": app_name},
                ],
            )
            operation = "create"

        # Save CloudFormation template to a file in the current directory
        cf_file_path = f"{app_name}-ecr-infrastructure.json"
        with open(cf_file_path, "w") as f:
            f.write(cf_template)

        # Wait for stack creation to complete
        logger.info(f"Waiting for ECR repository stack {stack_name} to be created...")
        waiter = cloudformation.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack_name)
        logger.info(f"ECR repository stack {stack_name} created successfully")

        # Get the ECR repository URI
        response = cloudformation.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]
        ecr_repo_uri = None
        for output in outputs:
            if output["OutputKey"] == "ECRRepositoryURI":
                ecr_repo_uri = output["OutputValue"]
                break

        return {
            "stack_name": stack_name,
            "stack_id": response.get("StackId"),
            "operation": operation,
            "template_path": cf_file_path,
            "resources": {
                "ecr_repository": f"{app_name}-repo",
                "ecr_repository_uri": ecr_repo_uri,
            },
        }

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def create_ecs_infrastructure(
    app_name: str,
    image_uri: Optional[str] = None,
    vpc_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    cpu: Optional[int] = None,
    memory: Optional[int] = None,
    desired_count: Optional[int] = None,
    enable_auto_scaling: Optional[bool] = None,
    container_port: Optional[int] = None,
    health_check_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates ECS infrastructure using CloudFormation.

    Args:
        app_name: Name of the application
        image_uri: URI of the container image
        vpc_id: VPC ID for deployment (optional, will create new if not provided)
        subnet_ids: List of subnet IDs for deployment (optional)
        cpu: CPU units for the task (optional, default: 256)
        memory: Memory (MB) for the task (optional, default: 512)
        desired_count: Desired number of tasks (optional, default: 1)
        enable_auto_scaling: Enable auto-scaling for the service (optional, default: False)
        container_port: Port the container listens on (optional, default: 80)
        health_check_path: Path for ALB health checks (optional, default: "/")

    Returns:
        Dict containing infrastructure creation results
    """
    logger.info(f"Creating ECS infrastructure for {app_name}")

    # Set default values
    cpu = cpu or 256
    memory = memory or 512
    desired_count = desired_count or 1
    enable_auto_scaling = enable_auto_scaling or False
    container_port = container_port or 80
    health_check_path = health_check_path or "/"

    # Get AWS account ID
    account_id = await get_aws_account_id()

    # Get VPC and subnet information if not provided
    if not vpc_id or not subnet_ids:
        vpc_info = await get_default_vpc_and_subnets()
        vpc_id = vpc_id or vpc_info["vpc_id"]
        subnet_ids = subnet_ids or vpc_info["subnet_ids"]

    # Generate CloudFormation template
    cf_template = await _generate_cloudformation_template(
        template_name="ecs_infrastructure.json.j2",
        app_name=app_name,
        vpc_id=vpc_id,
        subnet_ids=subnet_ids,
        cpu=cpu,
        memory=memory,
        desired_count=desired_count,
        enable_auto_scaling=enable_auto_scaling,
        account_id=account_id,
        image_uri=image_uri,
        container_port=container_port,
        health_check_path=health_check_path,
    )

    # Create a temporary file for the CloudFormation template
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(cf_template.encode("utf-8"))

    try:
        # Deploy the CloudFormation stack
        cloudformation = await get_aws_client("cloudformation")
        stack_name = f"{app_name}-ecs-infrastructure"

        # Check if stack already exists
        try:
            cloudformation.describe_stacks(StackName=stack_name)
            stack_exists = True
        except cloudformation.exceptions.ClientError:
            stack_exists = False

        if stack_exists:
            # Update existing stack
            response = cloudformation.update_stack(
                StackName=stack_name,
                TemplateBody=cf_template,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {"ParameterKey": "AppName", "ParameterValue": app_name},
                    {"ParameterKey": "VpcId", "ParameterValue": vpc_id},
                    {"ParameterKey": "SubnetIds", "ParameterValue": ",".join(subnet_ids)},
                    {"ParameterKey": "TaskCpu", "ParameterValue": str(cpu)},
                    {"ParameterKey": "TaskMemory", "ParameterValue": str(memory)},
                    {"ParameterKey": "DesiredCount", "ParameterValue": str(desired_count)},
                    {
                        "ParameterKey": "EnableAutoScaling",
                        "ParameterValue": str(enable_auto_scaling).lower(),
                    },
                    {"ParameterKey": "ImageUri", "ParameterValue": image_uri},
                    {"ParameterKey": "ContainerPort", "ParameterValue": str(container_port)},
                    {"ParameterKey": "HealthCheckPath", "ParameterValue": health_check_path}
                ],
            )
            operation = "update"
        else:
            # Create new stack
            response = cloudformation.create_stack(
                StackName=stack_name,
                TemplateBody=cf_template,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {"ParameterKey": "AppName", "ParameterValue": app_name},
                    {"ParameterKey": "VpcId", "ParameterValue": vpc_id},
                    {"ParameterKey": "SubnetIds", "ParameterValue": ",".join(subnet_ids)},
                    {"ParameterKey": "TaskCpu", "ParameterValue": str(cpu)},
                    {"ParameterKey": "TaskMemory", "ParameterValue": str(memory)},
                    {"ParameterKey": "DesiredCount", "ParameterValue": str(desired_count)},
                    {
                        "ParameterKey": "EnableAutoScaling",
                        "ParameterValue": str(enable_auto_scaling).lower(),
                    },
                    {"ParameterKey": "ImageUri", "ParameterValue": image_uri},
                    {"ParameterKey": "ContainerPort", "ParameterValue": str(container_port)},
                    {"ParameterKey": "HealthCheckPath", "ParameterValue": health_check_path}
                ],
            )
            operation = "create"

        # Save CloudFormation template to a file in the current directory
        cf_file_path = f"{app_name}-ecs-infrastructure.json"
        with open(cf_file_path, "w") as f:
            f.write(cf_template)

        return {
            "stack_name": stack_name,
            "stack_id": response.get("StackId"),
            "operation": operation,
            "template_path": cf_file_path,
            "vpc_id": vpc_id,
            "subnet_ids": subnet_ids,
            "resources": {
                "cluster": f"{app_name}-cluster",
                "service": f"{app_name}-service",
                "task_definition": f"{app_name}-task",
                "load_balancer": f"{app_name}-alb",
            },
        }

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def _generate_cloudformation_template(
    template_name: str,
    app_name: str,
    account_id: str,
    vpc_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    cpu: Optional[int] = None,
    memory: Optional[int] = None,
    desired_count: Optional[int] = None,
    enable_auto_scaling: Optional[bool] = None,
    image_uri: Optional[str] = None,
    container_port: Optional[int] = None,
    health_check_path: Optional[str] = None,
) -> str:
    """Generates a CloudFormation template."""
    templates_dir = get_templates_dir()
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True
    )

    template = env.get_template(template_name)

    # Generate ISO 8601 timestamp for deployment tracking
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Prepare template parameters
    template_params = {
        "app_name": app_name,
        "account_id": account_id,
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
        "timestamp": timestamp,
    }
    
    # Add optional parameters if provided
    if vpc_id:
        template_params["vpc_id"] = vpc_id
    if subnet_ids:
        template_params["subnet_ids"] = subnet_ids
    if cpu:
        template_params["cpu"] = cpu
    if memory:
        template_params["memory"] = memory
    if desired_count:
        template_params["desired_count"] = desired_count
    if enable_auto_scaling is not None:
        template_params["enable_auto_scaling"] = enable_auto_scaling
    if image_uri:
        template_params["image_uri"] = image_uri
    if container_port:
        template_params["container_port"] = container_port
    if health_check_path:
        template_params["health_check_path"] = health_check_path

    # Render the template
    cf_template = template.render(**template_params)

    return cf_template