"""测试安全子系统"""

import pytest
from agent_os_kernel.core.security import SecurityPolicy, PermissionLevel


class TestSecurityPolicy:
    """测试安全策略"""
    
    def test_default_policy(self):
        """测试默认策略"""
        policy = SecurityPolicy()
        
        assert policy.sandbox_enabled is True
        assert policy.rate_limit_enabled is True
        assert policy.audit_enabled is True
    
    def test_permission_level_enum(self):
        """测试权限级别枚举"""
        assert PermissionLevel.NONE.value == 0
        assert PermissionLevel.READ.value == 1
        assert PermissionLevel.WRITE.value == 2
        assert PermissionLevel.EXECUTE.value == 3
        assert PermissionLevel.ADMIN.value == 4
    
    def test_check_permission(self):
        """测试权限检查"""
        policy = SecurityPolicy()
        
        # 允许的操作
        assert policy.check_permission("read_file", PermissionLevel.READ) is True
        
        # 拒绝的操作（权限不足）
        assert policy.check_permission("read_file", PermissionLevel.EXECUTE) is False
    
    def test_rate_limit(self):
        """测试速率限制"""
        policy = SecurityPolicy(rate_limit_requests=10)
        
        # 前 10 次应该允许
        for i in range(10):
            assert policy.check_rate_limit() is True
        
        # 第 11 次应该拒绝
        assert policy.check_rate_limit() is False
    
    def test_sandbox_enabled(self):
        """测试沙箱启用"""
        policy = SecurityPolicy(sandbox_enabled=True)
        assert policy.is_sandbox_enabled() is True
        
        policy = SecurityPolicy(sandbox_enabled=False)
        assert policy.is_sandbox_enabled() is False
    
    def test_dangerous_patterns(self):
        """测试危险模式检测"""
        policy = SecurityPolicy()
        
        # 危险命令应该被拒绝
        dangerous = [
            "rm -rf /",
            "sudo rm -rf /",
            "__import__('os').system('ls')",
            "eval('2+2')"
        ]
        
        for cmd in dangerous:
            assert policy.contains_dangerous_pattern(cmd) is True
        
        # 安全命令应该通过
        safe = [
            "2 + 2",
            "print('hello')",
            "sqrt(16)"
        ]
        
        for cmd in safe:
            assert policy.contains_dangerous_pattern(cmd) is False


class TestPermissionLevel:
    """测试权限级别"""
    
    def test_permission_hierarchy(self):
        """测试权限层级"""
        assert PermissionLevel.ADMIN > PermissionLevel.EXECUTE
        assert PermissionLevel.EXECUTE > PermissionLevel.WRITE
        assert PermissionLevel.WRITE > PermissionLevel.READ
        assert PermissionLevel.READ > PermissionLevel.NONE
    
    def test_permission_checking(self):
        """测试权限检查"""
        # NONE 权限不能做任何事
        assert not PermissionLevel.NONE.can_read()
        assert not PermissionLevel.NONE.can_write()
        assert not PermissionLevel.NONE.can_execute()
        
        # READ 权限只能读
        assert PermissionLevel.READ.can_read()
        assert not PermissionLevel.READ.can_write()
        assert not PermissionLevel.READ.can_execute()
        
        # WRITE 权限可以读写
        assert PermissionLevel.WRITE.can_read()
        assert PermissionLevel.WRITE.can_write()
        assert not PermissionLevel.WRITE.can_execute()
        
        # EXECUTE 权限可以读写执行
        assert PermissionLevel.EXECUTE.can_read()
        assert PermissionLevel.EXECUTE.can_write()
        assert PermissionLevel.EXECUTE.can_execute()
        
        # ADMIN 权限可以做任何事
        assert PermissionLevel.ADMIN.can_read()
        assert PermissionLevel.ADMIN.can_write()
        assert PermissionLevel.ADMIN.can_execute()
        assert PermissionLevel.ADMIN.is_admin()
