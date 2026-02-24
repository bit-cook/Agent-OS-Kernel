# -*- coding: utf-8 -*-
"""
Metrics - Agent-OS-Kernel 轻量级指标模块

提供简单易用的指标收集功能:
- 计数器 (Counter): 累加值
- 仪表盘 (Gauge): 当前值
- 计时器 (Timer): 执行时间

支持标签、导出和基本统计。
"""

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    TIMER = "timer"


@dataclass
class Metric:
    """指标数据类"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""


class Counter:
    """简单计数器 - 只增不减"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0.0
        self._lock = threading.Lock()
    
    def inc(self, amount: float = 1.0) -> None:
        """增加计数"""
        with self._lock:
            self._value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """减少计数 (不应为负数)"""
        with self._lock:
            self._value = max(0.0, self._value - amount)
    
    def value(self) -> float:
        """获取当前值"""
        with self._lock:
            return self._value
    
    def reset(self) -> None:
        """重置计数器"""
        with self._lock:
            self._value = 0.0
    
    def get(self) -> Metric:
        """获取指标对象"""
        return Metric(
            name=self.name,
            value=self._value,
            metric_type=MetricType.COUNTER,
            description=self.description
        )


class Gauge:
    """仪表盘 - 可增可减的瞬时值"""
    
    def __init__(self, name: str, description: str = "", initial_value: float = 0.0):
        self.name = name
        self.description = description
        self._value = initial_value
        self._lock = threading.Lock()
    
    def set(self, value: float) -> None:
        """设置值"""
        with self._lock:
            self._value = value
    
    def inc(self, amount: float = 1.0) -> None:
        """增加"""
        with self._lock:
            self._value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """减少"""
        with self._lock:
            self._value -= amount
    
    def value(self) -> float:
        """获取当前值"""
        with self._lock:
            return self._value
    
    def get(self) -> Metric:
        """获取指标对象"""
        return Metric(
            name=self.name,
            value=self._value,
            metric_type=MetricType.GAUGE,
            description=self.description
        )


class Timer:
    """计时器 - 测量执行时间"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._durations: List[float] = []
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None
    
    def start(self) -> None:
        """开始计时"""
        self._start_time = time.time()
    
    def stop(self) -> float:
        """停止计时并记录时长"""
        if self._start_time is None:
            raise RuntimeError("Timer not started")
        duration = time.time() - self._start_time
        with self._lock:
            self._durations.append(duration)
        self._start_time = None
        return duration
    
    def time(self) -> 'TimerContext':
        """上下文管理器计时"""
        return TimerContext(self)
    
    def mean(self) -> float:
        """平均耗时"""
        with self._lock:
            if not self._durations:
                return 0.0
            return sum(self._durations) / len(self._durations)
    
    def max(self) -> float:
        """最大耗时"""
        with self._lock:
            if not self._durations:
                return 0.0
            return max(self._durations)
    
    def min(self) -> float:
        """最小耗时"""
        with self._lock:
            if not self._durations:
                return 0.0
            return min(self._durations)
    
    def count(self) -> int:
        """记录次数"""
        with self._lock:
            return len(self._durations)
    
    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._durations.clear()
    
    def get(self) -> Metric:
        """获取指标对象 (使用平均耗时)"""
        return Metric(
            name=self.name,
            value=self.mean(),
            metric_type=MetricType.TIMER,
            description=self.description
        )


class TimerContext:
    """计时器上下文管理器"""
    
    def __init__(self, timer: Timer):
        self.timer = timer
    
    def __enter__(self) -> 'TimerContext':
        self.timer.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.timer.stop()


class MetricsRegistry:
    """指标注册表 - 管理所有指标"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._timers: Dict[str, Timer] = {}
        self._lock = threading.Lock()
    
    def counter(self, name: str, description: str = "") -> Counter:
        """获取或创建计数器"""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description)
            return self._counters[name]
    
    def gauge(self, name: str, description: str = "", initial_value: float = 0.0) -> Gauge:
        """获取或创建仪表盘"""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description, initial_value)
            return self._gauges[name]
    
    def timer(self, name: str, description: str = "") -> Timer:
        """获取或创建计时器"""
        with self._lock:
            if name not in self._timers:
                self._timers[name] = Timer(name, description)
            return self._timers[name]
    
    def get_counter(self, name: str) -> Optional[Counter]:
        """获取计数器"""
        with self._lock:
            return self._counters.get(name)
    
    def get_gauge(self, name: str) -> Optional[Gauge]:
        """获取仪表盘"""
        with self._lock:
            return self._gauges.get(name)
    
    def get_timer(self, name: str) -> Optional[Timer]:
        """获取计时器"""
        with self._lock:
            return self._timers.get(name)
    
    def counters(self) -> Dict[str, Counter]:
        """获取所有计数器"""
        with self._lock:
            return dict(self._counters)
    
    def gauges(self) -> Dict[str, Gauge]:
        """获取所有仪表盘"""
        with self._lock:
            return dict(self._gauges)
    
    def timers(self) -> Dict[str, Timer]:
        """获取所有计时器"""
        with self._lock:
            return dict(self._timers)
    
    def all_metrics(self) -> List[Metric]:
        """获取所有指标"""
        metrics = []
        with self._lock:
            for counter in self._counters.values():
                metrics.append(counter.get())
            for gauge in self._gauges.values():
                metrics.append(gauge.get())
            for timer in self._timers.values():
                metrics.append(timer.get())
        return metrics
    
    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()
            for timer in self._timers.values():
                timer.reset()


