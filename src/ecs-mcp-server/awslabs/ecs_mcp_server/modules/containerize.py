"""
Containerize module for ECS MCP Server.
This module provides tools and prompts for containerizing web applications.
"""
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.containerize import containerize_app


def register_module(mcp: FastMCP) -> None:
    """Register containerize module tools and prompts with the MCP server."""
    
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
        1. Provide the path to your web application directory
        2. Optionally specify the framework, port, and environment variables
        3. The tool will generate the necessary files for containerization

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

    # Prompt patterns for containerization
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
        
    # Combined prompts
    @mcp.prompt("containerize and deploy")
    def containerize_and_deploy_prompt():
        """User wants to containerize and deploy an application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("docker and deploy")
    def docker_and_deploy_prompt():
        """User wants to containerize and deploy an application"""
        return ["containerize_app", "create_ecs_infrastructure"]
