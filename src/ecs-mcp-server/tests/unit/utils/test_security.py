"""
Unit tests for the security module.
"""

import unittest
from unittest.mock import patch

from awslabs.ecs_mcp_server.utils.security import (
    SecurityError,
    check_write_permission,
    enforce_sensitive_data_access,
    validate_security_permissions,
)


class TestSecurity(unittest.TestCase):
    """Test cases for the security module."""

    def test_check_write_permission_allowed(self):
        """Test that write operations are allowed when the flag is enabled."""
        config = {"allow-write": True}
        
        # Test with write tools
        self.assertTrue(check_write_permission(config, "create_ecs_infrastructure"))
        self.assertTrue(check_write_permission(config, "delete_ecs_infrastructure"))
        
        # Test with non-write tools
        self.assertTrue(check_write_permission(config, "containerize_app"))
        self.assertTrue(check_write_permission(config, "get_deployment_status"))

    def test_check_write_permission_denied(self):
        """Test that write operations are denied when the flag is disabled."""
        config = {"allow-write": False}
        
        # Test with non-write tools (should be allowed)
        self.assertTrue(check_write_permission(config, "containerize_app"))
        self.assertTrue(check_write_permission(config, "get_deployment_status"))
        
        # Test with write tools (should raise SecurityError)
        with self.assertRaises(SecurityError):
            check_write_permission(config, "create_ecs_infrastructure")
            
        with self.assertRaises(SecurityError):
            check_write_permission(config, "delete_ecs_infrastructure")

    def test_enforce_sensitive_data_access_allowed(self):
        """Test that sensitive data access is allowed when the flag is enabled."""
        config = {"allow-sensitive-data": True}
        
        # Test with sensitive data tools
        self.assertTrue(enforce_sensitive_data_access(config, "fetch_task_logs"))
        self.assertTrue(enforce_sensitive_data_access(config, "fetch_service_events"))
        self.assertTrue(enforce_sensitive_data_access(config, "fetch_task_failures"))
        
        # Test with non-sensitive data tools
        self.assertTrue(enforce_sensitive_data_access(config, "containerize_app"))
        self.assertTrue(enforce_sensitive_data_access(config, "get_deployment_status"))

    def test_enforce_sensitive_data_access_denied(self):
        """Test that sensitive data access is denied when the flag is disabled."""
        config = {"allow-sensitive-data": False}
        
        # Test with non-sensitive data tools (should be allowed)
        self.assertTrue(enforce_sensitive_data_access(config, "containerize_app"))
        self.assertTrue(enforce_sensitive_data_access(config, "get_deployment_status"))
        
        # Test with sensitive data tools (should raise SecurityError)
        with self.assertRaises(SecurityError):
            enforce_sensitive_data_access(config, "fetch_task_logs")
            
        with self.assertRaises(SecurityError):
            enforce_sensitive_data_access(config, "fetch_service_events")
            
        with self.assertRaises(SecurityError):
            enforce_sensitive_data_access(config, "fetch_task_failures")

    def test_validate_security_permissions(self):
        """Test the combined validation of security permissions."""
        # Both flags enabled
        config = {"allow-write": True, "allow-sensitive-data": True}
        self.assertTrue(validate_security_permissions(config, "create_ecs_infrastructure"))
        self.assertTrue(validate_security_permissions(config, "fetch_task_logs"))
        
        # Write enabled, sensitive data disabled
        config = {"allow-write": True, "allow-sensitive-data": False}
        self.assertTrue(validate_security_permissions(config, "create_ecs_infrastructure"))
        with self.assertRaises(SecurityError):
            validate_security_permissions(config, "fetch_task_logs")
        
        # Write disabled, sensitive data enabled
        config = {"allow-write": False, "allow-sensitive-data": True}
        with self.assertRaises(SecurityError):
            validate_security_permissions(config, "create_ecs_infrastructure")
        self.assertTrue(validate_security_permissions(config, "fetch_task_logs"))
        
        # Both flags disabled
        config = {"allow-write": False, "allow-sensitive-data": False}
        with self.assertRaises(SecurityError):
            validate_security_permissions(config, "create_ecs_infrastructure")
        with self.assertRaises(SecurityError):
            validate_security_permissions(config, "fetch_task_logs")
        
        # Non-restricted tools should always be allowed
        self.assertTrue(validate_security_permissions(config, "containerize_app"))
        self.assertTrue(validate_security_permissions(config, "get_deployment_status"))


if __name__ == "__main__":
    unittest.main()
