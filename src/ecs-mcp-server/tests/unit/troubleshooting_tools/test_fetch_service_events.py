"""
Unit tests for the fetch_service_events function.
"""

import datetime
import unittest
from unittest import mock

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_service_events
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events import (
    _extract_filtered_events,
    _check_target_group_health,
    _check_port_mismatch,
    _analyze_load_balancer_issues,
)


class TestHelperFunctions(unittest.TestCase):
    """Unit tests for the helper functions in fetch_service_events."""
    
    def test_extract_filtered_events(self):
        """Test extracting and filtering events by time window."""
        # Create a test service with events
        test_time = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        service = {
            "events": [
                {
                    "id": "1",
                    "createdAt": test_time,
                    "message": "event within window"
                },
                {
                    "id": "2",
                    "createdAt": test_time - datetime.timedelta(hours=2),
                    "message": "event outside window"
                }
            ]
        }
        
        # Define time window
        start_time = test_time - datetime.timedelta(hours=1)
        end_time = test_time + datetime.timedelta(hours=1)
        
        # Call helper function
        events = _extract_filtered_events(service, start_time, end_time)
        
        # Verify results
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], "1")
        self.assertEqual(events[0]["message"], "event within window")
    
    def test_extract_filtered_events_empty(self):
        """Test extracting events when service has no events."""
        service = {}  # No events key
        start_time = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        end_time = start_time + datetime.timedelta(hours=1)
        
        events = _extract_filtered_events(service, start_time, end_time)
        
        self.assertEqual(len(events), 0)
    
    @mock.patch("boto3.client")
    def test_check_target_group_health_unhealthy(self, mock_boto_client):
        """Test checking target group health with unhealthy targets."""
        mock_elb_client = mock.Mock()
        mock_elb_client.describe_target_health.return_value = {
            "TargetHealthDescriptions": [
                {
                    "TargetHealth": {
                        "State": "unhealthy"
                    }
                }
            ]
        }
        
        result = _check_target_group_health(mock_elb_client, "test-arn")
        
        self.assertEqual(result["type"], "unhealthy_targets")
        self.assertEqual(result["count"], 1)
    
    @mock.patch("boto3.client")
    def test_check_target_group_health_healthy(self, mock_boto_client):
        """Test checking target group health with all healthy targets."""
        mock_elb_client = mock.Mock()
        mock_elb_client.describe_target_health.return_value = {
            "TargetHealthDescriptions": [
                {
                    "TargetHealth": {
                        "State": "healthy"
                    }
                }
            ]
        }
        
        result = _check_target_group_health(mock_elb_client, "test-arn")
        
        self.assertIsNone(result)
    
    @mock.patch("boto3.client")
    def test_check_port_mismatch_with_mismatch(self, mock_boto_client):
        """Test checking port mismatch when ports don't match."""
        mock_elb_client = mock.Mock()
        mock_elb_client.describe_target_groups.return_value = {
            "TargetGroups": [
                {
                    "Port": 80
                }
            ]
        }
        
        result = _check_port_mismatch(mock_elb_client, "test-arn", 8080)
        
        self.assertEqual(result["type"], "port_mismatch")
        self.assertEqual(result["container_port"], 8080)
        self.assertEqual(result["target_group_port"], 80)
    
    @mock.patch("boto3.client")
    def test_check_port_mismatch_no_mismatch(self, mock_boto_client):
        """Test checking port mismatch when ports match."""
        mock_elb_client = mock.Mock()
        mock_elb_client.describe_target_groups.return_value = {
            "TargetGroups": [
                {
                    "Port": 8080
                }
            ]
        }
        
        result = _check_port_mismatch(mock_elb_client, "test-arn", 8080)
        
        self.assertIsNone(result)
    
    @mock.patch("boto3.client")
    @mock.patch("awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events._check_target_group_health")
    @mock.patch("awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events._check_port_mismatch")
    def test_analyze_load_balancer_issues(self, mock_check_port, mock_check_health, mock_boto_client):
        """Test analyzing load balancer issues."""
        mock_check_health.return_value = {"type": "unhealthy_targets", "count": 1}
        mock_check_port.return_value = {"type": "port_mismatch", "container_port": 8080, "target_group_port": 80}
        
        service = {
            "loadBalancers": [
                {
                    "targetGroupArn": "test-arn",
                    "containerPort": 8080
                }
            ]
        }
        
        issues = _analyze_load_balancer_issues(service)
        
        self.assertEqual(len(issues), 1)
        self.assertEqual(len(issues[0]["issues"]), 2)
        self.assertEqual(issues[0]["issues"][0]["type"], "unhealthy_targets")
        self.assertEqual(issues[0]["issues"][1]["type"], "port_mismatch")


