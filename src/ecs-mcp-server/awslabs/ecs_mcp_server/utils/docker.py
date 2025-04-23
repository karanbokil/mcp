"""
Docker utility functions.
"""

import logging
import os
import subprocess
from typing import Dict, Any

from awslabs.ecs_mcp_server.utils.aws import get_ecr_login_password, get_aws_account_id

logger = logging.getLogger(__name__)


async def validate_dockerfile(dockerfile_path: str) -> Dict[str, Any]:
    """
    Validates a Dockerfile using hadolint if available.

    Args:
        dockerfile_path: Path to the Dockerfile

    Returns:
        Dict containing validation results
    """
    # Check if hadolint is installed
    try:
        subprocess.run(["hadolint", "--version"], capture_output=True, check=True)
        has_hadolint = True
    except (subprocess.SubprocessError, FileNotFoundError):
        has_hadolint = False

    if not has_hadolint:
        return {
            "valid": True,
            "message": "Dockerfile validation skipped (hadolint not installed)",
            "warnings": [],
            "errors": [],
        }

    # Run hadolint
    try:
        result = subprocess.run(["hadolint", dockerfile_path], capture_output=True, text=True)

        if result.returncode == 0:
            return {
                "valid": True,
                "message": "Dockerfile validation passed",
                "warnings": [],
                "errors": [],
            }
        else:
            # Parse hadolint output
            issues = []
            for line in result.stdout.splitlines() + result.stderr.splitlines():
                if line.strip():
                    issues.append(line)

            return {
                "valid": False,
                "message": "Dockerfile validation failed",
                "warnings": [i for i in issues if "warning" in i.lower()],
                "errors": [i for i in issues if "error" in i.lower() or "warning" not in i.lower()],
            }

    except Exception as e:
        logger.error(f"Error validating Dockerfile: {e}")
        return {
            "valid": True,
            "message": f"Dockerfile validation error: {str(e)}",
            "warnings": [],
            "errors": [],
        }


async def build_and_push_image(app_path: str, repository_uri: str, tag: str = "latest") -> str:
    """
    Builds and pushes a Docker image to ECR.

    Args:
        app_path: Path to the application directory containing the Dockerfile
        repository_uri: ECR repository URI
        tag: Image tag

    Returns:
        Image tag
    """
    logger.info(f"Building and pushing Docker image to {repository_uri}:{tag}")

    # Get ECR login password
    password = await get_ecr_login_password()
    account_id = await get_aws_account_id()
    region = os.environ.get("AWS_REGION", "us-east-1")

    # Login to ECR
    login_cmd = f"docker login --username AWS --password {password} {account_id}.dkr.ecr.{region}.amazonaws.com"
    subprocess.run(login_cmd, shell=True, check=True, capture_output=True)

    # Build the image
    build_cmd = f"docker build -t {repository_uri}:{tag} {app_path}"
    subprocess.run(build_cmd, shell=True, check=True)

    # Push the image
    push_cmd = f"docker push {repository_uri}:{tag}"
    subprocess.run(push_cmd, shell=True, check=True)

    return tag
