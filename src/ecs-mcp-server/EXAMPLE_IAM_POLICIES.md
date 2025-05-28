# Example IAM Policies for ECS MCP Server

This document provides detailed examples of IAM policies that can be used with the ECS MCP Server to follow the principle of least privilege. These policies are organized by use case to help you implement appropriate security controls based on your specific needs.

## Read-Only Monitoring Role

This role allows safely using the read-only operations in production environments:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:Describe*",
        "ecs:List*",
        "ecr:Describe*", 
        "ecr:List*",
        "ecr:GetAuthorizationToken",
        "cloudformation:Describe*",
        "cloudformation:List*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "logs:Describe*",
        "logs:Get*",
        "logs:List*",
        "logs:StartQuery",
        "logs:StopQuery",
        "logs:TestMetricFilter",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting Role

This role enables all diagnostic operations but restricts infrastructure changes:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:Describe*",
        "ecs:List*",
        "ecr:Describe*",
        "ecr:List*",
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "cloudformation:Describe*",
        "cloudformation:List*",
        "cloudformation:GetTemplate",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "logs:Describe*",
        "logs:Get*",
        "logs:List*",
        "logs:StartQuery",
        "logs:StopQuery",
        "logs:TestMetricFilter",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Deployment Role

This role enables full deployment capabilities but should be used with caution:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ecr:*",
        "cloudformation:*",
        "iam:PassRole",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "elasticloadbalancing:*",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DeleteLogGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

## Scoped Down Service-Specific Role

For a more secure configuration, scope permissions to specific resource patterns:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:Describe*",
        "ecs:List*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:CreateService",
        "ecs:UpdateService",
        "ecs:DeleteService",
        "ecs:RegisterTaskDefinition",
        "ecs:DeregisterTaskDefinition"
      ],
      "Resource": [
        "arn:aws:ecs:*:*:service/my-ecs-cluster/*",
        "arn:aws:ecs:*:*:task-definition/my-app-*:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*"
      ],
      "Resource": [
        "arn:aws:ecr:*:*:repository/my-app-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*"
      ],
      "Resource": [
        "arn:aws:cloudformation:*:*:stack/my-app-*/*"
      ]
    }
  ]
}
```

## Permission Boundary Example

Apply this permission boundary to limit the maximum permissions an MCP Server can use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ecr:*",
        "cloudformation:*",
        "logs:*",
        "elasticloadbalancing:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Action": [
        "iam:*User*",
        "iam:*Group*",
        "ec2:*Vpc",
        "ec2:*Subnet",
        "ec2:*InternetGateway",
        "rds:*",
        "dynamodb:*Table",
        "s3:*Bucket"
      ],
      "Resource": "*"
    }
  ]
}
```

## Implementing These Policies

To implement these IAM roles:

1. **Create a dedicated IAM role** for the ECS MCP Server
2. **Attach the appropriate policy** based on your use case
3. **Configure AWS credentials** to use this role
4. **Apply a permission boundary** for additional security
5. **Regularly audit role permissions** to ensure least privilege
