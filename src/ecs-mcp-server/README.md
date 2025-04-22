# AWS ECS MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.ecs-mcp-server.svg)](https://pypi.org/project/awslabs.ecs-mcp-server/)

A server for automating containerization and deployment of web applications to AWS ECS.

## Features

- **Automated Containerization**: Generate Dockerfiles and container configurations for common web application frameworks
- **ECS Deployment**: Deploy containerized applications to AWS ECS using Fargate
- **Load Balancer Integration**: Automatically configure Application Load Balancers (ALBs) for web traffic
- **Infrastructure as Code**: Generate and apply CloudFormation templates for ECS infrastructure
- **URL Management**: Return public ALB URLs for immediate access to deployed applications
- **Scaling Configuration**: Set up auto-scaling policies based on application requirements
- **Security Best Practices**: Implement AWS security best practices for container deployments

## Installation

```bash
# Install using uv
uv pip install awslabs.ecs-mcp-server

# Or install using pip
pip install awslabs.ecs-mcp-server
```

## Configuration

Add the ECS MCP Server to your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.ecs-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ecs-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Usage

The ECS MCP Server provides tools for AI assistants to:

1. Analyze web applications to determine containerization requirements
2. Generate appropriate Dockerfiles and container configurations
3. Create ECS task definitions and service configurations
4. Deploy applications to ECS Fargate with appropriate networking and security settings
5. Configure Application Load Balancers for public access
6. Return public URLs for accessing the deployed application

## Vibe Coder Prompts

The ECS MCP Server is designed to recognize casual, conversational deployment requests. Here are examples of "vibe coder" prompts that will trigger the server:

### Containerization Prompts
- "Dockerize this app for me"
- "Can you containerize this project?"
- "Make a Docker container for this code"
- "Turn this into a container"
- "This needs to be in Docker"
- "Help me put this in a container"

### Deployment Prompts
- "Ship this to the cloud"
- "Deploy this app to AWS"
- "Get this running on the web"
- "Make this live on the internet"
- "Push this to production"
- "Launch this app online"
- "Can you host this somewhere?"
- "Put this on the web for me"
- "Make this accessible online"

### Framework-Specific Prompts
- "Deploy this Flask app"
- "Get my React app online"
- "Host this Express API"
- "Put my Django site on the web"
- "Launch this Node.js server"

### Combined Prompts
- "Containerize and deploy this app"
- "Docker this and put it on AWS"
- "Package this up and ship it"
- "Make this run in the cloud"
- "Get this app containerized and online"

## Example Prompts

- "Deploy this Flask application to AWS ECS"
- "Containerize this Node.js app and deploy it to AWS"
- "Create an ECS deployment for this web application with auto-scaling"
- "Set up a containerized environment for this Django app on AWS ECS"

## Requirements

- Python 3.10+
- AWS credentials with permissions for ECS, ECR, CloudFormation, and related services
- Docker (for local containerization testing)

## License

This project is licensed under the Apache-2.0 License.
