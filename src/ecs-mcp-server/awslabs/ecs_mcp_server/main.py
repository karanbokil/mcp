#!/usr/bin/env python3
"""
AWS ECS MCP Server - Main entry point
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.containerize import containerize_app
from awslabs.ecs_mcp_server.api.infrastructure import create_infrastructure
from awslabs.ecs_mcp_server.api.resource_management import ecs_resource_management
from awslabs.ecs_mcp_server.api.status import get_deployment_status
from awslabs.ecs_mcp_server.api.delete import delete_infrastructure
from awslabs.ecs_mcp_server.utils.config import get_config

# Configure logging
logging.basicConfig(
    level=os.environ.get("FASTMCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ecs-mcp-server")

# Create the MCP server
mcp = FastMCP(
    name="AWS ECS MCP Server",
    description="A server for automating containerization and deployment of web applications to AWS ECS",
    version="0.1.0",
    instructions="""Use this server to containerize and deploy web applications to AWS ECS.

WORKFLOW:
1. containerize_app:
   - Get guidance on how to containerize your web application
   - Learn best practices for Dockerfile creation
   - Get recommendations for container tools and architecture

2. create_ecs_infrastructure:
   - Create the necessary AWS infrastructure for ECS deployment
   - Set up VPC, subnets, security groups, and IAM roles
   - Configure ECS cluster, task definitions, and services

3. get_deployment_status:
   - Check the status of your ECS deployment
   - Get the ALB URL to access your application
   - Monitor the health of your ECS service

