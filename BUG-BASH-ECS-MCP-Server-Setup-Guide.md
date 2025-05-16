# ECS MCP Server Setup Guide

This guide provides step-by-step instructions for bug bash testers to download, set up, and integrate the ECS MCP server from the `feature/ecs-mcp-server` branch.

## Prerequisites

- Git installed
- Python 3.9 or higher
- AWS CLI configured with appropriate credentials
- VSCode with Cline, Amazon Q, or Cursor extension installed

## 1. Download the Repository

```bash
# Clone the specific branch of the repository
git clone -b feature/ecs-mcp-server https://github.com/karanbokil/mcp.git ecs-mcp-server
cd ecs-mcp-server
```

## 2. Set Up Python Environment

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
cd src/ecs-mcp-server
pip install -e .
```

## 3. Create the Server Script

Create a file named `run_ecs_mcp_server.sh` in the root directory with the following content:

```bash
#!/bin/bash

# Set environment variables
export HOME="$HOME"  # Use your home directory
export AWS_PROFILE="default"  # Change if using a different AWS profile
export AWS_REGION="us-west-2"  # Change to your preferred AWS region
export FASTMCP_LOG_LEVEL="ERROR"  # Set to DEBUG for more verbose logging
export PYTHONPATH="$PWD/src/ecs-mcp-server"  # Adjust if your directory structure differs

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
fi

# Run the server: redirect stderr to log file but keep stdout clean for JSON-RPC messages
cd $PWD/src/ecs-mcp-server
python -m awslabs.ecs_mcp_server.main 2> /tmp/ecs-mcp-server.log
```

Make the script executable:

```bash
chmod +x run_ecs_mcp_server.sh
```

## 4. Configure AWS Credentials

Ensure your AWS credentials are properly configured:

```bash
aws configure
```

Enter your AWS Access Key ID, Secret Access Key, default region (e.g., us-west-2), and preferred output format (e.g., json).

## 5. Integrate with Cline Extension

### For Cline

1. Open VS Code with the Cline extension installed
2. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux) to open the command palette
3. Search for "Cline: Configure MCP Servers"
4. Add a new server:
```
"awslabs.ecs-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "{PATH_TO_DIRECTORY}/run_ecs_mcp_server.sh",
      "args": [],
      "env": {
        "HOME": "{PATH TO HOME}",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "PYTHONPATH": "{PATH_TO_DIRECTORY}/mcp/src/ecs-mcp-server"
      },
      "transportType": "stdio"
    }
```
### For Amazon Q

1. Open VS Code with the Amazon Q extension installed
2. Navigate to Amazon Q settings
3. Look for the MCP servers configuration section
4. Add a new server with the same details as above

### For Cursor

1. Open Cursor
2. Go to Settings
3. Find the MCP configuration section
4. Add a new server with the same details as above

## 6. Testing the Setup

1. Start a chat with Cline/Amazon Q/Cursor
2. Verify that the ECS MCP server is connected by asking for available tools:
   ```
   What tools are available from the ECS MCP server?
   ```

## 7. Troubleshooting

- If the server fails to start, check the log file at `/tmp/ecs-mcp-server.log`
- Ensure AWS credentials are correctly configured and have appropriate permissions
- Make sure all environment variables are set correctly
- Verify that Python dependencies are installed properly

For additional issues, please report them to the repository owner.
