"""
AWS utility functions.
"""

import logging
import os
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)


async def get_aws_client(service_name: str):
    """Gets an AWS service client."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client(service_name, region_name=region)


async def get_aws_account_id() -> str:
    """Gets the AWS account ID."""
    sts = await get_aws_client("sts")
    return sts.get_caller_identity()["Account"]


async def get_default_vpc_and_subnets() -> Dict[str, Any]:
    """Gets the default VPC and subnets."""
    ec2 = await get_aws_client("ec2")

    # Get default VPC
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])

    if not vpcs["Vpcs"]:
        raise ValueError("No default VPC found. Please specify a VPC ID.")

    vpc_id = vpcs["Vpcs"][0]["VpcId"]

    # Get public subnets in the default VPC
    subnets = ec2.describe_subnets(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "map-public-ip-on-launch", "Values": ["true"]},
        ]
    )

    if not subnets["Subnets"]:
        # Fallback to all subnets in the VPC
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])

    subnet_ids = [subnet["SubnetId"] for subnet in subnets["Subnets"]]

    return {"vpc_id": vpc_id, "subnet_ids": subnet_ids}


async def create_ecr_repository(repository_name: str) -> Dict[str, Any]:
    """Creates an ECR repository if it doesn't exist."""
    ecr = await get_aws_client("ecr")

    try:
        # Check if repository exists
        response = ecr.describe_repositories(repositoryNames=[repository_name])
        return response["repositories"][0]
    except ecr.exceptions.RepositoryNotFoundException:
        # Create repository if it doesn't exist
        response = ecr.create_repository(
            repositoryName=repository_name,
            imageScanningConfiguration={"scanOnPush": True},
            encryptionConfiguration={"encryptionType": "AES256"},
        )
        return response["repository"]


async def get_ecr_login_password() -> str:
    """Gets ECR login password for Docker authentication."""
    ecr = await get_aws_client("ecr")
    response = ecr.get_authorization_token()

    if not response["authorizationData"]:
        raise ValueError("Failed to get ECR authorization token")

    auth_data = response["authorizationData"][0]
    token = auth_data["authorizationToken"]

    # Token is base64 encoded username:password
    import base64

    decoded = base64.b64decode(token).decode("utf-8")
    username, password = decoded.split(":")

    return password
