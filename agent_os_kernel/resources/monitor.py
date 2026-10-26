# -*- coding: utf-8 -*-
"""System Monitor - 系统监控

完整的系统监控和告警系统。
"""

import asyncio
import logging
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertRule:
    """告警规则"""
    
    def __init__(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str = ">",
        duration_seconds: int = 60
    ):
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.operator = operator  # >, <, >=, <=, ==
        self.duration_seconds = duration_seconds
        self._last_triggered: Optional[datetime] = None
    
    def evaluate(self, value: float) -> bool:
        """评估规则"""
        if self.operator == ">":
            triggered = value > self.threshold
        elif self.operator == ">=":
            triggered = value >= self.threshold
        elif self.operator == "<":
            triggered = value < self.threshold
        elif self.operator == "<=":
            triggered = value <= self.threshold
        elif self.operator == "==":
            triggered = value == self.threshold
        else:
            triggered = False
        
        if triggered:
            now = datetime.now()
            if self._last_triggered is None or \
               (now - self._last_triggered) > timedelta(seconds=self.duration_seconds):
                self._last_triggered = now
                return True
        
        return False


@dataclass
class Alert:
    """告警"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    metric: str
    value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False


class SystemMonitor:
    """
    系统监控器
    
    功能：
    1. 系统指标采集
    2. 历史数据存储
    3. 告警规则管理
    4. 告警通知
    """
    
    def __init__(self, history_size: int = 3600):  # 默认保存1小时
        self._history: Dict[str, deque] = {}
        self._history_size = history_size
        self._alert_rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []
        self._alert_callbacks: List[Callable] = []
        self._monitoring: bool = False
        self._update_interval: int = 5  # 秒
    
    def set_update_interval(self, seconds: int):
        """设置更新间隔"""
        self._update_interval = seconds
    
    async def start_monitoring(self):
        """开始监控"""
        self._monitoring = True
        
        # 默认告警规则
        self.add_alert_rule(AlertRule(
            name="High CPU Usage",
            metric="cpu_percent",
            threshold=80.0,
            operator=">",
            duration_seconds=60
        ))
        
        self.add_alert_rule(AlertRule(
            name="High Memory Usage",
            metric="memory_percent",
            threshold=85.0,
            operator=">",
            duration_seconds=60
        ))
        
        # 启动监控循环
        asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                metrics = await self.collect_metrics()
                
                # 存储历史
                self._record_metrics(metrics)
                
                # 检查告警
                await self._check_alerts(metrics)
                
                await asyncio.sleep(self._update_interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """采集指标"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used / (1024 * 1024),
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "disk_read_mb": psutil.disk_io_counters().read_bytes / (1024 * 1024),
            "disk_write_mb": psutil.disk_io_counters().write_bytes / (1024 * 1024),
            "network_sent_mb": psutil.net_io_counters().bytes_sent / (1024 * 1024),
            "network_recv_mb": psutil.net_io_counters().bytes_recv / (1024 * 1024),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "process_count": len(psutil.pids())
        }
    
    def _record_metrics(self, metrics: Dict[str, Any]):
        """记录指标历史"""
        for key, value in metrics.items():
            if key not in self._history:
                self._history[key] = deque(maxlen=self._history_size)
            
            self._history[key].append({
                "timestamp": metrics["timestamp"],
                "value": value
            })
    
    def get_history(self, metric: str, duration_seconds: int = 300) -> List[Dict]:
        """获取历史数据"""
        if metric not in self._history:
            return []
        
        cutoff = datetime.now() - timedelta(seconds=duration_seconds)
        
        return [
            {"timestamp": item["timestamp"], "value": item["value"]}
            for item in self._history[metric]
            if datetime.fromisoformat(item["timestamp"]) > cutoff
        ]
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self._alert_rules[rule.name] = rule
    
    def remove_alert_rule(self, name: str):
        """移除告警规则"""
        if name in self._alert_rules:
            del self._alert_rules[name]
    
    async def _check_alerts(self, metrics: Dict[str, Any]):
        """检查告警"""
        for name, rule in self._alert_rules.items():
            if rule.metric in metrics:
                value = metrics[rule.metric]
                
                if rule.evaluate(value):
                    await self._trigger_alert(
                        level=AlertLevel.WARNING,
                        title=name,
                        description=f"{rule.metric} = {value} {rule.operator} {rule.threshold}",
                        metric=rule.metric,
                        value=value,
                        threshold=rule.threshold
                    )
    
    async def _trigger_alert(
        self,
        level: AlertLevel,
        title: str,
        description: str,
        metric: str,
        value: float,
        threshold: float
    ):
        """触发告警"""
        alert = Alert(
            alert_id=f"alert_{int(datetime.now().timestamp())}",
            level=level,
            title=title,
            description=description,
            metric=metric,
            value=value,
            threshold=threshold,
            timestamp=datetime.now()
        )
        
        self._alerts.append(alert)
        
        # 调用回调
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.warning(f"Alert triggered: {title} - {description}")
    
    def on_alert(self, callback: Callable):
        """注册告警回调"""
        self._alert_callbacks.append(callback)
    
    def get_alerts(
        self,
        level: AlertLevel = None,
        acknowledged: bool = None,
        unresolved: bool = True,
        limit: int = 50
    ) -> List[Alert]:
        """获取告警列表"""
        result = self._alerts
        
        if level:
            result = [a for a in result if a.level == level]
        
        if acknowledged is not None:
            result = [a for a in result if a.acknowledged == acknowledged]
        
        if unresolved:
            result = [a for a in result if not a.resolved]
        
        return result[-limit:]
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        latest = {}
        
        for key, history in self._history.items():
            if history:
                latest[key] = history[-1]["value"]
        
        return {
            "monitoring": self._monitoring,
            "last_update": datetime.now().isoformat(),
            "current_metrics": latest,
            "active_alerts": len(self.get_alerts(unresolved=True)),
            "total_alerts": len(self._alerts),
            "rules_count": len(self._alert_rules)
        }
    
    def export_metrics(self, duration_seconds: int = 3600) -> Dict[str, Any]:
        """导出指标数据"""
        return {
            "exported_at": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "metrics": {
                metric: self.get_history(metric, duration_seconds)
                for metric in self._history.keys()
            }
        }


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
    
    def counter_inc(self, name: str, value: float = 1.0):
        """增加计数器"""
        self._counters[name] = self._counters.get(name, 0) + value
    
    def counter_value(self, name: str) -> float:
        """获取计数器值"""
        return self._counters.get(name, 0)
    
    def gauge_set(self, name: str, value: float):
        """设置仪表值"""
        self._gauges[name] = value
    
    def gauge_value(self, name: str) -> float:
        """获取仪表值"""
        return self._gauges.get(name, 0)
    
    def histogramObserve(self, name: str, value: float):
        """观察直方图值"""
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
    
    def histogram_stats(self, name: str) -> Dict[str, float]:
        """获取直方图统计"""
        values = self._histograms.get(name, [])
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "count": n,
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / n,
            "p50": sorted_values[n // 2],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)]
        }
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "counters": self._counters,
            "gauges": self._gauges,
            "histograms": {
                name: self.histogram_stats(name)
                for name in self._histograms
            }
        }


# 便捷函数
def create_system_monitor() -> SystemMonitor:
    """创建系统监控器"""
    return SystemMonitor()


def create_metrics_collector() -> MetricsCollector:
    """创建指标收集器"""
    return MetricsCollector()
