"""
Utilities for detecting web application frameworks.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


async def detect_framework(app_path: str) -> Optional[str]:
    """
    Detects the web application framework used in the given directory.

    Args:
        app_path: Path to the web application directory

    Returns:
        Framework name or None if not detected
    """
    logger.info(f"Detecting framework for application at {app_path}")

    # Check for Python frameworks
    if await _is_flask(app_path):
        return "flask"

    if await _is_django(app_path):
        return "django"

    # Check for Node.js frameworks
    if await _is_express(app_path):
        return "express"

    if await _is_react(app_path):
        return "react"

    # Check for Ruby frameworks
    if await _is_rails(app_path):
        return "rails"

    # Generic Node.js
    if await _is_node(app_path):
        return "node"

    # Could not determine framework
    return None


async def _is_flask(app_path: str) -> bool:
    """Checks if the application is a Flask application."""
    # Check for Flask imports in Python files
    for root, _, files in os.walk(app_path):
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r") as f:
                        content = f.read()
                        if "from flask import" in content or "import flask" in content:
                            return True
                except Exception:
                    pass

    # Check for Flask in requirements.txt
    req_path = os.path.join(app_path, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r") as f:
                content = f.read()
                if "flask" in content.lower():
                    return True
        except Exception:
            pass

    return False


async def _is_django(app_path: str) -> bool:
    """Checks if the application is a Django application."""
    # Check for Django-specific files
    if os.path.exists(os.path.join(app_path, "manage.py")):
        try:
            with open(os.path.join(app_path, "manage.py"), "r") as f:
                content = f.read()
                if "django" in content.lower():
                    return True
        except Exception:
            pass

    # Check for Django imports in Python files
    for root, _, files in os.walk(app_path):
        for file in files:
            if file.endswith(".py"):
                try:
                    with open(os.path.join(root, file), "r") as f:
                        content = f.read()
                        if "from django import" in content or "import django" in content:
                            return True
                except Exception:
                    pass

    # Check for Django in requirements.txt
    req_path = os.path.join(app_path, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r") as f:
                content = f.read()
                if "django" in content.lower():
                    return True
        except Exception:
            pass

    return False


async def _is_express(app_path: str) -> bool:
    """Checks if the application is an Express.js application."""
    # Check for Express in package.json
    pkg_path = os.path.join(app_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                if "express" in deps:
                    return True
        except Exception:
            pass

    # Check for Express imports in JavaScript files
    for root, _, files in os.walk(app_path):
        for file in files:
            if file.endswith((".js", ".ts")):
                try:
                    with open(os.path.join(root, file), "r") as f:
                        content = f.read()
                        if "require('express')" in content or 'require("express")' in content:
                            return True
                        if "from 'express'" in content or 'from "express"' in content:
                            return True
                except Exception:
                    pass

    return False


async def _is_react(app_path: str) -> bool:
    """Checks if the application is a React application."""
    # Check for React in package.json
    pkg_path = os.path.join(app_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                if "react" in deps and "react-dom" in deps:
                    return True
        except Exception:
            pass

    # Check for JSX files
    for root, _, files in os.walk(app_path):
        for file in files:
            if file.endswith((".jsx", ".tsx")):
                return True

    return False


async def _is_rails(app_path: str) -> bool:
    """Checks if the application is a Ruby on Rails application."""
    # Check for Rails-specific files
    if os.path.exists(os.path.join(app_path, "config", "routes.rb")):
        return True

    if os.path.exists(os.path.join(app_path, "Gemfile")):
        try:
            with open(os.path.join(app_path, "Gemfile"), "r") as f:
                content = f.read()
                if "rails" in content.lower():
                    return True
        except Exception:
            pass

    return False


async def _is_node(app_path: str) -> bool:
    """Checks if the application is a Node.js application."""
    # Check for package.json
    if os.path.exists(os.path.join(app_path, "package.json")):
        return True

    # Check for Node.js files
    for root, _, files in os.walk(app_path):
        for file in files:
            if file.endswith((".js", ".ts")):
                return True

    return False
