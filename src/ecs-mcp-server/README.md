# AWS ECS MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.ecs-mcp-server.svg)](https://pypi.org/project/awslabs.ecs-mcp-server/)

An MCP server for providing containerization guidance, deploying web applications to AWS ECS, troubleshooting ECS deployments, and managing ECS resources. This server enables AI assistants to help users with the full lifecycle of containerized applications on AWS.

## Features

Customers can use the `containerize_app` tool to help them containerize their applications with best practices and deploy them to AWS ECS. The `create_ecs_infrastructure` tool automates infrastructure deployment using CloudFormation, while `get_deployment_status` will return the status of deployments and provide the URL of the set up Application Load Balancer.

Customers can list and view their ECS resources (clusters, services, tasks, task definitions, ECR images) using the `ecs_resource_management` tool. When running into ECS deployment issues, they can use the `ecs_troubleshooting_tool` to diagnose and resolve common problems.

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

## MCP Tools

### Deployment Tools

These tools help you containerize applications and deploy them to AWS ECS with proper infrastructure setup and monitoring.

- **containerize_app**: Generates Dockerfile and container configurations for web applications
- **create_ecs_infrastructure**: Creates ECS infrastructure using CloudFormation/CDK
- **get_deployment_status**: Gets the status of an ECS deployment and returns the ALB URL
- **delete_ecs_infrastructure**: Deletes ECS infrastructure created by the ECS MCP Server

### Troubleshooting Tool

The troubleshooting tool helps diagnose and resolve common ECS deployment issues at various levels: infrastructure, service, task, and network configuration.

- **ecs_troubleshooting_tool**: Consolidated tool with the following actions:
  - **get_ecs_troubleshooting_guidance**: Initial assessment and troubleshooting path recommendation
  - **fetch_cloudformation_status**: Infrastructure-level diagnostics for CloudFormation stacks
  - **fetch_service_events**: Service-level diagnostics for ECS services
  - **fetch_task_failures**: Task-level diagnostics for ECS task failures
  - **fetch_task_logs**: Application-level diagnostics through CloudWatch logs
  - **detect_image_pull_failures**: Specialized tool for detecting container image pull failures
  - **analyze_network_configuration**: Network-level diagnostics for ECS services

### Resource Management

This tool provides read-only access to AWS ECS resources to help you monitor and understand your deployment environment.

- **ecs_resource_management**: List and describe ECS resources including:
  - **Clusters**: List all clusters, describe specific cluster details
  - **Services**: List services in a cluster, describe service configuration
  - **Tasks**: List running or stopped tasks, describe task details and status
  - **Task Definitions**: List task definition families, describe specific task definition revisions
  - **Container Instances**: List container instances, describe instance health and capacity
  - **Capacity Providers**: List and describe capacity providers associated with clusters

## Example Prompts

### Containerization and Deployment

- "Containerize this Node.js app and deploy it to AWS"
- "Deploy this Flask application to AWS ECS"
- "Create an ECS deployment for this web application with auto-scaling"

### Troubleshooting

- "Help me troubleshoot my ECS deployment"
- "My ECS tasks keep failing, can you diagnose the issue?"
- "The ALB health check is failing for my ECS service"
- "Why can't I access my deployed application?"
- "Check what's wrong with my CloudFormation stack"

### Resource Management

- "Show me my ECS clusters"
- "List all running tasks in my ECS cluster"
- "Describe my ECS service configuration"
- "Get information about my task definition"

## Requirements

- Python 3.10+
- AWS credentials with permissions for ECS, ECR, CloudFormation, and related services
- Docker (for local containerization testing)

## License

This project is licensed under the Apache-2.0 License.