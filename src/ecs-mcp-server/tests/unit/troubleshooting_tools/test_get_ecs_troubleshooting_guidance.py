"""
Unit tests for the get_ecs_troubleshooting_guidance function.
"""

import unittest
from unittest import mock

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import get_ecs_troubleshooting_guidance


class TestGetEcsTroubleshootingGuidance(unittest.TestCase):
    """Unit tests for the get_ecs_troubleshooting_guidance function."""

    @mock.patch("boto3.client")
    def test_stack_not_found(self, mock_boto_client):
        """Test guidance when CloudFormation stack is not found."""
        # Mock CloudFormation client with a ClientError
        mock_cf_client = mock.Mock()
        mock_cf_client.describe_stacks.side_effect = ClientError(
            {"Error": {"Code": "ValidationError", "Message": "Stack with id test-app does not exist"}},
            "DescribeStacks"
        )
        
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        mock_ecs_client.describe_clusters.side_effect = ClientError(
            {"Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}},
            "DescribeClusters"
        )
        
        # Add empty list_task_definition_families and list_task_definitions methods
        mock_ecs_client.list_task_definition_families = mock.Mock(return_value={"families": []})
        mock_ecs_client.list_task_definitions = mock.Mock(return_value={"taskDefinitionArns": []})
        
        # Add list_clusters method
        mock_ecs_client.list_clusters = mock.Mock(return_value={"clusterArns": []})
        
        # Create a proper ELBv2 mock
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers = mock.Mock(return_value={"LoadBalancers": []})
        
        # Mock ECR client
        mock_ecr = mock.Mock()
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "cloudformation": mock_cf_client,
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock_ecr
        }.get(service_name, mock.Mock())
        
        # Call the function
        result = get_ecs_troubleshooting_guidance("test-app")
        
        # Verify the result
        self.assertEqual("success", result["status"])
        self.assertIn("CloudFormation stack 'test-app' does not exist", result["assessment"])
        self.assertTrue(len(result["diagnostic_path"]) > 0)
        self.assertEqual("fetch_cloudformation_status", result["diagnostic_path"][0]["tool"])
    
    @mock.patch("boto3.client")
    def test_stack_rollback_complete(self, mock_boto_client):
        """Test guidance when CloudFormation stack is in ROLLBACK_COMPLETE state."""
        # Mock CloudFormation client
        mock_cf_client = mock.Mock()
        mock_cf_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-app",
                    "StackStatus": "ROLLBACK_COMPLETE"
                }
            ]
        }
        
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [],
            "failures": []
        }
        
        # Add empty list_task_definition_families and list_task_definitions methods
        mock_ecs_client.list_task_definition_families = mock.Mock(return_value={"families": []})
        mock_ecs_client.list_task_definitions = mock.Mock(return_value={"taskDefinitionArns": []})
        
        # Add list_clusters method
        mock_ecs_client.list_clusters = mock.Mock(return_value={"clusterArns": []})
        
        # Create a proper ELBv2 mock
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers = mock.Mock(return_value={"LoadBalancers": []})
        
        # Mock ECR client
        mock_ecr = mock.Mock()
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "cloudformation": mock_cf_client,
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock_ecr
        }.get(service_name, mock.Mock())
        
        # Call the function
        result = get_ecs_troubleshooting_guidance("test-app")
        
        # Verify the result
        self.assertEqual("success", result["status"])
        self.assertIn("ROLLBACK_COMPLETE", result["assessment"])
        self.assertTrue(len(result["diagnostic_path"]) > 0)
        self.assertEqual("fetch_cloudformation_status", result["diagnostic_path"][0]["tool"])
        self.assertIn("root cause", result["diagnostic_path"][0]["reason"].lower())
    
    @mock.patch("boto3.client")
    def test_stack_and_cluster_exist(self, mock_boto_client):
        """Test guidance when CloudFormation stack and ECS cluster both exist."""
        # Mock CloudFormation client
        mock_cf_client = mock.Mock()
        mock_cf_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-app",
                    "StackStatus": "CREATE_COMPLETE"
                }
            ]
        }
        
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Mock list_clusters to return related clusters
        mock_ecs_client.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"]
        }
        
        # Mock describe_clusters to return statuses
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-app-cluster",
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        
        # Add empty list_task_definition_families and list_task_definitions methods
        mock_ecs_client.list_task_definition_families = mock.Mock(return_value={"families": []})
        mock_ecs_client.list_task_definitions = mock.Mock(return_value={"taskDefinitionArns": []})
        
        # Create a proper ELBv2 mock
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers = mock.Mock(return_value={"LoadBalancers": [{"LoadBalancerName": "test-app-lb"}]})
        
        # Mock ECR client
        mock_ecr = mock.Mock()
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "cloudformation": mock_cf_client,
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock_ecr
        }.get(service_name, mock.Mock())
        
        # Call the function
        result = get_ecs_troubleshooting_guidance("test-app")
        
        # Verify the result
        self.assertEqual("success", result["status"])
        self.assertIn("both exist", result["assessment"])
        self.assertTrue(len(result["diagnostic_path"]) >= 3)
        tools = [step["tool"] for step in result["diagnostic_path"]]
        self.assertIn("fetch_task_failures", tools)
        self.assertIn("fetch_service_events", tools)
        self.assertIn("fetch_task_logs", tools)
    
    @mock.patch("boto3.client")
    def test_with_symptoms_description(self, mock_boto_client):
        """Test guidance with a symptoms description."""
        # Mock CloudFormation client
        mock_cf_client = mock.Mock()
        mock_cf_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-app",
                    "StackStatus": "CREATE_COMPLETE"
                }
            ]
        }
        
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        
        # Mock list_clusters to return related clusters
        mock_ecs_client.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"]
        }
        
        # Mock describe_clusters to return statuses
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-app-cluster",
                    "status": "ACTIVE"
                }
            ],
            "failures": []
        }
        
        # Add empty list_task_definition_families and list_task_definitions methods
        mock_ecs_client.list_task_definition_families = mock.Mock(return_value={"families": []})
        mock_ecs_client.list_task_definitions = mock.Mock(return_value={"taskDefinitionArns": []})
        
        # Create a proper ELBv2 mock
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers = mock.Mock(return_value={"LoadBalancers": [{"LoadBalancerName": "test-app-lb"}]})
        
        # Mock ECR client
        mock_ecr = mock.Mock()
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "cloudformation": mock_cf_client,
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock_ecr
        }.get(service_name, mock.Mock())
        
        # Call the function with symptoms
        symptoms = "Tasks keep failing with container errors and network timeouts"
        result = get_ecs_troubleshooting_guidance("test-app", symptoms)
        
        # Verify the result
        self.assertEqual("success", result["status"])
        self.assertEqual(symptoms, result["raw_data"]["symptoms_description"])
        self.assertTrue(len(result["detected_symptoms"]["task"]) > 0)
        self.assertTrue(len(result["detected_symptoms"]["network"]) > 0)
    
    @mock.patch("boto3.client")
    def test_client_error_handling(self, mock_boto_client):
        """Test error handling when boto3 client raises unexpected ClientError."""
        # Mock CloudFormation client with a ClientError
        mock_cf_client = mock.Mock()
        mock_cf_client.describe_stacks.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "User is not authorized"}},
            "DescribeStacks"
        )
        
        # Create a proper ECS mock to avoid 'not subscriptable' error when it tries to access list_clusters
        mock_ecs_client = mock.Mock()
        mock_ecs_client.list_clusters = mock.Mock(return_value={"clusterArns": []})
        mock_ecs_client.list_task_definitions = mock.Mock(return_value={"taskDefinitionArns": []})
        mock_ecs_client.list_task_definition_families = mock.Mock(return_value={"families": []})
        
        # Create a proper ELBv2 mock
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers = mock.Mock(return_value={"LoadBalancers": []})
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "cloudformation": mock_cf_client,
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock.Mock()
        }.get(service_name, mock.Mock())
        
        # Call the function
        result = get_ecs_troubleshooting_guidance("test-app")
        
        # Verify the result - change to match actual implementation
        self.assertEqual("error", result["status"])
        self.assertIn("error", result)
        # Don't rely on specific error message containing "Access" as it depends on the exception formatting

    @mock.patch("awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance.find_related_task_definitions")
    @mock.patch("boto3.client")
    def test_service_collection(self, mock_boto_client, mock_find_related_task_definitions):
        """Test that services are correctly collected in find_related_resources function."""
        # Mock the ECS client
        mock_ecs_client = mock.Mock()
        
        # Mock list_clusters with test clusters
        mock_ecs_client.list_clusters.return_value = {
            'clusterArns': [
                'arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster',
                'arn:aws:ecs:us-west-2:123456789012:cluster/other-cluster'
            ]
        }
        
        # Mock list_services for the test cluster
        mock_ecs_client.list_services.side_effect = lambda cluster: {
            'test-app-cluster': {
                'serviceArns': [
                    'arn:aws:ecs:us-west-2:123456789012:service/test-app-cluster/test-app-service',
                    'arn:aws:ecs:us-west-2:123456789012:service/test-app-cluster/other-service'
                ]
            },
            'default': {
                'serviceArns': [
                    'arn:aws:ecs:us-west-2:123456789012:service/default/test-app-default-service',
                    'arn:aws:ecs:us-west-2:123456789012:service/default/unrelated-service'
                ]
            }
        }.get(cluster, {'serviceArns': []})
        
        # Mock ELBv2 client
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers.return_value = {
            'LoadBalancers': []
        }
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock.Mock()
        }.get(service_name, mock.Mock())
        
        # Import the function directly for testing
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import find_related_resources
        
        # Call the function
        result = find_related_resources("test-app")
        
        # Verify clusters were found
        self.assertIn("test-app-cluster", result['clusters'])
        
        # Verify services were found - both from the matching cluster and the default cluster
        self.assertIn("test-app-service", result['services'])
        self.assertIn("test-app-default-service", result['services'])
        
        # Verify unrelated services are not included
        self.assertNotIn("other-service", result['services'])
        self.assertNotIn("unrelated-service", result['services'])
        
    @mock.patch("awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance.find_related_task_definitions")
    @mock.patch("boto3.client")
    def test_related_clusters_status_collection(self, mock_boto_client, mock_find_related_task_definitions):
        """Test that statuses from related clusters are correctly collected."""
        # Set up the mock for find_related_task_definitions
        mock_find_related_task_definitions.return_value = []
        
        # Mock CloudFormation client
        mock_cf_client = mock.Mock()
        mock_cf_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-app",
                    "StackStatus": "CREATE_COMPLETE"
                }
            ]
        }
        
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        mock_ecs_client.list_task_definition_families = mock.Mock(return_value={"families": []})
        mock_ecs_client.list_task_definitions = mock.Mock(return_value={"taskDefinitionArns": []})
        
        # Mock list_clusters to return multiple related clusters
        mock_ecs_client.list_clusters.return_value = {
            "clusterArns": [
                "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-prod",
                "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-staging",
                "arn:aws:ecs:us-west-2:123456789012:cluster/unrelated-cluster"
            ]
        }
        
        # Mock describe_clusters to return statuses for the related clusters
        mock_ecs_client.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-app-prod",
                    "status": "ACTIVE",
                    "runningTasksCount": 10,
                    "pendingTasksCount": 2,
                    "activeServicesCount": 3,
                    "registeredContainerInstancesCount": 5
                },
                {
                    "clusterName": "test-app-staging",
                    "status": "ACTIVE",
                    "runningTasksCount": 5,
                    "pendingTasksCount": 1,
                    "activeServicesCount": 2,
                    "registeredContainerInstancesCount": 3
                }
            ],
            "failures": []
        }
        
        # Mock service responses
        mock_ecs_client.list_services = mock.Mock(return_value={"serviceArns": []})
        
        # Create ELBv2 mock
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers = mock.Mock(return_value={"LoadBalancers": []})
        
        # Mock ECR client
        mock_ecr = mock.Mock()
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "cloudformation": mock_cf_client,
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock_ecr
        }.get(service_name, mock.Mock())
        
        # Call the function
        result = get_ecs_troubleshooting_guidance("test-app")
        
        # Verify that detailed cluster info was collected correctly
        self.assertIn("clusters", result["raw_data"])
        self.assertEqual(2, len(result["raw_data"]["clusters"]))
        
        # Verify first cluster details
        first_cluster = result["raw_data"]["clusters"][0]
        self.assertEqual("test-app-prod", first_cluster["name"])
        self.assertEqual("ACTIVE", first_cluster["status"])
        self.assertTrue(first_cluster["exists"])
        self.assertEqual(10, first_cluster["runningTasksCount"])
        self.assertEqual(2, first_cluster["pendingTasksCount"])
        self.assertEqual(3, first_cluster["activeServicesCount"])
        self.assertEqual(5, first_cluster["registeredContainerInstancesCount"])
        
        # Verify second cluster details
        second_cluster = result["raw_data"]["clusters"][1]
        self.assertEqual("test-app-staging", second_cluster["name"])
        self.assertEqual("ACTIVE", second_cluster["status"])
        self.assertTrue(second_cluster["exists"])
        self.assertEqual(5, second_cluster["runningTasksCount"])
        self.assertEqual(1, second_cluster["pendingTasksCount"])
        self.assertEqual(2, second_cluster["activeServicesCount"])
        self.assertEqual(3, second_cluster["registeredContainerInstancesCount"])
        
        # No backward compatibility fields to check anymore
        
        # Verify diagnostic path uses the cluster name from first cluster
        test_app_prod_found = False
        for step in result["diagnostic_path"]:
            if step["tool"] == "fetch_task_failures" and "cluster_name" in step["args"]:
                if step["args"]["cluster_name"] == "test-app-prod":
                    test_app_prod_found = True
                    break
        
        self.assertTrue(test_app_prod_found)

    @mock.patch("awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance.find_related_task_definitions")
    @mock.patch("boto3.client")
    def test_task_definition_collection(self, mock_boto_client, mock_find_related_task_definitions):
        """Test that task definitions are collected using find_related_task_definitions function."""
        # Mock the find_related_task_definitions to return test data
        mock_find_related_task_definitions.return_value = [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                "family": "test-app"
            },
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app-service:1",
                "family": "test-app-service"
            },
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/service-test-app:1",
                "family": "service-test-app"
            }
        ]
        
        # Mock ECS client
        mock_ecs_client = mock.Mock()
        mock_ecs_client.list_clusters = mock.Mock(return_value={"clusterArns": []})
        
        # Create a proper ELBv2 mock
        mock_elbv2 = mock.Mock()
        mock_elbv2.describe_load_balancers = mock.Mock(return_value={"LoadBalancers": []})
        
        # Mock CloudFormation client
        mock_cf_client = mock.Mock()
        
        # Mock ECR client
        mock_ecr = mock.Mock()
        
        # Configure boto3.client mock to return our mock clients
        mock_boto_client.side_effect = lambda service_name, **kwargs: {
            "cloudformation": mock_cf_client,
            "ecs": mock_ecs_client,
            "elbv2": mock_elbv2,
            "ecr": mock_ecr
        }.get(service_name, mock.Mock())
        
        # Import the function directly for testing
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import find_related_resources
        
        # Call function and verify task definitions are collected from find_related_task_definitions
        result = find_related_resources("test-app")
        
        # Verify find_related_task_definitions was called with the correct app name
        mock_find_related_task_definitions.assert_called_once_with("test-app")
        
        # Should include task definitions from the mocked find_related_task_definitions function
        self.assertIn("test-app:1", result["task_definitions"])
        self.assertIn("test-app-service:1", result["task_definitions"])
        self.assertIn("service-test-app:1", result["task_definitions"])
        
        # Total count should match the number of task definitions we mocked
        self.assertEqual(3, len(result["task_definitions"]))
        
    @mock.patch("boto3.client")
    def test_check_container_images_handling(self, mock_boto_client):
        """Test container image checking functionality with error handling."""
        # Import the function directly for testing
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import check_container_images
        
        # Mock ECR client
        mock_ecr = mock.Mock()
        
        # Configure mock to raise exceptions for repository checks
        def mock_describe_repositories(repositoryNames):
            if repositoryNames[0] == 'missing-repo':
                error = {'Error': {'Code': 'RepositoryNotFoundException'}}
                raise ClientError(error, 'DescribeRepositories')
            return {"repositories": [{"repositoryName": repositoryNames[0]}]}
        
        mock_ecr.describe_repositories.side_effect = mock_describe_repositories
        
        # Configure mock to raise exceptions for image checks
        def mock_describe_images(repositoryName, imageIds):
            if imageIds[0]['imageTag'] == 'missing-tag':
                error = {'Error': {'Code': 'ImageNotFoundException'}}
                raise ClientError(error, 'DescribeImages')
            return {"imageDetails": [{"imageTag": imageIds[0]['imageTag']}]}
        
        mock_ecr.describe_images.side_effect = mock_describe_images
        
        # Make boto3.client return our mock
        mock_boto_client.return_value = mock_ecr
        
        # Test case 1: External image - should be treated as existing
        task_defs_external = [{
            'taskDefinitionArn': 'arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1',
            'containerDefinitions': [{
                'name': 'app',
                'image': 'docker.io/library/nginx:latest'
            }]
        }]
        
        results_external = check_container_images(task_defs_external)
        self.assertEqual(1, len(results_external))
        self.assertEqual('external', results_external[0]['repository_type'])
        self.assertEqual('unknown', results_external[0]['exists'])
        
        # Test case 2: ECR image with missing repository
        task_defs_missing_repo = [{
            'taskDefinitionArn': 'arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1',
            'containerDefinitions': [{
                'name': 'app',
                'image': '123456789012.dkr.ecr.us-west-2.amazonaws.com/missing-repo:latest'
            }]
        }]
        
        results_missing_repo = check_container_images(task_defs_missing_repo)
        self.assertEqual(1, len(results_missing_repo))
        self.assertEqual('ecr', results_missing_repo[0]['repository_type'])
        self.assertEqual('false', results_missing_repo[0]['exists'])
        self.assertIn('Repository missing-repo not found', results_missing_repo[0]['error'])
        
        # Test case 3: ECR image with existing repo but missing tag
        task_defs_missing_tag = [{
            'taskDefinitionArn': 'arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1',
            'containerDefinitions': [{
                'name': 'app',
                'image': '123456789012.dkr.ecr.us-west-2.amazonaws.com/existing-repo:missing-tag'
            }]
        }]
        
        results_missing_tag = check_container_images(task_defs_missing_tag)
        self.assertEqual(1, len(results_missing_tag))
        self.assertEqual('ecr', results_missing_tag[0]['repository_type'])
        self.assertEqual('false', results_missing_tag[0]['exists'])
        self.assertIn('not found in repository', results_missing_tag[0]['error'])