class TestFetchServiceEvents(unittest.TestCase):
    """Unit tests for the fetch_service_events function."""
    
    @mock.patch("boto3.client")
    def test_service_exists(self, mock_boto_client):
        """Test when ECS service exists."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp - use datetime with timezone for proper filtering
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Mock describe_services response
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-app",
                    "status": "ACTIVE",
                    "deployments": [
                        {
                            "id": "ecs-svc/1234567890123456",
                            "status": "PRIMARY",
                            "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                            "desiredCount": 2,
                            "pendingCount": 0,
                            "runningCount": 2,
                            "createdAt": timestamp,
                            "updatedAt": timestamp
                        }
                    ],
                    "events": [
                        {
                            "id": "1234567890-1234567",
                            "createdAt": timestamp,
                            "message": "service test-app has reached a steady state."
                        },
                        {
                            "id": "1234567890-1234566",
                            "createdAt": timestamp - datetime.timedelta(minutes=5),
                            "message": "service test-app has started 2 tasks: (task 1234567890abcdef0, task 1234567890abcdef1)."
                        }
                    ],
                    "loadBalancers": [
                        {
                            "targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-app/1234567890123456",
                            "containerName": "test-app",
                            "containerPort": 8080
                        }
                    ]
                }
            ]
        }
        
        # Mock ELB client for target group health
        mock_elb_client = mock.Mock()
        mock_elb_client.describe_target_health.return_value = {
            "TargetHealthDescriptions": [
                {
                    "Target": {
                        "Id": "10.0.0.1",
                        "Port": 8080
                    },
                    "HealthCheckPort": "8080",
                    "TargetHealth": {
                        "State": "healthy"
                    }
                }
            ]
        }
        
        mock_elb_client.describe_target_groups.return_value = {
            "TargetGroups": [
                {
                    "TargetGroupName": "test-app",
                    "Protocol": "HTTP",
                    "Port": 8080,
                    "HealthCheckProtocol": "HTTP",
                    "HealthCheckPath": "/health"
                }
            ]
        }
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "ecs": mock_ecs_client,
            "elbv2": mock_elb_client
        }[service_name]
        
        # Call the function with time window that includes the mock events
        start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
        result = fetch_service_events("test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert result["service_status"] == "ACTIVE"
        assert len(result["events"]) == 2
        assert "steady state" in result["events"][0]["message"]
        assert "deployment_status" in result
        assert "primary" in result["deployment_status"]["active_deployment"]["status"].lower()
    
    @mock.patch("boto3.client")
    def test_service_with_load_balancer_issues(self, mock_boto_client):
        """Test when ECS service has load balancer issues."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp - use datetime with timezone for proper filtering
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Mock describe_services response
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-app",
                    "status": "ACTIVE",
                    "deployments": [
                        {
                            "id": "ecs-svc/1234567890123456",
                            "status": "PRIMARY",
                            "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                            "desiredCount": 2,
                            "pendingCount": 0,
                            "runningCount": 2,
                            "createdAt": timestamp,
                            "updatedAt": timestamp
                        }
                    ],
                    "events": [
                        {
                            "id": "1234567890-1234567",
                            "createdAt": timestamp,
                            "message": "service test-app has tasks that are unhealthy in target-group test-app"
                        }
                    ],
                    "loadBalancers": [
                        {
                            "targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-app/1234567890123456",
                            "containerName": "test-app",
                            "containerPort": 8080
                        }
                    ]
                }
            ]
        }
        
        # Mock ELB client for target group health
        mock_elb_client = mock.Mock()
        mock_elb_client.describe_target_health.return_value = {
            "TargetHealthDescriptions": [
                {
                    "Target": {
                        "Id": "10.0.0.1",
                        "Port": 8080
                    },
                    "HealthCheckPort": "8080",
                    "TargetHealth": {
                        "State": "unhealthy",
                        "Reason": "Target.FailedHealthChecks",
                        "Description": "Health checks failed"
                    }
                }
            ]
        }
        
        mock_elb_client.describe_target_groups.return_value = {
            "TargetGroups": [
                {
                    "TargetGroupName": "test-app",
                    "Protocol": "HTTP",
                    "Port": 80,  # Mismatch with container port 8080
                    "HealthCheckProtocol": "HTTP",
                    "HealthCheckPath": "/health"
                }
            ]
        }
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "ecs": mock_ecs_client,
            "elbv2": mock_elb_client
        }[service_name]
        
        # Call the function with time window that includes the mock events
        start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
        result = fetch_service_events("test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1
        assert "unhealthy" in result["events"][0]["message"]
        assert len(result["load_balancer_issues"]) == 1
        
        # Check for port mismatch issue
        lb_issues = result["load_balancer_issues"][0]["issues"]
        port_mismatch = next((issue for issue in lb_issues if issue["type"] == "port_mismatch"), None)
        assert port_mismatch is not None
        assert port_mismatch["container_port"] == 8080
        assert port_mismatch["target_group_port"] == 80
        
        # Check for unhealthy targets issue
        unhealthy_targets = next((issue for issue in lb_issues if issue["type"] == "unhealthy_targets"), None)
        assert unhealthy_targets is not None
        assert unhealthy_targets["count"] == 1
    
    @mock.patch("boto3.client")
    def test_service_not_found(self, mock_boto_client):
        """Test when ECS service does not exist."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Mock describe_services with ServiceNotFoundException
        mock_ecs_client.describe_services.return_value = {
            "services": [],
            "failures": [
                {
                    "arn": "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/test-app",
                    "reason": "MISSING"
                }
            ]
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function
        result = fetch_service_events("test-app", "test-cluster", "test-app", 3600)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == False
        assert "failures" in result
        
    @mock.patch("boto3.client")
    def test_with_explicit_start_time(self, mock_boto_client):
        """Test with explicit start_time parameter."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp - use datetime with timezone for proper filtering
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Mock describe_services response
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-app",
                    "status": "ACTIVE",
                    "events": [
                        {
                            "id": "1234567890-1234567",
                            "createdAt": timestamp,
                            "message": "service test-app has reached a steady state."
                        }
                    ]
                }
            ]
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function with explicit start_time that includes mock event date
        start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
        result = fetch_service_events("test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1
        
    @mock.patch("boto3.client")
    def test_with_explicit_end_time(self, mock_boto_client):
        """Test with explicit end_time parameter."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp - use datetime with timezone for proper filtering
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Mock describe_services response
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-app",
                    "status": "ACTIVE",
                    "events": [
                        {
                            "id": "1234567890-1234567",
                            "createdAt": timestamp,
                            "message": "service test-app has reached a steady state."
                        }
                    ]
                }
            ]
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function with explicit end_time that includes mock event date
        start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
        result = fetch_service_events("test-app", "test-cluster", "test-app", 3600, start_time=start_time, end_time=end_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1
        
    @mock.patch("boto3.client")
    def test_with_start_and_end_time(self, mock_boto_client):
        """Test with both start_time and end_time parameters."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp - use datetime with timezone for proper filtering
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Mock describe_services response
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-app",
                    "status": "ACTIVE",
                    "events": [
                        {
                            "id": "1234567890-1234567",
                            "createdAt": timestamp,
                            "message": "service test-app has reached a steady state."
                        }
                    ]
                }
            ]
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function with both start_time and end_time
        start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
        result = fetch_service_events(
            "test-app", 
            "test-cluster", 
            "test-app",
            3600, 
            start_time=start_time, 
            end_time=end_time
        )
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1
        
    @mock.patch("boto3.client")
    @mock.patch("awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events.calculate_time_window")
    def test_with_only_time_window(self, mock_calculate_time_window, mock_boto_client):
        """Test with only time_window parameter."""
        # Define time window boundaries
        mock_now = datetime.datetime(2025, 5, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
        window_start = mock_now - datetime.timedelta(hours=2)  # 2 hours time window
        mock_calculate_time_window.return_value = (window_start, mock_now)
        time_window = 7200
        
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Create events within and outside the 2-hour time window
        in_window_timestamp = mock_now - datetime.timedelta(minutes=30)  # 11:30, within the 2-hour window
        outside_window_timestamp = window_start - datetime.timedelta(minutes=30)  # 30 minutes before window start
        
        # Mock describe_services response
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-app",
                    "status": "ACTIVE",
                    "events": [
                        {
                            "id": "1234567890-1234567",
                            "createdAt": in_window_timestamp,
                            "message": "service test-app has reached a steady state."
                        },
                        {
                            "id": "1234567890-1234566",
                            "createdAt": outside_window_timestamp,
                            "message": "service test-app has started 2 tasks."
                        }
                    ]
                }
            ]
        }
        
        # Configure boto3.client mock to return our mock client
        mock_boto_client.return_value = mock_ecs_client
        
        # Call the function with ONLY time_window parameter
        # This properly tests the time_window functionality
        result = fetch_service_events(
            "test-app", 
            "test-cluster", 
            "test-app", 
            time_window=time_window
        )
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1  # Only the event within time window should be returned
        assert "steady state" in result["events"][0]["message"]
