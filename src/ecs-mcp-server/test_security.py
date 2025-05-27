#!/usr/bin/env python3
"""
Test script for security validation.
"""

from awslabs.ecs_mcp_server.utils.config import get_config
from awslabs.ecs_mcp_server.utils.security import validate_security_permissions

# Get configuration
config = get_config()
print(f'allow-write: {config.get("allow-write")}')
print(f'allow-sensitive-data: {config.get("allow-sensitive-data")}')

# Test write operations
try:
    validate_security_permissions(config, 'create_ecs_infrastructure')
    print('Security validation for create_ecs_infrastructure: PASSED')
except Exception as e:
    print(f'Security validation for create_ecs_infrastructure: FAILED - {e}')

try:
    validate_security_permissions(config, 'delete_ecs_infrastructure')
    print('Security validation for delete_ecs_infrastructure: PASSED')
except Exception as e:
    print(f'Security validation for delete_ecs_infrastructure: FAILED - {e}')

# Test sensitive data operations
try:
    validate_security_permissions(config, 'fetch_task_logs')
    print('Security validation for fetch_task_logs: PASSED')
except Exception as e:
    print(f'Security validation for fetch_task_logs: FAILED - {e}')

try:
    validate_security_permissions(config, 'fetch_service_events')
    print('Security validation for fetch_service_events: PASSED')
except Exception as e:
    print(f'Security validation for fetch_service_events: FAILED - {e}')

# Test non-restricted operations
try:
    validate_security_permissions(config, 'containerize_app')
    print('Security validation for containerize_app: PASSED')
except Exception as e:
    print(f'Security validation for containerize_app: FAILED - {e}')
