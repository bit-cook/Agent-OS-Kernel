# -*- coding: utf-8 -*-
"""
Metrics Collector - Agent-OS-Kernel 指标收集器

提供完整的指标收集系统,包括:
- Counter (计数器): 只增不减的指标
- Gauge (仪表盘): 可增可减的瞬时值指标
- Histogram (直方图): 统计分布的指标
- 指标导出功能

支持多种导出格式: JSON, Prometheus, Text
"""

import json
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from statistics import mean, median, stdev, pstdev

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class ExportFormat(Enum):
    """导出格式枚举"""
    JSON = "json"
    PROMETHEUS = "prometheus"
    TEXT = "text"


@dataclass
class MetricLabel:
    """指标标签"""
    name: str
    value: str


@dataclass
class MetricSample:
    """指标样本"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""


class Counter:
    """
    计数器 - 只增不减的指标
    
    适用于统计请求数量、错误数量等累计值。
    """
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None):
        """
        初始化计数器
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
        """
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def _get_label_values(self, label_values: Dict[str, str]) -> tuple:
        """获取标签元组"""
        if not self.labels:
            return ()
        return tuple(label_values.get(label, "") for label in self.labels)
    
    def inc(self, amount: float = 1.0, label_values: Dict[str, str] = None):
        """
        增加计数器
        
        Args:
            amount: 增加量
            label_values: 标签值字典
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            self._values[labels] += amount
    
    def dec(self, amount: float = 1.0, label_values: Dict[str, str] = None):
        """
        减少计数器
        
        Args:
            amount: 减少量
            label_values: 标签值字典
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            self._values[labels] = max(0, self._values[labels] - amount)
    
    def value(self, label_values: Dict[str, str] = None) -> float:
        """
        获取当前值
        
        Args:
            label_values: 标签值字典
            
        Returns:
            当前计数值
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            return self._values[labels]
    
    def get_all_values(self) -> Dict[tuple, float]:
        """获取所有标签组合的值"""
        with self._lock:
            return dict(self._values)
    
    def reset(self, label_values: Dict[str, str] = None):
        """
        重置计数器
        
        Args:
            label_values: 标签值字典
        """
        with self._lock:
            if label_values:
                labels = self._get_label_values(label_values)
                self._values[labels] = 0
            else:
                self._values.clear()
    
    def samples(self) -> List[MetricSample]:
        """生成指标样本"""
        samples = []
        for labels_tuple, value in self._values.items():
            label_dict = dict(zip(self.labels, labels_tuple)) if self.labels else {}
            samples.append(MetricSample(
                name=self.name,
                value=value,
                metric_type=MetricType.COUNTER,
                labels=label_dict,
                description=self.description
            ))
        return samples


class Gauge:
    """
    仪表盘 - 可增可减的瞬时值指标
    
    适用于当前连接数、内存使用量等瞬时值。
    """
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None):
        """
        初始化仪表盘
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
        """
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def _get_label_values(self, label_values: Dict[str, str]) -> tuple:
        """获取标签元组"""
        if not self.labels:
            return ()
        return tuple(label_values.get(label, "") for label in self.labels)
    
    def set(self, value: float, label_values: Dict[str, str] = None):
        """
        设置值
        
        Args:
            value: 设置的值
            label_values: 标签值字典
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            self._values[labels] = value
    
    def inc(self, amount: float = 1.0, label_values: Dict[str, str] = None):
        """
        增加
        
        Args:
            amount: 增加量
            label_values: 标签值字典
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            self._values[labels] += amount
    
    def dec(self, amount: float = 1.0, label_values: Dict[str, str] = None):
        """
        减少
        
        Args:
            amount: 减少量
            label_values: 标签值字典
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            self._values[labels] -= amount
    
    def value(self, label_values: Dict[str, str] = None) -> float:
        """
        获取当前值
        
        Args:
            label_values: 标签值字典
            
        Returns:
            当前值
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            return self._values[labels]
    
    def get_all_values(self) -> Dict[tuple, float]:
        """获取所有标签组合的值"""
        with self._lock:
            return dict(self._values)
    
    def reset(self, label_values: Dict[str, str] = None):
        """
        重置
        
        Args:
            label_values: 标签值字典
        """
        with self._lock:
            if label_values:
                labels = self._get_label_values(label_values)
                self._values[labels] = 0
            else:
                self._values.clear()
    
    def samples(self) -> List[MetricSample]:
        """生成指标样本"""
        samples = []
        for labels_tuple, value in self._values.items():
            label_dict = dict(zip(self.labels, labels_tuple)) if self.labels else {}
            samples.append(MetricSample(
                name=self.name,
                value=value,
                metric_type=MetricType.GAUGE,
                labels=label_dict,
                description=self.description
            ))
        return samples


