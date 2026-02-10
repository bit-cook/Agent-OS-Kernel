# -*- coding: utf-8 -*-
"""Monitoring - 监控系统

支持健康检查、性能监控、告警系统。
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """健康检查"""
    name: str
    status: HealthStatus
    message: str
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict = field(default_factory=dict)


@dataclass
class MetricPoint:
    """指标点"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict = field(default_factory=dict)


class Monitor:
    """监控系统"""
    
    def __init__(
        self,
        name: str = "agent-os",
        collect_interval: float = 10.0
    ):
        """
        初始化监控系统
        
        Args:
            name: 监控名称
            collect_interval: 采集间隔
        """
        self.name = name
        self.collect_interval = collect_interval
        
        self._health_checks: Dict[str, Callable] = {}
        self._metrics: List[MetricPoint] = []
        self._alerts: List[Dict] = []
        self._alert_callbacks: List[Callable] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        self._start_time = time.time()
        
        # 注册默认健康检查
        self._register_default_checks()
        
        logger.info(f"Monitor initialized: {name}")
    
    def _register_default_checks(self):
        """注册默认健康检查"""
        self.register_health_check("memory", self._check_memory)
        self.register_health_check("cpu", self._check_cpu)
        self.register_health_check("disk", self._check_disk)
    
    def register_health_check(self, name: str, check_func: Callable):
        """注册健康检查"""
        self._health_checks[name] = check_func
        logger.info(f"Health check registered: {name}")
    
    def _check_memory(self) -> HealthCheck:
        """检查内存"""
        try:
            memory = psutil.virtual_memory()
            latency = 1.0  # 模拟延迟
            
            if memory.percent > 90:
                status = HealthStatus.CRITICAL
                message = f"内存使用率 {memory.percent}%"
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f"内存使用率 {memory.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"内存使用率 {memory.percent}%"
            
            return HealthCheck(
                name="memory",
                status=status,
                message=message,
                latency_ms=latency,
                details={
                    "used": memory.used,
                    "available": memory.available,
                    "percent": memory.percent
                }
            )
        except Exception as e:
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=0
            )
    
    def _check_cpu(self) -> HealthCheck:
        """检查 CPU"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            latency = 1000  # 1秒
            
            if cpu_percent > 90:
                status = HealthStatus.CRITICAL
            elif cpu_percent > 80:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return HealthCheck(
                name="cpu",
                status=status,
                message=f"CPU 使用率 {cpu_percent}%",
                latency_ms=latency,
                details={
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                }
            )
        except Exception as e:
            return HealthCheck(
                name="cpu",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=0
            )
    
    def _check_disk(self) -> HealthCheck:
        """检查磁盘"""
        try:
            disk = psutil.disk_usage('/')
            latency = 1.0
            
            if disk.percent > 90:
                status = HealthStatus.CRITICAL
            elif disk.percent > 80:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return HealthCheck(
                name="disk",
                status=status,
                message=f"磁盘使用率 {disk.percent}%",
                latency_ms=latency,
                details={
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            )
        except Exception as e:
            return HealthCheck(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=0
            )
    
    async def check_health(self) -> Dict[str, HealthCheck]:
        """检查健康状态"""
        results = {}
        
        for name, check_func in self._health_checks.items():
            if asyncio.iscoroutinefunction(check_func):
                results[name] = await check_func()
            else:
                results[name] = check_func()
        
        return results
    
    def get_overall_status(self) -> HealthStatus:
        """获取整体状态"""
        overall = HealthStatus.HEALTHY
        
        for check in self._health_checks.values():
            if asyncio.iscoroutinefunction(check):
                # 同步检查
                result = check()
            else:
                result = check()
            
            if result.status == HealthStatus.CRITICAL:
                return HealthStatus.CRITICAL
            elif result.status == HealthStatus.UNHEALTHY and overall != HealthStatus.CRITICAL:
                overall = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall not in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
                overall = HealthStatus.DEGRADED
        
        return overall
    
    def record_metric(self, name: str, value: float, labels: Dict = None):
        """记录指标"""
        self._metrics.append(MetricPoint(
            name=name,
            value=value,
            labels=labels or {}
        ))
        
        # 保持最近 10000 个指标
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-10000:]
    
    def get_metrics(self, name: str = None, limit: int = 100) -> List[MetricPoint]:
        """获取指标"""
        if name:
            return [m for m in self._metrics if m.name == name][-limit:]
        return self._metrics[-limit:]
    
    def on_alert(self, callback: Callable):
        """注册告警回调"""
        self._alert_callbacks.append(callback)
    
    def trigger_alert(
        self,
        name: str,
        message: str,
        severity: str = "warning",
        details: Dict = None
    ):
        """触发告警"""
        alert = {
            "name": name,
            "message": message,
            "severity": severity,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._alerts.append(alert)
        
        # 调用回调
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(alert))
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.warning(f"Alert triggered: {name} - {message}")
    
    def get_alerts(self, limit: int = 100) -> List[Dict]:
        """获取告警"""
        return self._alerts[-limit:]
    
    def clear_alerts(self):
        """清除告警"""
        self._alerts.clear()
    
    def get_stats(self) -> Dict:
        """获取统计"""
        uptime = time.time() - self._start_time
        
        return {
            "name": self.name,
            "uptime_seconds": uptime,
            "health_checks_count": len(self._health_checks),
            "metrics_count": len(self._metrics),
            "alerts_count": len(self._alerts),
            "overall_status": self.get_overall_status().value,
            "alerts_callbacks": len(self._alert_callbacks)
        }
    
    def get_system_info(self) -> Dict:
        """获取系统信息"""
        return {
            "hostname": psutil.os.uname().nodename,
            "platform": psutil.os.uname().sysname,
            "release": psutil.os.uname().release,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_total": psutil.disk_usage('/').total,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }


# 全局监控器
_monitor: Optional[Monitor] = None


def get_monitor() -> Monitor:
    """获取全局监控器"""
    global _monitor
    if _monitor is None:
        _monitor = Monitor()
    return _monitor
