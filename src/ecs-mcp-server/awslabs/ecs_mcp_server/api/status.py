"""
API for getting the status of ECS deployments.
"""

import logging
from typing import Any, Dict, Optional

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


async def get_deployment_status(
    app_name: str, cluster_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gets the status of an ECS deployment and returns the ALB URL.

    Args:
        app_name: Name of the application
        cluster_name: Name of the ECS cluster (optional, defaults to {app_name}-cluster)

    Returns:
        Dict containing deployment status and ALB URL
    """
    logger.info(f"Getting deployment status for {app_name}")

    # Use provided cluster name or default
    cluster = cluster_name or f"{app_name}-cluster"

    # Get service status
    ecs_client = await get_aws_client("ecs")
    try:
        service_response = ecs_client.describe_services(
            cluster=cluster, services=[f"{app_name}-service"]
        )

        if not service_response["services"]:
            return {
                "status": "NOT_FOUND",
                "message": f"Service {app_name}-service not found in cluster {cluster}",
                "alb_url": None,
            }

        service = service_response["services"][0]
        service_status = service["status"]

        # Get deployment status
        deployments = service.get("deployments", [])
        deployment_status = "UNKNOWN"
        if deployments:
            primary_deployment = next(
                (d for d in deployments if d.get("status") == "PRIMARY"), None
            )
            if primary_deployment:
                if primary_deployment.get("rolloutState"):
                    deployment_status = primary_deployment["rolloutState"]
                else:
                    # For older ECS versions
                    running_count = primary_deployment.get("runningCount", 0)
                    desired_count = primary_deployment.get("desiredCount", 0)
                    if running_count == desired_count and desired_count > 0:
                        deployment_status = "COMPLETED"
                    else:
                        deployment_status = "IN_PROGRESS"

        # Get ALB URL
        alb_url = await _get_alb_url(app_name)

        # Get task status
        tasks_response = ecs_client.list_tasks(cluster=cluster, serviceName=f"{app_name}-service")

        task_status = []
        if tasks_response.get("taskArns"):
            task_details = ecs_client.describe_tasks(
                cluster=cluster, tasks=tasks_response["taskArns"]
            )

            for task in task_details.get("tasks", []):
                task_status.append(
                    {
                        "task_id": task["taskArn"].split("/")[-1],
                        "status": task["lastStatus"],
                        "health_status": task.get("healthStatus", "UNKNOWN"),
                        "started_at": (
                            task.get("startedAt", "").isoformat() if task.get("startedAt") else None
                        ),
                    }
                )

        return {
            "app_name": app_name,
            "cluster": cluster,
            "service_status": service_status,
            "deployment_status": deployment_status,
            "alb_url": alb_url,
            "tasks": task_status,
            "running_count": service.get("runningCount", 0),
            "desired_count": service.get("desiredCount", 0),
            "pending_count": service.get("pendingCount", 0),
            "message": f"Application {app_name} deployment status: {deployment_status}",
        }

    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        return {
            "status": "ERROR",
            "message": f"Error getting deployment status: {str(e)}",
            "alb_url": None,
        }


async def _get_alb_url(app_name: str) -> Optional[str]:
    """Gets the ALB URL from CloudFormation outputs."""
    cloudformation = await get_aws_client("cloudformation")

    try:
        response = cloudformation.describe_stacks(StackName=f"{app_name}-ecs-infrastructure")

        for output in response["Stacks"][0]["Outputs"]:
            if output["OutputKey"] == "LoadBalancerDNS":
                return f"http://{output['OutputValue']}"
    except Exception as e:
        logger.error(f"Error getting ALB URL: {e}")

    return None
