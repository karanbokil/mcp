"""
Unit tests for the fetch_service_events function.
"""

import datetime
import unittest
from unittest import mock

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_service_events


class TestFetchServiceEvents(unittest.TestCase):
    """Unit tests for the fetch_service_events function."""
    
    @mock.patch("boto3.client")
    def test_service_exists(self, mock_boto_client):
        """Test when ECS service exists."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
        
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
        
        # Call the function
        result = fetch_service_events("test-app", "test-cluster", 3600)
        
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
        
        # Event timestamp
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
        
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
        
        # Call the function
        result = fetch_service_events("test-app", "test-cluster", 3600)
        
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
        result = fetch_service_events("test-app", "test-cluster", 3600)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == False
        assert "failures" in result
        
    @mock.patch("boto3.client")
    def test_with_explicit_start_time(self, mock_boto_client):
        """Test with explicit start_time parameter."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
        
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
        
        # Call the function with explicit start_time
        start_time = datetime.datetime(2025, 5, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
        result = fetch_service_events("test-app", "test-cluster", 3600, start_time=start_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1
        
    @mock.patch("boto3.client")
    def test_with_explicit_end_time(self, mock_boto_client):
        """Test with explicit end_time parameter."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
        
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
        
        # Call the function with explicit end_time
        end_time = datetime.datetime(2025, 5, 13, 23, 59, 59, tzinfo=datetime.timezone.utc)
        result = fetch_service_events("test-app", "test-cluster", 3600, end_time=end_time)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1
        
    @mock.patch("boto3.client")
    def test_with_start_and_end_time(self, mock_boto_client):
        """Test with both start_time and end_time parameters."""
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Event timestamp
        timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
        
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
            3600, 
            start_time=start_time, 
            end_time=end_time
        )
        
        # Verify the result
        assert result["status"] == "success"
        assert result["service_exists"] == True
        assert len(result["events"]) == 1
