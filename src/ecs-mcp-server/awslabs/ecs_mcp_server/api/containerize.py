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

    # For Django apps, ensure we have gunicorn for production
    if analysis["framework"] == "django":
        # Check if we need to add gunicorn to requirements.txt
        req_path = os.path.join(app_path, "requirements.txt")
        if os.path.exists(req_path):
            try:
                with open(req_path, "r") as f:
                    content = f.read()
                    if "gunicorn" not in content.lower():
                        logger.info("Adding gunicorn to requirements.txt for production readiness")
                        with open(req_path, "a") as f:
                            f.write("\ngunicorn>=20.1.0\n")
            except Exception as e:
                logger.warning(f"Error modifying requirements.txt: {e}")

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
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True
    )

    # Select the appropriate template based on framework
    template_name = f"dockerfile_{framework}.j2"
    if not os.path.exists(os.path.join(templates_dir, template_name)):
        template_name = "dockerfile_generic.j2"

    template = env.get_template(template_name)

    # Determine the command to run the application
    cmd = _get_run_command(framework, app_path)

    # No need to convert cmd to JSON string, we'll handle it in the template
    # The template will properly format the CMD instruction based on the type
        
    # Additional template parameters
    template_params = {
        "base_image": base_image,
        "build_steps": build_steps,
        "port": port,
        "env_vars": env_vars,
        "cmd": cmd,
    }
    
    # For React applications, check if nginx.conf exists
    if framework == "react":
        nginx_conf_exists = os.path.exists(os.path.join(app_path, "nginx.conf"))
        template_params["nginx_conf_exists"] = nginx_conf_exists
        if not nginx_conf_exists:
            logger.info("No nginx.conf found for React app, will create a default one")
            # Create a default nginx.conf if it doesn't exist
            default_nginx_conf = """server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}"""
            nginx_conf_path = os.path.join(app_path, "nginx.conf")
            with open(nginx_conf_path, "w") as f:
                f.write(default_nginx_conf)
            logger.info(f"Created default nginx.conf at {nginx_conf_path}")

    # Render the template
    dockerfile_content = template.render(**template_params)

    return dockerfile_content


def _get_run_command(framework: str, app_path: str) -> str:
    """Returns the appropriate command to run the application based on framework."""
    if framework == "flask":
        # Check if gunicorn is in requirements.txt for Flask
        if _has_gunicorn(app_path):
            logger.info("Detected gunicorn in Flask app, using it for production deployment")
            # Get the Flask application module
            app_module = _detect_flask_app_module(app_path) or "app:app"
            return ["gunicorn", "--bind", "0.0.0.0:5000", app_module]
        return ["flask", "run", "--host=0.0.0.0"]
    elif framework == "django":
        # For Django, prefer gunicorn for production but support both options
        use_gunicorn = _has_gunicorn(app_path)
        
        # Get the Django project name
        project_name = _detect_django_project_name(app_path) or "project"
        
        if use_gunicorn:
            logger.info("Using gunicorn for Django app (recommended for production)")
            # Add workers and timeout for better performance and reliability
            return ["gunicorn", "--bind", "0.0.0.0:8000", "--workers=3", "--timeout=120", f"{project_name}.wsgi:application"]
        else:
            logger.warning("Using Django development server. Consider adding gunicorn for production.")
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


def _has_gunicorn(app_path: str) -> bool:
    """Check if gunicorn is in requirements.txt or Pipfile."""
    # Check requirements.txt
    req_path = os.path.join(app_path, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r") as f:
                content = f.read().lower()
                if "gunicorn" in content:
                    return True
        except Exception as e:
            logger.warning(f"Error reading requirements.txt: {e}")
    
    # Check Pipfile
    pipfile_path = os.path.join(app_path, "Pipfile")
    if os.path.exists(pipfile_path):
        try:
            with open(pipfile_path, "r") as f:
                content = f.read().lower()
                if "gunicorn" in content:
                    return True
        except Exception as e:
            logger.warning(f"Error reading Pipfile: {e}")
    
    return False


def _detect_flask_app_module(app_path: str) -> str:
    """Detect the Flask application module."""
    # Common Flask app patterns
    for file_name in ["app.py", "main.py", "wsgi.py", "application.py"]:
        file_path = os.path.join(app_path, file_name)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    # Look for app = Flask(__name__) pattern
                    if "Flask(__name__)" in content:
                        module_name = file_name.replace(".py", "")
                        # Check if there's a specific app variable name
                        import re
                        app_var_match = re.search(r"(\w+)\s*=\s*Flask\(__name__\)", content)
                        if app_var_match:
                            app_var = app_var_match.group(1)
                            return f"{module_name}:{app_var}"
                        return f"{module_name}:app"
            except Exception as e:
                logger.warning(f"Error analyzing Flask app file {file_name}: {e}")
    
    # Default to app:app if we can't detect
    return "app:app"


def _detect_django_project_name(app_path: str) -> str:
    """Detect the Django project name."""
    # Check manage.py for project name
    manage_py_path = os.path.join(app_path, "manage.py")
    if os.path.exists(manage_py_path):
        try:
            with open(manage_py_path, "r") as f:
                content = f.read()
                # Look for "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectname.settings')"
                import re
                settings_match = re.search(r"DJANGO_SETTINGS_MODULE['\"],\s*['\"]([^.]+)\.settings", content)
                if settings_match:
                    return settings_match.group(1)
        except Exception as e:
            logger.warning(f"Error detecting Django project name: {e}")
    
    # Default to project if we can't detect
    return "project"


async def _generate_docker_compose(app_name: str, port: int, env_vars: Dict[str, str]) -> str:
    """Generates a docker-compose.yml file for local testing."""
    templates_dir = get_templates_dir()
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True
    )

    template = env.get_template("docker-compose.yml.j2")

    # Render the template
    docker_compose_content = template.render(app_name=app_name, port=port, env_vars=env_vars)

    return docker_compose_content
