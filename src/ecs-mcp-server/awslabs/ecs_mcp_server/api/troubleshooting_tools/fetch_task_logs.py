"""
Application-level diagnostics through CloudWatch logs.

This module provides a function to retrieve and analyze CloudWatch logs for ECS tasks
to identify application-level issues.
"""

import logging
import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def fetch_task_logs(
    app_name: str,
    cluster_name: str,
    task_id: Optional[str] = None,
    time_window: int = 3600,
    filter_pattern: Optional[str] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None
) -> Dict[str, Any]:
    """
    Application-level diagnostics through CloudWatch logs.

    Parameters
    ----------
    app_name : str
        The name of the application to analyze
    cluster_name : str
        The name of the ECS cluster
    task_id : str, optional
        Specific task ID to retrieve logs for
    time_window : int, optional
        Time window in seconds to look back for logs (default: 3600)
    filter_pattern : str, optional
        CloudWatch logs filter pattern
    start_time : datetime, optional
        Explicit start time for the analysis window (UTC, takes precedence over time_window if provided)
    end_time : datetime, optional
        Explicit end time for the analysis window (UTC, defaults to current time if not provided)

    Returns
    -------
    Dict[str, Any]
        Log entries with severity markers, highlighted errors, context
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
            "log_groups": [],
            "log_entries": [],
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "pattern_summary": []
        }
        
        # Initialize CloudWatch Logs client
        logs = boto3.client('logs')
        
        # Determine log group name pattern
        # Usually follows the format /ecs/{cluster_name}/{task_or_service_name}
        log_group_pattern = f"/ecs/{cluster_name}/{app_name}"
        
        # List matching log groups
        log_groups = logs.describe_log_groups(logGroupNamePrefix=log_group_pattern)
        
        if not log_groups["logGroups"]:
            response["status"] = "not_found"
            response["message"] = f"No log groups found matching pattern '{log_group_pattern}'"
            return response
        
        # For each log group, get the log streams
        for log_group in log_groups["logGroups"]:
            log_group_name = log_group["logGroupName"]
            log_group_info = {
                "name": log_group_name,
                "log_streams": [],
                "entries": []
            }
            
            # Get log streams
            try:
                if task_id:
                    # If task_id is provided, look for matching log stream
                    stream_prefix = task_id.split("-")[0]  # Usually task ID starts with log stream name
                    log_streams = logs.describe_log_streams(
                        logGroupName=log_group_name,
                        logStreamNamePrefix=stream_prefix,
                        orderBy='LastEventTime',
                        descending=True
                    )
                else:
                    # Otherwise get all recent log streams
                    log_streams = logs.describe_log_streams(
                        logGroupName=log_group_name,
                        orderBy='LastEventTime',
                        descending=True
                    )
                
                for log_stream in log_streams["logStreams"]:
                    log_stream_name = log_stream["logStreamName"]
                    
                    # Skip if it's a specific task request and this stream doesn't match
                    if task_id and task_id not in log_stream_name:
                        continue
                    
                    # Get log events
                    try:
                        args = {
                            "logGroupName": log_group_name,
                            "logStreamName": log_stream_name,
                            "startTime": int(actual_start_time.timestamp() * 1000),  # Convert to milliseconds
                            "endTime": int(actual_end_time.timestamp() * 1000),
                            "limit": 1000  # Adjust as needed
                        }
                        
                        if filter_pattern:
                            args["filterPattern"] = filter_pattern
                            
                        log_events = logs.get_log_events(**args)
                        
                        # Process log events
                        for event in log_events["events"]:
                            timestamp = datetime.datetime.fromtimestamp(event["timestamp"] / 1000.0)
                            message = event["message"]
                            
                            # Determine log severity
                            severity = "INFO"
                            if "ERROR" in message.upper() or "EXCEPTION" in message.upper() or "FAIL" in message.upper():
                                severity = "ERROR"
                                response["error_count"] += 1
                            elif "WARN" in message.upper():
                                severity = "WARN"
                                response["warning_count"] += 1
                            else:
                                response["info_count"] += 1
                            
                            log_entry = {
                                "timestamp": timestamp.isoformat(),
                                "message": message,
                                "severity": severity,
                                "stream": log_stream_name
                            }
                            
                            log_group_info["entries"].append(log_entry)
                            response["log_entries"].append(log_entry)
                            
                    except ClientError as event_error:
                        response.setdefault("errors", []).append(f"Error retrieving log events for stream {log_stream_name}: {str(event_error)}")
                    
                    log_group_info["log_streams"].append(log_stream_name)
                    
            except ClientError as stream_error:
                response.setdefault("errors", []).append(f"Error retrieving log streams for group {log_group_name}: {str(stream_error)}")
            
            response["log_groups"].append(log_group_info)
        
        # Find error patterns
        error_messages = [entry["message"] for entry in response["log_entries"] if entry["severity"] == "ERROR"]
        
        # Simple pattern identification - count occurrences of common error messages
        error_patterns = {}
        for error in error_messages:
            # Simplify error message to identify patterns (first 50 chars)
            pattern = error[:50]
            if pattern in error_patterns:
                error_patterns[pattern] += 1
            else:
                error_patterns[pattern] = 1
        
        # Sort patterns by frequency
        sorted_patterns = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)
        
        # Add top patterns to response
        for pattern, count in sorted_patterns[:5]:  # Top 5 patterns
            response["pattern_summary"].append({
                "pattern": pattern,
                "count": count,
                "sample": next((error for error in error_messages if error.startswith(pattern)), "")
            })
        
        return response
            
    except Exception as e:
        logger.exception("Error in fetch_task_logs: %s", str(e))
        return {
            "status": "error",
            "error": str(e),
            "log_entries": []
        }
