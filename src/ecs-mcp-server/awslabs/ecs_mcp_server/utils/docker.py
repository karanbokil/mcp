"""
Docker utility functions.
"""

import base64
import logging
import os
import subprocess
import time
from typing import Optional

from awslabs.ecs_mcp_server.utils.aws import get_aws_account_id, get_aws_client

logger = logging.getLogger(__name__)


async def get_ecr_login_password() -> str:
    """
    Gets the ECR login password using the AWS SDK.

    Returns:
        ECR login password
    """
    try:
        # Get ECR client
        ecr_client = await get_aws_client("ecr")

        # Get authorization token
        try:
            response = await ecr_client.get_authorization_token()

            # Extract and decode the authorization token
            auth_token = response["authorizationData"][0]["authorizationToken"]
            decoded_token = base64.b64decode(auth_token).decode("utf-8")

            # The token is in the format "AWS:password"
            username, password = decoded_token.split(":", 1)

            return password
        except Exception as e:
            logger.error(f"Error getting ECR login password: {str(e)}", exc_info=True)
            raise Exception(f"Error getting ECR login password: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting ECR login password: {str(e)}", exc_info=True)
        raise


async def build_and_push_image(
    app_path: str, repository_uri: str, tag: Optional[str] = None
) -> str:
    """
    Builds and pushes a Docker image to ECR.

    Args:
        app_path: Path to the application directory containing the Dockerfile
        repository_uri: ECR repository URI
        tag: Image tag (if None, uses epoch timestamp)

    Returns:
        Image tag
    """
    # Generate a timestamp-based tag if none provided
    if tag is None:
        tag = str(int(time.time()))

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

        # Login to ECR using AWS CLI directly instead of shell piping
        logger.info("Logging in to ECR...")

        # Get ECR password using AWS CLI
        ecr_password_cmd = ["aws", "ecr", "get-login-password", "--region", region]

        # Add profile if specified
        if profile and profile != "default":
            ecr_password_cmd.extend(["--profile", profile])

        ecr_password_result = subprocess.run(
            ecr_password_cmd, capture_output=True, text=True, shell=False, check=False
        )

        if ecr_password_result.returncode != 0:
            logger.error(f"Failed to get ECR login password: {ecr_password_result.stderr}")
            raise RuntimeError(f"Failed to get ECR login password: {ecr_password_result.stderr}")

        ecr_password = ecr_password_result.stdout.strip()

        # Login to Docker using the password
        registry_url = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
        docker_login_cmd = [
            "docker",
            "login",
            "--username",
            "AWS",
            "--password-stdin",
            registry_url,
        ]

        docker_login_result = subprocess.run(
            docker_login_cmd,
            input=ecr_password,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )

        if docker_login_result.returncode != 0:
            logger.error(f"Docker login failed: {docker_login_result.stderr}")
            raise RuntimeError(f"Failed to login to ECR: {docker_login_result.stderr}")

        logger.info("Successfully logged in to ECR")

        # Build the image with platform specification for AMD64 (x86_64)
        # This ensures compatibility with ECS which runs on x86_64 architecture
        logger.info(f"Building Docker image at {app_path} for linux/amd64 platform...")

        # Try buildx first which allows platform specification
        try:
            # Use list arguments instead of shell=True for security
            buildx_cmd = [
                "docker",
                "buildx",
                "build",
                "--platform",
                "linux/amd64",
                "-t",
                f"{repository_uri}:{tag}",
                "--load",
                app_path,
            ]

            logger.info(f"Attempting buildx command: {' '.join(buildx_cmd)}")
            build_result = subprocess.run(
                buildx_cmd, capture_output=True, text=True, shell=False, check=False
            )

            if build_result.returncode != 0:
                logger.warning(f"Docker buildx failed: {build_result.stderr}")
                raise subprocess.CalledProcessError(build_result.returncode, buildx_cmd)

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to regular build with platform args if buildx fails
            logger.warning("Docker buildx failed, trying alternative approach")

            # Use list arguments instead of shell=True for security
            build_cmd = [
                "docker",
                "build",
                "--platform",
                "linux/amd64",
                "-t",
                f"{repository_uri}:{tag}",
                app_path,
            ]

            logger.info(f"Attempting alternative build command: {' '.join(build_cmd)}")
            build_result = subprocess.run(
                build_cmd, capture_output=True, text=True, shell=False, check=False
            )

            if build_result.returncode != 0:
                logger.error(f"Docker build failed: {build_result.stderr}")
                raise RuntimeError(f"Failed to build Docker image: {build_result.stderr}") from None

        logger.info("Docker image built successfully")
        logger.info(f"Build output: {build_result.stdout}")

        # Push the image
        logger.info(f"Pushing Docker image to {repository_uri}:{tag}...")

        # Use list arguments instead of shell=True for security
        push_cmd = ["docker", "push", f"{repository_uri}:{tag}"]

        push_result = subprocess.run(
            push_cmd, capture_output=True, text=True, shell=False, check=False
        )

        if push_result.returncode != 0:
            logger.error(f"Docker push failed: {push_result.stderr}")
            raise RuntimeError(f"Failed to push Docker image: {push_result.stderr}")

        logger.info("Docker image pushed successfully")
        logger.info(f"Push output: {push_result.stdout}")

        # Verify the image was pushed by listing images in the repository
        repo_name = repository_uri.split("/")[-1]
        logger.info(f"Verifying image in repository: {repo_name}")

        # Use list arguments instead of shell=True for security
        verify_cmd = [
            "aws",
            "ecr",
            "list-images",
            "--repository-name",
            repo_name,
            "--region",
            region,
        ]

        # Add profile if specified
        if profile and profile != "default":
            verify_cmd.extend(["--profile", profile])

        verify_result = subprocess.run(
            verify_cmd, capture_output=True, text=True, shell=False, check=False
        )

        if verify_result.returncode != 0:
            logger.warning(f"Could not verify image push: {verify_result.stderr}")
        else:
            logger.info(f"Image verification result: {verify_result.stdout}")
            if "imageTag" not in verify_result.stdout:
                logger.warning(
                    f"Image tag {tag} not found in repository. Push may have failed silently."
                )
                raise RuntimeError(f"Image tag {tag} not found in repository after push operation")

        return tag

    except Exception as e:
        logger.error(f"Error in build_and_push_image: {str(e)}", exc_info=True)
        raise