# 全局默认注册表
_default_registry: Optional[MetricsRegistry] = None
_registry_lock = threading.Lock()


def get_default_registry() -> MetricsRegistry:
    """获取默认指标注册表"""
    global _default_registry
    if _default_registry is None:
        with _registry_lock:
            if _default_registry is None:
                _default_registry = MetricsRegistry("default")
    return _default_registry


def create_counter(name: str, description: str = "") -> Counter:
    """创建计数器 (使用默认注册表)"""
    return get_default_registry().counter(name, description)


def create_gauge(name: str, description: str = "", initial_value: float = 0.0) -> Gauge:
    """创建仪表盘 (使用默认注册表)"""
    return get_default_registry().gauge(name, description, initial_value)


def create_timer(name: str, description: str = "") -> Timer:
    """创建计时器 (使用默认注册表)"""
    return get_default_registry().timer(name, description)


def export_metrics(registry: MetricsRegistry = None, format: str = "json") -> Union[str, Dict]:
    """
    导出指标
    
    Args:
        registry: 指标注册表 (默认使用全局注册表)
        format: 导出格式 (json, text)
    
    Returns:
        格式化后的指标字符串或字典
    """
    reg = registry or get_default_registry()
    
    if format == "json":
        return {
            "registry": reg.name,
            "counters": {name: c.value() for name, c in reg.counters().items()},
            "gauges": {name: g.value() for name, g in reg.gauges().items()},
            "timers": {name: {"mean": t.mean(), "max": t.max(), "min": t.min(), "count": t.count()} 
                      for name, t in reg.timers().items()}
        }
    elif format == "text":
        lines = [f"=== Metrics Registry: {reg.name} ==="]
        lines.append("\nCounters:")
        for name, c in reg.counters().items():
            lines.append(f"  {name}: {c.value()}")
        lines.append("\nGauges:")
        for name, g in reg.gauges().items():
            lines.append(f"  {name}: {g.value()}")
        lines.append("\nTimers:")
        for name, t in reg.timers().items():
            lines.append(f"  {name}: mean={t.mean():.4f}s, max={t.max():.4f}s, min={t.min():.4f}s, count={t.count()}")
        return "\n".join(lines)
    else:
        raise ValueError(f"Unknown format: {format}")


# 便捷装饰器
def counter_metric(name: str):
    """计数器装饰器 (用于函数调用计数)"""
    def decorator(func):
        func._counter = create_counter(name, f"Calls to {func.__name__}")
        def wrapper(*args, **kwargs):
            func._counter.inc()
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def gauge_metric(name: str, initial_value: float = 0.0):
    """仪表盘装饰器 (用于跟踪函数值)"""
    def decorator(func):
        func._gauge = create_gauge(name, f"Value of {func.__name__}", initial_value)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, (int, float)):
                func._gauge.set(float(result))
            return result
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def timer_metric(name: str):
    """计时器装饰器 (用于函数执行时间)"""
    def decorator(func):
        func._timer = create_timer(name, f"Execution time of {func.__name__}")
        def wrapper(*args, **kwargs):
            with func._timer.time():
                return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
