"""
API for listing ECS and related resources.
"""

import logging
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)

# Task Definition Functions
async def list_task_definitions(family_prefix: Optional[str] = None, 
                              status: str = "ACTIVE",
                              max_results: Optional[int] = None) -> Dict[str, Any]:
    """
    Lists ECS task definitions with optional filtering by family prefix and status.
    
    Args:
        family_prefix: Optional family name prefix to filter by
        status: ACTIVE or INACTIVE
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing task definitions with details
    """
    logger.info(f"Listing task definitions (family_prefix={family_prefix}, status={status})")
    ecs_client = await get_aws_client("ecs")
    
    params = {"status": status}
    if family_prefix:
        params["familyPrefix"] = family_prefix
    if max_results:
        params["maxResults"] = max_results
        
    try:
        response = ecs_client.list_task_definitions(**params)
        
        # Get details for each task definition
        task_defs = []
        for arn in response.get("taskDefinitionArns", []):
            task_def = ecs_client.describe_task_definition(taskDefinition=arn)
            task_defs.append(task_def["taskDefinition"])
        
        return {
            "task_definitions": task_defs,
            "next_token": response.get("nextToken"),
            "count": len(task_defs),
        }
    except Exception as e:
        logger.error(f"Error listing task definitions: {e}")
        raise

async def get_task_definition_details(task_definition: str) -> Dict[str, Any]:
    """
    Gets detailed information about a specific task definition.
    
    Args:
        task_definition: Name or ARN of the task definition
        
    Returns:
        Dictionary containing task definition details
    """
    logger.info(f"Getting details for task definition {task_definition}")
    ecs_client = await get_aws_client("ecs")
    
    try:
        response = ecs_client.describe_task_definition(taskDefinition=task_definition)
        
        # Find services using this task definition
        services_using = await _find_services_using_task_definition(task_definition)
        
        return {
            "task_definition": response["taskDefinition"],
            "services_using": services_using,
            "tags": response.get("tags", []),
        }
    except Exception as e:
        logger.error(f"Error getting task definition details: {e}")
        raise

# ECR Functions
async def list_ecr_repositories() -> Dict[str, Any]:
    """
    Lists all ECR repositories in the account.
    
    Returns:
        Dictionary containing ECR repositories
    """
    logger.info("Listing ECR repositories")
    ecr_client = await get_aws_client("ecr")
    
    try:
        response = ecr_client.describe_repositories()
        
        # Add image count to each repository
        for repo in response.get("repositories", []):
            image_count_response = ecr_client.describe_images(
                repositoryName=repo["repositoryName"],
                maxResults=1000,  # Use a high number to get count
            )
            repo["imageCount"] = len(image_count_response.get("imageDetails", []))
        
        return {
            "repositories": response.get("repositories", []),
            "count": len(response.get("repositories", [])),
        }
    except Exception as e:
        logger.error(f"Error listing ECR repositories: {e}")
        raise

