"""
Unit tests for Docker utility functions.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.docker import build_and_push_image


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
    @patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
    async def test_build_and_push_image(self, mock_get_account_id, mock_run):
        """Test build_and_push_image function."""
        # Create a Dockerfile
        self.create_file("Dockerfile", "FROM python:3.9-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"app.py\"]")
        
        # Mock get_aws_account_id
        mock_get_account_id.return_value = "123456789012"
        
        # Mock subprocess.run for all commands
        mock_run.return_value = MagicMock(returncode=0, stdout='{"imageIds": [{"imageTag": "latest"}]}')
        
        # Call build_and_push_image
        tag = await build_and_push_image(
            app_path=self.app_path,
            repository_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
            tag="latest"
        )
        
        # Verify get_aws_account_id was called
        mock_get_account_id.assert_called_once()
        
        # Verify the tag was returned
        self.assertEqual(tag, "latest")

    @pytest.mark.asyncio
    @patch("subprocess.run")
    @patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
    async def test_build_and_push_image_no_dockerfile(self, mock_get_account_id, mock_run):
        """Test build_and_push_image function when Dockerfile doesn't exist."""
        # Mock get_aws_account_id
        mock_get_account_id.return_value = "123456789012"
        
        # Call build_and_push_image and expect FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await build_and_push_image(
                app_path=self.app_path,
                repository_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/test-repo",
                tag="latest"
            )
        
        # Verify get_aws_account_id was called
        mock_get_account_id.assert_called_once()


if __name__ == "__main__":
    unittest.main()
