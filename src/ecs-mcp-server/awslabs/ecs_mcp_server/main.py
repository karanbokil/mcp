#!/usr/bin/env python3
"""
AWS ECS MCP Server - Main entry point
"""

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from awslabs.ecs_mcp_server.modules import (
    analyze,
    containerize,
    infrastructure,
    deployment_status,
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

4. get_deployment_status:
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


# Register all modules
analyze.register_module(mcp)
containerize.register_module(mcp)
infrastructure.register_module(mcp)
deployment_status.register_module(mcp)
resource_management.register_module(mcp)
troubleshooting.register_module(mcp)

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
