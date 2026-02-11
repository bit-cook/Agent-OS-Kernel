"""测试速率限制器"""

import pytest


class TestRateLimiterExists:
    """测试速率限制器存在"""
    
    def test_import(self):
        from agent_os_kernel.core.rate_limiter import RateLimiter
        assert RateLimiter is not None