class Histogram:
    """
    直方图 - 统计分布的指标
    
    适用于延迟分布、请求大小分布等需要统计分布的场景。
    支持自定义buckets,默认为标准的Prometheus buckets。
    """
    
    # 默认的bucket边界
    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.075,
        0.1, 0.25, 0.5, 0.75, 1.0, 2.5,
        5.0, 7.5, 10.0, +float('inf')
    )
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None,
        buckets: tuple = None
    ):
        """
        初始化直方图
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            buckets: 自定义bucket边界
        """
        self.name = name
        self.description = description
        self.labels = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        
        # 存储每个bucket的计数
        self._bucket_counts: Dict[tuple, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        # 存储所有观察值
        self._observations: Dict[tuple, List[float]] = defaultdict(list)
        # 存储总数和总和
        self._totals: Dict[tuple, int] = defaultdict(int)
        self._sums: Dict[tuple, float] = defaultdict(float)
        
        self._lock = threading.Lock()
    
    def _get_label_values(self, label_values: Dict[str, str]) -> tuple:
        """获取标签元组"""
        if not self.labels:
            return ()
        return tuple(label_values.get(label, "") for label in self.labels)
    
    def observe(self, value: float, label_values: Dict[str, str] = None):
        """
        观察一个值
        
        Args:
            value: 观察值
            label_values: 标签值字典
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            
            # 更新bucket计数
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[labels][bucket] += 1
            
            # 更新观察值列表
            self._observations[labels].append(value)
            
            # 更新总数和总和
            self._totals[labels] += 1
            self._sums[labels] += value
    
    def get_count(self, label_values: Dict[str, str] = None) -> int:
        """
        获取观察总数
        
        Args:
            label_values: 标签值字典
            
        Returns:
            观察总数
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            return self._totals[labels]
    
    def get_sum(self, label_values: Dict[str, str] = None) -> float:
        """
        获取观察值总和
        
        Args:
            label_values: 标签值字典
            
        Returns:
            观察值总和
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            return self._sums[labels]
    
    def get_bucket_counts(self, label_values: Dict[str, str] = None) -> Dict[float, int]:
        """
        获取bucket计数
        
        Args:
            label_values: 标签值字典
            
        Returns:
            bucket边界到计数的映射
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            return dict(self._bucket_counts[labels])
    
    def get_percentiles(
        self,
        percentiles: List[float] = None,
        label_values: Dict[str, str] = None
    ) -> Dict[float, float]:
        """
        获取百分位数
        
        Args:
            percentiles: 百分位数列表 (如 [0.5, 0.9, 0.99])
            label_values: 标签值字典
            
        Returns:
            百分位数到值的映射
        """
        with self._lock:
            labels = self._get_label_values(label_values or {})
            observations = self._observations[labels]
            
            if not observations:
                return {}
            
            observations.sort()
            result = {}
            for p in (percentiles or [0.5, 0.9, 0.95, 0.99]):
                idx = int(len(observations) * p)
                idx = min(idx, len(observations) - 1)
                result[p] = observations[idx]
            
            return result
    
    def reset(self, label_values: Dict[str, str] = None):
        """
        重置直方图
        
        Args:
            label_values: 标签值字典
        """
        with self._lock:
            if label_values:
                labels = self._get_label_values(label_values)
                self._bucket_counts[labels].clear()
                self._observations[labels].clear()
                self._totals[labels] = 0
                self._sums[labels] = 0
            else:
                self._bucket_counts.clear()
                self._observations.clear()
                self._totals.clear()
                self._sums.clear()
    
    def samples(self) -> List[MetricSample]:
        """生成指标样本"""
        samples = []
        
        for labels_tuple in self._totals.keys():
            label_dict = dict(zip(self.labels, labels_tuple)) if self.labels else {}
            
            # 添加_sum样本
            samples.append(MetricSample(
                name=f"{self.name}_sum",
                value=self._sums[labels_tuple],
                metric_type=MetricType.HISTOGRAM,
                labels=label_dict,
                description=self.description
            ))
            
            # 添加_count样本
            samples.append(MetricSample(
                name=f"{self.name}_count",
                value=float(self._totals[labels_tuple]),
                metric_type=MetricType.HISTOGRAM,
                labels=label_dict,
                description=self.description
            ))
            
            # 添加bucket样本
            for bucket in self.buckets:
                if bucket == float('inf'):
                    bucket_str = "+Inf"
                else:
                    bucket_str = str(bucket)
                
                samples.append(MetricSample(
                    name=f"{self.name}_bucket",
                    value=float(self._bucket_counts[labels_tuple][bucket]),
                    metric_type=MetricType.HISTOGRAM,
                    labels=dict(label_dict, **{"le": bucket_str}),
                    description=self.description
                ))
        
        return samples


class MetricsExporter:
    """指标导出器"""
    
    def __init__(self, registry: "MetricsRegistry"):
        """
        初始化导出器
        
        Args:
            registry: 指标注册表
        """
        self.registry = registry
    
    def export_json(self) -> str:
        """
        导出为JSON格式
        
        Returns:
            JSON字符串
        """
        samples = self.registry.samples()
        data = {
            "metrics": [
                {
                    "name": s.name,
                    "value": s.value,
                    "type": s.metric_type.value,
                    "labels": s.labels,
                    "timestamp": s.timestamp,
                    "description": s.description
                }
                for s in samples
            ]
        }
        return json.dumps(data, indent=2)
    
    def export_prometheus(self) -> str:
        """
        导出为Prometheus格式
        
        Returns:
            Prometheus格式字符串
        """
        lines = []
        samples = self.registry.samples()
        
        for sample in samples:
            # 构建标签部分
            if sample.labels:
                label_parts = []
                for key, value in sample.labels.items():
                    # 转义特殊字符
                    escaped_value = str(value).replace('"', '\\"')
                    label_parts.append(f'{key}="{escaped_value}"')
                labels_str = "{" + ",".join(label_parts) + "}"
            else:
                labels_str = ""
            
            # 添加HELP和TYPE行(只对每个指标名称添加一次)
            if sample.metric_type != MetricType.HISTOGRAM or "_bucket" not in sample.name:
                if sample.description:
                    lines.append(f"# HELP {sample.name} {sample.description}")
                type_name = sample.metric_type.value.upper()
                if sample.metric_type == MetricType.HISTOGRAM:
                    type_name = "HISTOGRAM"
                lines.append(f"# TYPE {sample.name} {type_name}")
            
            # 添加指标行
            lines.append(f"{sample.name}{labels_str} {sample.value}")
        
        return "\n".join(lines)
    
    def export_text(self) -> str:
        """
        导出为人类可读的文本格式
        
        Returns:
            文本格式字符串
        """
        lines = []
        samples = self.registry.samples()
        
        # 按指标类型分组
        by_type = defaultdict(list)
        for sample in samples:
            by_type[sample.metric_type].append(sample)
        
        for metric_type, type_samples in by_type.items():
            lines.append(f"\n{'=' * 50}")
            lines.append(f"Metric Type: {metric_type.value.upper()}")
            lines.append(f"{'=' * 50}")
            
            for sample in type_samples:
                lines.append(f"\n{sample.name}")
                if sample.description:
                    lines.append(f"  Description: {sample.description}")
                lines.append(f"  Type: {sample.metric_type.value}")
                lines.append(f"  Value: {sample.value}")
                if sample.labels:
                    lines.append(f"  Labels: {sample.labels}")
                lines.append(f"  Timestamp: {sample.timestamp}")
        
        return "\n".join(lines)


class MetricsRegistry:
    """
    指标注册表 - 管理和收集所有指标
    
    是指标系统的核心,负责注册、收集和导出指标。
    """
    
    def __init__(self, name: str = "default"):
        """
        初始化注册表
        
        Args:
            name: 注册表名称
        """
        self.name = name
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()
    
    def create_counter(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None
    ) -> Counter:
        """
        创建计数器
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            
        Returns:
            Counter实例
        """
        with self._lock:
            if name in self._counters:
                raise ValueError(f"Counter '{name}' already exists")
            counter = Counter(name, description, labels)
            self._counters[name] = counter
            return counter
    
    def create_gauge(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None
    ) -> Gauge:
        """
        创建仪表盘
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            
        Returns:
            Gauge实例
        """
        with self._lock:
            if name in self._gauges:
                raise ValueError(f"Gauge '{name}' already exists")
            gauge = Gauge(name, description, labels)
            self._gauges[name] = gauge
            return gauge
    
    def create_histogram(
        self,
        name: str,
        description: str = "",
        labels: List[str] = None,
        buckets: tuple = None
    ) -> Histogram:
        """
        创建直方图
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表
            buckets: 自定义bucket边界
            
        Returns:
            Histogram实例
        """
        with self._lock:
            if name in self._histograms:
                raise ValueError(f"Histogram '{name}' already exists")
            histogram = Histogram(name, description, labels, buckets)
            self._histograms[name] = histogram
            return histogram
    
    def get_counter(self, name: str) -> Optional[Counter]:
        """获取计数器"""
        return self._counters.get(name)
    
    def get_gauge(self, name: str) -> Optional[Gauge]:
        """获取仪表盘"""
        return self._gauges.get(name)
    
    def get_histogram(self, name: str) -> Optional[Histogram]:
        """获取直方图"""
        return self._histograms.get(name)
    
    def counter(self, name: str) -> Counter:
        """
        获取或创建计数器
        
        Args:
            name: 指标名称
            
        Returns:
            Counter实例
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name)
            return self._counters[name]
    
    def gauge(self, name: str) -> Gauge:
        """
        获取或创建仪表盘
        
        Args:
            name: 指标名称
            
        Returns:
            Gauge实例
        """
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name)
            return self._gauges[name]
    
    def histogram(self, name: str) -> Histogram:
        """
        获取或创建直方图
        
        Args:
            name: 指标名称
            
        Returns:
            Histogram实例
        """
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name)
            return self._histograms[name]
    
    def samples(self) -> List[MetricSample]:
        """收集所有指标样本"""
        samples = []
        
        with self._lock:
            for counter in self._counters.values():
                samples.extend(counter.samples())
            
            for gauge in self._gauges.values():
                samples.extend(gauge.samples())
            
            for histogram in self._histograms.values():
                samples.extend(histogram.samples())
        
        return samples
    
    def reset(self, name: str = None):
        """
        重置指标
        
        Args:
            name: 指标名称,为None则重置所有
        """
        with self._lock:
            if name:
                if name in self._counters:
                    self._counters[name].reset()
                if name in self._gauges:
                    self._gauges[name].reset()
                if name in self._histograms:
                    self._histograms[name].reset()
            else:
                for counter in self._counters.values():
                    counter.reset()
                for gauge in self._gauges.values():
                    gauge.reset()
                for histogram in self._histograms.values():
                    histogram.reset()
    
    def export(self, format: ExportFormat = ExportFormat.JSON) -> str:
        """
        导出指标
        
        Args:
            format: 导出格式
            
        Returns:
            格式化后的指标字符串
        """
        exporter = MetricsExporter(self)
        
        if format == ExportFormat.JSON:
            return exporter.export_json()
        elif format == ExportFormat.PROMETHEUS:
            return exporter.export_prometheus()
        elif format == ExportFormat.TEXT:
            return exporter.export_text()
        else:
            raise ValueError(f"Unknown export format: {format}")
    
    def list_metrics(self) -> Dict[str, List[str]]:
        """
        列出所有指标
        
        Returns:
            按类型分组的指标名称列表
        """
        with self._lock:
            return {
                "counters": list(self._counters.keys()),
                "gauges": list(self._gauges.keys()),
                "histograms": list(self._histograms.keys())
            }


# 全局默认注册表
_default_registry: Optional[MetricsRegistry] = None
_registry_lock = threading.Lock()


def get_default_registry() -> MetricsRegistry:
    """获取默认注册表"""
    global _default_registry
    if _default_registry is None:
        with _registry_lock:
            if _default_registry is None:
                _default_registry = MetricsRegistry("default")
    return _default_registry


def create_metrics_registry(name: str = "default") -> MetricsRegistry:
    """
    创建新的指标注册表
    
    Args:
        name: 注册表名称
        
    Returns:
        MetricsRegistry实例
    """
    return MetricsRegistry(name)


# 便捷函数
def create_counter(name: str, description: str = "", labels: List[str] = None) -> Counter:
    """创建计数器"""
    return get_default_registry().create_counter(name, description, labels)


def create_gauge(name: str, description: str = "", labels: List[str] = None) -> Gauge:
    """创建仪表盘"""
    return get_default_registry().create_gauge(name, description, labels)


def create_histogram(
    name: str,
    description: str = "",
    labels: List[str] = None,
    buckets: tuple = None
) -> Histogram:
    """创建直方图"""
    return get_default_registry().create_histogram(name, description, labels, buckets)


def counter(name: str) -> Counter:
    """获取或创建计数器"""
    return get_default_registry().counter(name)


def gauge(name: str) -> Gauge:
    """获取或创建仪表盘"""
    return get_default_registry().gauge(name)


def histogram(name: str) -> Histogram:
    """获取或创建直方图"""
    return get_default_registry().histogram(name)


def export_metrics(format: ExportFormat = ExportFormat.JSON) -> str:
    """导出指标"""
    return get_default_registry().export(format)
