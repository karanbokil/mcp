"""
Unit tests for Docker utility functions.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch

import pytest

from awslabs.ecs_mcp_server.utils.docker import (
    build_and_push_image,
    validate_dockerfile,
)


class TestDockerUtils(unittest.TestCase):
    """Tests for Docker utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app_path = self.temp_dir.name

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def create_file(self, path, content):
        """Create a file with the given content."""
        full_path = os.path.join(self.app_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_validate_dockerfile_success(self, mock_run):
        """Test validate_dockerfile function with successful validation."""
        # Create a Dockerfile
        dockerfile_path = os.path.join(self.app_path, "Dockerfile")
        self.create_file("Dockerfile", "FROM python:3.9-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"app.py\"]")
        
        # Mock subprocess.run for hadolint check
        mock_run.side_effect = [
            MagicMock(returncode=0),  # hadolint --version
            MagicMock(returncode=0, stdout="", stderr="")  # hadolint Dockerfile
        ]
        
        # Call validate_dockerfile
        result = await validate_dockerfile(dockerfile_path)
        
        # Verify subprocess.run was called with the correct parameters
        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_has_calls([
            call(["hadolint", "--version"], capture_output=True, check=True),
            call(["hadolint", dockerfile_path], capture_output=True, text=True)
        ])
        
        # Verify the result indicates success
        self.assertTrue(result["valid"])
        self.assertEqual(result["message"], "Dockerfile validation passed")
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["errors"], [])

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_validate_dockerfile_failure(self, mock_run):
        """Test validate_dockerfile function with validation failures."""
        # Create a Dockerfile
        dockerfile_path = os.path.join(self.app_path, "Dockerfile")
        self.create_file("Dockerfile", "FROM python:3.9-slim\nRUN apt-get update && apt-get install -y curl")
        
        # Mock subprocess.run for hadolint check
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = "Dockerfile:2 DL3008 warning: Pin versions in apt get install"
        mock_process.stderr = ""
        
        mock_run.side_effect = [
            MagicMock(returncode=0),  # hadolint --version
            mock_process  # hadolint Dockerfile
        ]
        
        # Call validate_dockerfile
        result = await validate_dockerfile(dockerfile_path)
        
        # Verify subprocess.run was called with the correct parameters
        self.assertEqual(mock_run.call_count, 2)
        
        # Verify the result indicates failure
        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], "Dockerfile validation failed")
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("DL3008", result["warnings"][0])
        self.assertEqual(result["errors"], [])

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_validate_dockerfile_no_hadolint(self, mock_run):
        """Test validate_dockerfile function when hadolint is not installed."""
        # Create a Dockerfile
        dockerfile_path = os.path.join(self.app_path, "Dockerfile")
        self.create_file("Dockerfile", "FROM python:3.9-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"app.py\"]")
        
        # Mock subprocess.run to raise FileNotFoundError
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'hadolint'")
        
        # Call validate_dockerfile
        result = await validate_dockerfile(dockerfile_path)
        
        # Verify subprocess.run was called once
        mock_run.assert_called_once()
        
        # Verify the result indicates success (skipped validation)
        self.assertTrue(result["valid"])
        self.assertIn("skipped", result["message"].lower())
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["errors"], [])

    @pytest.mark.asyncio
    @patch("subprocess.run")
    @patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
    @patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
    async def test_build_and_push_image(self, mock_get_account_id, mock_get_password, mock_run):
        """Test build_and_push_image function."""
        # Mock get_aws_account_id
        mock_get_account_id.return_value = "123456789012"
        
        # Mock get_ecr_login_password
        mock_get_password.return_value = "password123"
        
        # Mock subprocess.run
        mock_run.return_value = MagicMock(returncode=0)
        
        # Call build_and_push_image
        tag = await build_and_push_image(
            app_path=self.app_path,
            repository_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
            tag="latest"
        )
        
        # Verify get_aws_account_id was called
        mock_get_account_id.assert_called_once()
        
        # Verify get_ecr_login_password was called
        mock_get_password.assert_called_once()
        
        # Verify subprocess.run was called for login, build, and push
        self.assertEqual(mock_run.call_count, 3)
        
        # Verify the tag was returned
        self.assertEqual(tag, "latest")


if __name__ == "__main__":
    unittest.main()
