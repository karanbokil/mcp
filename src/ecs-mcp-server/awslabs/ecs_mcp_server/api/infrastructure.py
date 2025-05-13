"""
API for creating ECS infrastructure using CloudFormation/CDK.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from awslabs.ecs_mcp_server.utils.aws import (
    get_aws_account_id,
    get_aws_client,
    get_default_vpc_and_subnets,
)
from awslabs.ecs_mcp_server.utils.templates import get_templates_dir

logger = logging.getLogger(__name__)

def prepare_template_files(app_name: str, app_path: str) -> Dict[str, str]:
    """
    Prepares CloudFormation template files for ECR and ECS infrastructure.
    Creates the cloudformation-templates directory if it doesn't exist and
    returns paths to the template files.

    Args:
        app_name: Name of the application
        app_path: Path to the application directory

    Returns:
        Dict containing paths to the template files
    """
    # Create templates directory
    templates_dir = os.path.join(app_path, "cloudformation-templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    # Define template file paths
    ecr_template_path = os.path.join(templates_dir, f"{app_name}-ecr-infrastructure.json")
    ecs_template_path = os.path.join(templates_dir, f"{app_name}-ecs-infrastructure.json")
    
    # Read and write ECR template
    source_templates_dir = get_templates_dir()
    ecr_source_path = os.path.join(source_templates_dir, "ecr_infrastructure.json")
    
    with open(ecr_source_path, "r") as f:
        ecr_template_content = f.read()
    
    with open(ecr_template_path, "w") as f:
        f.write(ecr_template_content)
    
    # Read and write ECS template
    ecs_source_path = os.path.join(source_templates_dir, "ecs_infrastructure.json")
    
    with open(ecs_source_path, "r") as f:
        ecs_template_content = f.read()
    
    with open(ecs_template_path, "w") as f:
        f.write(ecs_template_content)
    
    return {
        "ecr_template_path": ecr_template_path,
        "ecs_template_path": ecs_template_path,
        "ecr_template_content": ecr_template_content,
        "ecs_template_content": ecs_template_content
    }

async def create_infrastructure(
    app_name: str,
    app_path: str,
    force_deploy: bool = False,
    vpc_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    route_table_ids: Optional[List[str]] = None,
    cpu: Optional[int] = None,
    memory: Optional[int] = None,
    desired_count: Optional[int] = None,
    container_port: Optional[int] = None,
    health_check_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates complete ECS infrastructure using CloudFormation.
    This method combines the creation of ECR and ECS infrastructure.
    If force_deploy is True, it will also build and push the Docker image.
    Otherwise, it will only generate the template files.

    Args:
        app_name: Name of the application
        app_path: Path to the application directory
        force_deploy: Whether to build and deploy the infrastructure or just generate templates
        vpc_id: VPC ID for deployment, (optional, default: default vpc)
        subnet_ids: List of subnet IDs for deployment (optional, default: default vpc subnets)
        cpu: CPU units for the task (optional, default: 256)
        memory: Memory (MB) for the task (optional, default: 512)
        desired_count: Desired number of tasks (optional, default: 1)
        enable_auto_scaling: Enable auto-scaling for the service (optional, default: False)
        container_port: Port the container listens on (optional, default: 80)
        health_check_path: Path for ALB health checks (optional, default: "/")

    Returns:
        Dict containing infrastructure creation results or template paths
    """
    logger.info(f"Creating infrastructure for {app_name}")
    
    # Step 1: Prepare template files
    template_files = prepare_template_files(app_name, app_path)
    ecr_template_path = template_files["ecr_template_path"]
    ecs_template_path = template_files["ecs_template_path"]
    
    # If not force_deploy, return the template paths and guidance
    if not force_deploy:
        return {
            "operation": "generate_templates",
            "template_paths": {
                "ecr_template": ecr_template_path,
                "ecs_template": ecs_template_path
            },
            "guidance": {
                "description": "CloudFormation templates have been generated for your review",
                "next_steps": [
                    "1. Review the generated templates in the cloudformation-templates directory",
                    "2. Build your Docker image locally: docker build -t your-app .",
                    "3. Create the ECR repository using AWS CLI or CloudFormation",
                    "4. Push your Docker image to the ECR repository",
                    "5. Update the ECS template with your ECR image URI",
                    "6. Deploy the ECS infrastructure using AWS CLI or CloudFormation"
                ],
                "aws_cli_commands": {
                    "deploy_ecr": f"aws cloudformation deploy --template-file {ecr_template_path} --stack-name {app_name}-ecr --capabilities CAPABILITY_IAM",
                    "get_ecr_uri": f"aws cloudformation describe-stacks --stack-name {app_name}-ecr --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryURI`].OutputValue' --output text",
                    "deploy_ecs": f"aws cloudformation deploy --template-file {ecs_template_path} --stack-name {app_name}-ecs --capabilities CAPABILITY_IAM --parameter-overrides AppName={app_name} ImageUri=YOUR_ECR_IMAGE_URI"
                },
                "alternative_tools": [
                    "AWS CDK: Use the templates as a reference to create CDK constructs",
                    "Terraform: Use the templates as a reference to create Terraform resources",
                    "AWS Console: Use the templates as a reference to create resources manually"
                ]
            }
        }
    
    # Step 2: Create ECR infrastructure
    ecr_result = await create_ecr_infrastructure(
        app_name=app_name, 
        template_content=template_files["ecr_template_content"]
    )
    
    # Get the ECR repository URI
    ecr_repo_uri = ecr_result["resources"]["ecr_repository_uri"]
    
    # Step 3: Build and push Docker image
    try:
        from awslabs.ecs_mcp_server.utils.docker import build_and_push_image
        logger.info(f"Building and pushing Docker image for {app_name} from {app_path}")
        
        image_tag = await build_and_push_image(
            app_path=app_path, repository_uri=ecr_repo_uri
        )
        logger.info(f"Image successfully built and pushed with tag: {image_tag}")
        image_uri = ecr_repo_uri
    except Exception as e:
        logger.error(f"Error building and pushing Docker image: {e}")
        # Return partial result with just ECR info if image build fails
        return {
            "stack_name": f"{app_name}-ecr-infrastructure",
            "operation": "create",
            "template_paths": {
                "ecr_template": ecr_template_path,
                "ecs_template": ecs_template_path
            },
            "resources": {
                "ecr_repository": f"{app_name}-repo",
                "ecr_repository_uri": ecr_repo_uri,
            },
            "message": f"Created ECR repository, but Docker image build failed: {str(e)}"
        }
    
    # Step 4: Create ECS infrastructure with the image URI
    try:
        ecs_result = await create_ecs_infrastructure(
            app_name=app_name,
            image_uri=image_uri,
            image_tag=image_tag,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            route_table_ids=route_table_ids,
            cpu=cpu,
            memory=memory,
            desired_count=desired_count,
            container_port=container_port,
            health_check_path=health_check_path if health_check_path else "/",
            template_content=template_files["ecs_template_content"]
        )
    except Exception as e:
        logger.error(f"Error creating ECS infrastructure: {e}")
        # Return partial result with just ECR info if ECS creation fails
        return {
            "stack_name": f"{app_name}-ecr-infrastructure",
            "operation": "create",
            "template_paths": {
                "ecr_template": ecr_template_path,
                "ecs_template": ecs_template_path
            },
            "resources": {
                "ecr_repository": f"{app_name}-repo",
                "ecr_repository_uri": ecr_repo_uri,
            },
            "message": f"Created ECR repository, but ECS infrastructure creation failed: {str(e)}"
        }
    
    # Combine results
    combined_result = {
        "stack_name": ecs_result.get("stack_name", f"{app_name}-ecs-infrastructure"),
        "stack_id": ecs_result.get("stack_id"),
        "operation": ecs_result.get("operation", "create"),
        "template_paths": {
            "ecr_template": ecr_template_path,
            "ecs_template": ecs_template_path
        },
        "vpc_id": ecs_result.get("vpc_id", vpc_id),
        "subnet_ids": ecs_result.get("subnet_ids", subnet_ids),
        "resources": {
            **(ecs_result.get("resources", {})),
            "ecr_repository": ecr_result["resources"]["ecr_repository"],
            "ecr_repository_uri": ecr_repo_uri,
        },
        "image_uri": image_uri
    }
    
    return combined_result

