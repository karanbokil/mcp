"""
Unit tests for framework detection utilities.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest

from awslabs.ecs_mcp_server.utils.framework_detection import (
    detect_framework,
    _is_flask,
    _is_django,
    _is_express,
    _is_react,
    _is_node,
)


class TestFrameworkDetection(unittest.TestCase):
    """Tests for framework detection utilities."""

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
    async def test_detect_flask(self):
        """Test detection of Flask applications."""
        # Create a Flask app.py
        self.create_file("app.py", "from flask import Flask\napp = Flask(__name__)")
        self.create_file("requirements.txt", "flask==2.0.1\nWerkzeug==2.0.1")

        framework = await detect_framework(self.app_path)
        self.assertEqual(framework, "flask")

    @pytest.mark.asyncio
    async def test_detect_django(self):
        """Test detection of Django applications."""
        # Create a Django manage.py
        self.create_file("manage.py", "#!/usr/bin/env python\nimport django\nfrom django.core.management import execute_from_command_line")
        self.create_file("requirements.txt", "django==3.2.5\nasgiref==3.4.1")

        framework = await detect_framework(self.app_path)
        self.assertEqual(framework, "django")

    @pytest.mark.asyncio
    async def test_detect_express(self):
        """Test detection of Express.js applications."""
        # Create an Express app.js
        self.create_file("app.js", "const express = require('express');\nconst app = express();")
        self.create_file("package.json", '{"dependencies": {"express": "^4.17.1"}}')

        framework = await detect_framework(self.app_path)
        self.assertEqual(framework, "express")

    @pytest.mark.asyncio
    async def test_detect_react(self):
        """Test detection of React applications."""
        # Create a React package.json
        self.create_file("package.json", '{"dependencies": {"react": "^17.0.2", "react-dom": "^17.0.2"}}')
        self.create_file("src/App.jsx", "import React from 'react';\nexport default function App() { return <div>Hello</div>; }")

        framework = await detect_framework(self.app_path)
        self.assertEqual(framework, "react")

    @pytest.mark.asyncio
    async def test_detect_node(self):
        """Test detection of generic Node.js applications."""
        # Create a Node.js package.json without specific framework
        self.create_file("package.json", '{"dependencies": {"lodash": "^4.17.21"}}')
        self.create_file("index.js", "console.log('Hello, world!');")

        framework = await detect_framework(self.app_path)
        self.assertEqual(framework, "node")

    @pytest.mark.asyncio
    async def test_detect_unknown(self):
        """Test detection of unknown frameworks."""
        # Create a generic HTML file
        self.create_file("index.html", "<html><body>Hello, world!</body></html>")

        framework = await detect_framework(self.app_path)
        self.assertIsNone(framework)

    @pytest.mark.asyncio
    async def test_is_flask(self):
        """Test _is_flask function."""
        # Create a Flask app.py
        self.create_file("app.py", "from flask import Flask\napp = Flask(__name__)")
        
        result = await _is_flask(self.app_path)
        self.assertTrue(result)
        
        # Test with non-Flask Python file
        self.temp_dir.cleanup()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app_path = self.temp_dir.name
        self.create_file("app.py", "print('Hello, world!')")
        
        result = await _is_flask(self.app_path)
        self.assertFalse(result)

    @pytest.mark.asyncio
    async def test_is_django(self):
        """Test _is_django function."""
        # Create a Django manage.py
        self.create_file("manage.py", "#!/usr/bin/env python\nimport django\nfrom django.core.management import execute_from_command_line")
        
        result = await _is_django(self.app_path)
        self.assertTrue(result)
        
        # Test with non-Django Python file
        self.temp_dir.cleanup()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app_path = self.temp_dir.name
        self.create_file("manage.py", "print('Hello, world!')")
        
        result = await _is_django(self.app_path)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
