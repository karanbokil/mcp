"""
API for creating ECS infrastructure using CloudFormation/CDK.
"""

import logging
import os
import json
import tempfile
from typing import Dict, List, Optional, Any

import boto3
from jinja2 import Environment, FileSystemLoader

from awslabs.ecs_mcp_server.utils.templates import get_templates_dir
from awslabs.ecs_mcp_server.utils.aws import get_aws_client, get_aws_account_id, get_default_vpc_and_subnets

logger = logging.getLogger(__name__)

async def create_infrastructure(
    app_name: str,
    vpc_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    cpu: Optional[int] = None,
    memory: Optional[int] = None,
    desired_count: Optional[int] = None,
    enable_auto_scaling: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Creates ECS infrastructure using CloudFormation.
    
    Args:
        app_name: Name of the application
        vpc_id: VPC ID for deployment (optional, will create new if not provided)
        subnet_ids: List of subnet IDs for deployment (optional)
        cpu: CPU units for the task (optional, default: 256)
        memory: Memory (MB) for the task (optional, default: 512)
        desired_count: Desired number of tasks (optional, default: 1)
        enable_auto_scaling: Enable auto-scaling for the service (optional, default: False)
        
    Returns:
        Dict containing infrastructure creation results
    """
    logger.info(f"Creating ECS infrastructure for {app_name}")
    
    # Set default values
    cpu = cpu or 256
    memory = memory or 512
    desired_count = desired_count or 1
    enable_auto_scaling = enable_auto_scaling or False
    
    # Get AWS account ID
    account_id = await get_aws_account_id()
    
    # Get VPC and subnet information if not provided
    if not vpc_id or not subnet_ids:
        vpc_info = await get_default_vpc_and_subnets()
        vpc_id = vpc_id or vpc_info["vpc_id"]
        subnet_ids = subnet_ids or vpc_info["subnet_ids"]
    
    # Generate CloudFormation template
    cf_template = await _generate_cloudformation_template(
        app_name=app_name,
        vpc_id=vpc_id,
        subnet_ids=subnet_ids,
        cpu=cpu,
        memory=memory,
        desired_count=desired_count,
        enable_auto_scaling=enable_auto_scaling,
        account_id=account_id
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
                    {"ParameterKey": "EnableAutoScaling", "ParameterValue": str(enable_auto_scaling).lower()},
                ]
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
                    {"ParameterKey": "EnableAutoScaling", "ParameterValue": str(enable_auto_scaling).lower()},
                ]
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
                "ecr_repository": f"{app_name}-repo",
            }
        }
    
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

async def _generate_cloudformation_template(
    app_name: str,
    vpc_id: str,
    subnet_ids: List[str],
    cpu: int,
    memory: int,
    desired_count: int,
    enable_auto_scaling: bool,
    account_id: str
) -> str:
    """Generates a CloudFormation template for ECS infrastructure."""
    templates_dir = get_templates_dir()
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    template = env.get_template("ecs_infrastructure.json.j2")
    
    # Render the template
    cf_template = template.render(
        app_name=app_name,
        vpc_id=vpc_id,
        subnet_ids=subnet_ids,
        cpu=cpu,
        memory=memory,
        desired_count=desired_count,
        enable_auto_scaling=enable_auto_scaling,
        account_id=account_id,
        aws_region=os.environ.get("AWS_REGION", "us-east-1")
    )
    
    return cf_template
