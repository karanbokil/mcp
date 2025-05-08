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
- **Resource Management**: List and explore ECS resources such as task definitions, services, clusters, and tasks
- **ECR Integration**: View repositories and container images in Amazon ECR


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
3. Create ECS infrastructure including task definitions, service configurations, and load balancers
4. Return public URLs for accessing the deployed application
7. List and inspect ECS resources across your AWS environment
8. Explore ECR repositories and container images

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
