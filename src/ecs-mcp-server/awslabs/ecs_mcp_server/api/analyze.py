"""
API for analyzing web applications to determine containerization requirements.
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any

from awslabs.ecs_mcp_server.utils.framework_detection import detect_framework
from awslabs.ecs_mcp_server.models.app_analysis import AppAnalysis

logger = logging.getLogger(__name__)


async def analyze_app(app_path: str, framework: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyzes a web application to determine containerization requirements.

    Args:
        app_path: Path to the web application directory
        framework: Web framework used (optional, will be auto-detected if not provided)

    Returns:
        Dict containing analysis results
    """
    logger.info(f"Analyzing web application at {app_path}")

    # Validate path exists
    if not os.path.isdir(app_path):
        raise ValueError(f"Application path does not exist or is not a directory: {app_path}")

    # Auto-detect framework if not provided
    detected_framework = framework or await detect_framework(app_path)
    if not detected_framework:
        logger.warning("Could not detect framework, defaulting to generic web application")
        detected_framework = "generic"

    # Analyze dependencies and requirements
    dependencies = await _analyze_dependencies(app_path, detected_framework)

    # Determine default port based on framework
    default_port = _get_default_port(detected_framework)

    # Determine container requirements
    container_requirements = await _determine_container_requirements(app_path, detected_framework)

    # Create analysis result
    analysis = AppAnalysis(
        framework=detected_framework,
        dependencies=dependencies,
        default_port=default_port,
        container_requirements=container_requirements,
        environment_variables=await _detect_environment_variables(app_path, detected_framework),
        build_steps=await _determine_build_steps(app_path, detected_framework),
        runtime_requirements=await _determine_runtime_requirements(app_path, detected_framework),
    )

    logger.info(f"Analysis complete: {analysis}")
    return analysis.model_dump()


async def _analyze_dependencies(app_path: str, framework: str) -> Dict[str, Any]:
    """Analyzes application dependencies based on framework."""
    dependencies = {}

    if framework == "flask" or framework == "django":
        # Check for requirements.txt
        req_path = os.path.join(app_path, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, "r") as f:
                dependencies["python"] = f.read().splitlines()

        # Check for Pipfile
        pipfile_path = os.path.join(app_path, "Pipfile")
        if os.path.exists(pipfile_path):
            dependencies["pipfile"] = True

    elif framework == "express" or framework == "react" or framework == "node":
        # Check for package.json
        pkg_path = os.path.join(app_path, "package.json")
        if os.path.exists(pkg_path):
            with open(pkg_path, "r") as f:
                try:
                    pkg_data = json.load(f)
                    if "dependencies" in pkg_data:
                        dependencies["npm"] = pkg_data["dependencies"]
                    if "devDependencies" in pkg_data:
                        dependencies["npm_dev"] = pkg_data["devDependencies"]
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse package.json at {pkg_path}")

    elif framework == "rails":
        # Check for Gemfile
        gemfile_path = os.path.join(app_path, "Gemfile")
        if os.path.exists(gemfile_path):
            with open(gemfile_path, "r") as f:
                dependencies["ruby"] = f.read()

    return dependencies


def _get_default_port(framework: str) -> int:
    """Returns the default port for a given framework."""
    port_map = {
        "flask": 5000,
        "django": 8000,
        "express": 3000,
        "react": 3000,
        "node": 3000,
        "rails": 3000,
        "generic": 8080,
    }
    return port_map.get(framework, 8080)


async def _determine_container_requirements(app_path: str, framework: str) -> Dict[str, Any]:
    """Determines container requirements based on framework."""
    requirements = {
        "base_image": _get_base_image(framework),
        "exposed_ports": [_get_default_port(framework)],
        "volumes": [],
        "working_dir": "/app",
    }

    return requirements


def _get_base_image(framework: str) -> str:
    """Returns the appropriate base image for a given framework."""
    image_map = {
        "flask": "python:3.9-slim",
        "django": "python:3.9-slim",
        "express": "node:18-alpine",
        "react": "node:18-alpine",
        "node": "node:18-alpine",
        "rails": "ruby:3.2-alpine",
        "generic": "nginx:alpine",
    }
    return image_map.get(framework, "nginx:alpine")


async def _detect_environment_variables(app_path: str, framework: str) -> Dict[str, str]:
    """Detects required environment variables."""
    env_vars = {}

    # Check for .env file
    env_file = os.path.join(app_path, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key, value = parts
                        # Don't include actual values, just keys with placeholders
                        env_vars[key] = "<value>"

    # Add framework-specific environment variables
    if framework == "flask":
        env_vars["FLASK_APP"] = "app.py"
        env_vars["FLASK_ENV"] = "production"
    elif framework == "django":
        env_vars["DJANGO_SETTINGS_MODULE"] = "project.settings"
        env_vars["DJANGO_SECRET_KEY"] = "<secret_key>"
    elif framework == "rails":
        env_vars["RAILS_ENV"] = "production"
        env_vars["SECRET_KEY_BASE"] = "<secret_key>"

    return env_vars


async def _determine_build_steps(app_path: str, framework: str) -> List[str]:
    """Determines build steps based on framework."""
    build_steps = []

    if framework in ["flask", "django"]:
        build_steps = [
            "COPY requirements.txt .",
            "RUN pip install --no-cache-dir -r requirements.txt",
            "COPY . .",
        ]
    elif framework in ["express", "react", "node"]:
        build_steps = [
            "COPY package*.json .",
            "RUN npm install",
            "COPY . .",
        ]

        # Check if there's a build script in package.json
        pkg_path = os.path.join(app_path, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r") as f:
                    pkg_data = json.load(f)
                    if "scripts" in pkg_data and "build" in pkg_data["scripts"]:
                        build_steps.append("RUN npm run build")
            except (json.JSONDecodeError, IOError):
                pass

    elif framework == "rails":
        build_steps = [
            "COPY Gemfile Gemfile.lock .",
            "RUN bundle install",
            "COPY . .",
            "RUN rails assets:precompile",
        ]

    return build_steps


async def _determine_runtime_requirements(app_path: str, framework: str) -> Dict[str, Any]:
    """Determines runtime requirements based on framework."""
    requirements = {
        "memory_min": 512,  # Default minimum memory in MB
        "cpu_min": 256,  # Default minimum CPU units
    }

    # Adjust based on framework
    if framework in ["django", "rails"]:
        requirements["memory_min"] = 1024

    return requirements
