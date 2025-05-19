"""
Infrastructure module for ECS MCP Server.
This module provides tools and prompts for creating ECS infrastructure.
"""
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.infrastructure import create_infrastructure


def register_module(mcp: FastMCP) -> None:
    """Register infrastructure module tools and prompts with the MCP server."""
    
    @mcp.tool(name="create_ecs_infrastructure")
    async def mcp_create_ecs_infrastructure(
        app_name: str = Field(
            ...,
            description="Name of the application",
        ),
        app_path: str = Field(
            ...,
            description="Path to the web application directory",
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
        the ECS cluster, task definitions, and services.

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

    # Prompt patterns for deployment
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

    @mcp.prompt("make accessible")
    def make_accessible_prompt():
        """User wants to make an application accessible online"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("ship it")
    def ship_it_prompt():
        """User wants to ship/deploy their application"""
        return ["containerize_app", "create_ecs_infrastructure"]

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
        
    @mcp.prompt("make accessible online")
    def make_accessible_online_prompt():
        """User wants to make an application accessible online"""
        return ["containerize_app", "create_ecs_infrastructure"]
