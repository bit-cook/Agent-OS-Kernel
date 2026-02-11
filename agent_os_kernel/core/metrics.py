# -*- coding: utf-8 -*-
"""
Metrics - 性能指标

支持：
1. 收集性能指标
2. 计算统计信息
3. 导出指标
4. 设置告警阈值
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
import json
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"           # 计数器
    GAUGE = "gauge"             # 仪表盘
    HISTOGRAM = "histogram"     # 直方图
    SUMMARY = "summary"          # 汇总


@dataclass
class Metric:
    """指标"""
    name: str
    metric_type: MetricType
    description: str = ""
    labels: Dict = field(default_factory=dict)
    value: float = 0
    count: int = 0
    sum_: float = 0
    buckets: Dict[float, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.buckets and self.metric_type == MetricType.HISTOGRAM:
            self.buckets = {0.1: 0, 0.5: 0, 1.0: 0, 5.0: 0, 10.0: 0}


class MetricsCollector:
    """
    指标收集器
    
    功能：
    1. 创建/更新指标
    2. 记录数值
    3. 计算统计
    4. 导出指标
    """
    
    def __init__(self, max_history: int = 1000):
        self._metrics: Dict[str, Metric] = {}
        self._history: List[Dict] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        
        # 注册默认指标
        self._register_defaults()
    
    def _register_defaults(self):
        """注册默认指标"""
        defaults = [
            ("agent_count", MetricType.GAUGE, "Number of active agents"),
            ("agent_started_total", MetricType.COUNTER, "Total agents started"),
            ("agent_completed_total", MetricType.COUNTER, "Total agents completed"),
            ("agent_failed_total", MetricType.COUNTER, "Total agents failed"),
            ("context_pages_total", MetricType.COUNTER, "Total context pages allocated"),
            ("context_switches_total", MetricType.COUNTER, "Total context switches"),
            ("scheduler_ticks_total", MetricType.COUNTER, "Total scheduler ticks"),
            ("api_calls_total", MetricType.COUNTER, "Total API calls"),
            ("api_latency_seconds", MetricType.HISTOGRAM, "API call latency"),
            ("tokens_used_total", MetricType.COUNTER, "Total tokens used"),
            ("memory_usage_bytes", MetricType.GAUGE, "Memory usage"),
            ("cpu_usage_percent", MetricType.GAUGE, "CPU usage"),
        ]
        
        for name, mtype, desc in defaults:
            self._metrics[name] = Metric(
                name=name,
                metric_type=mtype,
                description=desc
            )
    
    def counter(self, name: str, value: float = 1, labels: Dict = None):
        """增加计数器"""
        return self._update_metric(name, value, "counter", labels)
    
    def gauge(self, name: str, value: float, labels: Dict = None):
        """设置仪表盘"""
        return self._update_metric(name, value, "gauge", labels)
    
    def histogram(self, name: str, value: float, labels: Dict = None):
        """记录直方图"""
        metric = self._update_metric(name, value, "histogram", labels)
        
        # 更新 bucket
        for bucket in metric.buckets:
            if value <= bucket:
                metric.buckets[bucket] += 1
        
        return metric
    
    def _update_metric(
        self,
        name: str,
        value: float,
        mtype: str,
        labels: Dict = None
    ) -> Metric:
        """更新指标"""
        key = self._make_key(name, labels)
        
        if key not in self._metrics:
            mtype_enum = MetricType(mtype)
            self._metrics[key] = Metric(
                name=name,
                metric_type=mtype_enum,
                labels=labels or {},
                value=value
            )
        
        metric = self._metrics[key]
        
        if mtype == "counter":
            metric.value += value
            metric.count += 1
            metric.sum_ += value
        elif mtype == "gauge":
            metric.value = value
        elif mtype == "histogram":
            metric.value = value
            metric.count += 1
            metric.sum_ += value
        
        return metric
    
    def _make_key(self, name: str, labels: Dict = None) -> str:
        """生成指标 key"""
        if not labels:
            return name
        label_str = ".".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    
    def get(self, name: str, labels: Dict = None) -> Optional[Metric]:
        """获取指标"""
        key = self._make_key(name, labels)
        return self._metrics.get(key)
    
    def get_all(self) -> Dict[str, Metric]:
        """获取所有指标"""
        return copy.deepcopy(self._metrics)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_metrics": len(self._metrics),
            "metrics": {
                name: {
                    "type": m.metric_type.value,
                    "value": m.value,
                    "count": m.count,
                    "labels": m.labels
                }
                for name, m in self._metrics.items()
            }
        }
    
    def reset(self, name: str = None, labels: Dict = None):
        """重置指标"""
        if name:
            key = self._make_key(name, labels)
            if key in self._metrics:
                del self._metrics[key]
        else:
            self._metrics.clear()
            self._register_defaults()
    
    def export_prometheus(self) -> str:
        """导出 Prometheus 格式"""
        lines = ["# Agent OS Kernel Metrics"]
        
        for metric in self._metrics.values():
            labels = ""
            if metric.labels:
                label_str = ",".join(
                    f'{k}="{v}"'
                    for k, v in metric.labels.items()
                )
                labels = f"{{{label_str}}}"
            
            if metric.metric_type == MetricType.COUNTER:
                lines.append(f"# HELP {metric.name} {metric.description}")
                lines.append(f"# TYPE {metric.name} counter")
                lines.append(f"{metric.name}{labels} {metric.value}")
            
            elif metric.metric_type == MetricType.GAUGE:
                lines.append(f"# HELP {metric.name} {metric.description}")
                lines.append(f"# TYPE {metric.name} gauge")
                lines.append(f"{metric.name}{labels} {metric.value}")
            
            elif metric.metric_type == MetricType.HISTOGRAM:
                lines.append(f"# HELP {metric.name} {metric.description}")
                lines.append(f"# TYPE {metric.name} histogram")
                for bucket, count in metric.buckets.items():
                    lines.append(
                        f"{metric.name}_bucket{labels}"
                        f"{{le=\"{bucket}\"}} {count}"
                    )
                lines.append(f"{metric.name}_bucket{labels}{{le=\"+Inf\"}} {metric.count}")
                lines.append(f"{metric.name}_sum{labels} {metric.sum_}")
                lines.append(f"{metric.name}_count{labels} {metric.count}")
        
        return "\n".join(lines)
    
    def export_json(self) -> str:
        """导出 JSON 格式"""
        return json.dumps(self.get_stats(), indent=2, default=str)


# Timer 装饰器
def timer(metrics: MetricsCollector, metric_name: str):
    """计时装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start
                metrics.histogram(metric_name, elapsed)
        return wrapper
    return decorator


# 便捷函数
def create_metrics_collector(max_history: int = 1000) -> MetricsCollector:
    """创建指标收集器"""
    return MetricsCollector(max_history)
