"""
Security utilities for the ECS MCP Server.
"""

import functools
import logging
from typing import Any, Dict, Callable, Awaitable

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Exception raised for security-related errors."""
    pass


def check_write_permission(config: Dict[str, Any], tool_name: str) -> bool:
    """
    Checks if write operations are allowed based on configuration settings.
    
    Args:
        config: The MCP server configuration
        tool_name: The name of the tool being invoked
        
    Returns:
        bool: Whether the operation is allowed
    
    Raises:
        SecurityError: If the operation is not allowed
    """
    write_tools = ["create_ecs_infrastructure", "delete_ecs_infrastructure"]
    
    if tool_name in write_tools and not config.get("allow-write", False):
        raise SecurityError(
            "Write operations are disabled for security. "
            "Set ALLOW_WRITE=true in your environment to enable, "
            "but be aware of the security implications."
        )
    return True


def enforce_sensitive_data_access(config: Dict[str, Any], tool_name: str) -> bool:
    """
    Enforces sensitive data access restrictions based on configuration.
    
    Args:
        config: The MCP server configuration
        tool_name: The name of the tool being invoked
        
    Returns:
        bool: Whether the operation is allowed
    
    Raises:
        SecurityError: If the operation is not allowed
    """
    # Tools that can return sensitive data
    sensitive_data_tools = ["fetch_task_logs", "fetch_service_events", "fetch_task_failures"]
    
    if tool_name in sensitive_data_tools and not config.get("allow-sensitive-data", False):
        raise SecurityError(
            f"Tool {tool_name} is not allowed without ALLOW_SENSITIVE_DATA=true "
            "in your environment due to potential exposure of sensitive information."
        )
    return True


def validate_security_permissions(config: Dict[str, Any], tool_name: str) -> bool:
    """
    Validates all security permissions for a tool.
    
    Args:
        config: The MCP server configuration
        tool_name: The name of the tool being invoked
        
    Returns:
        bool: Whether the operation is allowed
    
    Raises:
        SecurityError: If the operation is not allowed
    """
    # Check write permissions
    check_write_permission(config, tool_name)
    
    # Check sensitive data access
    enforce_sensitive_data_access(config, tool_name)
    
    return True


def secure_tool(config: Dict[str, Any], tool_name: str):
    """
    Decorator to secure a tool function with permission checks.
    
    Args:
        config: The MCP server configuration
        tool_name: The name of the tool to secure
        
    Returns:
        Decorator function that wraps the tool with security checks
    """
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Validate security permissions
                validate_security_permissions(config, tool_name)
                # Call the original function if validation passes
                return await func(*args, **kwargs)
            except SecurityError as e:
                # Return error if validation fails
                logger.warning(f"Security validation failed for tool {tool_name}: {str(e)}")
                return {
                    "error": str(e),
                    "status": "failed",
                    "message": "Security validation failed. Please check your environment configuration."
                }
        return wrapper
    return decorator