async def create_ecr_infrastructure(
    app_name: str,
    template_content: str,
) -> Dict[str, Any]:
    """
    Creates ECR repository infrastructure using CloudFormation.

    Args:
        app_name: Name of the application
        template_content: Content of the template file

    Returns:
        Dict containing infrastructure creation results
    """
    logger.info(f"Creating ECR infrastructure for {app_name}")

    # Get AWS account ID
    account_id = await get_aws_account_id()

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
        try:
            response = cloudformation.update_stack(
                StackName=stack_name,
                TemplateBody=template_content,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {"ParameterKey": "AppName", "ParameterValue": app_name},
                ],
            )
            operation = "update"
            logger.info(f"Updating existing ECR repository stack {stack_name}...")
        except cloudformation.exceptions.ClientError as e:
            # Check if the error is "No updates are to be performed"
            if "No updates are to be performed" in str(e):
                logger.info(f"No updates needed for ECR repository stack {stack_name}")
                operation = "no_update_required"
                
                # Get the existing stack details
                response = cloudformation.describe_stacks(StackName=stack_name)
            else:
                # Re-raise if it's a different error
                raise
    else:
        # Create new stack
        response = cloudformation.create_stack(
            StackName=stack_name,
            TemplateBody=template_content,
            Capabilities=["CAPABILITY_NAMED_IAM"],
            Parameters=[
                {"ParameterKey": "AppName", "ParameterValue": app_name},
            ],
        )
        operation = "create"

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
        "resources": {
            "ecr_repository": f"{app_name}-repo",
            "ecr_repository_uri": ecr_repo_uri,
        },
    }


