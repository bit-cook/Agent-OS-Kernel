# -*- coding: utf-8 -*-
from typing import Dict
"""Circuit Breaker - 熔断器

保护系统免受级联故障影响。
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断状态"""
    CLOSED = "closed"  # 正常
    OPEN = "open"  # 打开（拒绝请求）
    HALF_OPEN = "half_open"  # 半开（测试恢复）


@dataclass
class CircuitConfig:
    """熔断器配置"""
    name: str
    failure_threshold: int = 5  # 失败次数阈值
    success_threshold: int = 3  # 成功次数阈值（半开状态）
    timeout_seconds: float = 60.0  # 超时时间
    half_open_max_calls: int = 3  # 半开状态最大并发调用数
    
    def __post_init__(self):
        if self.failure_threshold <= 0:
            self.failure_threshold = 5
        if self.timeout_seconds <= 0:
            self.timeout_seconds = 60.0


@dataclass
class CircuitMetrics:
    """熔断器指标"""
    name: str
    state: CircuitState = CircuitState.CLOSED
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changed_time: Optional[datetime] = None
    current_concurrent: int = 0
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        name: str = "default",
        config: CircuitConfig = None
    ):
        """
        初始化熔断器
        
        Args:
            name: 名称
            config: 配置
        """
        self.name = name
        self.config = config or CircuitConfig(name=name)
        
        self._state = CircuitState.CLOSED
        self._metrics = CircuitMetrics(name=name)
        self._last_failure_time: Optional[float] = None
        self._half_open_successes = 0
        self._lock = asyncio.Lock()
        
        logger.info(f"CircuitBreaker initialized: {name}")
    
    @property
    def state(self) -> CircuitState:
        """获取状态"""
        if self._state == CircuitState.OPEN:
            # 检查是否超时
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._metrics.state = CircuitState.HALF_OPEN
                    self._metrics.state_changed_time = datetime.now(timezone.utc)
                    logger.info(f"CircuitBreaker {self.name}: OPEN -> HALF_OPEN")
        return self._state
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        调用受保护的函数
        
        Args:
            func: 可调用对象
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值
        """
        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.current_concurrent += 1
        
        try:
            # 检查状态
            if self.state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"CircuitBreaker {self.name} is OPEN"
                )
            
            # 执行
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await self._on_success(result)
            return result
            
        except Exception as e:
            await self._on_failure(e)
            raise
    
    async def _on_success(self, result: Any):
        """成功处理"""
        async with self._lock:
            self._metrics.successful_calls += 1
            self._metrics.last_success_time = datetime.now(timezone.utc)
            self._metrics.current_concurrent -= 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            
            if self._half_open_successes >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._metrics.state = CircuitState.CLOSED
                self._metrics.state_changed_time = datetime.now(timezone.utc)
                self._half_open_successes = 0
                logger.info(f"CircuitBreaker {self.name}: HALF_OPEN -> CLOSED")
    
    async def _on_failure(self, error: Exception):
        """失败处理"""
        async with self._lock:
            self._metrics.failed_calls += 1
            self._metrics.last_failure_time = datetime.now(timezone.utc)
            self._last_failure_time = time.time()
            self._metrics.current_concurrent -= 1
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._metrics.state = CircuitState.OPEN
            self._metrics.state_changed_time = datetime.now(timezone.utc)
            self._half_open_successes = 0
            logger.warning(f"CircuitBreaker {self.name}: HALF_OPEN -> OPEN")
        
        elif self._state == CircuitState.CLOSED:
            if self._metrics.failed_calls >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                self._metrics.state = CircuitState.OPEN
                self._metrics.state_changed_time = datetime.now(timezone.utc)
                logger.warning(
                    f"CircuitBreaker {self.name}: CLOSED -> OPEN "
                    f"(failures: {self._metrics.failed_calls})"
                )
    
    def get_metrics(self) -> CircuitMetrics:
        """获取指标"""
        return self._metrics
    
    def reset(self):
        """重置熔断器"""
        self._state = CircuitState.CLOSED
        self._metrics = CircuitMetrics(name=self.name)
        self._last_failure_time = None
        self._half_open_successes = 0
        logger.info(f"CircuitBreaker {self.name} reset")


class CircuitOpenError(Exception):
    """熔断器打开错误"""
    pass


# 分布式熔断器（简化版）
class DistributedCircuitBreaker(CircuitBreaker):
    """分布式熔断器"""
    
    def __init__(
        self,
        name: str = "distributed",
        config: CircuitConfig = None,
        redis_client = None
    ):
        super().__init__(name, config)
        self._redis = redis_client
    
    async def _sync_state(self):
        """同步状态"""
        if self._redis:
            try:
                # 简化实现
                pass
            except Exception:
                pass
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """调用"""
        await self._sync_state()
        return await super().call(func, *args, **kwargs)


# 全局熔断器管理器
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str = "default", **kwargs) -> CircuitBreaker:
    """获取或创建熔断器"""
    global _circuit_breakers
    if name not in _circuit_breakers:
        config = CircuitConfig(name=name, **kwargs)
        _circuit_breakers[name] = CircuitBreaker(config=config)
    return _circuit_breakers[name]


def get_circuit_breaker_manager() -> Dict[str, CircuitBreaker]:
    """获取熔断器管理器"""
    return _circuit_breakers


def reset_all_circuit_breakers():
    """重置所有熔断器"""
    global _circuit_breakers
    for cb in _circuit_breakers.values():
        cb.reset()
