"""
API for deploying containerized applications to AWS ECS.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import boto3

from awslabs.ecs_mcp_server.api.containerize import containerize_app
from awslabs.ecs_mcp_server.api.infrastructure import create_ecr_infrastructure, create_ecs_infrastructure, create_infrastructure
from awslabs.ecs_mcp_server.utils.aws import get_aws_account_id, get_aws_client
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

    try:
        # Step 1: Containerize the application
        logger.info("Step 1: Containerizing the application...")
        containerization_result = await containerize_app(
            app_path=app_path, port=container_port, environment_vars=environment_vars
        )
        logger.info(f"Containerization successful: {containerization_result['dockerfile_path']}")

        # Step 2: Create ECR infrastructure
        logger.info("Step 2: Creating ECR infrastructure...")
        ecr_result = await create_ecr_infrastructure(app_name=app_name)
        
        # Get the ECR repository URI
        ecr_repo_uri = ecr_result["resources"]["ecr_repository_uri"]
        logger.info(f"ECR repository created: {ecr_repo_uri}")

        # Step 3: Build and push Docker image to ECR
        logger.info("Step 3: Building and pushing Docker image to ECR...")
        try:
            # Use the ECR repository URI from the CloudFormation stack
            logger.info(f"Using ECR repository: {ecr_repo_uri}")
            
            image_tag = await build_and_push_image(
                app_path=app_path, repository_uri=ecr_repo_uri, tag="latest"
            )
            logger.info(f"Image successfully built and pushed with tag: {image_tag}")
        except Exception as e:
            logger.error(f"Failed to build and push Docker image: {str(e)}", exc_info=True)
            return {
                "app_name": app_name,
                "repository_uri": ecr_repo_uri,
                "status": "ERROR",
                "message": f"Failed to build and push Docker image: {str(e)}",
                "error": str(e)
            }
        
        # Full image URI with tag
        image_uri = f"{ecr_repo_uri}:{image_tag}"

        # Step 4: Create ECS infrastructure with the image URI
        logger.info("Step 4: Creating ECS infrastructure...")
        ecs_result = await create_ecs_infrastructure(
            app_name=app_name,
            image_uri=image_uri,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            cpu=cpu,
            memory=memory,
        )
        logger.info(f"ECS infrastructure created: {ecs_result['stack_name']}")

        # Step 5: Wait for service to stabilize and get the ALB URL
        logger.info("Step 5: Getting ALB URL...")
        alb_url = await _get_alb_url(app_name)
        logger.info(f"ALB URL: {alb_url}")

        return {
            "app_name": app_name,
            "repository_uri": ecr_repo_uri,
            "image_tag": image_tag,
            "image_uri": image_uri,
            "alb_url": alb_url,
            "status": "DEPLOYING",
            "message": f"Application {app_name} is being deployed. Check status with get_deployment_status tool.",
        }
    except Exception as e:
        logger.error(f"Error in deploy_to_ecs: {str(e)}", exc_info=True)
        return {
            "app_name": app_name,
            "status": "ERROR",
            "message": f"Deployment failed: {str(e)}",
            "error": str(e)
        }


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