IMPORTANT:
- Make sure your application has a clear entry point
- Ensure all dependencies are properly defined in requirements.txt, package.json, etc.
- For containerization, your application should listen on a configurable port
- AWS credentials must be properly configured with appropriate permissions
""",
)


# Register tools with decorators
@mcp.tool(name="containerize_app")
async def mcp_containerize_app(
    app_path: str = Field(
        ...,
        description="Absolute file path to the web application directory",
    ),
    port: int = Field(
        ...,
        description="Port the application listens on",
    )
) -> Dict[str, Any]:
    """
    Start here if a user wants to run their application locally or deploy an app to the cloud.
    Provides guidance for containerizing a web application.

    This tool provides guidance on how to build Docker images for web applications,
    including recommendations for base images, build tools, and architecture choices.

    USAGE INSTRUCTIONS:
    1. Run this tool to get guidance on how to configure your application for ECS.
    2. Follow the steps generated from the tool.
    3. Proceed to create_ecs_infrastructure tool.

    The guidance includes:
    - Example Dockerfile content
    - Example docker-compose.yml content
    - Build commands for different container tools
    - Architecture recommendations
    - Troubleshooting tips

    Parameters:
        app_path: Path to the web application directory
        port: Port the application listens on

    Returns:
        Dictionary containing containerization guidance
    """
    return await containerize_app(app_path, port)


@mcp.tool(name="create_ecs_infrastructure")
async def mcp_create_ecs_infrastructure(
    app_name: str = Field(
        ...,
        description="Name of the application",
    ),
    app_path: str = Field(
        ...,
        description="Absolute file path to the web application directory",
    ),
    force_deploy: bool = Field(
        default=False,
        description="Set to True ONLY if you have Docker installed and running, and you agree to let the server build and deploy your image to ECR, as well as deploy ECS infrastructure for you in CloudFormation. If False, template files will be generated locally for your review.",
    ),
    vpc_id: Optional[str] = Field(
        default=None,
        description="VPC ID for deployment (optional, will use default if not provided)",
    ),
    subnet_ids: Optional[List[str]] = Field(
        default=None,
        description="List of subnet IDs for deployment, will use from default VPC if not provided",
    ),
    route_table_ids: Optional[List[str]] = Field(
        default=None,
        description="List of route table IDs for S3 Gateway endpoint association, will use main route table if not provided",
    ),
    cpu: Optional[int] = Field(
        default=None,
        description="CPU units for the task (e.g., 256, 512, 1024)",
    ),
    memory: Optional[int] = Field(
        default=None,
        description="Memory (MB) for the task (e.g., 512, 1024, 2048)",
    ),
    desired_count: Optional[int] = Field(
        default=None,
        description="Desired number of tasks",
    ),
    container_port: Optional[int] = Field(
        default=None,
        description="Port the container listens on",
    ),
    health_check_path: Optional[str] = Field(
        default=None,
        description="Path for ALB health checks",
    ),
) -> Dict[str, Any]:
    """
    Creates ECS infrastructure using CloudFormation.

    This tool sets up the necessary AWS infrastructure for deploying applications to ECS.
    It creates or uses an existing VPC, sets up security groups, IAM roles, and configures
    the ECS cluster, task definitions, and services. Deployment is asynchronous, poll the
    get_deployment_status tool every 30 seconds after successful invocation of this.

    USAGE INSTRUCTIONS:
    1. Provide a name for your application
    2. Provide the path to your web application directory
    3. Decide whether to use force_deploy:
       - If False (default): Template files will be generated locally for your review
       - If True: Docker image will be built and pushed to ECR, and CloudFormation stacks will be deployed
       - ENSURE you get user permission to deploy and inform that this is only for non-production applications.
    4. Optionally specify VPC and subnet IDs if you want to use existing resources
    5. Configure CPU, memory, and scaling options as needed

    The created infrastructure includes:
    - Security groups
    - IAM roles and policies
    - ECS cluster
    - Task definition template
    - Service configuration
    - Application Load Balancer

    Parameters:
        app_name: Name of the application
        app_path: Path to the web application directory
        force_deploy: Whether to build and deploy the infrastructure or just generate templates
        vpc_id: VPC ID for deployment
        subnet_ids: List of subnet IDs for deployment
        route_table_ids: List of route table IDs for S3 Gateway endpoint association
        cpu: CPU units for the task (e.g., 256, 512, 1024)
        memory: Memory (MB) for the task (e.g., 512, 1024, 2048)
        desired_count: Desired number of tasks
        container_port: Port the container listens on
        health_check_path: Path for ALB health checks

    Returns:
        Dictionary containing infrastructure details or template paths
    """
    return await create_infrastructure(
        app_name=app_name,
        app_path=app_path,
        force_deploy=force_deploy,
        vpc_id=vpc_id, 
        subnet_ids=subnet_ids,
        route_table_ids=route_table_ids,
        cpu=cpu, 
        memory=memory, 
        desired_count=desired_count, 
        container_port=container_port,
        health_check_path=health_check_path
    )


@mcp.tool(name="get_deployment_status")
async def mcp_get_deployment_status(
    app_name: str = Field(
        ...,
        description="Name of the application",
    ),
    cluster_name: Optional[str] = Field(
        default=None,
        description="Name of the ECS cluster",
    ),
) -> Dict[str, Any]:
    """
    Gets the status of an ECS deployment and returns the ALB URL.

    This tool checks the status of your ECS deployment and provides information
    about the service, tasks, and the Application Load Balancer URL for accessing
    your application.

    USAGE INSTRUCTIONS:
    1. Provide the name of your application
    2. Optionally specify the cluster name if different from the application name
    3. The tool will return the deployment status and access URL once the deployment is complete.

    Poll this tool every 30 seconds till the status is active.

    The status information includes:
    - Service status (active, draining, etc.)
    - Running task count
    - Desired task count
    - Application Load Balancer URL
    - Recent deployment events
    - Health check status
    - Custom domain and HTTPS setup guidance (when deployment is complete)

    Parameters:
        app_name: Name of the application
        cluster_name: Name of the ECS cluster (optional, defaults to app_name)

    Returns:
        Dictionary containing deployment status and ALB URL
    """
    return await get_deployment_status(app_name, cluster_name)


@mcp.tool(name="delete_ecs_infrastructure")
async def mcp_delete_ecs_infrastructure(
    app_name: str = Field(
        ...,
        description="Name of the application",
    ),
    ecr_template_path: str = Field(
        ...,
        description="Path to the ECR CloudFormation template file",
    ),
    ecs_template_path: str = Field(
        ...,
        description="Path to the ECS CloudFormation template file",
    ),
) -> Dict[str, Any]:
    """
    Deletes ECS infrastructure created by the ECS MCP Server.
    
    WARNING: This tool is not intended for production usage and is best suited for
    tearing down prototyped work done with the ECS MCP Server.
    
    This tool attempts to identify and delete CloudFormation stacks based on the
    provided app name and template files. It will scan the user's CloudFormation stacks,
    using the app name as a heuristic, and identify if the templates match the files
    provided in the input. It will only attempt to delete stacks if they are found and
    match the provided templates.
    
    USAGE INSTRUCTIONS:
    1. Provide the name of your application
    2. Provide paths to the ECR and ECS CloudFormation template files
       - Templates will be compared to ensure they match the deployed stacks
    3. The tool will attempt to delete the stacks in the correct order (ECS first, then ECR)
    
    IMPORTANT:
    - This is a best-effort deletion
    - If a stack is in a transitional state (e.g., CREATE_IN_PROGRESS), it will be skipped
    - You may need to manually delete resources if the deletion fails
    
    Parameters:
        app_name: Name of the application
        ecr_template_path: Path to the ECR CloudFormation template file
        ecs_template_path: Path to the ECS CloudFormation template file
        
    Returns:
        Dictionary containing deletion results and guidance
    """
    return await delete_infrastructure(
        app_name=app_name,
        ecr_template_path=ecr_template_path,
        ecs_template_path=ecs_template_path,
    )


# New unified ECS resource management tool
@mcp.tool(name="ecs_resource_management")
async def mcp_ecs_resource_management(
    action: str = Field(
        ...,
        description="Action to perform (list, describe)",
    ),
    resource_type: str = Field(
        ...,
        description="Type of resource (cluster, service, task, task_definition, container_instance, capacity_provider)",
    ),
    identifier: Optional[str] = Field(
        default=None,
        description="Resource identifier (name or ARN) for describe actions",
    ),
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filters for list operations (e.g., {\"cluster\": \"my-cluster\", \"status\": \"RUNNING\"})",
    ),
) -> Dict[str, Any]:
    """
    Read-only tool for managing ECS resources.
    
    This tool provides a consistent interface to list and describe various ECS resources.
    
    USAGE EXAMPLES:
    - List all clusters: ecs_resource_management("list", "cluster")
    - Describe a cluster: ecs_resource_management("describe", "cluster", "my-cluster")
    - List services in cluster: ecs_resource_management("list", "service", filters={"cluster": "my-cluster"})
    - List tasks by status: ecs_resource_management("list", "task", filters={"cluster": "my-cluster", "status": "RUNNING"})
    - Describe a task: ecs_resource_management("describe", "task", "task-id", filters={"cluster": "my-cluster"})
    - List task definitions: ecs_resource_management("list", "task_definition", filters={"family": "nginx"})
    - Describe a task definition: ecs_resource_management("describe", "task_definition", "family:revision")
    
    Parameters:
        action: Action to perform (list, describe)
        resource_type: Type of resource (cluster, service, task, task_definition, container_instance, capacity_provider)
        identifier: Resource identifier (name or ARN) for describe actions (optional)
        filters: Filters for list operations (optional)
        
    Returns:
        Dictionary containing the requested ECS resources
    """
    return await ecs_resource_management(action, resource_type, identifier, filters)


# ECS resource management prompt patterns
@mcp.prompt("list ecs resources")
def list_ecs_resources_prompt():
    """User wants to list ECS resources"""
    return ["ecs_resource_management"]

@mcp.prompt("show ecs clusters")
def show_ecs_clusters_prompt():
    """User wants to see ECS clusters"""
    return ["ecs_resource_management"]

@mcp.prompt("describe ecs service")
def describe_ecs_service_prompt():
    """User wants to describe an ECS service"""
    return ["ecs_resource_management"]

@mcp.prompt("view ecs tasks")
def view_ecs_tasks_prompt():
    """User wants to view ECS tasks"""
    return ["ecs_resource_management"]

@mcp.prompt("check task definitions")
def check_task_definitions_prompt():
    """User wants to check ECS task definitions"""
    return ["ecs_resource_management"]

@mcp.prompt("show running containers")
def show_running_containers_prompt():
    """User wants to see running containers in ECS"""
    return ["ecs_resource_management"]

@mcp.prompt("view ecs resources")
def view_ecs_resources_prompt():
    """User wants to view ECS resources"""
    return ["ecs_resource_management"]

@mcp.prompt("inspect ecs")
def inspect_ecs_prompt():
    """User wants to inspect ECS resources"""
    return ["ecs_resource_management"]

@mcp.prompt("check ecs status")
def check_ecs_status_prompt():
    """User wants to check ECS status"""
    return ["ecs_resource_management"]


# Register prompt patterns
@mcp.prompt("dockerize")
def dockerize_prompt():
    """User wants to containerize an application"""
    return ["containerize_app"]


@mcp.prompt("containerize")
def containerize_prompt():
    """User wants to containerize an application"""
    return ["containerize_app"]


@mcp.prompt("docker container")
def docker_container_prompt():
    """User wants to create a Docker container"""
    return ["containerize_app"]


@mcp.prompt("put in container")
def put_in_container_prompt():
    """User wants to containerize an application"""
    return ["containerize_app"]


@mcp.prompt("deploy to aws")
def deploy_to_aws_prompt():
    """User wants to deploy an application to AWS"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy to cloud")
