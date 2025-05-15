"""
Unit tests for the fetch_task_logs function.
"""

import datetime
import unittest
from unittest import mock

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_task_logs


class TestFetchTaskLogs(unittest.TestCase):
    """Unit tests for the fetch_task_logs function."""
    
    @mock.patch("boto3.client")
    def test_logs_found(self, mock_boto_client):
        """Test when CloudWatch logs are found."""
        # Mock CloudWatch Logs client
        mock_logs_client = mock.Mock()
        
        # Timestamps
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
        
        # Mock describe_log_groups response
        mock_logs_client.describe_log_groups.return_value = {
            "logGroups": [
                {
                    "logGroupName": "/ecs/test-cluster/test-app",
                    "creationTime": int(timestamp.timestamp()) * 1000,
                    "metricFilterCount": 0,
                    "arn": "arn:aws:logs:us-west-2:123456789012:log-group:/ecs/test-cluster/test-app:*",
                    "storedBytes": 1234
                }
            ]
        }
        
        # Mock describe_log_streams response
        mock_logs_client.describe_log_streams.return_value = {
            "logStreams": [
                {
                    "logStreamName": "ecs/test-app/1234567890abcdef0",
                    "creationTime": int(timestamp.timestamp()) * 1000,
                    "firstEventTimestamp": int(timestamp.timestamp()) * 1000,
                    "lastEventTimestamp": int(timestamp.timestamp()) * 1000,
                    "lastIngestionTime": int(timestamp.timestamp()) * 1000,
                    "uploadSequenceToken": "1234567890",
                    "arn": "arn:aws:logs:us-west-2:123456789012:log-group:/ecs/test-cluster/test-app:log-stream:ecs/test-app/1234567890abcdef0",
                    "storedBytes": 1234
                }
            ]
        }
        
        # Mock get_log_events response
        mock_logs_client.get_log_events.return_value = {
            "events": [
                {
                    "timestamp": int(timestamp.timestamp()) * 1000,
                    "message": "INFO: Application starting",
                    "ingestionTime": int(timestamp.timestamp()) * 1000
                },
                {
                    "timestamp": int((timestamp + datetime.timedelta(seconds=1)).timestamp()) * 1000,
                    "message": "WARN: Configuration file not found, using defaults",
                    "ingestionTime": int((timestamp + datetime.timedelta(seconds=1)).timestamp()) * 1000
                },
                {
                    "timestamp": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000,
                    "message": "ERROR: Failed to connect to database",
                    "ingestionTime": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000
                }
            ],
            "nextForwardToken": "f/1234567890",
            "nextBackwardToken": "b/1234567890"
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_logs_client
        
        # Call the function
        result = fetch_task_logs("test-app", "test-cluster", None, 3600)
        
        # Verify the result
        assert result["status"] == "success"
        assert len(result["log_groups"]) == 1
        assert len(result["log_entries"]) == 3
        assert result["error_count"] == 1
        assert result["warning_count"] == 1
        assert result["info_count"] == 1
    
    @mock.patch("boto3.client")
    def test_no_logs_found(self, mock_boto_client):
        """Test when no CloudWatch logs are found."""
        # Mock CloudWatch Logs client
        mock_logs_client = mock.Mock()
        
        # Mock describe_log_groups response with no log groups
        mock_logs_client.describe_log_groups.return_value = {
            "logGroups": []
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_logs_client
        
        # Call the function
        result = fetch_task_logs("test-app", "test-cluster", None, 3600)
        
        # Verify the result
        assert result["status"] == "success"
        assert len(result["log_groups"]) == 0
        assert "No log groups found" in result["note"]
    
    @mock.patch("boto3.client")
    def test_with_filter_pattern(self, mock_boto_client):
        """Test retrieving logs with a filter pattern."""
        # Mock CloudWatch Logs client
        mock_logs_client = mock.Mock()
        
        # Timestamps
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
        
        # Mock describe_log_groups response
        mock_logs_client.describe_log_groups.return_value = {
            "logGroups": [
                {
                    "logGroupName": "/ecs/test-cluster/test-app",
                    "creationTime": int(timestamp.timestamp()) * 1000
                }
            ]
        }
        
        # Mock describe_log_streams response
        mock_logs_client.describe_log_streams.return_value = {
            "logStreams": [
                {
                    "logStreamName": "ecs/test-app/1234567890abcdef0",
                    "creationTime": int(timestamp.timestamp()) * 1000
                }
            ]
        }
        
        # Mock get_log_events response with filtered events
        mock_logs_client.get_log_events.return_value = {
            "events": [
                {
                    "timestamp": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000,
                    "message": "ERROR: Failed to connect to database",
                    "ingestionTime": int((timestamp + datetime.timedelta(seconds=2)).timestamp()) * 1000
                }
            ],
            "nextForwardToken": "f/1234567890",
            "nextBackwardToken": "b/1234567890"
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_logs_client
        
        # Call the function with a filter pattern
        result = fetch_task_logs("test-app", "test-cluster", None, 3600, "ERROR")
        
        # Verify the result
        assert result["status"] == "success"
        assert len(result["log_entries"]) == 1
        assert result["error_count"] == 1
        assert result["warning_count"] == 0
        assert result["info_count"] == 0
