"""
Analyze module for ECS MCP Server.
This module provides tools to analyze web applications for containerization.
"""
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.analyze import analyze_app


def register_module(mcp: FastMCP) -> None:
    """Register analyze module tools and prompts with the MCP server."""
    
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
