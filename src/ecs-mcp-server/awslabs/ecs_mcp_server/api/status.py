"""
API for getting the status of ECS deployments.
"""

import logging
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


async def get_deployment_status(
    app_name: str, cluster_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gets the status of an ECS deployment and returns the ALB URL.
    
    This function also polls the CloudFormation stack status to provide
    more complete deployment information. When deployment is successful,
    it provides guidance on setting up custom domains and HTTPS.

    Args:
        app_name: Name of the application
        cluster_name: Name of the ECS cluster (optional, defaults to {app_name}-cluster)

    Returns:
        Dict containing deployment status, CloudFormation stack status, ALB URL,
        and guidance for custom domain and HTTPS setup when deployment is successful
    """
    logger.info(f"Getting deployment status for {app_name}")

    # Use provided cluster name or default
    cluster = cluster_name or f"{app_name}-cluster"
    
    # Get CloudFormation stack status
    stack_name = f"{app_name}-ecs-infrastructure"
    stack_status = await _get_cfn_stack_status(stack_name)
    
    # If stack doesn't exist or is in a failed state, return early
    if stack_status.get("status") in ["NOT_FOUND", "ROLLBACK_COMPLETE", "ROLLBACK_IN_PROGRESS", "DELETE_COMPLETE"]:
        return {
            "app_name": app_name,
            "status": "INFRASTRUCTURE_UNAVAILABLE",
            "stack_status": stack_status,
            "message": f"Infrastructure for {app_name} is not available: {stack_status.get('status')}",
            "alb_url": None,
        }

    # Get service status
    ecs_client = await get_aws_client("ecs")
    try:
        service_response = ecs_client.describe_services(
            cluster=cluster, services=[f"{app_name}-service"]
        )

        if not service_response["services"]:
            return {
                "app_name": app_name,
                "status": "NOT_FOUND",
                "stack_status": stack_status,
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
                
        # Determine overall deployment status
        overall_status = "IN_PROGRESS"
        if stack_status.get("status") == "CREATE_COMPLETE" and deployment_status == "COMPLETED":
            if service.get("runningCount", 0) == service.get("desiredCount", 0) and service.get("desiredCount", 0) > 0:
                overall_status = "COMPLETE"
        elif "FAIL" in stack_status.get("status", "") or "ROLLBACK" in stack_status.get("status", ""):
            overall_status = "FAILED"
            
        # Generate custom domain and HTTPS guidance if deployment is complete
        custom_domain_guidance = None
        if overall_status == "COMPLETE" and alb_url:
            custom_domain_guidance = _generate_custom_domain_guidance(app_name, alb_url)

        return {
            "app_name": app_name,
            "cluster": cluster,
            "status": overall_status,
            "service_status": service_status,
            "deployment_status": deployment_status,
            "stack_status": stack_status,
            "alb_url": alb_url,
            "tasks": task_status,
            "running_count": service.get("runningCount", 0),
            "desired_count": service.get("desiredCount", 0),
            "pending_count": service.get("pendingCount", 0),
            "message": f"Application {app_name} deployment status: {overall_status}",
            "custom_domain_guidance": custom_domain_guidance,
        }

    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        return {
            "app_name": app_name,
            "status": "ERROR",
            "stack_status": stack_status,
            "message": f"Error getting deployment status: {str(e)}",
            "alb_url": None,
        }


async def _get_cfn_stack_status(stack_name: str) -> Dict[str, Any]:
    """
    Gets the status of a CloudFormation stack.
    
    Args:
        stack_name: Name of the CloudFormation stack
        
    Returns:
        Dictionary containing stack status information
    """
    cloudformation = await get_aws_client("cloudformation")
    
    try:
        # Use boto3 to describe the stack
        response = cloudformation.describe_stacks(StackName=stack_name)
        
        if not response.get("Stacks"):
            return {"status": "NOT_FOUND", "details": "Stack not found"}
            
        stack = response["Stacks"][0]
        
        # Get stack events for more detailed information
        events_response = cloudformation.describe_stack_events(StackName=stack_name)
        recent_events = events_response.get("StackEvents", [])[:5]  # Get 5 most recent events
        
        formatted_events = []
        for event in recent_events:
            formatted_events.append({
                "timestamp": event.get("Timestamp").isoformat() if event.get("Timestamp") else None,
                "resource_type": event.get("ResourceType"),
                "status": event.get("ResourceStatus"),
                "reason": event.get("ResourceStatusReason", "")
            })
        
        # Extract outputs
        outputs = {}
        for output in stack.get("Outputs", []):
            outputs[output["OutputKey"]] = output["OutputValue"]
        
        return {
            "status": stack.get("StackStatus"),
            "creation_time": stack.get("CreationTime").isoformat() if stack.get("CreationTime") else None,
            "last_updated_time": stack.get("LastUpdatedTime").isoformat() if stack.get("LastUpdatedTime") else None,
            "outputs": outputs,
            "recent_events": formatted_events
        }
    except Exception as e:
        logger.error(f"Error getting CloudFormation stack status: {e}")
        if "does not exist" in str(e):
            return {"status": "NOT_FOUND", "details": f"Stack {stack_name} not found"}
        return {"status": "ERROR", "details": str(e)}


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


def _generate_custom_domain_guidance(app_name: str, alb_url: str) -> Dict[str, Any]:
    """
    Generates guidance for setting up a custom domain and HTTPS for the deployed application.
    
    Args:
        app_name: Name of the application
        alb_url: The ALB URL for the deployed application
        
    Returns:
        Dictionary containing guidance for custom domain setup and HTTPS configuration
    """
    # Extract the ALB hostname from the URL
    alb_hostname = alb_url.replace("http://", "").strip("/")
    
    return {
        "custom_domain": {
            "title": "Setting up a Custom Domain",
            "description": "Your application is currently accessible via the ALB URL. For a more professional setup, you can use a custom domain.",
            "steps": [
                "Register a domain through Route 53 or another domain registrar if you don't already have one.",
                f"Create a CNAME record pointing to the ALB hostname: {alb_hostname}",
                "If using Route 53, create a hosted zone for your domain and add an alias record pointing to the ALB."
            ],
            "route53_commands": [
                f"# Create a hosted zone for your domain",
                f"aws route53 create-hosted-zone --name yourdomain.com --caller-reference {app_name}-$(date +%s)",
                f"",
                f"# Add an alias record pointing to the ALB",
                f"aws route53 change-resource-record-sets --hosted-zone-id YOUR_HOSTED_ZONE_ID --change-batch '{{\n"
                f"  \"Changes\": [{{\n"
                f"    \"Action\": \"CREATE\",\n"
                f"    \"ResourceRecordSet\": {{\n"
                f"      \"Name\": \"yourdomain.com\",\n"
                f"      \"Type\": \"A\",\n"
                f"      \"AliasTarget\": {{\n"
                f"        \"HostedZoneId\": \"YOUR_ALB_HOSTED_ZONE_ID\",\n"
                f"        \"DNSName\": \"{alb_hostname}\",\n"
                f"        \"EvaluateTargetHealth\": true\n"
                f"      }}\n"
                f"    }}\n"
                f"  }}]\n"
                f"}}'"
            ]
        },
        "https_setup": {
            "title": "Setting up HTTPS with AWS Certificate Manager",
            "description": "Secure your application with HTTPS using AWS Certificate Manager (ACM) and update your ALB listener.",
            "steps": [
                "Request a certificate through AWS Certificate Manager for your domain.",
                "Validate the certificate (typically through DNS validation).",
                "Add an HTTPS listener to your ALB that uses the certificate.",
                "Optional: Redirect HTTP traffic to HTTPS for better security."
            ],
            "acm_commands": [
                f"# Request a certificate for your domain",
                f"aws acm request-certificate --domain-name yourdomain.com --validation-method DNS",
                f"",
                f"# Get the certificate ARN",
                f"aws acm list-certificates --query \"CertificateSummaryList[?DomainName=='yourdomain.com'].CertificateArn\" --output text",
                f"",
                f"# Add an HTTPS listener to your ALB",
                f"aws elbv2 create-listener \\",
                f"  --load-balancer-arn YOUR_ALB_ARN \\",
                f"  --protocol HTTPS \\",
                f"  --port 443 \\",
                f"  --certificates CertificateArn=YOUR_CERTIFICATE_ARN \\",
                f"  --ssl-policy ELBSecurityPolicy-2016-08 \\",
                f"  --default-actions Type=forward,TargetGroupArn=YOUR_TARGET_GROUP_ARN",
                f"",
                f"# Optional: Create a redirect from HTTP to HTTPS",
                f"aws elbv2 modify-listener \\",
                f"  --listener-arn YOUR_HTTP_LISTENER_ARN \\",
                f"  --default-actions Type=redirect,RedirectConfig='{{\"Protocol\":\"HTTPS\",\"Port\":\"443\",\"StatusCode\":\"HTTP_301\"}}'"
            ]
        },
        "cloudformation_update": {
            "title": "Update Your CloudFormation Stack for HTTPS",
            "description": "You can also update your CloudFormation stack to add HTTPS support.",
            "steps": [
                "Download your current CloudFormation template.",
                "Add an HTTPS listener to the ALB configuration.",
                "Update the stack with the modified template."
            ],
            "commands": [
                f"# Download your current CloudFormation template",
                f"aws cloudformation get-template --stack-name {app_name}-ecs-infrastructure --query TemplateBody --output json > {app_name}-template.json",
                f"",
                f"# After modifying the template, update the stack",
                f"aws cloudformation update-stack --stack-name {app_name}-ecs-infrastructure --template-body file://{app_name}-template.json --capabilities CAPABILITY_IAM"
            ]
        },
        "next_steps": [
            "Set up monitoring and alerts for your application using CloudWatch.",
            "Configure auto-scaling policies based on your application's traffic patterns.",
            "Implement a CI/CD pipeline for automated deployments."
        ]
    }
