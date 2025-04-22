"""
Integration tests for ECS MCP Server.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from awslabs.ecs_mcp_server.api.analyze import analyze_app
from awslabs.ecs_mcp_server.api.containerize import containerize_app
from awslabs.ecs_mcp_server.api.deploy import deploy_to_ecs
from awslabs.ecs_mcp_server.api.status import get_deployment_status


class TestIntegration(unittest.TestCase):
    """Integration tests for ECS MCP Server."""

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.containerize.analyze_app")
    @patch("awslabs.ecs_mcp_server.api.containerize._generate_dockerfile")
    @patch("awslabs.ecs_mcp_server.api.containerize._generate_docker_compose")
    @patch("awslabs.ecs_mcp_server.api.containerize.validate_dockerfile")
    async def test_analyze_and_containerize_flow(
        self, mock_validate, mock_docker_compose, mock_dockerfile, mock_analyze
    ):
        """Test the flow from analyze_app to containerize_app."""
        # Mock analyze_app to return a sample analysis
        mock_analyze.return_value = {
            "framework": "flask",
            "default_port": 5000,
            "environment_variables": {"FLASK_ENV": "production"},
            "build_steps": ["COPY requirements.txt .", "RUN pip install -r requirements.txt"],
            "container_requirements": {"base_image": "python:3.9-slim"},
        }
        
        # Mock _generate_dockerfile to return a sample Dockerfile content
        mock_dockerfile.return_value = "FROM python:3.9-slim\nWORKDIR /app\n..."
        
        # Mock _generate_docker_compose to return a sample docker-compose.yml content
        mock_docker_compose.return_value = "version: '3'\nservices:\n  app:\n    build: ."
        
        # Mock validate_dockerfile to return a successful validation
        mock_validate.return_value = {
            "valid": True,
            "message": "Dockerfile validation passed",
            "warnings": [],
            "errors": [],
        }
        
        # Call containerize_app
        result = await containerize_app(
            app_path="/app",
            port=8000,
            environment_vars={"DEBUG": "false"}
        )
        
        # Verify analyze_app was called with correct parameters
        mock_analyze.assert_called_once_with("/app", None)
        
        # Verify the result contains expected keys
        self.assertIn("dockerfile_path", result)
        self.assertIn("docker_compose_path", result)
        self.assertIn("container_port", result)
        self.assertIn("environment_variables", result)
        self.assertIn("validation_result", result)
        self.assertIn("framework", result)
        self.assertIn("base_image", result)
        
        # Verify the container port was set to the provided value
        self.assertEqual(result["container_port"], 8000)
        
        # Verify environment variables were merged
        self.assertIn("FLASK_ENV", result["environment_variables"])
        self.assertIn("DEBUG", result["environment_variables"])
        self.assertEqual(result["environment_variables"]["DEBUG"], "false")

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.deploy.containerize_app")
    @patch("awslabs.ecs_mcp_server.api.deploy.create_infrastructure")
    @patch("awslabs.ecs_mcp_server.api.deploy.build_and_push_image")
    @patch("awslabs.ecs_mcp_server.api.deploy._update_task_definition")
    @patch("awslabs.ecs_mcp_server.api.deploy._update_ecs_service")
    @patch("awslabs.ecs_mcp_server.api.deploy._get_alb_url")
    @patch("awslabs.ecs_mcp_server.api.deploy.get_aws_account_id")
    async def test_deploy_flow(
        self, mock_get_account_id, mock_get_alb_url, mock_update_service, 
        mock_update_task, mock_build_push, mock_create_infra, mock_containerize
    ):
        """Test the flow from containerize_app to deploy_to_ecs."""
        # Mock get_aws_account_id
        mock_get_account_id.return_value = "123456789012"
        
        # Mock containerize_app to return a sample containerization result
        mock_containerize.return_value = {
            "dockerfile_path": "/app/Dockerfile",
            "docker_compose_path": "/app/docker-compose.yml",
            "container_port": 5000,
            "environment_variables": {"FLASK_ENV": "production"},
            "validation_result": {"valid": True},
            "framework": "flask",
            "base_image": "python:3.9-slim",
        }
        
        # Mock create_infrastructure to return a sample infrastructure result
        mock_create_infra.return_value = {
            "stack_name": "test-app-ecs-infrastructure",
            "stack_id": "arn:aws:cloudformation:us-east-1:123456789012:stack/test-app-ecs-infrastructure/1234",
            "operation": "create",
            "template_path": "test-app-ecs-infrastructure.json",
            "vpc_id": "vpc-12345678",
            "subnet_ids": ["subnet-12345678", "subnet-87654321"],
            "resources": {
                "cluster": "test-app-cluster",
                "service": "test-app-service",
                "task_definition": "test-app-task",
                "load_balancer": "test-app-alb",
                "ecr_repository": "test-app-repo",
            }
        }
        
        # Mock build_and_push_image to return a sample image tag
        mock_build_push.return_value = "latest"
        
        # Mock _update_task_definition to return a sample task definition
        mock_update_task.return_value = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test-app-task:1"
        }
        
        # Mock _update_ecs_service to return a sample service
        mock_update_service.return_value = {
            "serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/test-app-cluster/test-app-service"
        }
        
        # Mock _get_alb_url to return a sample ALB URL
        mock_get_alb_url.return_value = "http://test-app-alb-1234567890.us-east-1.elb.amazonaws.com"
        
        # Call deploy_to_ecs
        result = await deploy_to_ecs(
            app_path="/app",
            app_name="test-app",
            container_port=5000,
            cpu=256,
            memory=512,
            environment_vars={"DEBUG": "false"},
            health_check_path="/health"
        )
        
        # Verify containerize_app was called with correct parameters
        mock_containerize.assert_called_once()
        args, kwargs = mock_containerize.call_args
        self.assertEqual(kwargs["app_path"], "/app")
        self.assertEqual(kwargs["port"], 5000)
        self.assertEqual(kwargs["environment_vars"], {"DEBUG": "false"})
        
        # Verify create_infrastructure was called with correct parameters
        mock_create_infra.assert_called_once()
        args, kwargs = mock_create_infra.call_args
        self.assertEqual(kwargs["app_name"], "test-app")
        self.assertEqual(kwargs["cpu"], 256)
        self.assertEqual(kwargs["memory"], 512)
        
        # Verify build_and_push_image was called
        mock_build_push.assert_called_once()
        
        # Verify _update_task_definition was called
        mock_update_task.assert_called_once()
        
        # Verify _update_ecs_service was called
        mock_update_service.assert_called_once()
        
        # Verify _get_alb_url was called
        mock_get_alb_url.assert_called_once_with("test-app")
        
        # Verify the result contains expected keys
        self.assertIn("app_name", result)
        self.assertIn("repository_uri", result)
        self.assertIn("image_tag", result)
        self.assertIn("task_definition_arn", result)
        self.assertIn("service_arn", result)
        self.assertIn("alb_url", result)
        self.assertIn("status", result)
        self.assertIn("message", result)
        
        # Verify the ALB URL was returned
        self.assertEqual(result["alb_url"], "http://test-app-alb-1234567890.us-east-1.elb.amazonaws.com")

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
    async def test_get_deployment_status(self, mock_get_alb_url, mock_get_client):
        """Test get_deployment_status function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            "services": [{
                "serviceName": "test-app-service",
                "status": "ACTIVE",
                "desiredCount": 2,
                "runningCount": 2,
                "pendingCount": 0,
                "deployments": [{
                    "status": "PRIMARY",
                    "rolloutState": "COMPLETED",
                    "desiredCount": 2,
                    "runningCount": 2,
                }]
            }]
        }
        mock_ecs.list_tasks.return_value = {
            "taskArns": [
                "arn:aws:ecs:us-east-1:123456789012:task/test-app-cluster/1234567890abcdef",
                "arn:aws:ecs:us-east-1:123456789012:task/test-app-cluster/fedcba0987654321"
            ]
        }
        mock_ecs.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/test-app-cluster/1234567890abcdef",
                    "lastStatus": "RUNNING",
                    "healthStatus": "HEALTHY",
                    "startedAt": "2023-01-01T00:00:00Z"
                },
                {
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/test-app-cluster/fedcba0987654321",
                    "lastStatus": "RUNNING",
                    "healthStatus": "HEALTHY",
                    "startedAt": "2023-01-01T00:00:00Z"
                }
            ]
        }
        mock_get_client.return_value = mock_ecs
        
        # Mock _get_alb_url to return a sample ALB URL
        mock_get_alb_url.return_value = "http://test-app-alb-1234567890.us-east-1.elb.amazonaws.com"
        
        # Call get_deployment_status
        result = await get_deployment_status(app_name="test-app")
        
        # Verify get_aws_client was called with the correct parameters
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify describe_services was called with the correct parameters
        mock_ecs.describe_services.assert_called_once()
        args, kwargs = mock_ecs.describe_services.call_args
        self.assertEqual(kwargs["cluster"], "test-app-cluster")
        self.assertEqual(kwargs["services"], ["test-app-service"])
        
        # Verify list_tasks was called with the correct parameters
        mock_ecs.list_tasks.assert_called_once()
        args, kwargs = mock_ecs.list_tasks.call_args
        self.assertEqual(kwargs["cluster"], "test-app-cluster")
        self.assertEqual(kwargs["serviceName"], "test-app-service")
        
        # Verify describe_tasks was called with the correct parameters
        mock_ecs.describe_tasks.assert_called_once()
        
        # Verify _get_alb_url was called
        mock_get_alb_url.assert_called_once_with("test-app")
        
        # Verify the result contains expected keys
        self.assertIn("app_name", result)
        self.assertIn("cluster", result)
        self.assertIn("service_status", result)
        self.assertIn("deployment_status", result)
        self.assertIn("alb_url", result)
        self.assertIn("tasks", result)
        self.assertIn("running_count", result)
        self.assertIn("desired_count", result)
        self.assertIn("pending_count", result)
        self.assertIn("message", result)
        
        # Verify the deployment status was returned
        self.assertEqual(result["deployment_status"], "COMPLETED")
        
        # Verify the ALB URL was returned
        self.assertEqual(result["alb_url"], "http://test-app-alb-1234567890.us-east-1.elb.amazonaws.com")
        
        # Verify the task count was returned
        self.assertEqual(result["running_count"], 2)
        self.assertEqual(result["desired_count"], 2)
        self.assertEqual(result["pending_count"], 0)


if __name__ == "__main__":
    unittest.main()
