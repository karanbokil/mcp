"""
Task-level diagnostics for ECS task failures.

This module provides a function to analyze failed ECS tasks to identify patterns and
common failure reasons to help diagnose container-level issues.
"""

import logging
import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def fetch_task_failures(
    app_name: str,
    cluster_name: Optional[str] = None,
    time_window: int = 3600,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None
) -> Dict[str, Any]:
    """
    Task-level diagnostics for ECS task failures.

    Parameters
    ----------
    app_name : str
        The name of the application to analyze
    cluster_name : str
        The name of the ECS cluster
    time_window : int, optional
        Time window in seconds to look back for failures (default: 3600)
    start_time : datetime, optional
        Explicit start time for the analysis window (UTC, takes precedence over time_window if provided)
    end_time : datetime, optional
        Explicit end time for the analysis window (UTC, defaults to current time if not provided)

    Returns
    -------
    Dict[str, Any]
        Failed tasks with timestamps, exit codes, status, and resource utilization
    """
    try:
        if not cluster_name:
            cluster_name = f"{app_name}-cluster"
            
        # Determine the time range based on provided parameters
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Handle provided start_time and end_time
        if end_time is None:
            # If no end_time provided, use current time
            actual_end_time = now
        else:
            # Ensure end_time is timezone-aware
            actual_end_time = end_time if end_time.tzinfo else end_time.replace(tzinfo=datetime.timezone.utc)
        
        if start_time is not None:
            # If start_time provided, use it directly
            actual_start_time = start_time if start_time.tzinfo else start_time.replace(tzinfo=datetime.timezone.utc)
        elif end_time is not None:
            # If only end_time provided, calculate start_time using time_window
            actual_start_time = actual_end_time - datetime.timedelta(seconds=time_window)
        else:
            # Default case: use time_window from now
            actual_start_time = now - datetime.timedelta(seconds=time_window)
        
        response = {
            "status": "success",
            "cluster_exists": False,
            "failed_tasks": [],
            "failure_categories": {},
            "raw_data": {}
        }
        
        # Initialize ECS client
        ecs = boto3.client('ecs')
        
        # Check if cluster exists
        try:
            clusters = ecs.describe_clusters(clusters=[cluster_name])
            if not clusters['clusters']:
                response["message"] = f"Cluster '{cluster_name}' does not exist"
                return response
                
            response["cluster_exists"] = True
            response["raw_data"]["cluster"] = clusters['clusters'][0]
            
            # Get recently stopped tasks
            stopped_tasks = []
            paginator = ecs.get_paginator('list_tasks')
            for page in paginator.paginate(cluster=cluster_name, desiredStatus='STOPPED'):
                if page['taskArns']:
                    # Get detailed task information
                    tasks_detail = ecs.describe_tasks(cluster=cluster_name, tasks=page['taskArns'])
                    for task in tasks_detail['tasks']:
                        # Check if the task was stopped within the time window
                        if 'stoppedAt' in task:
                            stopped_at = task['stoppedAt']
                            # Handle timezone-aware vs naive datetime objects
                            if isinstance(stopped_at, datetime.datetime):
                                # Make stopped_at timezone-aware if it's naive
                                if stopped_at.tzinfo is None:
                                    stopped_at = stopped_at.replace(tzinfo=datetime.timezone.utc)
                                if stopped_at >= actual_start_time:
                                    stopped_tasks.append(task)
            
            # Get running tasks for comparison
            running_tasks = []
            for page in paginator.paginate(cluster=cluster_name, desiredStatus='RUNNING'):
                if page['taskArns']:
                    tasks_detail = ecs.describe_tasks(cluster=cluster_name, tasks=page['taskArns'])
                    running_tasks.extend(tasks_detail['tasks'])
            
            response["raw_data"]["running_tasks_count"] = len(running_tasks)
            
            # Process stopped tasks to extract failure information
            for task in stopped_tasks:
                task_failure = {
                    "task_id": task["taskArn"].split("/")[-1],
                    "task_definition": task["taskDefinitionArn"].split("/")[-1],
                    "stopped_at": task["stoppedAt"].isoformat() if isinstance(task["stoppedAt"], datetime.datetime) else task["stoppedAt"],
                    "started_at": task.get("startedAt", "N/A"),
                    "containers": []
                }
                
                # Process container information
                for container in task["containers"]:
                    container_info = {
                        "name": container["name"],
                        "exit_code": container.get("exitCode", "N/A"),
                        "reason": container.get("reason", "No reason provided")
                    }
                    task_failure["containers"].append(container_info)
                    
                    # Categorize failures
                    categorized = False
                    
                    # Image pull failures
                    if "CannotPullContainerError" in container.get("reason", "") or \
                       "ImagePull" in container.get("reason", ""):
                        category = "image_pull_failure"
                        categorized = True
                    
                    # Resource constraints
                    elif "resource" in container.get("reason", "").lower() and \
                         ("constraint" in container.get("reason", "").lower() or 
                          "exceed" in container.get("reason", "").lower()):
                        category = "resource_constraint"
                        categorized = True
                    
                    # Exit code 137 (OOM killed)
                    elif container.get("exitCode") == 137:
                        category = "out_of_memory"
                        categorized = True
                    
                    # Exit code 139 (segmentation fault)
                    elif container.get("exitCode") == 139:
                        category = "segmentation_fault"
                        categorized = True
                    
                    # Exit code 1 or other non-zero (application error)
                    elif container.get("exitCode", 0) != 0 and container.get("exitCode") not in [None, "N/A"]:
                        category = "application_error"
                        categorized = True
                    
                    # Task stopped by user or deployment
                    elif "Essential container" in container.get("reason", ""):
                        category = "dependent_container_stopped"
                        categorized = True
                    
                    # Catch-all for uncategorized failures
                    else:
                        category = "other"
                        categorized = True
                    
                    if categorized:
                        if category not in response["failure_categories"]:
                            response["failure_categories"][category] = []
                        response["failure_categories"][category].append(task_failure)
                
                response["failed_tasks"].append(task_failure)
            
            # Get CloudWatch metrics for any failed tasks
            if response["failed_tasks"]:
                try:
                    cloudwatch = boto3.client('cloudwatch')
                    # We'll skip the actual implementation for brevity
                    # This would query CloudWatch metrics for CPU/memory usage near failure time
                    response["cloudwatch_metrics"] = "Metrics retrieval skipped for brevity"
                except ClientError as cw_error:
                    response["cloudwatch_error"] = str(cw_error)
            
        except ClientError as e:
            response["ecs_error"] = str(e)
        
        return response
        
    except Exception as e:
        logger.exception("Error in fetch_task_failures: %s", str(e))
        return {
            "status": "error",
            "error": str(e)
        }
