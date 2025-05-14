#!/usr/bin/env python3
"""
AWS ECS MCP Server - Main entry point
"""

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from awslabs.ecs_mcp_server.modules import (
    containerize,
    infrastructure,
    deployment_status,
    delete,
    resource_management,
    troubleshooting
)
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
@mcp.tool(name="analyze_web_app")
async def mcp_analyze_web_app(
    app_path: str = Field(
        ...,
        description="Path to the web application directory",
    ),
    framework: Optional[str] = Field(
        default=None,
        description="Web framework used (e.g., flask, express, django, rails, etc.)",
    ),
) -> Dict[str, Any]:
    """
    Analyzes a web application to determine containerization requirements.

    This tool examines your web application directory to identify the framework,
    dependencies, and runtime requirements needed for containerization. It provides
    recommendations for creating a Docker container for your application.

    USAGE INSTRUCTIONS:
    1. Provide the path to your web application directory
    2. Optionally specify the framework if you want to override auto-detection
    3. The tool will analyze your application and return detailed information

    The analysis includes:
    - Framework detection (Flask, Django, Express, etc.)
    - Dependency identification
    - Default port determination
    - Container requirements (base image, exposed ports)
    - Environment variable detection
    - Build steps for containerization
    - Runtime requirements (memory, CPU)

    Parameters:
        app_path: Path to the web application directory
        framework: Web framework used (optional, will be auto-detected if not provided)

    Returns:
        Dictionary containing analysis results
    """
    return await analyze_app(app_path, framework)


@mcp.tool(name="containerize_app")
async def mcp_containerize_app(
    app_path: str = Field(
        ...,
        description="Absolute file path to the web application directory",
    ),
    framework: Optional[str] = Field(
        default=None,
        description="Web framework used (e.g., flask, express, django, rails, etc.)",
    ),
    port: Optional[int] = Field(
        default=None,
        description="Port the application listens on",
    ),
    environment_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables as a JSON object",
    ),
) -> Dict[str, Any]:
    """
    Generates Dockerfile and container configurations for a web application.

    This tool creates a Dockerfile and docker-compose.yml file for your web application
    based on the framework and requirements. It uses best practices for containerizing
    different types of web applications.

    USAGE INSTRUCTIONS:
    1. First use analyze_web_app to understand your application's requirements
    2. Provide the path to your web application directory
    3. Optionally specify the framework, port, and environment variables
    4. The tool will generate the necessary files for containerization

    The generated files include:
    - Dockerfile: Instructions for building a container image
    - docker-compose.yml: Configuration for local testing

    The tool also validates the generated Dockerfile to ensure it follows best practices.

    Parameters:
        app_path: Path to the web application directory
        framework: Web framework used (optional, will be auto-detected if not provided)
        port: Port the application listens on (optional)
        environment_vars: Environment variables as a JSON object (optional)

    Returns:
        Dictionary containing containerization results
    """
    return await containerize_app(app_path, framework, port, environment_vars)


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
    vpc_id: Optional[str] = Field(
        default=None,
        description="VPC ID for deployment (optional, will create new if not provided)",
    ),
    subnet_ids: Optional[List[str]] = Field(
        default=None,
        description="List of subnet IDs for deployment",
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
    enable_auto_scaling: Optional[bool] = Field(
        default=None,
        description="Enable auto-scaling for the service",
    ),
    container_port: Optional[int] = Field(
        default=None,
        description="Port the container listens on",
    ),
    environment_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables as a JSON object",
    ),
    health_check_path: Optional[str] = Field(
        default=None,
        description="Path for ALB health checks",
    ),
) -> Dict[str, Any]:
    """
    Creates ECS infrastructure using CloudFormation/CDK.

    This tool sets up the necessary AWS infrastructure for deploying applications to ECS.
    It creates or uses an existing VPC, sets up security groups, IAM roles, and configures
    the ECS cluster, task definitions, and services. Deployment is asynchronous, poll the
    get_deployment_status tool every 30 seconds after successful invocation of this.

    USAGE INSTRUCTIONS:
    1. Provide a name for your application
    2. Provide the path to your web application directory
    3. Optionally specify VPC and subnet IDs if you want to use existing resources
    4. Configure CPU, memory, and scaling options as needed
    5. The tool will create the infrastructure and return the details

    The created infrastructure includes:
    - VPC and subnets (if not provided)
    - Security groups
    - IAM roles and policies
    - ECS cluster
    - Task definition template
    - Service configuration
    - Application Load Balancer

    Parameters:
        app_name: Name of the application
        app_path: Path to the web application directory
        vpc_id: VPC ID for deployment (optional, will create new if not provided)
        subnet_ids: List of subnet IDs for deployment
        cpu: CPU units for the task (e.g., 256, 512, 1024)
        memory: Memory (MB) for the task (e.g., 512, 1024, 2048)
        desired_count: Desired number of tasks
        enable_auto_scaling: Enable auto-scaling for the service
        container_port: Port the container listens on
        environment_vars: Environment variables as a JSON object
        health_check_path: Path for ALB health checks

    Returns:
        Dictionary containing infrastructure details
    """
    return await create_infrastructure(
        app_name=app_name,
        app_path=app_path,
        vpc_id=vpc_id, 
        subnet_ids=subnet_ids, 
        cpu=cpu, 
        memory=memory, 
        desired_count=desired_count, 
        enable_auto_scaling=enable_auto_scaling,
        container_port=container_port,
        environment_vars=environment_vars,
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

    Parameters:
        app_name: Name of the application
        cluster_name: Name of the ECS cluster (optional, defaults to app_name)

    Returns:
        Dictionary containing deployment status and ALB URL
    """
    return await get_deployment_status(app_name, cluster_name)


# Register prompt patterns
@mcp.prompt("dockerize")
def dockerize_prompt():
    """User wants to containerize an application"""
    return ["analyze_web_app", "containerize_app"]


@mcp.prompt("containerize")
def containerize_prompt():
    """User wants to containerize an application"""
    return ["analyze_web_app", "containerize_app"]


@mcp.prompt("docker container")
def docker_container_prompt():
    """User wants to create a Docker container"""
    return ["analyze_web_app", "containerize_app"]


@mcp.prompt("put in container")
def put_in_container_prompt():
    """User wants to containerize an application"""
    return ["analyze_web_app", "containerize_app"]


@mcp.prompt("deploy to aws")
def deploy_to_aws_prompt():
    """User wants to deploy an application to AWS"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy to cloud")
