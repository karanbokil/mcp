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

from awslabs.ecs_mcp_server.api.analyze import analyze_app
from awslabs.ecs_mcp_server.api.containerize import containerize_app
from awslabs.ecs_mcp_server.api.deploy import deploy_to_ecs
from awslabs.ecs_mcp_server.api.infrastructure import create_infrastructure
from awslabs.ecs_mcp_server.api.resource_management import ecs_resource_management
from awslabs.ecs_mcp_server.api.status import get_deployment_status
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
1. analyze_web_app:
   - Analyze your web application to determine containerization requirements
   - Detect the framework, dependencies, and runtime requirements
   - Get recommendations for containerization

2. containerize_app:
   - Generate a Dockerfile and container configurations for your web application
   - Create a docker-compose.yml file for local testing
   - Customize port mappings and environment variables

3. create_ecs_infrastructure:
   - Create the necessary AWS infrastructure for ECS deployment
   - Set up VPC, subnets, security groups, and IAM roles
   - Configure ECS cluster, task definitions, and services

4. deploy_to_ecs:
   - Deploy your containerized application to AWS ECS
   - Set up an Application Load Balancer for routing traffic
   - Configure health checks and auto-scaling

5. get_deployment_status:
   - Check the status of your ECS deployment
   - Get the ALB URL to access your application
   - Monitor the health of your ECS service

SUPPORTED FRAMEWORKS:
- Flask: Python web framework
- Django: Python web framework
- Express: Node.js web framework
- React: JavaScript frontend framework
- Node.js: JavaScript runtime
- Rails: Ruby web framework
- Generic: Any other web application

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
        description="Path to the web application directory",
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
) -> Dict[str, Any]:
    """
    Creates ECS infrastructure using CloudFormation/CDK.

    This tool sets up the necessary AWS infrastructure for deploying applications to ECS.
    It creates or uses an existing VPC, sets up security groups, IAM roles, and configures
    the ECS cluster, task definitions, and services.

    USAGE INSTRUCTIONS:
    1. Provide a name for your application
    2. Optionally specify VPC and subnet IDs if you want to use existing resources
    3. Configure CPU, memory, and scaling options as needed
    4. The tool will create the infrastructure and return the details

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
        vpc_id: VPC ID for deployment (optional, will create new if not provided)
        subnet_ids: List of subnet IDs for deployment
        cpu: CPU units for the task (e.g., 256, 512, 1024)
        memory: Memory (MB) for the task (e.g., 512, 1024, 2048)
        desired_count: Desired number of tasks
        enable_auto_scaling: Enable auto-scaling for the service

    Returns:
        Dictionary containing infrastructure details
    """
    return await create_infrastructure(
        app_name, vpc_id, subnet_ids, cpu, memory, desired_count, enable_auto_scaling
    )


@mcp.tool(name="deploy_to_ecs")
async def mcp_deploy_to_ecs(
    app_path: str = Field(
        ...,
        description="Path to the web application directory",
    ),
    app_name: str = Field(
        ...,
        description="Name of the application",
    ),
    container_port: int = Field(
        ...,
        description="Port the container listens on",
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
    Deploys a containerized application to AWS ECS with Fargate and ALB.

    This tool takes your containerized application and deploys it to AWS ECS using
    Fargate and an Application Load Balancer. It builds the Docker image, pushes it
    to ECR, and configures the ECS service.

    USAGE INSTRUCTIONS:
    1. First use containerize_app to prepare your application for deployment
    2. Provide the path to your application directory and a name for the deployment
    3. Specify the container port and any other configuration options
    4. The tool will deploy your application and return the deployment details

    The deployment process includes:
    - Building the Docker image
    - Creating an ECR repository
    - Pushing the image to ECR
    - Creating or updating the ECS task definition
    - Deploying the ECS service with an Application Load Balancer
    - Configuring health checks and auto-scaling

    Parameters:
        app_path: Path to the web application directory
        app_name: Name of the application
        container_port: Port the container listens on
        vpc_id: VPC ID for deployment (optional, will create new if not provided)
        subnet_ids: List of subnet IDs for deployment
        cpu: CPU units for the task (e.g., 256, 512, 1024)
        memory: Memory (MB) for the task (e.g., 512, 1024, 2048)
        environment_vars: Environment variables as a JSON object
        health_check_path: Path for ALB health checks

    Returns:
        Dictionary containing deployment details
    """
    return await deploy_to_ecs(
        app_path,
        app_name,
        container_port,
        vpc_id,
        subnet_ids,
        cpu,
        memory,
        environment_vars,
        health_check_path,
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
    3. The tool will return the deployment status and access URL

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
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("deploy to cloud")
def deploy_to_cloud_prompt():
    """User wants to deploy an application to the cloud"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("deploy to ecs")
def deploy_to_ecs_prompt():
    """User wants to deploy an application to AWS ECS"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("ship to cloud")
def ship_to_cloud_prompt():
    """User wants to deploy an application to the cloud"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("put on the web")
def put_on_web_prompt():
    """User wants to make an application accessible online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("host online")
def host_online_prompt():
    """User wants to host an application online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("make live")
def make_live_prompt():
    """User wants to make an application live"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("launch online")
def launch_online_prompt():
    """User wants to launch an application online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("get running on the web")
def get_running_on_web_prompt():
    """User wants to make an application accessible on the web"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("make accessible online")
def make_accessible_online_prompt():
    """User wants to make an application accessible online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


# Framework-specific prompts
@mcp.prompt("deploy flask")
def deploy_flask_prompt():
    """User wants to deploy a Flask application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("deploy django")
def deploy_django_prompt():
    """User wants to deploy a Django application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("deploy react")
def deploy_react_prompt():
    """User wants to deploy a React application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("deploy express")
def deploy_express_prompt():
    """User wants to deploy an Express.js application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("deploy node")
def deploy_node_prompt():
    """User wants to deploy a Node.js application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


# Combined prompts
@mcp.prompt("containerize and deploy")
def containerize_and_deploy_prompt():
    """User wants to containerize and deploy an application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("docker and deploy")
def docker_and_deploy_prompt():
    """User wants to containerize and deploy an application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


# Vibe coder prompts
@mcp.prompt("ship it")
def ship_it_prompt():
    """User wants to deploy an application"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("push to prod")
def push_to_prod_prompt():
    """User wants to deploy an application to production"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("get this online")
def get_this_online_prompt():
    """User wants to make an application accessible online"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("make this public")
def make_this_public_prompt():
    """User wants to make an application publicly accessible"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("put this on aws")
def put_this_on_aws_prompt():
    """User wants to deploy an application to AWS"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("can people access this")
def can_people_access_this_prompt():
    """User wants to make an application accessible to others"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


@mcp.prompt("how do i share this app")
def how_do_i_share_this_app_prompt():
    """User wants to make an application accessible to others"""
    return ["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]


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
