"""
Models for application analysis.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AppAnalysis(BaseModel):
    """Model for application analysis results."""

    framework: str = Field(description="Detected web framework")

    dependencies: Dict[str, Any] = Field(
        default_factory=dict, description="Application dependencies"
    )

    default_port: int = Field(default=8080, description="Default port for the application")

    container_requirements: Dict[str, Any] = Field(
        default_factory=dict, description="Container requirements (base image, ports, etc.)"
    )

    environment_variables: Dict[str, str] = Field(
        default_factory=dict, description="Required environment variables"
    )

    build_steps: List[str] = Field(
        default_factory=list, description="Build steps for the Dockerfile"
    )

    runtime_requirements: Dict[str, Any] = Field(
        default_factory=dict, description="Runtime requirements (memory, CPU, etc.)"
    )
