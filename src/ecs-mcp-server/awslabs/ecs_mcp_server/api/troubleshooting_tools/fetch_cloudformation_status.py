"""
Infrastructure-level diagnostics for CloudFormation stacks.

This module provides a function to analyze CloudFormation stacks, check stack status,
identify failed resources, and extract error messages to help diagnose infrastructure-level issues.
"""

import logging
import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def fetch_cloudformation_status(app_name: str) -> Dict[str, Any]:
    """
    Infrastructure-level diagnostics for CloudFormation stacks.

    Parameters
    ----------
    app_name : str
        The name of the application/stack to analyze

    Returns
    -------
    Dict[str, Any]
        Stack status, resources, failure reasons, and raw events
    """
    try:
        response = {
            "status": "success",
            "stack_exists": False,
            "stack_status": None,
            "resources": [],
            "failure_reasons": [],
            "raw_events": []
        }
        
        # Initialize CloudFormation client
        cloudformation = boto3.client('cloudformation')
        
        # Check if stack exists
        try:
            stack_response = cloudformation.describe_stacks(StackName=app_name)
            stack = stack_response["Stacks"][0]
            response["stack_exists"] = True
            response["stack_status"] = stack["StackStatus"]
            
            # Get stack resources
            try:
                resources_response = cloudformation.list_stack_resources(StackName=app_name)
                response["resources"] = resources_response["StackResourceSummaries"]
                
                # Extract failed resources
                for resource in response["resources"]:
                    if resource["ResourceStatus"].endswith("FAILED"):
                        failure_reason = {
                            "logical_id": resource["LogicalResourceId"],
                            "physical_id": resource.get("PhysicalResourceId", "N/A"),
                            "resource_type": resource["ResourceType"],
                            "status": resource["ResourceStatus"],
                            "reason": resource.get("ResourceStatusReason", "No reason provided")
                        }
                        response["failure_reasons"].append(failure_reason)
            except ClientError as e:
                response["resources_error"] = str(e)
            
            # Get stack events for deeper analysis
            try:
                events_response = cloudformation.describe_stack_events(StackName=app_name)
                response["raw_events"] = events_response["StackEvents"]
                
                # Extract additional failure reasons from events
                for event in response["raw_events"]:
                    if event["ResourceStatus"].endswith("FAILED") and \
                       "ResourceStatusReason" in event and \
                       not any(failure["logical_id"] == event["LogicalResourceId"] for failure in response["failure_reasons"]):
                        failure_reason = {
                            "logical_id": event["LogicalResourceId"],
                            "physical_id": event.get("PhysicalResourceId", "N/A"),
                            "resource_type": event["ResourceType"],
                            "status": event["ResourceStatus"],
                            "reason": event.get("ResourceStatusReason", "No reason provided"),
                            "timestamp": event["Timestamp"].isoformat() if isinstance(event["Timestamp"], datetime.datetime) else event["Timestamp"]
                        }
                        response["failure_reasons"].append(failure_reason)
            except ClientError as e:
                response["events_error"] = str(e)
                
        except ClientError as e:
            if "does not exist" in str(e):
                # Stack doesn't exist, check for deleted stacks
                try:
                    deleted_stacks = []
                    paginator = cloudformation.get_paginator('list_stacks')
                    for page in paginator.paginate(StackStatusFilter=['DELETE_COMPLETE']):
                        for stack_summary in page['StackSummaries']:
                            if stack_summary['StackName'] == app_name:
                                deleted_stacks.append(stack_summary)
                    
                    if deleted_stacks:
                        response["deleted_stacks"] = deleted_stacks
                        response["note"] = f"Found {len(deleted_stacks)} deleted stacks with name '{app_name}'"
                except ClientError as list_error:
                    response["list_error"] = str(list_error)
            else:
                raise
                
        return response
        
    except Exception as e:
        logger.exception("Error in fetch_cloudformation_status: %s", str(e))
        return {
            "status": "error",
            "error": str(e),
            "stack_exists": False
        }
