"""
Unit tests for main server module.
"""

import unittest
from unittest.mock import patch, MagicMock

# We need to patch the imports before importing the module under test
class MockMCPServer:
    def __init__(self, name, description, version):
        self.name = name
        self.description = description
        self.version = version
        self.tools = []
        self.prompt_patterns = []
    
    def register_tool(self, tool):
        self.tools.append(tool)
        
    def register_prompt_patterns(self, patterns):
        self.prompt_patterns.extend(patterns)

class MockMCPTool:
    def __init__(self, name, description, function, parameters):
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters

class MockMCPPromptPattern:
    def __init__(self, pattern, description, tools):
        self.pattern = pattern
        self.description = description
        self.tools = tools

class MockMCPToolParameter:
    def __init__(self, name, description, type, required):
        self.name = name
        self.description = description
        self.type = type
        self.required = required

# Apply the patches
patch('fastmcp.MCPServer', MockMCPServer).start()
patch('fastmcp.models.MCPTool', MockMCPTool).start()
patch('fastmcp.models.MCPPromptPattern', MockMCPPromptPattern).start()
patch('fastmcp.models.MCPToolParameter', MockMCPToolParameter).start()

# Now import the module under test
with patch('fastmcp.MCPServer', MockMCPServer), \
     patch('fastmcp.models.MCPTool', MockMCPTool), \
     patch('fastmcp.models.MCPPromptPattern', MockMCPPromptPattern), \
     patch('fastmcp.models.MCPToolParameter', MockMCPToolParameter):
    from awslabs.ecs_mcp_server.main import create_server


class TestMain(unittest.TestCase):
    """Tests for main server module."""

    def test_create_server(self):
        """Test create_server function."""
        # Call create_server
        server = create_server()
        
        # Verify the server is an instance of MockMCPServer
        self.assertIsInstance(server, MockMCPServer)
        
        # Verify the server has the correct name and description
        self.assertEqual(server.name, "AWS ECS MCP Server")
        self.assertIn("containerization", server.description.lower())
        self.assertIn("deployment", server.description.lower())
        self.assertIn("aws ecs", server.description.lower())
        
        # Verify the server has registered tools
        self.assertGreaterEqual(len(server.tools), 1)
        
        # Verify the server has registered prompt patterns
        self.assertGreaterEqual(len(server.prompt_patterns), 1)


if __name__ == "__main__":
    unittest.main()
