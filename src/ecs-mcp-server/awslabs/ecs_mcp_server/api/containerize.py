"""
API for containerizing web applications.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from awslabs.ecs_mcp_server.api.analyze import analyze_app
from awslabs.ecs_mcp_server.utils.docker import validate_dockerfile
from awslabs.ecs_mcp_server.utils.templates import get_templates_dir

logger = logging.getLogger(__name__)


async def containerize_app(
    app_path: str,
    framework: Optional[str] = None,
    port: Optional[int] = None,
    environment_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Generates Dockerfile and container configurations for a web application.

    Args:
        app_path: Path to the web application directory
        framework: Web framework used (optional, will be auto-detected if not provided)
        port: Port the application listens on (optional)
        environment_vars: Environment variables as a dictionary (optional)

    Returns:
        Dict containing containerization results
    """
    logger.info(f"Containerizing web application at {app_path}")

    # First analyze the app to get framework and requirements
    analysis = await analyze_app(app_path, framework)

    # Use provided port or default from analysis
    container_port = port or analysis["default_port"]

    # Merge provided environment variables with detected ones
    env_vars = analysis["environment_variables"].copy()
    if environment_vars:
        env_vars.update(environment_vars)

    # Generate Dockerfile
    dockerfile_content = await _generate_dockerfile(
        app_path=app_path,
        framework=analysis["framework"],
        build_steps=analysis["build_steps"],
        base_image=analysis["container_requirements"]["base_image"],
        port=container_port,
        env_vars=env_vars,
    )

    # Write Dockerfile to app directory
    dockerfile_path = os.path.join(app_path, "Dockerfile")
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)

    # Generate docker-compose.yml for local testing
    docker_compose_content = await _generate_docker_compose(
        app_name=os.path.basename(os.path.abspath(app_path)), port=container_port, env_vars=env_vars
    )

    # Write docker-compose.yml to app directory
    docker_compose_path = os.path.join(app_path, "docker-compose.yml")
    with open(docker_compose_path, "w") as f:
        f.write(docker_compose_content)

    # Validate the generated Dockerfile
    validation_result = await validate_dockerfile(dockerfile_path)

    return {
        "dockerfile_path": dockerfile_path,
        "docker_compose_path": docker_compose_path,
        "container_port": container_port,
        "environment_variables": env_vars,
        "validation_result": validation_result,
        "framework": analysis["framework"],
        "base_image": analysis["container_requirements"]["base_image"],
    }


async def _generate_dockerfile(
    app_path: str,
    framework: str,
    build_steps: List[str],
    base_image: str,
    port: int,
    env_vars: Dict[str, str],
) -> str:
    """Generates a Dockerfile based on the application framework and requirements."""
    templates_dir = get_templates_dir()
    env = Environment(loader=FileSystemLoader(templates_dir))

    # Select the appropriate template based on framework
    template_name = f"dockerfile_{framework}.j2"
    if not os.path.exists(os.path.join(templates_dir, template_name)):
        template_name = "dockerfile_generic.j2"

    template = env.get_template(template_name)

    # Determine the command to run the application
    cmd = _get_run_command(framework, app_path)

    # Render the template
    dockerfile_content = template.render(
        base_image=base_image, build_steps=build_steps, port=port, env_vars=env_vars, cmd=cmd
    )

    return dockerfile_content


def _get_run_command(framework: str, app_path: str) -> str:
    """Returns the appropriate command to run the application based on framework."""
    if framework == "flask":
        return ["flask", "run", "--host=0.0.0.0"]
    elif framework == "django":
        return ["python", "manage.py", "runserver", "0.0.0.0:8000"]
    elif framework == "express" or framework == "node":
        # Check package.json for start script and main file
        pkg_path = os.path.join(app_path, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r") as f:
                    pkg_data = json.load(f)
                    if "scripts" in pkg_data and "start" in pkg_data["scripts"]:
                        # Get the actual command from the start script
                        start_script = pkg_data["scripts"]["start"]
                        if start_script.startswith("node "):
                            # Extract the file name from the start script
                            file_name = start_script.replace("node ", "").strip()
                            return ["node", file_name]
                    # If no start script or it's not a node command, check for main file
                    if "main" in pkg_data:
                        return ["node", pkg_data["main"]]
            except (json.JSONDecodeError, IOError):
                pass
        
        # Check for common entry point files
        for file_name in ["server.js", "app.js", "index.js"]:
            if os.path.exists(os.path.join(app_path, file_name)):
                return ["node", file_name]
                
        return ["node", "index.js"]
    elif framework == "rails":
        return ["rails", "server", "-b", "0.0.0.0"]
    else:
        return ["nginx", "-g", "daemon off;"]


async def _generate_docker_compose(app_name: str, port: int, env_vars: Dict[str, str]) -> str:
    """Generates a docker-compose.yml file for local testing."""
    templates_dir = get_templates_dir()
    env = Environment(loader=FileSystemLoader(templates_dir))

    template = env.get_template("docker-compose.yml.j2")

    # Render the template
    docker_compose_content = template.render(app_name=app_name, port=port, env_vars=env_vars)

    return docker_compose_content