def deploy_to_cloud_prompt():
    """User wants to deploy an application to the cloud"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy to ecs")
def deploy_to_ecs_prompt():
    """User wants to deploy an application to AWS ECS"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("ship to cloud")
def ship_to_cloud_prompt():
    """User wants to deploy an application to the cloud"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("put on the web")
def put_on_web_prompt():
    """User wants to make an application accessible online"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("host online")
def host_online_prompt():
    """User wants to host an application online"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("make live")
def make_live_prompt():
    """User wants to make an application live"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("launch online")
def launch_online_prompt():
    """User wants to launch an application online"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("get running on the web")
def get_running_on_web_prompt():
    """User wants to make an application accessible on the web"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("make accessible online")
def make_accessible_online_prompt():
    """User wants to make an application accessible online"""
    return ["containerize_app", "create_ecs_infrastructure"]


# Framework-specific prompts
@mcp.prompt("deploy flask")
def deploy_flask_prompt():
    """User wants to deploy a Flask application"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy django")
def deploy_django_prompt():
    """User wants to deploy a Django application"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy react")
def deploy_react_prompt():
    """User wants to deploy a React application"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy express")
def deploy_express_prompt():
    """User wants to deploy an Express.js application"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy node")
def deploy_node_prompt():
    """User wants to deploy a Node.js application"""
    return ["containerize_app", "create_ecs_infrastructure"]


