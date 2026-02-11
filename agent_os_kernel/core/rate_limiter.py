# -*- coding: utf-8 -*-
"""Rate Limiter - 速率限制器

用于控制 API 调用频率。
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timezone, timedelta, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests_per_second: float = 10.0
    requests_per_minute: float = 600.0
    burst_size: int = 20
    window_seconds: int = 60


class RateLimiter:
    """滑动窗口速率限制器"""
    
    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        name: str = "default"
    ):
        self.config = config or RateLimitConfig()
        self.name = name
        
        # 滑动窗口
        self._requests: Dict[str, deque] = {}
        self._lock = asyncio.Lock()
        
        # 令牌桶
        self._tokens: Dict[str, float] = {}
        self._last_update: Dict[str, float] = {}
        
        logger.info(f"RateLimiter '{name}' initialized: {self.config}")
    
    async def acquire(self, key: str = "default") -> Tuple[bool, float]:
        """
        获取许可
        
        Args:
            key: 标识符 (如 API Key, User ID)
            
        Returns:
            (是否成功, 等待时间)
        """
        now = time.time()
        
        async with self._lock:
            # 初始化
            if key not in self._tokens:
                self._tokens[key] = self.config.burst_size
                self._last_update[key] = now
            
            # 更新令牌
            elapsed = now - self._last_update[key]
            self._tokens[key] = min(
                self.config.burst_size,
                self._tokens[key] + elapsed * self.config.requests_per_second
            )
            self._last_update[key] = now
            
            # 检查是否有令牌
            if self._tokens[key] >= 1:
                self._tokens[key] -= 1
                return True, 0.0
            
            # 计算等待时间
            wait_time = (1 - self._tokens[key]) / self.config.requests_per_second
            return False, wait_time
    
    async def wait(self, key: str = "default", timeout: float = 30.0) -> bool:
        """
        等待获取许可
        
        Args:
            key: 标识符
            timeout: 超时时间
            
        Returns:
            是否成功获取
        """
        start_time = time.time()
        
        while True:
            success, wait_time = await self.acquire(key)
            
            if success:
                return True
            
            if time.time() - start_time > timeout:
                logger.warning(f"Rate limit timeout for '{key}'")
                return False
            
            await asyncio.sleep(min(wait_time, 0.1))
    
    async def check_limit(self, key: str = "default") -> bool:
        """
        检查是否超过限制 (不消耗令牌)
        
        Returns:
            是否在限制内
        """
        now = time.time()
        
        async with self._lock:
            if key not in self._tokens:
                return True
            
            elapsed = now - self._last_update[key]
            tokens = min(
                self.config.burst_size,
                self._tokens[key] + elapsed * self.config.requests_per_second
            )
            
            return tokens >= 1
    
    def get_remaining(self, key: str = "default") -> int:
        """获取剩余请求数"""
        if key not in self._tokens:
            return self.config.burst_size
        
        elapsed = time.time() - self._last_update.get(key, time.time())
        tokens = min(
            self.config.burst_size,
            self._tokens[key] + elapsed * self.config.requests_per_second
        )
        
        return max(0, int(tokens))
    
    def get_stats(self, key: str = "default") -> Dict:
        """获取统计信息"""
        return {
            "remaining": self.get_remaining(key),
            "limit": self.config.burst_size,
            "rps": self.config.requests_per_second,
            "rpm": self.config.requests_per_minute
        }


class MultiLimiter:
    """多维度速率限制器"""
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()
    
    def add_limiter(self, name: str, config: RateLimitConfig):
        """添加限制器"""
        self._limiters[name] = RateLimiter(config, name)
        logger.info(f"Added rate limiter: {name}")
    
    async def acquire(self, **limits) -> Tuple[bool, float]:
        """
        检查所有限制
        
        Returns:
            (是否所有限制都通过, 最大等待时间)
        """
        max_wait = 0.0
        success = True
        
        async with self._lock:
            for name, key in limits.items():
                if name in self._limiters:
                    limiter_success, wait_time = await self._limiters[name].acquire(key)
                    success = success and limiter_success
                    max_wait = max(max_wait, wait_time)
        
        return success, max_wait
    
    async def wait(self, timeout: float = 30.0, **limits) -> bool:
        """等待所有限制通过"""
        start_time = time.time()
        
        async with self._lock:
            limiters_to_wait = {}
            for name, key in limits.items():
                if name in self._limiters:
                    limiters_to_wait[name] = key
        
        for name, key in limiters_to_wait.items():
            if not await self._limiters[name].wait(key, timeout):
                return False
        
        return True
    
    def get_stats(self, **limits) -> Dict:
        """获取所有限制的统计"""
        stats = {}
        for name, key in limits.items():
            if name in self._limiters:
                stats[name] = self._limiters[name].get_stats(key)
        return stats


# 全局速率限制器
_global_limiter: Optional[MultiLimiter] = None


def get_global_limiter() -> MultiLimiter:
    """获取全局速率限制器"""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = MultiLimiter()
        _global_limiter.add_limiter(
            "api",
            RateLimitConfig(
                requests_per_second=10.0,
                requests_per_minute=600.0,
                burst_size=20
            )
        )
    return _global_limiter


