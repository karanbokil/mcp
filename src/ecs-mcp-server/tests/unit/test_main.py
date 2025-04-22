"""
Unit tests for main server module.
"""

import unittest
from unittest.mock import patch, MagicMock

# We need to patch the imports before importing the module under test
class MockFastMCP:
    def __init__(self, name, description=None, version=None, instructions=None):
        self.name = name
        self.description = description or ""
        self.version = version
        self.instructions = instructions
        self.tools = []
        self.prompt_patterns = []
    
    def tool(self, name=None):
        def decorator(func):
            self.tools.append({"name": name or func.__name__, "function": func})
            return func
        return decorator
    
    def prompt(self, pattern):
        def decorator(func):
            self.prompt_patterns.append({"pattern": pattern, "function": func})
            return func
        return decorator
    
    def run(self):
        pass

# Apply the patches
with patch('mcp.server.fastmcp.FastMCP', MockFastMCP):
    from awslabs.ecs_mcp_server.main import mcp


class TestMain(unittest.TestCase):
    """Tests for main server module."""

    def test_server_configuration(self):
        """Test server configuration."""
        # Verify the server has the correct name
        self.assertEqual(mcp.name, "AWS ECS MCP Server")
        
        # Verify the description contains expected keywords
        self.assertIn("containerization", mcp.description.lower())
        self.assertIn("deployment", mcp.description.lower())
        self.assertIn("aws ecs", mcp.description.lower())
        
        # Verify the server has registered tools
        self.assertGreaterEqual(len(mcp.tools), 1)
        
        # Verify the server has registered prompt patterns
        self.assertGreaterEqual(len(mcp.prompt_patterns), 1)
        
        # Verify tool names
        tool_names = [tool["name"] for tool in mcp.tools]
        self.assertIn("analyze_web_app", tool_names)
        self.assertIn("containerize_app", tool_names)
        self.assertIn("create_ecs_infrastructure", tool_names)
        self.assertIn("deploy_to_ecs", tool_names)
        self.assertIn("get_deployment_status", tool_names)
        
        # Verify prompt patterns
        patterns = [pattern["pattern"] for pattern in mcp.prompt_patterns]
        self.assertIn("dockerize", patterns)
        self.assertIn("deploy to ecs", patterns)
        self.assertIn("ship it", patterns)


if __name__ == "__main__":
    unittest.main()
