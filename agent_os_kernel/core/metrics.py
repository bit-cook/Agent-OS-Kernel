# -*- coding: utf-8 -*-
"""性能指标收集器"""

import time
import threading
from collections import deque
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .types import PerformanceMetrics


@dataclass
class MetricsCollector:
    """性能指标收集器"""
    window_size: int = 60  # 窗口大小（秒）
    max_history: int = 3600  # 最大历史记录数
    
    _cpu_history: deque = field(default_factory=deque)
    _memory_history: deque = field(default_factory=deque)
    _context_hit_history: deque = field(default_factory=deque)
    _swap_history: deque = field(default_factory=deque)
    _timestamps: deque = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def record_cpu(self, usage: float):
        """记录 CPU 使用率"""
        with self._lock:
            self._cpu_history.append(usage)
            self._timestamps.append(time.time())
            self._cleanup()
    
    def record_memory(self, usage: float):
        """记录内存使用率"""
        with self._lock:
            self._memory_history.append(usage)
            self._cleanup()
    
    def record_context_hit_rate(self, rate: float):
        """记录上下文命中率"""
        with self._lock:
            self._context_hit_history.append(rate)
            self._cleanup()
    
    def record_swap(self):
        """记录一次 swap 操作"""
        with self._lock:
            if self._swap_history:
                last = self._swap_history[-1]
                self._swap_history.append(last + 1)
            else:
                self._swap_history.append(1)
            self._cleanup()
    
    def _cleanup(self):
        """清理过期数据"""
        now = time.time()
        cutoff = now - self.window_size
        
        while self._timestamps and self._timestamps[0] < cutoff:
            self._cpu_history.popleft()
            self._memory_history.popleft()
            self._timestamps.popleft()
        
        # 限制历史长度
        while len(self._cpu_history) > self.max_history:
            self._cpu_history.popleft()
            self._memory_history.popleft()
            self._context_hit_history.popleft()
            self._swap_history.popleft()
    
    def get_average_cpu(self, seconds: int = 60) -> float:
        """获取平均 CPU 使用率"""
        with self._lock:
            if not self._cpu_history:
                return 0.0
            cutoff = time.time() - seconds
            values = [v for t, v in zip(self._timestamps, self._cpu_history) if t >= cutoff]
            return sum(values) / len(values) if values else 0.0
    
    def get_average_memory(self, seconds: int = 60) -> float:
        """获取平均内存使用率"""
        with self._lock:
            if not self._memory_history:
                return 0.0
            cutoff = time.time() - seconds
            values = [v for t, v in zip(self._timestamps, self._memory_history) if t >= cutoff]
            return sum(values) / len(values) if values else 0.0
    
    def get_context_hit_rate(self, seconds: int = 60) -> float:
        """获取上下文命中率"""
        with self._lock:
            if not self._context_hit_history:
                return 0.0
            cutoff = time.time() - seconds
            values = [v for t, v in zip(self._timestamps, self._context_hit_history) if t >= cutoff]
            return sum(values) / len(values) if values else 0.0
    
    def get_total_swaps(self) -> int:
        """获取总 swap 次数"""
        with self._lock:
            return self._swap_history[-1] if self._swap_history else 0
    
    def get_metrics(self, active_agents: int = 0, queued_agents: int = 0) -> PerformanceMetrics:
        """获取当前性能指标"""
        with self._lock:
            return PerformanceMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=self.get_average_cpu(),
                memory_usage=self.get_average_memory(),
                context_hit_rate=self.get_context_hit_rate(),
                swap_count=self.get_total_swaps(),
                active_agents=active_agents,
                queued_agents=queued_agents
            )
    
    def get_history(self, seconds: int = 60) -> Dict[str, List]:
        """获取历史数据"""
        with self._lock:
            cutoff = time.time() - seconds
            indices = [i for i, t in enumerate(self._timestamps) if t >= cutoff]
            return {
                "timestamps": [self._timestamps[i] for i in indices],
                "cpu": [self._cpu_history[i] for i in indices],
                "memory": [self._memory_history[i] for i in indices],
                "context_hit_rate": [self._context_hit_history[i] for i in indices]
            }


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: deque = deque()
        self._lock = threading.Lock()
    
    def allow(self) -> bool:
        """是否允许请求"""
        with self._lock:
            now = time.time()
            
            # 清理过期请求
            while self._requests and self._requests[0] < now - self.window_seconds:
                self._requests.popleft()
            
            # 检查是否超出限制
            if len(self._requests) >= self.max_requests:
                return False
            
            # 记录请求
            self._requests.append(now)
            return True
    
    def remaining(self) -> int:
        """剩余请求数"""
        with self._lock:
            now = time.time()
            valid = sum(1 for t in self._requests if t >= now - self.window_seconds)
            return max(0, self.max_requests - valid)
    
    def reset(self):
        """重置速率限制器"""
        with self._lock:
            self._requests.clear()


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_time: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
    
    def allow(self) -> bool:
        """是否允许请求"""
        with self._lock:
            # 检查是否在熔断状态
            if self._is_circuit_open():
                return False
            
            return True
    
    def record_success(self):
        """记录成功"""
        with self._lock:
            self._failure_count = 0
    
    def record_failure(self):
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
    
    def _is_circuit_open(self) -> bool:
        """检查熔断器是否开启"""
        if self._failure_count < self.failure_threshold:
            return False
        
        if self._last_failure_time is None:
            return False
        
        # 检查是否超过恢复时间
        return time.time() - self._last_failure_time < self.recovery_time
    
    def get_state(self) -> str:
        """获取熔断器状态"""
        with self._lock:
            if self._is_circuit_open():
                return "OPEN"
            elif self._failure_count > 0:
                return "HALF_OPEN"
            return "CLOSED"