# Combined prompts
@mcp.prompt("containerize and deploy")
def containerize_and_deploy_prompt():
    """User wants to containerize and deploy an application"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("docker and deploy")
def docker_and_deploy_prompt():
    """User wants to containerize and deploy an application"""
    return ["containerize_app", "create_ecs_infrastructure"]


# Vibe coder prompts
@mcp.prompt("ship it")
def ship_it_prompt():
    """User wants to deploy an application"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("push to prod")
def push_to_prod_prompt():
    """User wants to deploy an application to production"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("get this online")
def get_this_online_prompt():
    """User wants to make an application accessible online"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("make this public")
def make_this_public_prompt():
    """User wants to make an application publicly accessible"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("delete infrastructure")
def delete_infrastructure_prompt():
    """User wants to delete an application infrastructure"""
    return ["delete_ecs_infrastructure"]


@mcp.prompt("tear down")
def tear_down_prompt():
    """User wants to tear down infrastructure"""
    return ["delete_ecs_infrastructure"]


@mcp.prompt("remove deployment")
def remove_deployment_prompt():
    """User wants to remove a deployment"""
    return ["delete_ecs_infrastructure"]


@mcp.prompt("clean up resources")
def clean_up_resources_prompt():
    """User wants to clean up resources"""
    return ["delete_ecs_infrastructure"]

@mcp.prompt("put this on aws")
def put_this_on_aws_prompt():
    """User wants to deploy an application to AWS"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("can people access this")
def can_people_access_this_prompt():
    """User wants to make an application accessible to others"""
    return ["containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("how do i share this app")
def how_do_i_share_this_app_prompt():
    """User wants to make an application accessible to others"""
    return ["containerize_app", "create_ecs_infrastructure"]


def main() -> None:
    """Main entry point for the ECS MCP Server."""
    try:
        # Load configuration
        config = get_config()

        # Start the server
        logger.info("Server started")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
