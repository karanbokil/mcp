# AWS ECS MCP Server

[![PyPI version](https://img.shields.io/pypi/v/awslabs.ecs-mcp-server.svg)](https://pypi.org/project/awslabs.ecs-mcp-server/)

A server for providing containerization guidance and deploying web applications to AWS ECS.

## Features

- **Containerization Guidance**: Provides best practices and guidance for containerizing web applications
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

## MCP Tools

The ECS MCP Server provides the following tools for containerization and deployment:

### 1. containerize_app

Provides guidance for containerizing a web application.

**Parameters:**
```json
{
  "app_path": {
    "type": "string",
    "description": "Path to the web application directory",
    "required": true
  },
  "port": {
    "type": "integer",
    "description": "Port the application listens on",
    "required": true
  },
  "base_image": {
    "type": "string",
    "description": "Base Docker image to use",
    "required": true
  }
}
```

**Returns:**
- Container port
- Base image recommendation
- Comprehensive containerization guidance including:
  - Example Dockerfile content
  - Example docker-compose.yml content
  - Tool comparison (Docker vs Finch)
  - Architecture recommendations (ARM64 vs AMD64)
  - Validation guidance using Hadolint
  - Troubleshooting tips
  - Best practices

**Example:**
```python
result = await containerize_app(
    app_path="/path/to/app",
    port=8000,
    base_image="amazonlinux:2023"
)
```

### 2. create_ecs_infrastructure

Creates ECS infrastructure using CloudFormation.

**Parameters:**
```json
{
  "app_name": {
    "type": "string",
    "description": "Name of the application",
    "required": true
  },
  "app_path": {
    "type": "string",
    "description": "Path to the web application directory",
    "required": true
  },
  "force_deploy": {
    "type": "boolean",
    "description": "Set to True ONLY if you have Docker installed and running, and you agree to let the server build and deploy your image to ECR, as well as deploy ECS infrastructure for you in CloudFormation. If False, template files will be generated locally for your review.",
    "required": false,
    "default": false
  },
  "vpc_id": {
    "type": "string",
    "description": "VPC ID for deployment (optional, will create new if not provided)",
    "required": false
  },
  "subnet_ids": {
    "type": "array",
    "items": {
      "type": "string"
    },
    "description": "List of subnet IDs for deployment",
    "required": false
  },
  "cpu": {
    "type": "integer",
    "description": "CPU units for the task (e.g., 256, 512, 1024)",
    "required": false
  },
  "memory": {
    "type": "integer",
    "description": "Memory (MB) for the task (e.g., 512, 1024, 2048)",
    "required": false
  },
  "desired_count": {
    "type": "integer",
    "description": "Desired number of tasks",
    "required": false
  },
  "enable_auto_scaling": {
    "type": "boolean",
    "description": "Enable auto-scaling for the service",
    "required": false
  },
  "container_port": {
    "type": "integer",
    "description": "Port the container listens on",
    "required": false
  },
  "environment_vars": {
    "type": "object",
    "description": "Environment variables as a JSON object",
    "required": false
  },
  "health_check_path": {
    "type": "string",
    "description": "Path for ALB health checks",
    "required": false
  }
}
```

**Returns:**
- If force_deploy is False: Template files and guidance for manual deployment
- If force_deploy is True: Stack name and ID, VPC and subnet IDs, Resources (cluster, service, task definition, load balancer), ECR repository URI, Image URI

**Example:**
```python
# Generate templates only
result = await create_ecs_infrastructure(
    app_name="my-app",
    app_path="/path/to/app",
    force_deploy=False,
    memory=1024,
    cpu=512,
    health_check_path="/health/"
)

# Build, push, and deploy
result = await create_ecs_infrastructure(
    app_name="my-app",
    app_path="/path/to/app",
    force_deploy=True,
    memory=1024,
    cpu=512,
    health_check_path="/health/"
)
```

### 3. get_deployment_status

Gets the status of an ECS deployment and returns the ALB URL.

**Parameters:**
```json
{
  "app_name": {
    "type": "string",
    "description": "Name of the application",
    "required": true
  },
  "cluster_name": {
    "type": "string",
    "description": "Name of the ECS cluster (optional, defaults to app_name)",
    "required": false
  }
}
```

**Returns:**
- Service status (active, draining, etc.)
- Running task count
- Desired task count
- Application Load Balancer URL
- Recent deployment events
- Health check status

**Example:**
```python
status = await get_deployment_status(app_name="my-app")
```

## Usage

The ECS MCP Server provides tools for AI assistants to:

1. Provide guidance on containerizing web applications with best practices
2. Create ECS infrastructure including task definitions, service configurations, and load balancers
3. Return public URLs for accessing the deployed application

## Workflow

The typical workflow when using the ECS MCP Server is:

1. Use `containerize_app` to get guidance on how to containerize your application
2. Follow the guidance to create your Dockerfile and build your container image
3. Use `create_ecs_infrastructure` with `force_deploy=False` to generate CloudFormation templates
4. Review the generated templates and make any necessary adjustments
5. Either:
   - Deploy the templates manually using AWS CLI, CloudFormation console, or other IaC tools
   - Use `create_ecs_infrastructure` with `force_deploy=True` to automatically build, push, and deploy
6. Use `get_deployment_status` to monitor the deployment and get the public URL

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

## Development

This section provides guidance for developers who want to contribute to the ECS MCP Server.

### Setting Up a Development Environment

1. **Clone the Repository**

   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp
   ```

2. **Set Up a Virtual Environment**

   Using `uv` (recommended):
   ```bash
   uv venv
   source .venv/bin/activate  # On Unix/macOS
   .venv\Scripts\activate     # On Windows
   ```

   Or using standard Python tools:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Unix/macOS
   .venv\Scripts\activate     # On Windows
   ```

3. **Install Development Dependencies**

   ```bash
   cd src/ecs-mcp-server
   uv pip install -e ".[dev]"
   ```

4. **Configure AWS Credentials**

   Ensure you have AWS credentials configured with appropriate permissions:
   ```bash
   aws configure
   ```

### Running the Server Locally

To run the server locally for development:

```bash
cd src/ecs-mcp-server
python -m awslabs.ecs_mcp_server.main
```

### Testing

The ECS MCP Server uses pytest for testing. The tests are organized into unit tests and integration tests.

#### Running Unit Tests

To run all unit tests:

```bash
cd src/ecs-mcp-server
python -m pytest tests/unit
```

To run a specific test file:

```bash
python -m pytest tests/unit/test_main.py
```

To run a specific test case with verbose output:

```bash
python -m pytest tests/unit/test_main.py::TestMain::test_server_tools -v
```

#### Test Coverage

To generate a test coverage report:

```bash
# Generate coverage report
python -m pytest --cov=awslabs.ecs_mcp_server tests/
```

For a detailed HTML coverage report:

```bash
python -m pytest --cov=awslabs.ecs_mcp_server --cov-report=html tests/
```

This will create an `htmlcov` directory with an interactive HTML report that you can open in your browser.

### Code Style and Linting

The project follows PEP 8 style guidelines. To check code style:

```bash
# Run flake8
flake8 awslabs/ecs_mcp_server

# Run black in check mode
black --check awslabs/ecs_mcp_server

# Run isort in check mode
isort --check-only awslabs/ecs_mcp_server
```

To automatically format the code:

```bash
# Format with black
black awslabs/ecs_mcp_server

# Sort imports with isort
isort awslabs/ecs_mcp_server
```

### Building and Publishing

To build the package:

```bash
cd src/ecs-mcp-server
python -m build
```

The package can be published to PyPI using twine:

```bash
twine upload dist/*
```

## Requirements

- Python 3.10+
- AWS credentials with permissions for ECS, ECR, CloudFormation, and related services
- Docker (for local containerization testing)

## License

This project is licensed under the Apache-2.0 License.
