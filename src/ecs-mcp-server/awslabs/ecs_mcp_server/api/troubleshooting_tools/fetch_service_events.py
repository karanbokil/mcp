"""
Service-level diagnostics for ECS services.

This module provides a function to analyze ECS service events and configuration to identify
service-level issues that may be affecting deployments.
"""

import logging
import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def fetch_service_events(
    app_name: str,
    cluster_name: str,
    service_name: str,
    time_window: int = 3600,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None
) -> Dict[str, Any]:
    """
    Service-level diagnostics for ECS services.

    Parameters
    ----------
    app_name : str
        The name of the application to analyze
    cluster_name : str
        The name of the ECS cluster
    service_name : str
        The name of the ECS service to analyze
    time_window : int, optional
        Time window in seconds to look back for events (default: 3600)
    start_time : datetime, optional
        Explicit start time for the analysis window (UTC, takes precedence over time_window if provided)
    end_time : datetime, optional
        Explicit end time for the analysis window (UTC, defaults to current time if not provided)

    Returns
    -------
    Dict[str, Any]
        Service status, events, deployment status, and configuration issues
    """
    try:            
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
            "service_exists": False,
            "service_status": None,
            "events": [],
            "deployment_status": None,
            "load_balancer_issues": [],
            "raw_data": {}
        }
        
        # Initialize ECS client
        ecs = boto3.client('ecs')
        
        # Check if service exists
        try:
            services = ecs.describe_services(cluster=cluster_name, services=[service_name])
            
            if not services['services'] or services['services'][0]['status'] == 'INACTIVE':
                response["service_exists"] = False
                if services.get('failures'):
                    response["failures"] = services['failures']
                return response
                
            response["service_exists"] = True
            service = services['services'][0]
            response["service_status"] = service["status"]
            response["raw_data"]["service"] = service
            
            # Extract deployment status
            if "deployments" in service:
                deployments = service["deployments"]
                response["deployment_status"] = {
                    "active_deployment": next((d for d in deployments if d["status"] == "PRIMARY"), None),
                    "previous_deployments": [d for d in deployments if d["status"] == "ACTIVE" and d != next((d for d in deployments if d["status"] == "PRIMARY"), None)],
                    "count": len(deployments)
                }
            
            # Extract service events
            if "events" in service:
                filtered_events = []
                for event in service["events"]:
                    filtered_events.append({
                        "message": event["message"],
                        "timestamp": event["createdAt"].isoformat() if isinstance(event["createdAt"], datetime.datetime) else event["createdAt"],
                        "id": event.get("id", "unknown")
                    })
                
                response["events"] = filtered_events
            
            # Check for load balancer issues
            if "loadBalancers" in service:
                for lb in service["loadBalancers"]:
                    # Check for common load balancer issues
                    lb_issues = []
                    
                    # Check if target group exists and is healthy
                    if "targetGroupArn" in lb:
                        elb = boto3.client('elbv2')
                        try:
                            tg_health = elb.describe_target_health(TargetGroupArn=lb["targetGroupArn"])
                            
                            # Check if any targets are unhealthy
                            unhealthy_targets = [t for t in tg_health.get("TargetHealthDescriptions", []) 
                                              if t.get("TargetHealth", {}).get("State") != "healthy"]
                            
                            if unhealthy_targets:
                                lb_issues.append({
                                    "type": "unhealthy_targets",
                                    "count": len(unhealthy_targets),
                                    "details": unhealthy_targets
                                })
                                
                            # Check if container port and target group port match
                            if "containerPort" in lb:
                                try:
                                    tg = elb.describe_target_groups(TargetGroupArns=[lb["targetGroupArn"]])
                                    if tg["TargetGroups"] and tg["TargetGroups"][0]["Port"] != lb["containerPort"]:
                                        lb_issues.append({
                                            "type": "port_mismatch",
                                            "container_port": lb["containerPort"],
                                            "target_group_port": tg["TargetGroups"][0]["Port"]
                                        })
                                except ClientError as tg_error:
                                    lb_issues.append({
                                        "type": "target_group_error",
                                        "error": str(tg_error)
                                    })
                                    
                        except ClientError as health_error:
                            lb_issues.append({
                                "type": "health_check_error",
                                "error": str(health_error)
                            })
                    
                    if lb_issues:
                        response["load_balancer_issues"].append({
                            "load_balancer": lb,
                            "issues": lb_issues
                        })
            
        except ClientError as e:
            response["service_error"] = str(e)
            if "ClusterNotFoundException" in str(e):
                response["message"] = f"Cluster '{cluster_name}' does not exist"
            elif "ServiceNotFoundException" in str(e):
                response["message"] = f"Service '{service_name}' does not exist in cluster '{cluster_name}'"
        
        return response
        
    except Exception as e:
        logger.exception("Error in fetch_service_events: %s", str(e))
        return {
            "status": "error",
            "error": str(e)
        }
