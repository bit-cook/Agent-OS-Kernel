# -*- coding: utf-8 -*-
"""Metrics Collector - 指标收集器

生产级别的指标收集和监控系统。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
import json
import uuid
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AggregationType(Enum):
    """聚合类型"""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    PERCENTILE_50 = "p50"
    PERCENTILE_90 = "p90"
    PERCENTILE_99 = "p99"


@dataclass
class MetricConfig:
    """指标配置"""
    name: str
    metric_type: MetricType
    description: str = ""
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histogram
    percentiles: Optional[List[float]] = None  # For summary


class MetricsCollector:
    """指标收集器"""
    
    def __init__(
        self,
        flush_interval: int = 60,
        max_samples: int = 10000,
        enable_console: bool = False
    ):
        """
        初始化指标收集器
        
        Args:
            flush_interval: 刷新间隔（秒）
            max_samples: 最大样本数
            enable_console: 是否启用控制台输出
        """
        self.flush_interval = flush_interval
        self.max_samples = max_samples
        self.enable_console = enable_console
        
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timestamps: Dict[str, datetime] = {}
        
        self._labels: Dict[str, Dict[str, str]] = {}
        
        self._lock = threading.Lock()
        
        self._running = False
        self._flush_task: Optional[threading.Thread] = None
        
        logger.info(f"MetricsCollector initialized: flush={flush_interval}s")
    
    def start(self):
        """启动收集器"""
        if not self._running:
            self._running = True
            self._flush_task = threading.Thread(target=self._flush_loop)
            self._flush_task.daemon = True
            self._flush_task.start()
            logger.info("MetricsCollector started")
    
    def stop(self):
        """停止收集器"""
        self._running = False
        if self._flush_task:
            self._flush_task.join(timeout=5)
        logger.info("MetricsCollector stopped")
    
    def counter(
        self,
        name: str,
        value: float = 1,
        labels: Dict[str, str] = None
    ):
        """增加计数器"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value
            self._timestamps[key] = datetime.now(timezone.utc)
    
    def gauge(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None
    ):
        """设置仪表值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            self._timestamps[key] = datetime.now(timezone.utc)
    
    def histogram(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None
    ):
        """记录直方图"""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            if len(self._histograms[key]) > self.max_samples:
                self._histograms[key] = self._histograms[key][-self.max_samples:]
            self._timestamps[key] = datetime.now(timezone.utc)
    
    def timer(
        self,
        name: str,
        seconds: float,
        labels: Dict[str, str] = None
    ):
        """记录计时器（直方图）"""
        self.histogram(name, seconds * 1000, labels)  # ms
    
    def gauge_increment(
        self,
        name: str,
        labels: Dict[str, str] = None
    ):
        """仪表值 +1"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0) + 1
            self._timestamps[key] = datetime.now(timezone.utc)
    
    def gauge_decrement(
        self,
        name: str,
        labels: Dict[str, str] = None
    ):
        """仪表值 -1"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0) - 1
            self._timestamps[key] = datetime.now(timezone.utc)
    
    def get_counter(self, name: str, labels: Dict[str, str] = None) -> float:
        """获取计数器值"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> float:
        """获取仪表值"""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0)
    
    def get_histogram_percentile(
        self,
        name: str,
        percentile: float,
        labels: Dict[str, str] = None
    ) -> Optional[float]:
        """获取直方图百分位"""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])
        if not values:
            return None
        values.sort()
        idx = int(len(values) * percentile / 100)
        return values[idx]
    
    def get_all(self) -> Dict:
        """获取所有指标"""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: {
                        "count": len(v),
                        "sum": sum(v),
                        "min": min(v) if v else 0,
                        "max": max(v) if v else 0,
                        "p50": self._percentile(v, 50),
                        "p90": self._percentile(v, 90),
                        "p99": self._percentile(v, 99)
                    }
                    for k, v in self._histograms.items()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timestamps.clear()
        logger.info("MetricsCollector reset")
    
    def export_prometheus(self) -> str:
        """导出 Prometheus 格式"""
        lines = ["# Agent-OS-Kernel Metrics"]
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        with self._lock:
            # Counters
            for key, value in self._counters.items():
                metric_name, labels = self._parse_key(key)
                labels_str = self._format_labels(labels)
                lines.append(f"{metric_name}{labels_str} {value} {timestamp}")
            
            # Gauges
            for key, value in self._gauges.items():
                metric_name, labels = self._parse_key(key)
                labels_str = self._format_labels(labels)
                lines.append(f"{metric_name}{labels_str} {value} {timestamp}")
            
            # Histograms
            for key, values in self._histograms.items():
                metric_name, labels = self._parse_key(key)
                labels_str = self._format_labels(labels)
                count = len(values)
                sum_value = sum(values)
                lines.append(f"{metric_name}_count{labels_str} {count} {timestamp}")
                lines.append(f"{metric_name}_sum{labels_str} {sum_value} {timestamp}")
        
        return "\n".join(lines)
    
    def _flush_loop(self):
        """刷新循环"""
        while self._running:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._flush(),
                    asyncio.new_event_loop()
                )
                self._flush()
            except Exception as e:
                logger.error(f"Flush error: {e}")
            
            import time
            time.sleep(self.flush_interval)
    
    async def _flush(self):
        """刷新指标"""
        if self.enable_console:
            metrics = self.get_all()
            print(f"\n{'='*60}")
            print("Metrics Flush")
            print(f"{'='*60}")
            print(json.dumps(metrics, indent=2, default=str))
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """创建键"""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def _parse_key(self, key: str) -> tuple:
        """解析键"""
        if key.startswith("{") and key.endswith("}"):
            name = key.split("{")[0]
            labels_str = key[1:-1]
            labels = dict(l.split("=") for l in labels_str.split(","))
            return name, labels
        return key, {}
    
    def _format_labels(self, labels: Dict[str, str]) -> str:
        """格式化标签"""
        if not labels:
            return ""
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{{{label_str}}}"
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """计算百分位"""
        if not values:
            return 0
        values.sort()
        idx = int(len(values) * percentile / 100)
        return values[min(idx, len(values) - 1)]


# 全局收集器
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


# 便捷装饰器
def timed(name: str, labels: Dict[str, str] = None):
    """计时装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                collector = get_metrics_collector()
                collector.timer(name, time.time() - start, labels)
        return wrapper
    return decorator
