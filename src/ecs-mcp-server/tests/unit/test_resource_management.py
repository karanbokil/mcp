"""
Unit tests for ECS resource management module.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

import pytest

from awslabs.ecs_mcp_server.api.resource_management import (
    ecs_resource_management,
    list_clusters,
    describe_cluster,
    list_services,
    describe_service,
    list_tasks,
    describe_task,
    list_task_definitions,
    describe_task_definition,
    list_container_instances,
    describe_container_instance,
    list_capacity_providers,
    describe_capacity_provider,
)


class TestEcsResourceManagement(unittest.TestCase):
    """Tests for the main ecs_resource_management function."""
    
    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.list_clusters")
    async def test_ecs_resource_management_list_clusters(self, mock_list_clusters):
        """Test routing to list_clusters handler."""
        # Setup mock
        mock_list_clusters.return_value = {"clusters": [], "count": 0}
        
        # Call the function
        result = await ecs_resource_management("list", "cluster")
        
        # Verify list_clusters was called with empty filters
        mock_list_clusters.assert_called_once_with({})
        
        # Verify result
        self.assertEqual(result, {"clusters": [], "count": 0})

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.describe_cluster")
    async def test_ecs_resource_management_describe_cluster(self, mock_describe_cluster):
        """Test routing to describe_cluster handler."""
        # Setup mock
        mock_describe_cluster.return_value = {"cluster": {}, "service_count": 0}
        
        # Call the function
        result = await ecs_resource_management("describe", "cluster", "test-cluster")
        
        # Verify describe_cluster was called with correct parameters
        mock_describe_cluster.assert_called_once_with("test-cluster", {})
        
        # Verify result
        self.assertEqual(result, {"cluster": {}, "service_count": 0})

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.list_services")
    async def test_ecs_resource_management_list_services(self, mock_list_services):
        """Test routing to list_services handler."""
        # Setup mock
        mock_list_services.return_value = {"services": [], "count": 0}
        
        # Define filters
        filters = {"cluster": "test-cluster"}
        
        # Call the function
        result = await ecs_resource_management("list", "service", filters=filters)
        
        # Verify list_services was called with correct filters
        mock_list_services.assert_called_once_with(filters)
        
        # Verify result
        self.assertEqual(result, {"services": [], "count": 0})

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.describe_service")
    async def test_ecs_resource_management_describe_service(self, mock_describe_service):
        """Test routing to describe_service handler."""
        # Setup mock
        mock_describe_service.return_value = {"service": {}}
        
        # Define filters
        filters = {"cluster": "test-cluster"}
        
        # Call the function
        result = await ecs_resource_management("describe", "service", "test-service", filters)
        
        # Verify describe_service was called with correct parameters
        mock_describe_service.assert_called_once_with("test-service", filters)
        
        # Verify result
        self.assertEqual(result, {"service": {}})

    @pytest.mark.asyncio
    async def test_ecs_resource_management_describe_service_missing_cluster(self):
        """Test validation for describe_service when cluster is missing."""
        # Call the function and expect ValueError
        with self.assertRaises(ValueError) as context:
            await ecs_resource_management("describe", "service", "test-service")
        
        # Verify error message
        self.assertIn("cluster", str(context.exception))

    @pytest.mark.asyncio
    async def test_ecs_resource_management_invalid_action(self):
        """Test validation for invalid action."""
        # Call the function and expect ValueError
        with self.assertRaises(ValueError) as context:
            await ecs_resource_management("invalid", "cluster")
        
        # Verify error message
        self.assertIn("Unsupported action", str(context.exception))

    @pytest.mark.asyncio
    async def test_ecs_resource_management_invalid_resource_type(self):
        """Test validation for invalid resource type."""
        # Call the function and expect ValueError
        with self.assertRaises(ValueError) as context:
            await ecs_resource_management("list", "invalid")
        
        # Verify error message
        self.assertIn("Unsupported resource type", str(context.exception))

    @pytest.mark.asyncio
    async def test_ecs_resource_management_describe_missing_identifier(self):
        """Test validation for describe action missing identifier."""
        # Call the function and expect ValueError
        with self.assertRaises(ValueError) as context:
            await ecs_resource_management("describe", "cluster")
        
        # Verify error message
        self.assertIn("Identifier is required", str(context.exception))


class TestClusterOperations(unittest.TestCase):
    """Tests for cluster operations."""
    
    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_clusters(self, mock_get_client):
        """Test list_clusters function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster"]
        }
        mock_ecs.describe_clusters.return_value = {
            "clusters": [{"clusterName": "test-cluster", "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster"}]
        }
        mock_get_client.return_value = mock_ecs
        
        # Call list_clusters
        result = await list_clusters({})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify list_clusters was called
        mock_ecs.list_clusters.assert_called_once()
        
        # Verify describe_clusters was called with correct parameters
        mock_ecs.describe_clusters.assert_called_once()
        args, kwargs = mock_ecs.describe_clusters.call_args
        self.assertIn("clusters", kwargs)
        
        # Verify the result
        self.assertIn("clusters", result)
        self.assertEqual(len(result["clusters"]), 1)
        self.assertEqual(result["count"], 1)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_clusters_empty(self, mock_get_client):
        """Test list_clusters function with empty result."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": []}
        mock_get_client.return_value = mock_ecs
        
        # Call list_clusters
        result = await list_clusters({})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify list_clusters was called
        mock_ecs.list_clusters.assert_called_once()
        
        # Verify describe_clusters was not called
        mock_ecs.describe_clusters.assert_not_called()
        
        # Verify the result
        self.assertIn("clusters", result)
        self.assertEqual(len(result["clusters"]), 0)
        self.assertEqual(result["count"], 0)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_clusters_error(self, mock_get_client):
        """Test list_clusters function with error."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.side_effect = Exception("Test error")
        mock_get_client.return_value = mock_ecs
        
        # Call list_clusters
        result = await list_clusters({})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify list_clusters was called
        mock_ecs.list_clusters.assert_called_once()
        
        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["clusters"], [])
        self.assertEqual(result["count"], 0)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_cluster(self, mock_get_client):
        """Test describe_cluster function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_clusters.return_value = {
            "clusters": [{"clusterName": "test-cluster", "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster"}]
        }
        mock_ecs.list_services.return_value = {"serviceArns": ["service-1", "service-2"]}
        mock_ecs.list_tasks.side_effect = [
            {"taskArns": ["task-1", "task-2"]},  # Running tasks
            {"taskArns": ["task-3"]}            # Stopped tasks
        ]
        mock_get_client.return_value = mock_ecs
        
        # Call describe_cluster
        result = await describe_cluster("test-cluster", {})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify describe_clusters was called with correct parameters
        mock_ecs.describe_clusters.assert_called_once()
        args, kwargs = mock_ecs.describe_clusters.call_args
        self.assertIn("clusters", kwargs)
        self.assertEqual(kwargs["clusters"], ["test-cluster"])
        
        # Verify list_services was called
        mock_ecs.list_services.assert_called_once()
        
        # Verify list_tasks was called twice (for running and stopped tasks)
        self.assertEqual(mock_ecs.list_tasks.call_count, 2)
        
        # Verify the result
        self.assertIn("cluster", result)
        self.assertEqual(result["cluster"]["clusterName"], "test-cluster")
        self.assertEqual(result["service_count"], 2)
        self.assertEqual(result["running_task_count"], 2)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_cluster_not_found(self, mock_get_client):
        """Test describe_cluster function with non-existent cluster."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_clusters.return_value = {"clusters": []}
        mock_get_client.return_value = mock_ecs
        
        # Call describe_cluster
        result = await describe_cluster("non-existent-cluster", {})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify describe_clusters was called
        mock_ecs.describe_clusters.assert_called_once()
        
        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["cluster"], None)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_cluster_error(self, mock_get_client):
        """Test describe_cluster function with error."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_clusters.side_effect = Exception("Test error")
        mock_get_client.return_value = mock_ecs
        
        # Call describe_cluster
        result = await describe_cluster("test-cluster", {})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify describe_clusters was called
        mock_ecs.describe_clusters.assert_called_once()
        
        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["cluster"], None)


class TestServiceOperations(unittest.TestCase):
    """Tests for service operations."""
    
    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_services_specific_cluster(self, mock_get_client):
        """Test list_services function with specific cluster."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_services.return_value = {"serviceArns": ["service-1", "service-2"]}
        mock_ecs.describe_services.return_value = {
            "services": [
                {"serviceName": "service-1", "serviceArn": "service-1"},
                {"serviceName": "service-2", "serviceArn": "service-2"}
            ]
        }
        mock_get_client.return_value = mock_ecs
        
        # Call list_services with cluster filter
        result = await list_services({"cluster": "test-cluster"})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify list_services was called with correct cluster
        mock_ecs.list_services.assert_called_once()
        args, kwargs = mock_ecs.list_services.call_args
        self.assertEqual(kwargs["cluster"], "test-cluster")
        
        # Verify describe_services was called
        mock_ecs.describe_services.assert_called_once()
        
        # Verify the result
        self.assertIn("services", result)
        self.assertEqual(len(result["services"]), 2)
        self.assertEqual(result["count"], 2)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_services_all_clusters(self, mock_get_client):
        """Test list_services function for all clusters."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.return_value = {"clusterArns": ["cluster-1", "cluster-2"]}
        mock_ecs.list_services.return_value = {"serviceArns": ["service-1"]}
        mock_ecs.describe_services.return_value = {
            "services": [{"serviceName": "service-1", "serviceArn": "service-1"}]
        }
        mock_get_client.return_value = mock_ecs
        
        # Call list_services without cluster filter
        result = await list_services({})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify list_clusters was called
        mock_ecs.list_clusters.assert_called_once()
        
        # Verify list_services and describe_services were called for each cluster
        self.assertEqual(mock_ecs.list_services.call_count, 2)
        self.assertEqual(mock_ecs.describe_services.call_count, 2)
        
        # Verify the result
        self.assertIn("services", result)
        self.assertEqual(len(result["services"]), 2)  # 1 service from each of 2 clusters
        self.assertEqual(result["count"], 2)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_services_error(self, mock_get_client):
        """Test list_services function with error."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_clusters.side_effect = Exception("Test error")
        mock_get_client.return_value = mock_ecs
        
        # Call list_services
        result = await list_services({})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify the result contains error
        self.assertIn("error", result)
        self.assertEqual(result["services"], [])
        self.assertEqual(result["count"], 0)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_service(self, mock_get_client):
        """Test describe_service function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_services.return_value = {
            "services": [{"serviceName": "test-service", "events": [{"message": "event-1"}, {"message": "event-2"}]}]
        }
        mock_ecs.list_tasks.side_effect = [
            {"taskArns": ["task-1", "task-2"]},  # Running tasks
            {"taskArns": ["task-3"]}            # Stopped tasks
        ]
        mock_get_client.return_value = mock_ecs
        
        # Call describe_service
        result = await describe_service("test-service", {"cluster": "test-cluster"})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify describe_services was called with correct parameters
        mock_ecs.describe_services.assert_called_once()
        args, kwargs = mock_ecs.describe_services.call_args
        self.assertEqual(kwargs["cluster"], "test-cluster")
        self.assertEqual(kwargs["services"], ["test-service"])
        
        # Verify list_tasks was called twice (for running and stopped tasks)
        self.assertEqual(mock_ecs.list_tasks.call_count, 2)
        
        # Verify the result
        self.assertIn("service", result)
        self.assertEqual(result["service"]["serviceName"], "test-service")
        self.assertEqual(result["running_task_count"], 2)
        self.assertEqual(result["stopped_task_count"], 1)
        self.assertEqual(len(result["recent_events"]), 2)


class TestTaskOperations(unittest.TestCase):
    """Tests for task operations."""
    
    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_tasks_with_filters(self, mock_get_client):
        """Test list_tasks function with filters."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_tasks.return_value = {"taskArns": ["task-1", "task-2"]}
        mock_ecs.describe_tasks.return_value = {
            "tasks": [
                {"taskArn": "task-1", "lastStatus": "RUNNING"},
                {"taskArn": "task-2", "lastStatus": "RUNNING"}
            ]
        }
        mock_get_client.return_value = mock_ecs
        
        # Call list_tasks with filters
        filters = {
            "cluster": "test-cluster",
            "service": "test-service",
            "status": "RUNNING"
        }
        result = await list_tasks(filters)
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify list_tasks was called with correct parameters
        mock_ecs.list_tasks.assert_called_once()
        args, kwargs = mock_ecs.list_tasks.call_args
        self.assertEqual(kwargs["cluster"], "test-cluster")
        self.assertEqual(kwargs["serviceName"], "test-service")
        self.assertEqual(kwargs["desiredStatus"], "RUNNING")
        
        # Verify describe_tasks was called
        mock_ecs.describe_tasks.assert_called_once()
        
        # Verify the result
        self.assertIn("tasks", result)
        self.assertEqual(len(result["tasks"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["running_count"], 2)
        self.assertEqual(result["stopped_count"], 0)

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_task(self, mock_get_client):
        """Test describe_task function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_tasks.return_value = {
            "tasks": [{
                "taskArn": "task-1",
                "lastStatus": "RUNNING",
                "taskDefinitionArn": "task-def-1",
                "containers": [
                    {
                        "name": "container-1",
                        "image": "image-1",
                        "lastStatus": "RUNNING"
                    }
                ]
            }]
        }
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": "task-def-1",
                "family": "task-family"
            }
        }
        mock_get_client.return_value = mock_ecs
        
        # Call describe_task
        result = await describe_task("task-1", {"cluster": "test-cluster"})
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify describe_tasks was called with correct parameters
        mock_ecs.describe_tasks.assert_called_once()
        args, kwargs = mock_ecs.describe_tasks.call_args
        self.assertEqual(kwargs["cluster"], "test-cluster")
        self.assertEqual(kwargs["tasks"], ["task-1"])
        
        # Verify describe_task_definition was called
        mock_ecs.describe_task_definition.assert_called_once()
        
        # Verify the result
        self.assertIn("task", result)
        self.assertEqual(result["task"]["taskArn"], "task-1")
        self.assertIn("task_definition", result)
        self.assertIn("container_statuses", result)
        self.assertEqual(len(result["container_statuses"]), 1)
        self.assertEqual(result["is_failed"], False)


class TestTaskDefinitionOperations(unittest.TestCase):
    """Tests for task definition operations."""
    
    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_list_task_definitions_with_filters(self, mock_get_client):
        """Test list_task_definitions function with filters."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.list_task_definitions.return_value = {
            "taskDefinitionArns": ["arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"],
            "nextToken": "next-token"
        }
        mock_get_client.return_value = mock_ecs
        
        # Call list_task_definitions with filters
        filters = {
            "family": "test-task",
            "status": "ACTIVE",
            "max_results": 10
        }
        result = await list_task_definitions(filters)
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify list_task_definitions was called with correct parameters
        mock_ecs.list_task_definitions.assert_called_once()
        args, kwargs = mock_ecs.list_task_definitions.call_args
        self.assertEqual(kwargs["familyPrefix"], "test-task")
        self.assertEqual(kwargs["status"], "ACTIVE")
        self.assertEqual(kwargs["maxResults"], 10)
        
        # Verify the result
        self.assertIn("task_definition_arns", result)
        self.assertEqual(len(result["task_definition_arns"]), 1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["next_token"], "next-token")

    @pytest.mark.asyncio
    @patch("awslabs.ecs_mcp_server.api.resource_management.get_aws_client")
    async def test_describe_task_definition(self, mock_get_client):
        """Test describe_task_definition function."""
        # Mock get_aws_client
        mock_ecs = MagicMock()
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1",
                "family": "test-task",
                "revision": 1
            },
            "tags": [{"key": "Name", "value": "test-task"}]
        }
        mock_ecs.list_task_definitions.return_value = {
            "taskDefinitionArns": ["arn:aws:ecs:us-east-1:123456789012:task-definition/test-task:1"]
        }
        mock_get_client.return_value = mock_ecs
        
        # Call describe_task_definition
        result = await describe_task_definition("test-task:1")
        
        # Verify get_aws_client was called
        mock_get_client.assert_called_once_with("ecs")
        
        # Verify describe_task_definition was called with correct parameters
        mock_ecs.describe_task_definition.assert_called_once()
        args, kwargs = mock_ecs.describe_task_definition.call_args
        self.assertEqual(kwargs["taskDefinition"], "test-task:1")
        
        # Verify the result
        self.assertIn("task_definition", result)
        self.assertEqual(result["task_definition"]["family"], "test-task")
        self.assertEqual(result["task_definition"]["revision"], 1)
        self.assertEqual(len(result["tags"]), 1)
        self.assertEqual(result["is_latest"], True)


if __name__ == "__main__":
    unittest.main()
