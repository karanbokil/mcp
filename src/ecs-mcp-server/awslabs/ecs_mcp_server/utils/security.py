"""
Security utilities for the ECS MCP Server.
"""

import functools
import logging
from typing import Any, Dict, Callable, Awaitable, Literal

logger = logging.getLogger(__name__)

# Define permission types as constants
PERMISSION_WRITE = "write"
PERMISSION_SENSITIVE_DATA = "sensitive-data"
PERMISSION_NONE = "none"

# Define permission type
PermissionType = Literal[PERMISSION_WRITE, PERMISSION_SENSITIVE_DATA, PERMISSION_NONE]


class SecurityError(Exception):
    """Exception raised for security-related errors."""
    pass


def check_permission(config: Dict[str, Any], permission_type: PermissionType) -> bool:
    """
    Checks if the specified permission is allowed based on configuration settings.
    
    Args:
        config: The MCP server configuration
        permission_type: The type of permission to check
        
    Returns:
        bool: Whether the operation is allowed
    
    Raises:
        SecurityError: If the operation is not allowed
    """
    if permission_type == PERMISSION_WRITE and not config.get("allow-write", False):
        raise SecurityError(
            "Write operations are disabled for security. "
            "Set ALLOW_WRITE=true in your environment to enable, "
            "but be aware of the security implications."
        )
    elif permission_type == PERMISSION_SENSITIVE_DATA and not config.get("allow-sensitive-data", False):
        raise SecurityError(
            "Access to sensitive data is not allowed without ALLOW_SENSITIVE_DATA=true "
            "in your environment due to potential exposure of sensitive information."
        )
    
    return True


def secure_tool(config: Dict[str, Any], permission_type: PermissionType, tool_name: str = None):
    """
    Decorator to secure a tool function with permission checks.
    
    Args:
        config: The MCP server configuration
        permission_type: The type of permission required for this tool
        tool_name: Optional name of the tool (for logging purposes)
        
    Returns:
        Decorator function that wraps the tool with security checks
    """
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Validate security permissions
                check_permission(config, permission_type)
                # Call the original function if validation passes
                return await func(*args, **kwargs)
            except SecurityError as e:
                # Get tool name for logging
                log_tool_name = tool_name or func.__name__
                # Return error if validation fails
                logger.warning(f"Security validation failed for tool {log_tool_name}: {str(e)}")
                return {
                    "error": str(e),
                    "status": "failed",
                    "message": "Security validation failed. Please check your environment configuration."
                }
        return wrapper
    return decorator
