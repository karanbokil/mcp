"""
Security utilities for the ECS MCP Server.
"""

import functools
import logging
import os.path
import re
import json
from typing import Any, Dict, Callable, Awaitable, Literal, Union

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


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


def validate_app_name(app_name: str) -> bool:
    """
    Validates application name to ensure it contains only allowed characters.
    
    Args:
        app_name: The application name to validate
        
    Returns:
        bool: Whether the name is valid
        
    Raises:
        ValidationError: If the name contains invalid characters
    """
    # Allow alphanumeric characters, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9\-_]+$'
    if not re.match(pattern, app_name):
        raise ValidationError(
            f"Application name '{app_name}' contains invalid characters. "
            "Only alphanumeric characters, hyphens, and underscores are allowed."
        )
    return True


def validate_file_path(path: str) -> str:
    """
    Validates file path to prevent directory traversal attacks.
    
    Args:
        path: The file path to validate
        
    Returns:
        str: The normalized absolute path
        
    Raises:
        ValidationError: If the path is invalid or doesn't exist
    """
    # Convert to absolute path and normalize
    abs_path = os.path.abspath(os.path.normpath(path))
    
    # Check if the path exists
    if not os.path.exists(abs_path):
        raise ValidationError(f"Path '{path}' does not exist")
    
    # Check for suspicious path components that might indicate traversal attempts
    suspicious_patterns = [
        r'/\.\./',  # /../
        r'\\\.\.\\',  # \..\ (Windows)
        r'^\.\./',  # ../
        r'^\.\.\\',  # ..\ (Windows)
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, path):
            raise ValidationError(f"Path '{path}' contains suspicious traversal patterns")
    
    return abs_path


def validate_cloudformation_template(template_path: str) -> bool:
    """
    Validates a CloudFormation template against basic schema requirements.
    
    Args:
        template_path: Path to the CloudFormation template file
        
    Returns:
        bool: Whether the template is valid
        
    Raises:
        ValidationError: If the template is invalid
    """
    # First validate the file path
    validated_path = validate_file_path(template_path)
    
    # Read template file
    try:
        with open(validated_path, 'r') as f:
            template_content = f.read()
    except Exception as e:
        raise ValidationError(f"Failed to read template file: {str(e)}")
    
    # Validate JSON format
    try:
        template = json.loads(template_content)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in CloudFormation template: {str(e)}")
    
    # Basic CloudFormation template validation
    if not isinstance(template, dict):
        raise ValidationError("CloudFormation template must be a JSON object")
    
    # Check for required sections
    if "Resources" not in template:
        raise ValidationError("CloudFormation template must contain a 'Resources' section")
    
    # Check that Resources is a dictionary
    if not isinstance(template["Resources"], dict):
        raise ValidationError("'Resources' section must be a JSON object")
    
    # Check that at least one resource is defined
    if not template["Resources"]:
        raise ValidationError("CloudFormation template must define at least one resource")
    
    # Additional security checks could be added here
    
    return True


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
