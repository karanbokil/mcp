#!/usr/bin/env python3
"""
AWS ECS MCP Server - Main entry point
"""

import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional

from fastmcp import MCPServer
from fastmcp.models import MCPTool, MCPToolParameter, MCPPromptPattern

from awslabs.ecs_mcp_server.api.containerize import containerize_app
from awslabs.ecs_mcp_server.api.deploy import deploy_to_ecs
from awslabs.ecs_mcp_server.api.analyze import analyze_app
from awslabs.ecs_mcp_server.api.infrastructure import create_infrastructure
from awslabs.ecs_mcp_server.api.status import get_deployment_status
from awslabs.ecs_mcp_server.utils.config import get_config

# Configure logging
logging.basicConfig(
    level=os.environ.get("FASTMCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ecs-mcp-server")


def create_server() -> MCPServer:
    """Create and configure the ECS MCP Server."""
    server = MCPServer(
        name="AWS ECS MCP Server",
        description="A server for automating containerization and deployment of web applications to AWS ECS",
        version="0.1.0",
    )

    # Register prompt patterns to help AI assistants recognize when to use this server
    # These patterns are used to match against user queries
    server.register_prompt_patterns([
        # Containerization patterns
        MCPPromptPattern(
            pattern="dockerize",
            description="User wants to containerize an application",
            tools=["analyze_web_app", "containerize_app"]
        ),
        MCPPromptPattern(
            pattern="containerize",
            description="User wants to containerize an application",
            tools=["analyze_web_app", "containerize_app"]
        ),
        MCPPromptPattern(
            pattern="docker container",
            description="User wants to create a Docker container",
            tools=["analyze_web_app", "containerize_app"]
        ),
        MCPPromptPattern(
            pattern="put in container",
            description="User wants to containerize an application",
            tools=["analyze_web_app", "containerize_app"]
        ),
        
        # Deployment patterns
        MCPPromptPattern(
            pattern="deploy to aws",
            description="User wants to deploy an application to AWS",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="deploy to cloud",
            description="User wants to deploy an application to the cloud",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="deploy to ecs",
            description="User wants to deploy an application to AWS ECS",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="ship to cloud",
            description="User wants to deploy an application to the cloud",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="put on the web",
            description="User wants to make an application accessible online",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="host online",
            description="User wants to host an application online",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="make live",
            description="User wants to make an application live",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="launch online",
            description="User wants to launch an application online",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="get running on the web",
            description="User wants to make an application accessible on the web",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="make accessible online",
            description="User wants to make an application accessible online",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        
        # Framework-specific patterns
        MCPPromptPattern(
            pattern="deploy flask",
            description="User wants to deploy a Flask application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="deploy django",
            description="User wants to deploy a Django application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="deploy react",
            description="User wants to deploy a React application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="deploy express",
            description="User wants to deploy an Express.js application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="deploy node",
            description="User wants to deploy a Node.js application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        
        # Combined patterns
        MCPPromptPattern(
            pattern="containerize and deploy",
            description="User wants to containerize and deploy an application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="docker and deploy",
            description="User wants to containerize and deploy an application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        
        # Vibe coder patterns
        MCPPromptPattern(
            pattern="ship it",
            description="User wants to deploy an application",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="push to prod",
            description="User wants to deploy an application to production",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="get this online",
            description="User wants to make an application accessible online",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="make this public",
            description="User wants to make an application publicly accessible",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="put this on aws",
            description="User wants to deploy an application to AWS",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="can people access this",
            description="User wants to make an application accessible to others",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
        MCPPromptPattern(
            pattern="how do i share this app",
            description="User wants to make an application accessible to others",
            tools=["analyze_web_app", "containerize_app", "create_ecs_infrastructure", "deploy_to_ecs"]
        ),
    ])

    # Register tools
    server.register_tool(
        MCPTool(
            name="analyze_web_app",
            description="Analyzes a web application to determine containerization requirements",
            function=analyze_app,
            parameters=[
                MCPToolParameter(
                    name="app_path",
                    description="Path to the web application directory",
                    type="string",
                    required=True,
                ),
                MCPToolParameter(
                    name="framework",
                    description="Web framework used (e.g., flask, express, django, rails, etc.)",
                    type="string",
                    required=False,
                ),
            ],
        )
    )

    server.register_tool(
        MCPTool(
            name="containerize_app",
            description="Generates Dockerfile and container configurations for a web application",
            function=containerize_app,
            parameters=[
                MCPToolParameter(
                    name="app_path",
                    description="Path to the web application directory",
                    type="string",
                    required=True,
                ),
                MCPToolParameter(
                    name="framework",
                    description="Web framework used (e.g., flask, express, django, rails, etc.)",
                    type="string",
                    required=False,
                ),
                MCPToolParameter(
                    name="port",
                    description="Port the application listens on",
                    type="integer",
                    required=False,
                ),
                MCPToolParameter(
                    name="environment_vars",
                    description="Environment variables as a JSON object",
                    type="object",
                    required=False,
                ),
            ],
        )
    )

    server.register_tool(
        MCPTool(
            name="create_ecs_infrastructure",
            description="Creates ECS infrastructure using CloudFormation/CDK",
            function=create_infrastructure,
            parameters=[
                MCPToolParameter(
                    name="app_name",
                    description="Name of the application",
                    type="string",
                    required=True,
                ),
                MCPToolParameter(
                    name="vpc_id",
                    description="VPC ID for deployment (optional, will create new if not provided)",
                    type="string",
                    required=False,
                ),
                MCPToolParameter(
                    name="subnet_ids",
                    description="List of subnet IDs for deployment",
                    type="array",
                    required=False,
                ),
                MCPToolParameter(
                    name="cpu",
                    description="CPU units for the task (e.g., 256, 512, 1024)",
                    type="integer",
                    required=False,
                ),
                MCPToolParameter(
                    name="memory",
                    description="Memory (MB) for the task (e.g., 512, 1024, 2048)",
                    type="integer",
                    required=False,
                ),
                MCPToolParameter(
                    name="desired_count",
                    description="Desired number of tasks",
                    type="integer",
                    required=False,
                ),
                MCPToolParameter(
                    name="enable_auto_scaling",
                    description="Enable auto-scaling for the service",
                    type="boolean",
                    required=False,
                ),
            ],
        )
    )

    server.register_tool(
        MCPTool(
            name="deploy_to_ecs",
            description="Deploys a containerized application to AWS ECS with Fargate and ALB",
            function=deploy_to_ecs,
            parameters=[
                MCPToolParameter(
                    name="app_path",
                    description="Path to the web application directory",
                    type="string",
                    required=True,
                ),
                MCPToolParameter(
                    name="app_name",
                    description="Name of the application",
                    type="string",
                    required=True,
                ),
                MCPToolParameter(
                    name="container_port",
                    description="Port the container listens on",
                    type="integer",
                    required=True,
                ),
                MCPToolParameter(
                    name="vpc_id",
                    description="VPC ID for deployment (optional, will create new if not provided)",
                    type="string",
                    required=False,
                ),
                MCPToolParameter(
                    name="subnet_ids",
                    description="List of subnet IDs for deployment",
                    type="array",
                    required=False,
                ),
                MCPToolParameter(
                    name="cpu",
                    description="CPU units for the task (e.g., 256, 512, 1024)",
                    type="integer",
                    required=False,
                ),
                MCPToolParameter(
                    name="memory",
                    description="Memory (MB) for the task (e.g., 512, 1024, 2048)",
                    type="integer",
                    required=False,
                ),
                MCPToolParameter(
                    name="environment_vars",
                    description="Environment variables as a JSON object",
                    type="object",
                    required=False,
                ),
                MCPToolParameter(
                    name="health_check_path",
                    description="Path for ALB health checks",
                    type="string",
                    required=False,
                ),
            ],
        )
    )

    server.register_tool(
        MCPTool(
            name="get_deployment_status",
            description="Gets the status of an ECS deployment and returns the ALB URL",
            function=get_deployment_status,
            parameters=[
                MCPToolParameter(
                    name="app_name",
                    description="Name of the application",
                    type="string",
                    required=True,
                ),
                MCPToolParameter(
                    name="cluster_name",
                    description="Name of the ECS cluster",
                    type="string",
                    required=False,
                ),
            ],
        )
    )

    return server


def main() -> None:
    """Main entry point for the ECS MCP Server."""
    try:
        # Load configuration
        config = get_config()
        
        # Create and start the server
        server = create_server()
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