async def create_ecs_infrastructure(
    app_name: str,
    template_content: str,
    image_uri: Optional[str] = None,
    image_tag: Optional[str] = None,
    vpc_id: Optional[str] = None,
    subnet_ids: Optional[List[str]] = None,
    route_table_ids: Optional[List[str]] = None,
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
        template_content: Content of the template file
        image_uri: URI of the container image
        image_tag: Tag of the container image
        vpc_id: VPC ID for deployment (optional, will create new if not provided)
        subnet_ids: List of subnet IDs for deployment (optional)
        route_table_ids: List of route table IDs for S3 Gateway endpoint association
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
        
    # Get route table IDs if not provided
    if not route_table_ids:
        from awslabs.ecs_mcp_server.utils.aws import get_route_tables_for_vpc
        route_table_ids = await get_route_tables_for_vpc(vpc_id)

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

    # Check if stack already exists
    try:
        cloudformation.describe_stacks(StackName=stack_name)
        stack_exists = True
    except cloudformation.exceptions.ClientError:
        stack_exists = False

    if stack_exists:
        # Update existing stack
        try:
            response = cloudformation.update_stack(
                StackName=stack_name,
                TemplateBody=template_content,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {"ParameterKey": "AppName", "ParameterValue": app_name},
                    {"ParameterKey": "VpcId", "ParameterValue": vpc_id},
                    {"ParameterKey": "SubnetIds", "ParameterValue": ",".join(subnet_ids)},
                    {"ParameterKey": "RouteTableIds", "ParameterValue": ",".join(route_table_ids)},
                    {"ParameterKey": "TaskCpu", "ParameterValue": str(cpu)},
                    {"ParameterKey": "TaskMemory", "ParameterValue": str(memory)},
                    {"ParameterKey": "DesiredCount", "ParameterValue": str(desired_count)},
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
) -> str:
    """Generates a CloudFormation template."""
    templates_dir = get_templates_dir()
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True
    )

    template = env.get_template(template_name)

    # Prepare template parameters
    template_params = {
        "app_name": app_name,
        "account_id": account_id,
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
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
            "cluster": f"{app_name}-cluster",
            "service": f"{app_name}-service",
            "task_definition": f"{app_name}-task",
            "load_balancer": f"{app_name}-alb",
        },
    }
