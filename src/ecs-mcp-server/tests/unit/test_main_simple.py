"""
Simplified unit tests for main server module.
"""

import unittest
from unittest.mock import patch, MagicMock

# Import the module under test with mocks
with patch('fastmcp.MCPServer') as mock_server_class, \
     patch('fastmcp.models.MCPTool') as mock_tool_class, \
     patch('fastmcp.models.MCPPromptPattern') as mock_pattern_class, \
     patch('fastmcp.models.MCPToolParameter') as mock_param_class:
    
    # Set up the mock server
    mock_server = MagicMock()
    mock_server_class.return_value = mock_server
    
    # Now import the module
    from awslabs.ecs_mcp_server.main import create_server


class TestMainSimple(unittest.TestCase):
    """Simplified tests for main server module."""

    @patch('fastmcp.MCPServer')
    def test_create_server_basic(self, mock_server_class):
        """Test that create_server creates a server with the correct name."""
        # Set up the mock
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Call create_server
        server = create_server()
        
        # Verify the server was created with the correct parameters
        mock_server_class.assert_called_once()
        args, kwargs = mock_server_class.call_args
        self.assertEqual(kwargs['name'], "AWS ECS MCP Server")
        self.assertIn("containerization", kwargs['description'].lower())
        self.assertIn("deployment", kwargs['description'].lower())
        
        # Verify register_tool and register_prompt_patterns were called
        self.assertTrue(mock_server.register_tool.called)
        self.assertTrue(mock_server.register_prompt_patterns.called)


if __name__ == "__main__":
    unittest.main()