def deploy_to_cloud_prompt():
    """User wants to deploy an application to the cloud"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy to ecs")
def deploy_to_ecs_prompt():
    """User wants to deploy an application to AWS ECS"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("ship to cloud")
def ship_to_cloud_prompt():
    """User wants to deploy an application to the cloud"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("put on the web")
def put_on_web_prompt():
    """User wants to make an application accessible online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("host online")
def host_online_prompt():
    """User wants to host an application online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("make live")
def make_live_prompt():
    """User wants to make an application live"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("launch online")
def launch_online_prompt():
    """User wants to launch an application online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("get running on the web")
def get_running_on_web_prompt():
    """User wants to make an application accessible on the web"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("make accessible online")
def make_accessible_online_prompt():
    """User wants to make an application accessible online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


# Framework-specific prompts
@mcp.prompt("deploy flask")
def deploy_flask_prompt():
    """User wants to deploy a Flask application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy django")
def deploy_django_prompt():
    """User wants to deploy a Django application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy react")
def deploy_react_prompt():
    """User wants to deploy a React application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy express")
def deploy_express_prompt():
    """User wants to deploy an Express.js application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("deploy node")
def deploy_node_prompt():
    """User wants to deploy a Node.js application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


# Combined prompts
@mcp.prompt("containerize and deploy")
def containerize_and_deploy_prompt():
    """User wants to containerize and deploy an application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("docker and deploy")
def docker_and_deploy_prompt():
    """User wants to containerize and deploy an application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


# Vibe coder prompts
@mcp.prompt("ship it")
def ship_it_prompt():
    """User wants to deploy an application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("push to prod")
def push_to_prod_prompt():
    """User wants to deploy an application to production"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("get this online")
def get_this_online_prompt():
    """User wants to make an application accessible online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("make this public")
def make_this_public_prompt():
    """User wants to make an application publicly accessible"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("put this on aws")
def put_this_on_aws_prompt():
    """User wants to deploy an application to AWS"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("can people access this")
def can_people_access_this_prompt():
    """User wants to make an application accessible to others"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


@mcp.prompt("how do i share this app")
def how_do_i_share_this_app_prompt():
    """User wants to make an application accessible to others"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure"]


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
