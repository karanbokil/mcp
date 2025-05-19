"""
Unit tests for the fetch_task_failures function.
"""

import datetime
import unittest
from unittest import mock

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_task_failures


class TestFetchTaskFailures(unittest.TestCase):
    """Unit tests for the fetch_task_failures function."""
    
    @mock.patch("boto3.client")
    def test_failed_tasks_found(self, mock_boto_client):
        """Test when failed tasks are found."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Timestamps
        now = datetime.datetime.now()
        started_at = now - datetime.timedelta(minutes=10)
        stopped_at = now - datetime.timedelta(minutes=5)
        
        # Mock describe_clusters response
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        
        # Mock list_tasks and describe_tasks for stopped tasks
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = [
            {"taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/test-cluster/1234567890abcdef0"]}
        ]
        mock_ecs_client.get_paginator.return_value = mock_paginator
        
        mock_ecs_client.describe_tasks.side_effect = [
            # Stopped tasks
            {
                "tasks": [
                    {
                        "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/1234567890abcdef0",
                        "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                        "startedAt": started_at,
                        "stoppedAt": stopped_at,
                        "containers": [
                            {
                                "name": "test-app",
                                "exitCode": 1,
                                "reason": "CannotPullContainerError: Error response from daemon: pull access denied for non-existent-image, repository does not exist or may require 'docker login': denied: requested access to the resource is denied"
                            }
                        ]
                    }
                ],
                "failures": []
            },
            # Running tasks
            {
                "tasks": [
                    {
                        "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/1234567890abcdef1",
                        "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                        "startedAt": started_at,
                        "containers": [
                            {
                                "name": "test-app"
                            }
                        ]
                    }
                ]
            }
        ]
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function
        result = fetch_task_failures("test-app", "test-cluster", 3600)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["cluster_exists"] == True
        assert len(result["failed_tasks"]) == 1
        assert result["raw_data"]["running_tasks_count"] == 1
        
        # Check failure categorization
        assert "image_pull_failure" in result["failure_categories"]
        assert len(result["failure_categories"]["image_pull_failure"]) == 1
    
    @mock.patch("boto3.client")
    def test_out_of_memory_failure(self, mock_boto_client):
        """Test detecting an out-of-memory task failure."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Timestamps
        now = datetime.datetime.now()
        started_at = now - datetime.timedelta(minutes=10)
        stopped_at = now - datetime.timedelta(minutes=5)
        
        # Mock describe_clusters response
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        
        # Mock list_tasks and describe_tasks for stopped tasks
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = [
            {"taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/test-cluster/1234567890abcdef0"]}
        ]
        mock_ecs_client.get_paginator.return_value = mock_paginator
        
        mock_ecs_client.describe_tasks.side_effect = [
            # Stopped tasks with OOM exit code 137
            {
                "tasks": [
                    {
                        "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/1234567890abcdef0",
                        "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                        "startedAt": started_at,
                        "stoppedAt": stopped_at,
                        "containers": [
                            {
                                "name": "test-app",
                                "exitCode": 137,
                                "reason": "Container killed due to memory usage"
                            }
                        ]
                    }
                ],
                "failures": []
            },
            # Empty running tasks
            {"tasks": []}
        ]
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function
        result = fetch_task_failures("test-app", "test-cluster", 3600)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["cluster_exists"] == True
        assert len(result["failed_tasks"]) == 1
        
        # Check failure categorization
        assert "out_of_memory" in result["failure_categories"]
        assert len(result["failure_categories"]["out_of_memory"]) == 1
    
    @mock.patch("boto3.client")
    def test_cluster_not_found(self, mock_boto_client):
        """Test when ECS cluster does not exist."""
        # Mock ECS client with a ClientError
        mock_ecs_client = mock.Mock()
        mock_ecs_client.describe_clusters.side_effect = ClientError(
            {"Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}},
            "DescribeClusters"
        )
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function
        result = fetch_task_failures("test-app", "test-cluster", 3600)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["cluster_exists"] == False
        
    @mock.patch("boto3.client")
    def test_with_explicit_start_time(self, mock_boto_client):
        """Test with explicit start_time parameter."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Timestamps
        now = datetime.datetime.now(datetime.timezone.utc)
        started_at = now - datetime.timedelta(minutes=10)
        stopped_at = now - datetime.timedelta(minutes=5)
        
        # Mock describe_clusters response
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        
        # Mock list_tasks and describe_tasks
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = []  # No tasks found
        mock_ecs_client.get_paginator.return_value = mock_paginator
        
        # Configure boto3.client mock
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function with explicit start_time
        start_time = now - datetime.timedelta(hours=2)
        result = fetch_task_failures("test-app", "test-cluster", 3600, start_time=start_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["cluster_exists"] == True
        assert len(result["failed_tasks"]) == 0  # No tasks found
        
    @mock.patch("boto3.client")
    def test_with_explicit_end_time(self, mock_boto_client):
        """Test with explicit end_time parameter."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Timestamps
        now = datetime.datetime.now(datetime.timezone.utc)
        started_at = now - datetime.timedelta(minutes=10)
        stopped_at = now - datetime.timedelta(minutes=5)
        
        # Mock describe_clusters response
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        
        # Mock list_tasks and describe_tasks
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = []  # No tasks found
        mock_ecs_client.get_paginator.return_value = mock_paginator
        
        # Configure boto3.client mock
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function with explicit end_time
        end_time = now - datetime.timedelta(minutes=1)
        result = fetch_task_failures("test-app", "test-cluster", 3600, end_time=end_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["cluster_exists"] == True
        assert len(result["failed_tasks"]) == 0  # No tasks found
        
    @mock.patch("boto3.client")
    def test_with_start_and_end_time(self, mock_boto_client):
        """Test with both start_time and end_time parameters."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Timestamps
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Mock describe_clusters response
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        
        # Mock list_tasks and describe_tasks
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = []  # No tasks found
        mock_ecs_client.get_paginator.return_value = mock_paginator
        
        # Configure boto3.client mock
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function with both start_time and end_time
        start_time = now - datetime.timedelta(hours=2)
        end_time = now - datetime.timedelta(minutes=1)
        result = fetch_task_failures(
            "test-app", 
            "test-cluster", 
            3600, 
            start_time=start_time, 
            end_time=end_time
        )
        
        # Verify the result
        assert result["status"] == "success"
        assert result["cluster_exists"] == True
        assert len(result["failed_tasks"]) == 0  # No tasks found