async def list_ecr_images(repository_name: str, filter_tag: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists images in an ECR repository with optional tag filtering.
    
    Args:
        repository_name: Name of the ECR repository
        filter_tag: Optional tag to filter images
        
    Returns:
        Dictionary containing ECR images
    """
    logger.info(f"Listing ECR images for repository {repository_name}")
    ecr_client = await get_aws_client("ecr")
    
    try:
        params = {"repositoryName": repository_name}
        if filter_tag:
            params["imageIds"] = [{"imageTag": filter_tag}]
            
        response = ecr_client.describe_images(**params)
        
        # Get scan findings for each image
        for image in response.get("imageDetails", []):
            if "imageScanStatus" in image and image["imageScanStatus"].get("status") == "COMPLETE":
                try:
                    scan_response = ecr_client.describe_image_scan_findings(
                        repositoryName=repository_name,
                        imageId={"imageDigest": image["imageDigest"]},
                    )
                    image["scanFindings"] = scan_response.get("imageScanFindings", {})
                except Exception as scan_error:
                    # Some images might not have scan results available
                    logger.warning(f"Error getting scan findings: {scan_error}")
                    image["scanFindings"] = {"status": "ERROR", "message": str(scan_error)}
        
        return {
            "repository": repository_name,
            "images": response.get("imageDetails", []),
            "count": len(response.get("imageDetails", [])),
        }
    except Exception as e:
        logger.error(f"Error listing ECR images: {e}")
        raise

# Cluster Functions
async def list_ecs_clusters() -> Dict[str, Any]:
    """
    Lists all ECS clusters in the account.
    
    Returns:
        Dictionary containing ECS clusters
    """
    logger.info("Listing ECS clusters")
    
    try:
        # Use a simplified approach that just returns the cluster ARNs initially
        # without making additional API calls for details
        ecs_client = await get_aws_client("ecs")
        
        response = ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])
        
        # Just extract the cluster names from ARNs for lightweight response
        clusters = []
        for arn in cluster_arns:
            name = arn.split("/")[-1]  # Extract name from ARN
            clusters.append({
                "clusterArn": arn,
                "clusterName": name,
            })
        
        return {
            "clusters": clusters,
            "count": len(clusters),
            "message": "Note: This is a simplified view. Use get_cluster_details for complete information."
        }
    except Exception as e:
        logger.error(f"Error listing ECS clusters: {e}")
        # Return empty result instead of raising to avoid server crashes
        return {
            "clusters": [],
            "count": 0,
            "error": str(e)
        }

async def get_cluster_details(cluster_name: str) -> Dict[str, Any]:
    """
    Gets detailed information about a specific ECS cluster.
    
    Args:
        cluster_name: Name or ARN of the cluster
        
    Returns:
        Dictionary containing cluster details
    """
    logger.info(f"Getting details for cluster {cluster_name}")
    ecs_client = await get_aws_client("ecs")
    
    try:
        response = ecs_client.describe_clusters(
            clusters=[cluster_name],
            include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
        )
        
        if not response.get("clusters"):
            raise ValueError(f"Cluster {cluster_name} not found")
            
        cluster = response["clusters"][0]
        
        # Get services in this cluster
        services = await list_ecs_services(cluster_name)
        
        # Get tasks in this cluster
        tasks = await list_tasks(cluster_name)
        
        return {
            "cluster": cluster,
            "services": services.get("services", []),
            "tasks": tasks.get("tasks", []),
            "service_count": len(services.get("services", [])),
            "running_task_count": len([t for t in tasks.get("tasks", []) 
                                     if t.get("lastStatus") == "RUNNING"]),
            "failed_task_count": len([t for t in tasks.get("tasks", [])
                                    if t.get("lastStatus") == "STOPPED" and
                                      t.get("stopCode") != "TaskSucceeded"])
        }
    except Exception as e:
        logger.error(f"Error getting cluster details: {e}")
        raise

# Service Functions
async def list_ecs_services(cluster_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists ECS services, optionally filtered by cluster.
    
    Args:
        cluster_name: Optional name or ARN of the cluster to filter by
        
    Returns:
        Dictionary containing ECS services
    """
    logger.info(f"Listing ECS services (cluster={cluster_name})")
    ecs_client = await get_aws_client("ecs")
    
    try:
        services = []
        
        # If no cluster specified, get all clusters first
        clusters = []
        if cluster_name:
            clusters = [cluster_name]
        else:
            clusters_response = await list_ecs_clusters()
            clusters = [c["clusterArn"] for c in clusters_response.get("clusters", [])]
        
        for cluster in clusters:
            service_arns = []
            paginator = ecs_client.get_paginator("list_services")
            
            for page in paginator.paginate(cluster=cluster):
                service_arns.extend(page.get("serviceArns", []))
            
            if service_arns:
                # Describe services in batches of 10 (API limit)
                for i in range(0, len(service_arns), 10):
                    batch = service_arns[i:i+10]
                    service_details = ecs_client.describe_services(
                        cluster=cluster,
                        services=batch,
                        include=["TAGS"]
                    )
                    services.extend(service_details.get("services", []))
        
        return {
            "services": services,
            "count": len(services),
        }
    except Exception as e:
        logger.error(f"Error listing ECS services: {e}")
        raise

async def get_service_details(cluster_name: str, service_name: str) -> Dict[str, Any]:
    """
    Gets detailed information about a specific ECS service.
    
    Args:
        cluster_name: Name or ARN of the cluster
        service_name: Name or ARN of the service
        
    Returns:
        Dictionary containing service details
    """
    logger.info(f"Getting details for service {service_name} in cluster {cluster_name}")
    ecs_client = await get_aws_client("ecs")
    
    try:
        response = ecs_client.describe_services(
            cluster=cluster_name,
            services=[service_name],
            include=["TAGS"]
        )
        
        if not response.get("services"):
            raise ValueError(f"Service {service_name} not found in cluster {cluster_name}")
            
        service = response["services"][0]
        
        # Get tasks for this service
        tasks = await list_tasks(cluster_name, service_name)
        
        return {
            "service": service,
            "tasks": tasks.get("tasks", []),
            "running_task_count": len([t for t in tasks.get("tasks", [])
                                     if t.get("lastStatus") == "RUNNING"]),
            "failed_task_count": len([t for t in tasks.get("tasks", [])
                                    if t.get("lastStatus") == "STOPPED" and
                                      t.get("stopCode") != "TaskSucceeded"])
        }
    except Exception as e:
        logger.error(f"Error getting service details: {e}")
        raise

# Task Functions
async def list_tasks(cluster_name: Optional[str] = None, 
                    service_name: Optional[str] = None,
                    status: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists ECS tasks with optional filtering by cluster, service, and status.
    
    Args:
        cluster_name: Optional name or ARN of the cluster to filter by
        service_name: Optional name or ARN of the service to filter by
        status: Optional status to filter by (RUNNING, STOPPED)
        
    Returns:
        Dictionary containing ECS tasks
    """
    logger.info(f"Listing ECS tasks (cluster={cluster_name}, service={service_name}, status={status})")
    ecs_client = await get_aws_client("ecs")
    
    try:
        tasks = []
        
        # If no cluster specified, get all clusters first
        clusters = []
        if cluster_name:
            clusters = [cluster_name]
        else:
            clusters_response = await list_ecs_clusters()
            clusters = [c["clusterArn"] for c in clusters_response.get("clusters", [])]
        
        for cluster in clusters:
            params = {"cluster": cluster}
            if service_name:
                params["serviceName"] = service_name
            if status:
                # ECS API uses desiredStatus
                params["desiredStatus"] = status
                
            task_arns = []
            paginator = ecs_client.get_paginator("list_tasks")
            
            for page in paginator.paginate(**params):
                task_arns.extend(page.get("taskArns", []))
            
            if task_arns:
                # Describe tasks in batches of 100 (API limit)
                for i in range(0, len(task_arns), 100):
                    batch = task_arns[i:i+100]
                    task_details = ecs_client.describe_tasks(
                        cluster=cluster,
                        tasks=batch,
                        include=["TAGS"]
                    )
                    tasks.extend(task_details.get("tasks", []))
        
        return {
            "tasks": tasks,
            "count": len(tasks),
            "running_count": len([t for t in tasks if t.get("lastStatus") == "RUNNING"]),
            "stopped_count": len([t for t in tasks if t.get("lastStatus") == "STOPPED"]),
            "failed_count": len([t for t in tasks 
                               if t.get("lastStatus") == "STOPPED" and
                               t.get("stopCode") != "TaskSucceeded"])
        }
    except Exception as e:
        logger.error(f"Error listing ECS tasks: {e}")
        raise

async def list_running_tasks(cluster_name: Optional[str] = None,
                           service_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists running ECS tasks.
    
    Args:
        cluster_name: Optional name or ARN of the cluster to filter by
        service_name: Optional name or ARN of the service to filter by
        
    Returns:
        Dictionary containing running ECS tasks
    """
    return await list_tasks(cluster_name, service_name, "RUNNING")

async def list_failed_tasks(cluster_name: Optional[str] = None,
                          service_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists failed ECS tasks (stopped with non-zero exit code).
    
    Args:
        cluster_name: Optional name or ARN of the cluster to filter by
        service_name: Optional name or ARN of the service to filter by
        
    Returns:
        Dictionary containing failed ECS tasks
    """
    result = await list_tasks(cluster_name, service_name, "STOPPED")
    
    # Filter to only include tasks that failed
    failed_tasks = [t for t in result.get("tasks", []) 
                   if t.get("stopCode") != "TaskSucceeded"]
    
    return {
        "tasks": failed_tasks,
        "count": len(failed_tasks),
    }

# CloudFormation Functions
async def list_cloudformation_stacks_for_ecs() -> Dict[str, Any]:
    """
    Lists CloudFormation stacks related to ECS.
    
    Returns:
        Dictionary containing CloudFormation stacks
    """
    logger.info("Listing CloudFormation stacks for ECS")
    cloudformation = await get_aws_client("cloudformation")
    
    try:
        # Get all stacks
        stacks = []
        paginator = cloudformation.get_paginator("list_stacks")
        
        for page in paginator.paginate(
            StackStatusFilter=[
                "CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"
            ]
        ):
            stacks.extend(page.get("StackSummaries", []))
        
        # Filter to only include stacks with ECS resources
        ecs_stacks = []
        for stack in stacks:
            stack_name = stack["StackName"]
            
            try:
                # Check if stack has ECS resources
                resources = cloudformation.list_stack_resources(StackName=stack_name)
                
                has_ecs = any(
                    r["ResourceType"].startswith("AWS::ECS::")
                    for r in resources.get("StackResourceSummaries", [])
                )
                
                if has_ecs:
                    stack_details = cloudformation.describe_stacks(StackName=stack_name)
                    if stack_details.get("Stacks"):
                        ecs_stacks.append(stack_details["Stacks"][0])
            except Exception as stack_error:
                logger.warning(f"Error checking stack {stack_name}: {stack_error}")
                continue
        
        return {
            "stacks": ecs_stacks,
            "count": len(ecs_stacks),
        }
    except Exception as e:
        logger.error(f"Error listing CloudFormation stacks: {e}")
        raise

async def get_cloudformation_stack_details(stack_name: str) -> Dict[str, Any]:
    """
    Gets detailed information about a specific CloudFormation stack.
    
    Args:
        stack_name: Name or ARN of the stack
        
    Returns:
        Dictionary containing stack details
    """
    logger.info(f"Getting details for CloudFormation stack {stack_name}")
    cloudformation = await get_aws_client("cloudformation")
    
    try:
        stack_response = cloudformation.describe_stacks(StackName=stack_name)
        
        if not stack_response.get("Stacks"):
            raise ValueError(f"Stack {stack_name} not found")
            
        stack = stack_response["Stacks"][0]
        
        # Get resources in this stack
        resources = cloudformation.list_stack_resources(StackName=stack_name)
        
        # Filter to only include ECS resources
        ecs_resources = [
            r for r in resources.get("StackResourceSummaries", [])
            if r["ResourceType"].startswith("AWS::ECS::")
        ]
        
        return {
            "stack": stack,
            "ecs_resources": ecs_resources,
            "ecs_resource_count": len(ecs_resources),
            "outputs": stack.get("Outputs", []),
            "parameters": stack.get("Parameters", []),
        }
    except Exception as e:
        logger.error(f"Error getting CloudFormation stack details: {e}")
        raise

# Consolidated Resource Functions

async def get_ecs_resources(resource_type: Optional[str] = None,
                           cluster_name: Optional[str] = None,
                           service_name: Optional[str] = None,
                           resource_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Consolidated function to get ECS resources of various types.
    
    Args:
        resource_type: Type of resource (clusters, services, tasks, running_tasks, failed_tasks)
                      If None, returns all resource types
        cluster_name: Optional name or ARN of cluster to filter by
        service_name: Optional name or ARN of service to filter by
        resource_id: Optional resource ID/name/ARN to get details for
        
    Returns:
        Dictionary containing the requested resources
    """
    logger.info(f"Getting ECS resources of type {resource_type} (cluster={cluster_name}, service={service_name}, resource_id={resource_id})")
    
    try:
        # If no resource_type provided, return all resources
        if not resource_type:
            clusters = await list_ecs_clusters()
            services = await list_ecs_services(cluster_name)
            tasks = await list_tasks(cluster_name, service_name)
            running_tasks = await list_running_tasks(cluster_name, service_name)
            failed_tasks = await list_failed_tasks(cluster_name, service_name)
            
            return {
                "clusters": clusters.get("clusters", []),
                "services": services.get("services", []),
                "tasks": tasks.get("tasks", []),
                "running_tasks": [t for t in tasks.get("tasks", []) if t.get("lastStatus") == "RUNNING"],
                "failed_tasks": [t for t in tasks.get("tasks", []) 
                                if t.get("lastStatus") == "STOPPED" and t.get("stopCode") != "TaskSucceeded"],
                "cluster_count": len(clusters.get("clusters", [])),
                "service_count": len(services.get("services", [])),
                "task_count": len(tasks.get("tasks", [])),
                "running_task_count": len([t for t in tasks.get("tasks", []) if t.get("lastStatus") == "RUNNING"]),
                "failed_task_count": len([t for t in tasks.get("tasks", [])
                                      if t.get("lastStatus") == "STOPPED" and t.get("stopCode") != "TaskSucceeded"])
            }
        
        # Handle different resource types
        elif resource_type == "clusters":
            if resource_id:
                return await get_cluster_details(resource_id)
            else:
                return await list_ecs_clusters()
                
        elif resource_type == "services":
            if resource_id and cluster_name:
                return await get_service_details(cluster_name, resource_id)
            else:
                return await list_ecs_services(cluster_name)
                
        elif resource_type == "tasks":
            return await list_tasks(cluster_name, service_name)
            
        elif resource_type == "running_tasks":
            return await list_running_tasks(cluster_name, service_name)
            
        elif resource_type == "failed_tasks":
            return await list_failed_tasks(cluster_name, service_name)
            
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
            
    except Exception as e:
        logger.error(f"Error getting ECS resources: {e}")
        return {
            "error": str(e),
            "resource_type": resource_type
        }

async def get_ecr_resources(resource_type: Optional[str] = None,
                           repository_name: Optional[str] = None,
                           filter_tag: Optional[str] = None) -> Dict[str, Any]:
    """
    Consolidated function to get ECR resources of various types.
    
    Args:
        resource_type: Type of resource (repositories, images)
                      If None, returns all resource types
        repository_name: Name of repository (required for images)
        filter_tag: Optional tag to filter images by
        
    Returns:
        Dictionary containing the requested resources
    """
    logger.info(f"Getting ECR resources of type {resource_type} (repository={repository_name}, filter_tag={filter_tag})")
    
    try:
        # If no resource_type provided, return all resources
        if not resource_type:
            repositories = await list_ecr_repositories()
            
            # If repository name is provided, include images from that repository
            images_data = {}
            if repository_name:
                try:
                    images_data = await list_ecr_images(repository_name, filter_tag)
                except Exception as img_error:
                    logger.warning(f"Error getting images for repository {repository_name}: {img_error}")
                    images_data = {"images": [], "count": 0, "error": str(img_error)}
            
            return {
                "repositories": repositories.get("repositories", []),
                "repository_count": len(repositories.get("repositories", [])),
                "images": images_data.get("images", []) if repository_name else [],
                "image_count": images_data.get("count", 0) if repository_name else 0,
                "repository_name": repository_name
            }
            
        elif resource_type == "repositories":
            return await list_ecr_repositories()
            
        elif resource_type == "images":
            if not repository_name:
                raise ValueError("repository_name is required for resource_type='images'")
            return await list_ecr_images(repository_name, filter_tag)
            
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
            
    except Exception as e:
        logger.error(f"Error getting ECR resources: {e}")
        return {
            "error": str(e),
            "resource_type": resource_type
        }

async def get_task_definitions(task_definition_id: Optional[str] = None,
                              family_prefix: Optional[str] = None,
                              status: str = "ACTIVE",
                              max_results: Optional[int] = None) -> Dict[str, Any]:
    """
    Consolidated function to get task definitions.
    
    Args:
        task_definition_id: Specific task definition ID/ARN to get details for
        family_prefix: Family prefix to filter task definitions by
        status: Status of task definitions to list (ACTIVE or INACTIVE)
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary containing task definitions
    """
    logger.info(f"Getting task definitions (id={task_definition_id}, family_prefix={family_prefix}, status={status})")
    
    try:
        if task_definition_id:
            return await get_task_definition_details(task_definition_id)
        else:
            return await list_task_definitions(family_prefix, status, max_results)
            
    except Exception as e:
        logger.error(f"Error getting task definitions: {e}")
        return {
            "error": str(e),
            "task_definition_id": task_definition_id
        }

async def get_ecs_cfn_resources(stack_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Consolidated function to get CloudFormation resources related to ECS.
    
    Args:
        stack_name: Optional stack name to get details for
        
    Returns:
        Dictionary containing CloudFormation resources
    """
    logger.info(f"Getting ECS CloudFormation resources (stack_name={stack_name})")
    
    try:
        if stack_name:
            return await get_cloudformation_stack_details(stack_name)
        else:
            return await list_cloudformation_stacks_for_ecs()
            
    except Exception as e:
        logger.error(f"Error getting CloudFormation resources: {e}")
        return {
            "error": str(e),
            "stack_name": stack_name
        }

# Helper Functions
async def _find_services_using_task_definition(task_definition: str) -> List[Dict[str, Any]]:
    """
    Finds services using a specific task definition.
    
    Args:
        task_definition: ARN or family:revision of the task definition
        
    Returns:
        List of services using the task definition
    """
    services = []
    
    # Get task definition ARN if family:revision format was provided
    if ":" in task_definition and "/" not in task_definition:
        ecs_client = await get_aws_client("ecs")
        try:
            td_response = ecs_client.describe_task_definition(taskDefinition=task_definition)
            task_definition_arn = td_response["taskDefinition"]["taskDefinitionArn"]
        except Exception:
            # If describe_task_definition fails, use the provided value
            task_definition_arn = task_definition
    else:
        task_definition_arn = task_definition
    
    # Check all services in all clusters
    clusters_result = await list_ecs_clusters()
    
    for cluster in clusters_result.get("clusters", []):
        cluster_name = cluster["clusterArn"]
        
        services_result = await list_ecs_services(cluster_name)
        
        for service in services_result.get("services", []):
            if service.get("taskDefinition") == task_definition_arn:
                services.append({
                    "cluster": cluster_name,
                    "service": service["serviceName"],
                    "service_arn": service["serviceArn"],
                })
    
    return services
