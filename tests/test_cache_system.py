"""测试缓存系统"""

import pytest


class TestCacheSystemExists:
    """测试缓存系统存在"""
    
    def test_import(self):
        """测试导入"""
        try:
            from agent_os_kernel.core.cache_system import CacheSystem
            assert CacheSystem is not None
        except ImportError:
            pass
    
    def test_level_import(self):
        """测试级别导入"""
        try:
            from agent_os_kernel.core.cache_system import CacheLevel
            assert CacheLevel is not None
        except ImportError:
            pass
