"""
Unit tests for containerization API.
"""

import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.containerize import (
    _generate_docker_compose,
    _generate_dockerfile,
    _get_run_command,
    containerize_app,
)


class TestContainerize(unittest.TestCase):
    """Tests for containerization API."""

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
    @patch("awslabs.ecs_mcp_server.api.containerize.analyze_app")
    @patch("awslabs.ecs_mcp_server.api.containerize._generate_dockerfile")
    @patch("awslabs.ecs_mcp_server.api.containerize._generate_docker_compose")
    @patch("awslabs.ecs_mcp_server.api.containerize.validate_dockerfile")
    async def test_containerize_app(
        self, mock_validate, mock_docker_compose, mock_dockerfile, mock_analyze
    ):
        """Test containerize_app function."""
        # Mock analyze_app to return a sample analysis
        mock_analyze.return_value = {
            "framework": "flask",
            "default_port": 5000,
            "environment_variables": {"FLASK_ENV": "production"},
            "build_steps": ["COPY requirements.txt .", "RUN pip install -r requirements.txt"],
            "container_requirements": {"base_image": "python:3.9-slim"},
        }
        
        # Mock _generate_dockerfile to return a sample Dockerfile content
        mock_dockerfile.return_value = "FROM python:3.9-slim\nWORKDIR /app\n..."
        
        # Mock _generate_docker_compose to return a sample docker-compose.yml content
        mock_docker_compose.return_value = "version: '3'\nservices:\n  app:\n    build: ."
        
        # Mock validate_dockerfile to return a successful validation
        mock_validate.return_value = {
            "valid": True,
            "message": "Dockerfile validation passed",
            "warnings": [],
            "errors": [],
        }
        
        # Call containerize_app
        result = await containerize_app(
            app_path=self.app_path,
            port=8000,
            environment_vars={"DEBUG": "false"}
        )
        
        # Verify analyze_app was called with correct parameters
        mock_analyze.assert_called_once_with(self.app_path, None)
        
        # Verify _generate_dockerfile was called with correct parameters
        mock_dockerfile.assert_called_once()
        
        # Verify _generate_docker_compose was called with correct parameters
        mock_docker_compose.assert_called_once()
        
        # Verify validate_dockerfile was called
        mock_validate.assert_called_once()
        
        # Verify the result contains expected keys
        self.assertIn("dockerfile_path", result)
        self.assertIn("docker_compose_path", result)
        self.assertIn("container_port", result)
        self.assertIn("environment_variables", result)
        self.assertIn("validation_result", result)
        self.assertIn("framework", result)
        self.assertIn("base_image", result)
        
        # Verify the container port was set to the provided value
        self.assertEqual(result["container_port"], 8000)
        
        # Verify environment variables were merged
        self.assertIn("FLASK_ENV", result["environment_variables"])
        self.assertIn("DEBUG", result["environment_variables"])
        self.assertEqual(result["environment_variables"]["DEBUG"], "false")

    @pytest.mark.asyncio
    async def test_get_run_command(self):
        """Test _get_run_command function."""
        # Test Flask
        cmd = _get_run_command("flask", self.app_path)
        self.assertEqual(cmd, "flask run --host=0.0.0.0")
        
        # Test Django
        cmd = _get_run_command("django", self.app_path)
        self.assertEqual(cmd, "python manage.py runserver 0.0.0.0:8000")
        
        # Test Express with package.json
        self.create_file("package.json", '{"scripts": {"start": "node server.js"}}')
        cmd = _get_run_command("express", self.app_path)
        self.assertEqual(cmd, "npm start")
        
        # Test Node.js without start script
        self.create_file("package.json", '{"scripts": {"test": "jest"}}')
        cmd = _get_run_command("node", self.app_path)
        self.assertEqual(cmd, "node index.js")
        
        # Test Rails
        cmd = _get_run_command("rails", self.app_path)
        self.assertEqual(cmd, "rails server -b 0.0.0.0")
        
        # Test generic
        cmd = _get_run_command("generic", self.app_path)
        self.assertEqual(cmd, "nginx -g 'daemon off;'")


if __name__ == "__main__":
    unittest.main()
