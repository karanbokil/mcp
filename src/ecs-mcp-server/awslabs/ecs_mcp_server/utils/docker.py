"""
Docker utility functions.
"""

import json
import logging
import os
import subprocess
from typing import Any, Dict

from awslabs.ecs_mcp_server.utils.aws import get_aws_account_id, get_ecr_login_password

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

    try:
        # Get ECR login password and account info
        account_id = await get_aws_account_id()
        region = os.environ.get("AWS_REGION", "us-east-1")
        profile = os.environ.get("AWS_PROFILE", "default")
        
        logger.info(f"Using AWS profile: {profile} and region: {region}")
        logger.info(f"Using AWS account ID: {account_id}")
        logger.info(f"Application path: {app_path}")
        
        # Verify Dockerfile exists
        dockerfile_path = os.path.join(app_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            raise FileNotFoundError(f"Dockerfile not found at {dockerfile_path}")
        
        # Login to ECR - simplified command that works more reliably
        logger.info("Logging in to ECR...")
        login_cmd = f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com"
        login_result = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
        
        if login_result.returncode != 0:
            logger.error(f"ECR login failed: {login_result.stderr}")
            raise RuntimeError(f"Failed to login to ECR: {login_result.stderr}")
        logger.info("Successfully logged in to ECR")

        # Build the image with platform specification for AMD64 (x86_64)
        # This ensures compatibility with ECS which runs on x86_64 architecture
        logger.info(f"Building Docker image at {app_path} for linux/amd64 platform...")
        
        # Try buildx first which allows platform specification
        build_cmd = f"docker buildx build --platform linux/amd64 -t {repository_uri}:{tag} {app_path} --load"
        try:
            logger.info(f"Attempting buildx command: {build_cmd}")
            build_result = subprocess.run(build_cmd, shell=True, capture_output=True, text=True)
            if build_result.returncode != 0:
                logger.warning(f"Docker buildx failed: {build_result.stderr}")
                raise subprocess.CalledProcessError(build_result.returncode, build_cmd)
        except subprocess.CalledProcessError:
            # Fallback to regular build with platform args if buildx fails
            logger.warning("Docker buildx failed, trying alternative approach")
            build_cmd = f"docker build --platform linux/amd64 -t {repository_uri}:{tag} {app_path}"
            logger.info(f"Attempting alternative build command: {build_cmd}")
            build_result = subprocess.run(build_cmd, shell=True, capture_output=True, text=True)
            
            if build_result.returncode != 0:
                logger.error(f"Docker build failed: {build_result.stderr}")
                raise RuntimeError(f"Failed to build Docker image: {build_result.stderr}")
        
        logger.info("Docker image built successfully")
        logger.info(f"Build output: {build_result.stdout}")

        # Push the image
        logger.info(f"Pushing Docker image to {repository_uri}:{tag}...")
        push_cmd = f"docker push {repository_uri}:{tag}"
        push_result = subprocess.run(push_cmd, shell=True, capture_output=True, text=True)
        
        if push_result.returncode != 0:
            logger.error(f"Docker push failed: {push_result.stderr}")
            raise RuntimeError(f"Failed to push Docker image: {push_result.stderr}")
        
        logger.info("Docker image pushed successfully")
        logger.info(f"Push output: {push_result.stdout}")
        
        # Verify the image was pushed by listing images in the repository
        repo_name = repository_uri.split('/')[-1]
        logger.info(f"Verifying image in repository: {repo_name}")
        verify_cmd = f"aws ecr list-images --repository-name {repo_name} --region {region}"
        verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
        
        if verify_result.returncode != 0:
            logger.warning(f"Could not verify image push: {verify_result.stderr}")
        else:
            logger.info(f"Image verification result: {verify_result.stdout}")
            if "imageTag" not in verify_result.stdout:
                logger.warning(f"Image tag {tag} not found in repository. Push may have failed silently.")
                raise RuntimeError(f"Image tag {tag} not found in repository after push operation")

        return tag
        
    except Exception as e:
        logger.error(f"Error in build_and_push_image: {str(e)}", exc_info=True)
        raise
