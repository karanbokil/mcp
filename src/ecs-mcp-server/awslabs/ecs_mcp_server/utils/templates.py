"""
Template utilities for the ECS MCP Server.
"""

import logging
import os
import pkg_resources
from typing import Optional

logger = logging.getLogger(__name__)

def get_templates_dir() -> str:
    """
    Gets the path to the templates directory.
    
    Returns:
        Path to the templates directory
    """
    # First, try to get templates from the package resources
    try:
        templates_dir = pkg_resources.resource_filename("awslabs.ecs_mcp_server", "templates")
        if os.path.isdir(templates_dir):
            return templates_dir
    except Exception as e:
        logger.debug(f"Could not find templates in package resources: {e}")
    
    # Fallback to the templates directory in the current file's directory
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(current_dir, "templates")
    
    # Create the templates directory if it doesn't exist
    if not os.path.isdir(templates_dir):
        os.makedirs(templates_dir)
        logger.warning(f"Created templates directory at {templates_dir}")
    
    return templates_dir
