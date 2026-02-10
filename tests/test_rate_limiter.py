# -*- coding: utf-8 -*-
"""测试 Rate Limiter"""

import pytest
import asyncio
import time
from agent_os_kernel.core.rate_limiter import RateLimiter, RateLimitConfig, MultiLimiter


class TestRateLimiter:
    """RateLimiter 测试类"""
    
    @pytest.fixture
    def limiter(self):
        """创建测试限制器"""
        config = RateLimitConfig(
            requests_per_second=10.0,
            requests_per_minute=600.0,
            burst_size=5
        )
        return RateLimiter(config, "test")
    
    def test_initial_state(self, limiter):
        """测试初始状态"""
        stats = limiter.get_stats("test")
        
        assert stats["remaining"] == limiter.config.burst_size
        assert stats["limit"] == limiter.config.burst_size
        assert stats["rps"] == limiter.config.requests_per_second
        assert stats["rpm"] == limiter.config.requests_per_minute
    
    @pytest.mark.asyncio
    async def test_acquire_success(self, limiter):
        """测试获取许可成功"""
        success, wait_time = await limiter.acquire("test")
        
        assert success is True
        assert wait_time == 0.0
    
    @pytest.mark.asyncio
    async def test_acquire_exhaust(self, limiter):
        """测试耗尽令牌"""
        # 消耗所有令牌
        for _ in range(limiter.config.burst_size):
            await limiter.acquire("test")
        
        # 下一次应该失败
        success, wait_time = await limiter.acquire("test")
        
        assert success is False
        assert wait_time > 0
    
    @pytest.mark.asyncio
    async def test_wait_success(self, limiter):
        """测试等待获取"""
        # 耗尽令牌
        for _ in range(limiter.config.burst_size):
            await limiter.acquire("test")
        
        # 等待应该成功
        success = await limiter.wait("test", timeout=2.0)
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_wait_timeout(self, limiter):
        """测试等待超时"""
        # 设置一个很小的突发容量
        limiter.config.burst_size = 1
        
        # 消耗令牌
        await limiter.acquire("test")
        
        # 等待应该超时
        success = await limiter.wait("test", timeout=0.1)
        
        assert success is False
    
    def test_get_remaining(self, limiter):
        """测试剩余请求数"""
        initial = limiter.get_remaining("test")
        assert initial == limiter.config.burst_size
        
        # 消耗一个
        limiter._tokens["test"] -= 1
        
        remaining = limiter.get_remaining("test")
        assert remaining == limiter.config.burst_size - 1
    
    @pytest.mark.asyncio
    async def test_different_keys(self, limiter):
        """测试不同 key"""
        await limiter.acquire("key1")
        await limiter.acquire("key2")
        
        # 每个 key 有独立的令牌桶
        remaining1 = limiter.get_remaining("key1")
        remaining2 = limiter.get_remaining("key2")
        
        assert remaining1 == limiter.config.burst_size - 1
        assert remaining2 == limiter.config.burst_size - 1


class TestMultiLimiter:
    """MultiLimiter 测试类"""
    
    @pytest.fixture
    def multi(self):
        """创建多维度限制器"""
        multi = MultiLimiter()
        multi.add_limiter("api", RateLimitConfig(requests_per_second=10, burst_size=5))
        multi.add_limiter("batch", RateLimitConfig(requests_per_second=2, burst_size=2))
        return multi
    
    @pytest.mark.asyncio
    async def test_acquire_all(self, multi):
        """测试获取所有限制"""
        success, wait_time = await multi.acquire(api="user1", batch="job1")
        
        assert success is True
        assert wait_time == 0.0
    
    @pytest.mark.asyncio
    async def test_wait_all(self, multi):
        """测试等待所有限制"""
        success = await multi.wait(api="user1", batch="job1")
        
        assert success is True
    
    def test_get_stats(self, multi):
        """测试获取统计"""
        stats = multi.get_stats(api="user1", batch="job1")
        
        assert "api" in stats
        assert "batch" in stats
    
    @pytest.mark.asyncio
    async def test_nonexistent_limiter(self, multi):
        """测试不存在的限制器"""
        # 应该忽略不存在的限制器
        success, wait_time = await multi.acquire(
            api="user1",
            nonexistent="key"
        )
        
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
