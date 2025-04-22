"""
Unit tests for application analysis API.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from awslabs.ecs_mcp_server.api.analyze import (
    analyze_app,
    _analyze_dependencies,
    _get_default_port,
    _determine_container_requirements,
    _get_base_image,
    _detect_environment_variables,
    _determine_build_steps,
    _determine_runtime_requirements,
)


class TestAnalyze(unittest.TestCase):
    """Tests for application analysis API."""

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
    @patch("awslabs.ecs_mcp_server.api.analyze.detect_framework")
    async def test_analyze_app_with_provided_framework(self, mock_detect):
        """Test analyze_app with provided framework."""
        # Call analyze_app with a provided framework
        result = await analyze_app(self.app_path, framework="flask")
        
        # Verify detect_framework was not called
        mock_detect.assert_not_called()
        
        # Verify the result contains the provided framework
        self.assertEqual(result["framework"], "flask")
        
        # Verify the result contains expected keys
        self.assertIn("dependencies", result)
        self.assertIn("default_port", result)
        self.assertIn("container_requirements", result)
        self.assertIn("environment_variables", result)
        self.assertIn("build_steps", result)
        self.assertIn("runtime_requirements", result)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.analyze.detect_framework")
    async def test_analyze_app_with_detected_framework(self, mock_detect):
        """Test analyze_app with detected framework."""
        # Mock detect_framework to return "django"
        mock_detect.return_value = "django"
        
        # Call analyze_app without providing a framework
        result = await analyze_app(self.app_path)
        
        # Verify detect_framework was called with the correct path
        mock_detect.assert_called_once_with(self.app_path)
        
        # Verify the result contains the detected framework
        self.assertEqual(result["framework"], "django")

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.analyze.detect_framework")
    async def test_analyze_app_with_unknown_framework(self, mock_detect):
        """Test analyze_app with unknown framework."""
        # Mock detect_framework to return None
        mock_detect.return_value = None
        
        # Call analyze_app without providing a framework
        result = await analyze_app(self.app_path)
        
        # Verify detect_framework was called with the correct path
        mock_detect.assert_called_once_with(self.app_path)
        
        # Verify the result contains the generic framework
        self.assertEqual(result["framework"], "generic")

    @pytest.mark.asyncio
    async def test_analyze_dependencies_flask(self):
        """Test _analyze_dependencies for Flask applications."""
        # Create a requirements.txt file
        self.create_file("requirements.txt", "flask==2.0.1\nWerkzeug==2.0.1")
        
        # Call _analyze_dependencies
        result = await _analyze_dependencies(self.app_path, "flask")
        
        # Verify the result contains the dependencies
        self.assertIn("python", result)
        self.assertEqual(len(result["python"]), 2)
        self.assertIn("flask==2.0.1", result["python"])
        self.assertIn("Werkzeug==2.0.1", result["python"])

    @pytest.mark.asyncio
    async def test_analyze_dependencies_node(self):
        """Test _analyze_dependencies for Node.js applications."""
        # Create a package.json file
        self.create_file(
            "package.json",
            '{"dependencies": {"express": "^4.17.1"}, "devDependencies": {"jest": "^27.0.6"}}'
        )
        
        # Call _analyze_dependencies
        result = await _analyze_dependencies(self.app_path, "express")
        
        # Verify the result contains the dependencies
        self.assertIn("npm", result)
        self.assertIn("npm_dev", result)
        self.assertEqual(result["npm"], {"express": "^4.17.1"})
        self.assertEqual(result["npm_dev"], {"jest": "^27.0.6"})

    def test_get_default_port(self):
        """Test _get_default_port function."""
        # Test default ports for different frameworks
        self.assertEqual(_get_default_port("flask"), 5000)
        self.assertEqual(_get_default_port("django"), 8000)
        self.assertEqual(_get_default_port("express"), 3000)
        self.assertEqual(_get_default_port("react"), 3000)
        self.assertEqual(_get_default_port("rails"), 3000)
        self.assertEqual(_get_default_port("generic"), 8080)
        self.assertEqual(_get_default_port("unknown"), 8080)  # Default for unknown frameworks

    @pytest.mark.asyncio
    async def test_determine_container_requirements(self):
        """Test _determine_container_requirements function."""
        # Call _determine_container_requirements for Flask
        result = await _determine_container_requirements(self.app_path, "flask")
        
        # Verify the result contains expected keys
        self.assertIn("base_image", result)
        self.assertIn("exposed_ports", result)
        self.assertIn("volumes", result)
        self.assertIn("working_dir", result)
        
        # Verify the base image is correct
        self.assertEqual(result["base_image"], "python:3.9-slim")
        
        # Verify the exposed ports include the default port
        self.assertIn(5000, result["exposed_ports"])

    def test_get_base_image(self):
        """Test _get_base_image function."""
        # Test base images for different frameworks
        self.assertEqual(_get_base_image("flask"), "python:3.9-slim")
        self.assertEqual(_get_base_image("django"), "python:3.9-slim")
        self.assertEqual(_get_base_image("express"), "node:18-alpine")
        self.assertEqual(_get_base_image("react"), "node:18-alpine")
        self.assertEqual(_get_base_image("rails"), "ruby:3.2-alpine")
        self.assertEqual(_get_base_image("generic"), "nginx:alpine")
        self.assertEqual(_get_base_image("unknown"), "nginx:alpine")  # Default for unknown frameworks

    @pytest.mark.asyncio
    async def test_detect_environment_variables(self):
        """Test _detect_environment_variables function."""
        # Create a .env file
        self.create_file(".env", "DEBUG=true\nSECRET_KEY=mysecret\n# Comment line\nPORT=5000")
        
        # Call _detect_environment_variables for Flask
        result = await _detect_environment_variables(self.app_path, "flask")
        
        # Verify the result contains the environment variables
        self.assertIn("DEBUG", result)
        self.assertIn("SECRET_KEY", result)
        self.assertIn("PORT", result)
        self.assertIn("FLASK_APP", result)
        self.assertIn("FLASK_ENV", result)
        
        # Verify the values are placeholders for security
        self.assertEqual(result["DEBUG"], "<value>")
        self.assertEqual(result["SECRET_KEY"], "<value>")
        self.assertEqual(result["PORT"], "<value>")

    @pytest.mark.asyncio
    async def test_determine_build_steps(self):
        """Test _determine_build_steps function."""
        # Call _determine_build_steps for Flask
        result = await _determine_build_steps(self.app_path, "flask")
        
        # Verify the result contains the expected build steps
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "COPY requirements.txt .")
        self.assertEqual(result[1], "RUN pip install --no-cache-dir -r requirements.txt")
        self.assertEqual(result[2], "COPY . .")
        
        # Test with Node.js with build script
        self.create_file("package.json", '{"scripts": {"build": "webpack"}}')
        result = await _determine_build_steps(self.app_path, "react")
        
        # Verify the result contains the build step
        self.assertEqual(len(result), 4)
        self.assertEqual(result[3], "RUN npm run build")

    @pytest.mark.asyncio
    async def test_determine_runtime_requirements(self):
        """Test _determine_runtime_requirements function."""
        # Call _determine_runtime_requirements for Flask
        result = await _determine_runtime_requirements(self.app_path, "flask")
        
        # Verify the result contains expected keys
        self.assertIn("memory_min", result)
        self.assertIn("cpu_min", result)
        
        # Verify the values are correct
        self.assertEqual(result["memory_min"], 512)
        self.assertEqual(result["cpu_min"], 256)
        
        # Test with Django (higher memory requirements)
        result = await _determine_runtime_requirements(self.app_path, "django")
        self.assertEqual(result["memory_min"], 1024)


if __name__ == "__main__":
    unittest.main()
