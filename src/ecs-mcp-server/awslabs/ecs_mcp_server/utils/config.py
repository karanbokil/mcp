"""
Configuration utilities for the ECS MCP Server.
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_config() -> Dict[str, Any]:
    """
    Gets the configuration for the ECS MCP Server.

    Returns:
        Dict containing configuration values
    """
    config = {
        "aws_region": os.environ.get("AWS_REGION", "us-east-1"),
        "aws_profile": os.environ.get("AWS_PROFILE", None),
        "log_level": os.environ.get("FASTMCP_LOG_LEVEL", "INFO"),
    }

    logger.debug(f"Loaded configuration: {config}")
    return config
