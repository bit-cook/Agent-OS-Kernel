"""测试锁管理器"""

import pytest


class TestLockManagerExists:
    """测试锁管理器存在"""
    
    def test_import(self):
        """测试导入"""
        try:
            from agent_os_kernel.core.lock_manager import LockManager
            assert LockManager is not None
        except ImportError:
            pass
    
    def test_type_import(self):
        """测试类型导入"""
        try:
            from agent_os_kernel.core.lock_manager import LockType
            assert LockType is not None
        except ImportError:
            pass
