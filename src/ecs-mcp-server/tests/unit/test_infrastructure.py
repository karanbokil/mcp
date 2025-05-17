"""
Unit tests for infrastructure module.
"""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.infrastructure import (
    create_infrastructure,
    create_ecr_infrastructure,
    create_ecs_infrastructure,
)


class TestInfrastructure(unittest.TestCase):
    """Unit tests for infrastructure module."""

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
    @patch("awslabs.ecs_mcp_server.api.infrastructure.get_default_vpc_and_subnets")
    async def test_create_ecs_infrastructure(
        self, mock_get_vpc, mock_get_account_id, mock_get_aws_client
    ):
        """Test creating ECS infrastructure with updated template."""
        # Setup mocks
        mock_get_account_id.return_value = "123456789012"
        mock_get_vpc.return_value = {
            "vpc_id": "vpc-12345",
            "subnet_ids": ["subnet-1", "subnet-2"],
        }
        
        mock_cf_client = MagicMock()
        mock_cf_client.create_stack.return_value = {"StackId": "stack-id"}
        mock_get_aws_client.return_value = mock_cf_client
        
        # Call the function
        result = await create_ecs_infrastructure(
            app_name="test-app",
            image_uri="test-image",
            cpu=256,
            memory=512,
            desired_count=1,
            container_port=80,
            health_check_path="/",
            force_deploy=True,
        )
        
        # Verify the function called CloudFormation with the correct parameters
        mock_cf_client.create_stack.assert_called_once()
        
        # Extract the parameters from the call
        call_args = mock_cf_client.create_stack.call_args[1]
        parameters = call_args["Parameters"]
        
        # Verify expected parameters are present
        param_keys = [p["ParameterKey"] for p in parameters]
        self.assertIn("AppName", param_keys)
        self.assertIn("VpcId", param_keys)
        self.assertIn("SubnetIds", param_keys)
        self.assertIn("TaskCpu", param_keys)
        self.assertIn("TaskMemory", param_keys)
        self.assertIn("DesiredCount", param_keys)
        self.assertIn("ImageUri", param_keys)
        self.assertIn("ContainerPort", param_keys)
        self.assertIn("HealthCheckPath", param_keys)
        self.assertIn("Timestamp", param_keys)


if __name__ == "__main__":
    unittest.main()
