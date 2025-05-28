"""Tests for the simplified fetch_network_configuration function."""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
    fetch_network_configuration,
    get_network_data,
    discover_vpcs_from_clusters,
    discover_vpcs_from_loadbalancers,
    discover_vpcs_from_cloudformation,
    get_ec2_resource,
    get_elb_resources,
    get_associated_target_groups,
    handle_aws_api_call
)


class TestFetchNetworkConfiguration(unittest.IsolatedAsyncioTestCase):
    """Tests for fetch_network_configuration."""

    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_network_data')
    async def test_fetch_network_configuration_calls_get_network_data(self, mock_get_data):
        """Test that fetch_network_configuration calls get_network_data with correct params."""
        # Configure mock
        mock_get_data.return_value = {"status": "success", "data": {}}
        
        # Call the function
        result = await fetch_network_configuration(
            app_name="test-app", 
            vpc_id="vpc-12345678",
            cluster_name="test-cluster"
        )
        
        # Verify correct call
        mock_get_data.assert_called_once_with(
            "test-app", 
            "vpc-12345678",
            "test-cluster"
        )
        
        # Verify result
        self.assertEqual(result["status"], "success")

    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_network_data')
    async def test_fetch_network_configuration_handles_exceptions(self, mock_get_data):
        """Test that fetch_network_configuration handles exceptions properly."""
        # Configure mock to raise exception
        mock_get_data.side_effect = Exception("Test error")
        
        # Call the function
        result = await fetch_network_configuration(app_name="test-app")
        
        # Verify result
        self.assertEqual(result["status"], "error")
        self.assertIn("Internal error", result["error"])

    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_get_network_data_happy_path(self, mock_get_aws_client):
        """Test the happy path of get_network_data."""
        # Configure mocks for different AWS services
        mock_ec2 = AsyncMock()
        mock_ecs = AsyncMock()
        mock_elbv2 = AsyncMock()
        
        # Configure get_aws_client to return our mocks
        async def mock_get_client(service_name):
            if service_name == 'ec2':
                return mock_ec2
            elif service_name == 'ecs':
                return mock_ecs
            elif service_name == 'elbv2':
                return mock_elbv2
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        
        # Mock specific responses with awaitable results
        mock_ec2.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-12345678"}]}
        mock_ecs.list_clusters.return_value = {"clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster"]}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        
        # Call the function with specific VPC ID
        result = await get_network_data("test-app", "vpc-12345678")
        
        # Verify result structure
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertIn("timestamp", result["data"])
        self.assertIn("app_name", result["data"])
        self.assertIn("vpc_ids", result["data"])
        self.assertIn("raw_resources", result["data"])
        self.assertIn("analysis_guide", result["data"])
        
        # Verify VPC ID was used
        self.assertEqual(result["data"]["vpc_ids"], ["vpc-12345678"])

    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_get_network_data_no_vpc(self, mock_get_aws_client):
        """Test get_network_data when no VPC is found."""
        # Configure mocks for different AWS services
        mock_ec2 = AsyncMock()
        mock_ecs = AsyncMock()
        mock_elbv2 = AsyncMock()
        
        # Configure get_aws_client to return our mocks
        async def mock_get_client(service_name):
            if service_name == 'ec2':
                return mock_ec2
            elif service_name == 'ecs':
                return mock_ecs
            elif service_name == 'elbv2':
                return mock_elbv2
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        
        # Mock empty responses for VPC discovery
        mock_ecs.list_clusters.return_value = {"clusterArns": []}
        mock_ecs.list_tasks.return_value = {"taskArns": []}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}
        
        # Call the function
        result = await get_network_data("test-app-no-vpc")
        
        # Verify result
        self.assertEqual(result["status"], "warning")
        self.assertIn("No VPC found", result["message"])

    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_discover_vpcs_from_clusters(self, mock_get_aws_client):
        """Test VPC discovery from ECS clusters."""
        # Configure mock clients
        mock_ecs = AsyncMock()
        mock_ec2 = AsyncMock()
        
        # Configure get_aws_client to return our mocks
        async def mock_get_client(service_name):
            if service_name == 'ecs':
                return mock_ecs
            elif service_name == 'ec2':
                return mock_ec2
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        
        # Configure responses
        mock_ecs.list_tasks.return_value = {
            'taskArns': ['arn:aws:ecs:us-west-2:123456789012:task/test-cluster/abcdef123456']
        }
        mock_ecs.describe_tasks.return_value = {
            'tasks': [{
                'attachments': [{
                    'type': 'ElasticNetworkInterface',
                    'details': [
                        {'name': 'networkInterfaceId', 'value': 'eni-12345678'}
                    ]
                }]
            }]
        }
        mock_ec2.describe_network_interfaces.return_value = {
            'NetworkInterfaces': [{
                'NetworkInterfaceId': 'eni-12345678',
                'VpcId': 'vpc-12345678'
            }]
        }
        
        # Call function
        vpc_ids = await discover_vpcs_from_clusters(['test-cluster'])
        
        # Verify result
        self.assertEqual(vpc_ids, ['vpc-12345678'])
        
        # Verify correct API calls made
        mock_ecs.list_tasks.assert_called_once_with(cluster='test-cluster')
        mock_ecs.describe_tasks.assert_called_once()
        mock_ec2.describe_network_interfaces.assert_called_once()
        
    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_discover_vpcs_from_clusters_no_tasks(self, mock_get_aws_client):
        """Test VPC discovery when no tasks are found."""
        mock_ecs = AsyncMock()
        
        # Configure get_aws_client to return our mock
        async def mock_get_client(service_name):
            if service_name == 'ecs':
                return mock_ecs
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        mock_ecs.list_tasks.return_value = {'taskArns': []}
        
        # Call function
        vpc_ids = await discover_vpcs_from_clusters(['empty-cluster'])
        
        # Verify result - should be empty list
        self.assertEqual(vpc_ids, [])
        
        # Verify no describe_tasks call was made
        mock_ecs.describe_tasks.assert_not_called()
        
    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_discover_vpcs_from_loadbalancers(self, mock_get_aws_client):
        """Test VPC discovery from load balancers."""
        mock_elbv2 = AsyncMock()
        
        # Configure get_aws_client to return our mock
        async def mock_get_client(service_name):
            if service_name == 'elbv2':
                return mock_elbv2
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        
        # Configure responses
        mock_elbv2.describe_load_balancers.return_value = {
            'LoadBalancers': [
                {
                    'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/test-app-alb/1234567890',
                    'LoadBalancerName': 'test-app-alb',
                    'VpcId': 'vpc-12345678'
                },
                {
                    'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/other-alb/0987654321',
                    'LoadBalancerName': 'other-alb',
                    'VpcId': 'vpc-87654321'
                }
            ]
        }
        
        # Call function
        vpc_ids = await discover_vpcs_from_loadbalancers('test-app')
        
        # Verify result - should find only the matching ALB's VPC
        self.assertEqual(vpc_ids, ['vpc-12345678'])
        
    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_discover_vpcs_from_loadbalancers_with_tags(self, mock_get_aws_client):
        """Test VPC discovery from load balancers with name in tags."""
        mock_elbv2 = AsyncMock()
        
        # Configure get_aws_client to return our mock
        async def mock_get_client(service_name):
            if service_name == 'elbv2':
                return mock_elbv2
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        
        # Configure responses
        mock_elbv2.describe_load_balancers.return_value = {
            'LoadBalancers': [
                {
                    'LoadBalancerArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/generic-alb/1234567890',
                    'LoadBalancerName': 'generic-alb',
                    'VpcId': 'vpc-12345678'
                }
            ]
        }
        
        mock_elbv2.describe_tags.return_value = {
            'TagDescriptions': [
                {
                    'ResourceArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/generic-alb/1234567890',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'test-app-production'}
                    ]
                }
            ]
        }
        
        # Call function
        vpc_ids = await discover_vpcs_from_loadbalancers('test-app')
        
        # Verify result - should find VPC from tagged ALB
        self.assertEqual(vpc_ids, ['vpc-12345678'])
        
    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_discover_vpcs_from_cloudformation(self, mock_get_aws_client):
        """Test VPC discovery from CloudFormation stacks."""
        mock_cfn = AsyncMock()
        
        # Configure get_aws_client to return our mock
        async def mock_get_client(service_name):
            if service_name == 'cloudformation':
                return mock_cfn
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        
        # Configure responses
        mock_cfn.list_stacks.return_value = {
            'StackSummaries': [
                {
                    'StackName': 'test-app-ecs-stack',
                    'StackStatus': 'CREATE_COMPLETE'
                },
                {
                    'StackName': 'other-stack',
                    'StackStatus': 'CREATE_COMPLETE'
                },
                {
                    'StackName': 'deleted-stack',
                    'StackStatus': 'DELETE_COMPLETE'
                }
            ]
        }
        
        mock_cfn.list_stack_resources.return_value = {
            'StackResourceSummaries': [
                {
                    'LogicalResourceId': 'VPC',
                    'ResourceType': 'AWS::EC2::VPC',
                    'PhysicalResourceId': 'vpc-cloudfoundation'
                }
            ]
        }
        
        # Call function
        vpc_ids = await discover_vpcs_from_cloudformation('test-app')
        
        # Verify result - should find VPC from CloudFormation
        self.assertEqual(vpc_ids, ['vpc-cloudfoundation'])
        
        # Verify proper filtering of stacks
        mock_cfn.list_stack_resources.assert_called_once_with(StackName='test-app-ecs-stack')
        
    @patch('awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration.get_aws_client')
    async def test_discover_vpcs_from_cloudformation_pagination(self, mock_get_aws_client):
        """Test VPC discovery with CloudFormation pagination."""
        mock_cfn = AsyncMock()
        
        # Configure get_aws_client to return our mock
        async def mock_get_client(service_name):
            if service_name == 'cloudformation':
                return mock_cfn
            return AsyncMock()
            
        mock_get_aws_client.side_effect = mock_get_client
        
        # Setup pagination responses
        mock_cfn.list_stacks.side_effect = [
            {
                'StackSummaries': [
                    {'StackName': 'test-app-stack1', 'StackStatus': 'CREATE_COMPLETE'}
                ],
                'NextToken': 'page2token'
            },
            {
                'StackSummaries': [
                    {'StackName': 'test-app-stack2', 'StackStatus': 'CREATE_COMPLETE'}
                ]
            }
        ]
        
        mock_cfn.list_stack_resources.side_effect = [
            {'StackResourceSummaries': [{'ResourceType': 'AWS::EC2::VPC', 'PhysicalResourceId': 'vpc-page1'}]},
            {'StackResourceSummaries': [{'ResourceType': 'AWS::EC2::VPC', 'PhysicalResourceId': 'vpc-page2'}]}
        ]
        
        # Call function
        vpc_ids = await discover_vpcs_from_cloudformation('test-app')
        
        # Verify both pages were processed
        self.assertEqual(sorted(vpc_ids), sorted(['vpc-page1', 'vpc-page2']))
        self.assertEqual(mock_cfn.list_stacks.call_count, 2)
        self.assertEqual(mock_cfn.list_stack_resources.call_count, 2)
        
    async def test_get_ec2_resource_with_filters(self):
        """Test EC2 resource retrieval with VPC filtering."""
        mock_ec2 = AsyncMock()
        
        vpc_ids = ['vpc-12345678']
        
        # Test describe_subnets with VPC filter
        await get_ec2_resource(mock_ec2, 'describe_subnets', vpc_ids)
        mock_ec2.describe_subnets.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': vpc_ids}]
        )
        
        # Reset mock
        mock_ec2.reset_mock()
        
        # Test describe_vpcs with VpcIds parameter
        await get_ec2_resource(mock_ec2, 'describe_vpcs', vpc_ids)
        mock_ec2.describe_vpcs.assert_called_once_with(VpcIds=vpc_ids)
        
    async def test_get_ec2_resource_handles_errors(self):
        """Test EC2 resource retrieval handles errors gracefully."""
        mock_ec2 = AsyncMock()
        
        # Configure mock to raise exception
        mock_ec2.describe_subnets.side_effect = Exception("API Error")
        
        # Call function
        result = await get_ec2_resource(mock_ec2, 'describe_subnets')
        
        # Verify error is returned but doesn't raise exception
        self.assertIn("error", result)
        # The error message format was updated in the implementation
        self.assertEqual(result["error"], "API Error")
        
    async def test_get_elb_resources_with_vpc_filter(self):
        """Test ELB resource retrieval with VPC filtering."""
        mock_elbv2 = AsyncMock()
        
        # Configure mock response
        mock_elbv2.describe_load_balancers.return_value = {
            'LoadBalancers': [
                {'LoadBalancerArn': 'arn1', 'VpcId': 'vpc-12345678'},
                {'LoadBalancerArn': 'arn2', 'VpcId': 'vpc-87654321'}
            ]
        }
        
        # Call function with VPC filter
        result = await get_elb_resources(mock_elbv2, 'describe_load_balancers', ['vpc-12345678'])
        
        # Verify result contains only matching VPC
        self.assertEqual(len(result['LoadBalancers']), 1)
        self.assertEqual(result['LoadBalancers'][0]['VpcId'], 'vpc-12345678')
        
    async def test_get_associated_target_groups(self):
        """Test target group retrieval and health checking."""
        mock_elbv2 = AsyncMock()
        
        # Configure mock responses
        mock_elbv2.describe_target_groups.return_value = {
            'TargetGroups': [
                {
                    'TargetGroupArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-app-tg/1234567890',
                    'TargetGroupName': 'test-app-tg',
                    'VpcId': 'vpc-12345678'
                },
                {
                    'TargetGroupArn': 'arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/other-tg/0987654321',
                    'TargetGroupName': 'other-tg',
                    'VpcId': 'vpc-12345678'
                }
            ]
        }
        
        mock_elbv2.describe_target_health.return_value = {
            'TargetHealthDescriptions': [
                {
                    'Target': {'Id': 'i-12345678', 'Port': 80},
                    'TargetHealth': {'State': 'healthy'}
                }
            ]
        }
        
        # Call function
        result = await get_associated_target_groups(mock_elbv2, 'test-app', ['vpc-12345678'])
        
        # Verify name filtering
        self.assertEqual(len(result['TargetGroups']), 1)
        self.assertEqual(result['TargetGroups'][0]['TargetGroupName'], 'test-app-tg')
        
        # Verify health was checked
        self.assertIn('TargetHealth', result)
        tg_arn = 'arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-app-tg/1234567890'
        self.assertIn(tg_arn, result['TargetHealth'])

    def test_generate_analysis_guide(self):
        """Test that analysis guide is generated with the expected structure."""
        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import generate_analysis_guide
        
        # Get guide
        guide = generate_analysis_guide()
        
        # Verify structure
        self.assertIn("common_issues", guide)
        self.assertIn("resource_relationships", guide)
        
        # Check common_issues
        self.assertTrue(isinstance(guide["common_issues"], list))
        self.assertTrue(len(guide["common_issues"]) > 0)
        
        # Check resource_relationships
        self.assertTrue(isinstance(guide["resource_relationships"], list))
        self.assertTrue(len(guide["resource_relationships"]) > 0)
        
        # Check format of first issue
        first_issue = guide["common_issues"][0]
        self.assertIn("issue", first_issue)
        self.assertIn("description", first_issue)
        self.assertIn("checks", first_issue)
