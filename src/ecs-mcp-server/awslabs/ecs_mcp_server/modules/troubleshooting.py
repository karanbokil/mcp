"""
Troubleshooting module for ECS MCP Server.
This module provides tools and prompts for troubleshooting ECS deployments.
"""
import datetime
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.troubleshooting_tools import (
    get_ecs_troubleshooting_guidance,
    fetch_cloudformation_status,
    fetch_service_events,
    fetch_task_failures,
    fetch_task_logs,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures import (
    detect_image_pull_failures,
)


def register_module(mcp: FastMCP) -> None:
    """Register troubleshooting module tools and prompts with the MCP server."""
    
    @mcp.tool(name="get_ecs_troubleshooting_guidance")
    async def mcp_get_ecs_troubleshooting_guidance(
        app_name: str = Field(
            ...,
            description="The name of the application/stack to troubleshoot",
        ),
        symptoms_description: Optional[str] = Field(
            default=None,
            description="Description of symptoms experienced by the user",
        ),
    ) -> Dict[str, Any]:
        """
        Initial entry point that analyzes symptoms and recommends specific diagnostic paths.

        This tool serves as the starting point for troubleshooting ECS deployments by analyzing
        symptoms and recommending specific diagnostic tools to use next. It examines the state
        of your deployment and creates a guided troubleshooting plan.
        
        IMPORTANT USAGE GUIDELINES:
        When this tool identifies a clear root cause such as:
        - Invalid container image references
        - Specific CloudFormation error messages 
        - Missing required configuration parameters
        
        DO NOT use additional diagnostic tools unless they would provide new, relevant 
        information not already discovered. Avoid redundant checks when a definitive cause is found.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. Optionally describe the symptoms you're experiencing
        3. The tool will recommend a diagnostic path based on detected issues

        The guidance includes:
        - Initial assessment of the deployment state
        - Categorized symptoms detection (infrastructure, service, task, application, network)
        - Recommended diagnostic tools to use next with reasoning
        - Raw data about the current deployment state for further analysis

        Parameters:
            app_name: The name of the application/stack to troubleshoot
            symptoms_description: Optional description of symptoms experienced by the user

        Returns:
            Diagnostic path recommendation, initial assessment, and detected symptoms
        """
        return get_ecs_troubleshooting_guidance(app_name, symptoms_description)


    @mcp.tool(name="fetch_cloudformation_status")
    async def mcp_fetch_cloudformation_status(
        stack_id: str = Field(
            ...,
            description="The CloudFormation stack identifier to analyze",
        ),
    ) -> Dict[str, Any]:
        """
        Infrastructure-level diagnostics for CloudFormation stacks.

        This tool analyzes the CloudFormation stack used to deploy your ECS infrastructure.
        It checks the stack status, identifies failed resources, and extracts error messages
        to help diagnose infrastructure-level issues.
        
        IMPORTANT USAGE GUIDELINES:
        When this tool reveals specific error messages that explain the deployment failure
        (such as "Network Configuration must be provided when networkMode 'awsvpc' is specified"),
        consider this a definitive root cause. Do not use additional tools to verify what is 
        already clearly indicated by CloudFormation errors.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. The tool will analyze the CloudFormation stack and return detailed information

        The analysis includes:
        - Stack existence confirmation
        - Current stack status (e.g., CREATE_COMPLETE, ROLLBACK_COMPLETE)
        - List of resources with their status
        - Failed resources with detailed failure reasons
        - Historical stack events for deeper analysis

        Parameters:
            stack_id: The CloudFormation stack identifier to analyze

        Returns:
            Stack status, resources, failure reasons, and raw events
        """
        return fetch_cloudformation_status(stack_id)


    @mcp.tool(name="fetch_service_events")
    async def mcp_fetch_service_events(
        app_name: str = Field(
            ...,
            description="The name of the application to analyze",
        ),
        cluster_name: str = Field(
            ...,
            description="The name of the ECS cluster",
        ),
        service_name: str = Field(
            ...,
            description="The name of the ECS service to analyze",
        ),
        time_window: int = Field(
            default=3600,
            description="Time window in seconds to look back for events (default: 3600)",
        ),
        start_time: Optional[datetime.datetime] = Field(
            default=None,
            description="Explicit start time for the analysis window (UTC, takes precedence over time_window if provided)",
        ),
        end_time: Optional[datetime.datetime] = Field(
            default=None,
            description="Explicit end time for the analysis window (UTC, defaults to current time if not provided)",
        ),
    ) -> Dict[str, Any]:
        """
        Service-level diagnostics for ECS services.

        This tool analyzes ECS service events and configuration to identify service-level
        issues that may be affecting your deployment. It examines recent service events,
        deployment status, and load balancer configuration.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. Specify the cluster name
        3. Specify the service name
        4. Optionally specify the time window to analyze (default is last hour)
        5. The tool will analyze service events and configuration

        The analysis includes:
        - Service status summary
        - Chronological list of service events
        - Deployment status and history
        - Load balancer configuration issues
        - Detailed service configuration

        Parameters:
            app_name: The name of the application/service to analyze
            cluster_name: The name of the ECS cluster (optional)
            time_window: Time window in seconds to look back for events

        Returns:
            Service status, events, deployment status, and configuration issues
        """
        return fetch_service_events(app_name, cluster_name, service_name, time_window, start_time, end_time)


    @mcp.tool(name="fetch_task_failures")
    async def mcp_fetch_task_failures(
        app_name: str = Field(
            ...,
            description="The name of the application to analyze",
        ),
        cluster_name: str = Field(
            ...,
            description="The name of the ECS cluster",
        ),
        time_window: int = Field(
            default=3600,
            description="Time window in seconds to look back for failures (default: 3600)",
        ),
        start_time: Optional[datetime.datetime] = Field(
            default=None,
            description="Explicit start time for the analysis window (UTC, takes precedence over time_window if provided)",
        ),
        end_time: Optional[datetime.datetime] = Field(
            default=None,
            description="Explicit end time for the analysis window (UTC, defaults to current time if not provided)",
        ),
    ) -> Dict[str, Any]:
        """
        Task-level diagnostics for ECS task failures.

        This tool analyzes failed ECS tasks to identify patterns and common failure reasons.
        It categorizes failures by type and extracts relevant information to help diagnose
        container-level issues.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. Specify the cluster name
        3. Optionally specify the time window to analyze (default is last hour)
        4. The tool will analyze failed tasks and identify patterns

        The analysis includes:
        - List of failed tasks with timestamps
        - Exit codes and failure reasons
        - Container status information
        - Resource utilization at failure time
        - Categorized failures (image pull, resource constraints, application errors)

        Parameters:
            app_name: The name of the application to analyze
            cluster_name: The name of the ECS cluster (optional)
            time_window: Time window in seconds to look back for failures

        Returns:
            Failed tasks with timestamps, exit codes, status, and resource utilization
        """
        return fetch_task_failures(app_name, cluster_name, time_window, start_time, end_time)


    @mcp.tool(name="fetch_task_logs")
    async def mcp_fetch_task_logs(
        app_name: str = Field(
            ...,
            description="The name of the application to analyze",
        ),
        cluster_name: str = Field(
            ...,
            description="The name of the ECS cluster",
        ),
        task_id: Optional[str] = Field(
            default=None,
            description="Specific task ID to retrieve logs for",
        ),
        time_window: int = Field(
            default=3600,
            description="Time window in seconds to look back for logs (default: 3600)",
        ),
        filter_pattern: Optional[str] = Field(
            default=None,
            description="CloudWatch logs filter pattern",
        ),
        start_time: Optional[datetime.datetime] = Field(
            default=None,
            description="Explicit start time for the analysis window (UTC, takes precedence over time_window if provided)",
        ),
        end_time: Optional[datetime.datetime] = Field(
            default=None,
            description="Explicit end time for the analysis window (UTC, defaults to current time if not provided)",
        ),
    ) -> Dict[str, Any]:
        """
        Application-level diagnostics through CloudWatch logs.

        This tool retrieves and analyzes CloudWatch logs for your ECS tasks to identify
        application-level issues. It categorizes log entries by severity, highlights errors,
        and identifies common error patterns.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. Specify the cluster name
        3. Optionally provide a specific task ID to focus on a single task
        4. Optionally specify the time window and filter pattern
        5. The tool will retrieve and analyze logs

        The analysis includes:
        - Chronological log entries with severity markers
        - Highlighted error messages
        - Context around errors (preceding and following logs)
        - Log pattern summary (recurring errors)
        - Error and warning counts

        Parameters:
            app_name: The name of the application to analyze
            cluster_name: The name of the ECS cluster (optional)
            task_id: Specific task ID to retrieve logs for (optional)
            time_window: Time window in seconds to look back for logs
            filter_pattern: CloudWatch logs filter pattern (optional)

        Returns:
            Log entries with severity markers, highlighted errors, context
        """
        return fetch_task_logs(app_name, cluster_name, task_id, time_window, filter_pattern, start_time, end_time)
        
    @mcp.tool(name="detect_image_pull_failures")
    async def mcp_detect_image_pull_failures(
        app_name: str = Field(
            ...,
            description="Application name to check for image pull failures",
        ),
    ) -> Dict[str, Any]:
        """
        Specialized tool for detecting container image pull failures.

        This tool finds all task definitions related to the application and checks
        if their container images exist and are accessible. It is particularly useful
        for diagnosing "ImagePullBackOff" type issues in ECS.
        
        IMPORTANT USAGE GUIDELINES:
        This tool provides definitive information about container image issues. 
        When it confirms an invalid image reference, DO NOT use additional tools
        to verify what's already known. Proceed directly to recommending solutions
        based on the findings from this tool.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. The tool will check for image pull failures and provide recommendations

        The analysis includes:
        - Finding related task definitions by name pattern
        - Checking ECR repositories for image existence
        - Validating image references
        - Providing specific recommendations to fix image issues

        Parameters:
            app_name: The name of the application to check

        Returns:
            Dictionary with image issues analysis and recommendations
        """
        return detect_image_pull_failures(app_name)

    # Troubleshooting prompt patterns
    @mcp.prompt("troubleshoot ecs")
    def troubleshoot_ecs_prompt():
        """
        User wants to troubleshoot ECS deployment.
        Start with get_ecs_troubleshooting_guidance and only use additional
        tools if the root cause isn't clearly identified in the initial assessment.
        """
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("ecs deployment failed")
    def ecs_deployment_failed_prompt():
        """
        User has an ECS deployment failure.
        Begin with get_ecs_troubleshooting_guidance and avoid redundant tool usage
        if a definitive root cause (like image issues or CloudFormation errors) is found.
        """
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("diagnose ecs")
    def diagnose_ecs_prompt():
        """
        User wants to diagnose ECS issues.
        Use get_ecs_troubleshooting_guidance to identify potential issues and
        only proceed with additional tools if the root cause isn't clear.
        """
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("ecs tasks failing")
    def ecs_tasks_failing_prompt():
        """User has failing ECS tasks"""
        return ["fetch_task_failures"]

    @mcp.prompt("check ecs logs")
    def check_ecs_logs_prompt():
        """User wants to check ECS logs"""
        return ["fetch_task_logs"]

    @mcp.prompt("cloudformation stack failed")
    def cloudformation_stack_failed_prompt():
        """User has a failed CloudFormation stack"""
        return ["fetch_cloudformation_status"]

    @mcp.prompt("ecs service events")
    def ecs_service_events_prompt():
        """User wants to see ECS service events"""
        return ["fetch_service_events"]

    @mcp.prompt("fix ecs deployment")
    def fix_ecs_deployment_prompt():
        """User wants to fix an ECS deployment"""
        return ["get_ecs_troubleshooting_guidance"]

    # Specific Stack Name Troubleshooting Patterns
    @mcp.prompt("stack .* is broken")
    def stack_is_broken_prompt():
        """User has a broken CloudFormation stack with a specific name"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt("fix .* stack")
    def fix_named_stack_prompt():
        """User wants to fix a specific stack"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt("failed stack .*")
    def failed_stack_named_prompt():
        """User has a failed stack with a specific name"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt("stack .* failed")
    def stack_named_failed_prompt():
        """User has a failed stack with a specific name"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt(".*-stack.* is broken")
    def test_stack_is_broken_prompt():
        """User has a broken test stack with random suffix"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt(".*-stack.* failed")
    def test_stack_failed_prompt():
        """User has a failed test stack with random suffix"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt("help me fix .*-stack.*")
    def help_fix_test_stack_prompt():
        """User wants help fixing a test stack with random suffix"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt("why did my stack fail")
    def why_did_stack_fail_prompt():
        """User wants to know why their stack failed"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    # Generic troubleshooting patterns
    @mcp.prompt("fix my deployment")
    def fix_deployment_prompt():
        """User wants to fix their deployment"""
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("deployment issues")
    def deployment_issues_prompt():
        """User has deployment issues"""
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("what's wrong with my stack")
    def whats_wrong_with_stack_prompt():
        """User wants to know what's wrong with their stack"""
        return ["fetch_cloudformation_status", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt("deployment is broken")
    def deployment_broken_prompt():
        """User's deployment is broken"""
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("app won't deploy")
    def app_wont_deploy_prompt():
        """User's app won't deploy"""
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("help debug ecs")
    def help_debug_ecs_prompt():
        """User wants help debugging ECS"""
        return ["get_ecs_troubleshooting_guidance"]

    @mcp.prompt("service is failing")
    def service_failing_prompt():
        """User's service is failing"""
        return ["fetch_service_events", "get_ecs_troubleshooting_guidance"]

    @mcp.prompt("container is failing")
    def container_failing_prompt():
        """User's container is failing"""
        return ["fetch_task_failures", "fetch_task_logs", "get_ecs_troubleshooting_guidance"]
    
    # New prompts for image pull failures
    @mcp.prompt("image pull failure")
    def image_pull_failure_prompt():
        """
        User has an image pull failure.
        Use detect_image_pull_failures for definitive diagnosis. The results from
        this tool are typically conclusive for image issues, so avoid redundant tool usage.
        """
        return ["detect_image_pull_failures"]

    @mcp.prompt("container image not found")
    def container_image_not_found_prompt():
        """
        User has a container image not found error.
        detect_image_pull_failures will provide a definitive diagnosis and specific
        recommendations. No need for additional tools once the image issue is confirmed.
        """
        return ["detect_image_pull_failures"]

    @mcp.prompt("imagepullbackoff")
    def imagepullbackoff_prompt():
        """
        User has an ImagePullBackOff error.
        detect_image_pull_failures is sufficient to diagnose this issue.
        Additional tools are only needed if image validation is inconclusive.
        """
        return ["detect_image_pull_failures"]
        
    @mcp.prompt("can't pull image")
    def cant_pull_image_prompt():
        """
        User reports that the container can't pull an image.
        Start with detect_image_pull_failures for direct image validation,
        then only use get_ecs_troubleshooting_guidance if additional context is needed.
        Avoid unnecessary tool usage if the image pull failure cause is clear.
        """
        return ["detect_image_pull_failures", "get_ecs_troubleshooting_guidance"]
        
    @mcp.prompt("invalid container image")
    def invalid_container_image_prompt():
        """
        User has an invalid container image reference.
        detect_image_pull_failures provides a conclusive diagnosis and specific
        recommendations for this issue. Additional tool usage is typically unnecessary.
        """
        return ["detect_image_pull_failures"]
