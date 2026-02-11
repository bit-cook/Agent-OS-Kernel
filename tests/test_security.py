"""测试安全策略"""

import pytest


class TestSecurityPolicyExists:
    """测试安全策略存在"""
    
    def test_import(self):
        from agent_os_kernel.core.security import SecurityPolicy
        assert SecurityPolicy is not None
    
    def test_permission_import(self):
        from agent_os_kernel.core.security import PermissionLevel
        assert PermissionLevel is not None
