# -*- coding: utf-8 -*-
"""
Resource Monitor - Agent-OS-Kernel 资源监控器模块

提供系统资源监控功能，包括CPU、内存、磁盘、网络等资源的实时监控。
支持阈值告警、历史数据记录和资源使用趋势分析。
"""

import time
import threading
import psutil
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import deque


class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"
    THREAD = "thread"


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceSnapshot:
    """资源快照数据"""
    timestamp: datetime
    resource_type: ResourceType
    usage_percent: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "resource_type": self.resource_type.value,
            "usage_percent": self.usage_percent,
            "details": self.details
        }


@dataclass
class AlertRule:
    """告警规则"""
    resource_type: ResourceType
    threshold: float
    comparison: str  # "gt", "lt", "gte", "lte", "eq"
    level: AlertLevel
    message: str = ""
    enabled: bool = True
    cooldown_seconds: int = 60
    
    def check(self, usage_percent: float) -> bool:
        """检查是否触发告警"""
        if not self.enabled:
            return False
        
        if self.comparison == "gt":
            triggered = usage_percent > self.threshold
        elif self.comparison == "lt":
            triggered = usage_percent < self.threshold
        elif self.comparison == "gte":
            triggered = usage_percent >= self.threshold
        elif self.comparison == "lte":
            triggered = usage_percent <= self.threshold
        elif self.comparison == "eq":
            triggered = usage_percent == self.threshold
        else:
            triggered = False
        
        return triggered


class ResourceMonitor:
    """
    资源监控器主类
    
    提供系统资源的实时监控功能，支持：
    - CPU使用率监控
    - 内存使用率监控
    - 磁盘使用率监控
    - 网络流量监控
    - 自定义告警规则
    - 历史数据存储
    """
    
    def __init__(self, history_size: int = 1000):
        """
        初始化资源监控器
        
        Args:
            history_size: 每个资源的历史数据最大保存条数
        """
        self.history_size = history_size
        self._history: Dict[ResourceType, deque] = {
            rt: deque(maxlen=history_size) for rt in ResourceType
        }
        self._alert_rules: List[AlertRule] = []
        self._alert_callbacks: List[Callable[[AlertRule, ResourceSnapshot], None]] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_alert_time: Dict[str, datetime] = {}
        self._custom_metrics: Dict[str, Callable[[], float]] = {}
        
    def start(self, interval: float = 1.0):
        """
        启动后台监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop(self):
        """停止后台监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
    
    def _monitor_loop(self, interval: float):
        """后台监控循环"""
        while self._monitoring:
            try:
                self.collect_all()
                self._check_alerts()
            except Exception:
                pass
            time.sleep(interval)
    
    def collect_all(self) -> Dict[ResourceType, ResourceSnapshot]:
        """
        收集所有资源的使用情况
        
        Returns:
            包含各资源快照的字典
        """
        snapshots = {}
        
        # CPU监控
        snapshots[ResourceType.CPU] = self.get_cpu_usage()
        
        # 内存监控
        snapshots[ResourceType.MEMORY] = self.get_memory_usage()
        
        # 磁盘监控
        snapshots[ResourceType.DISK] = self.get_disk_usage()
        
        # 网络监控
        snapshots[ResourceType.NETWORK] = self.get_network_usage()
        
        # 进程监控
        snapshots[ResourceType.PROCESS] = self.get_process_usage()
        
        return snapshots
    
    def get_cpu_usage(self) -> ResourceSnapshot:
        """
        获取CPU使用率
        
        Returns:
            CPU使用率快照
        """
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        details = {
            "cpu_count": cpu_count,
            "cpu_percent": cpu_percent
        }
        if cpu_freq:
            details["cpu_freq_mhz"] = cpu_freq.current
        
        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow(),
            resource_type=ResourceType.CPU,
            usage_percent=cpu_percent,
            details=details
        )
        
        self._add_to_history(snapshot)
        return snapshot
    
    def get_memory_usage(self) -> ResourceSnapshot:
        """
        获取内存使用率
        
        Returns:
            内存使用率快照
        """
        mem = psutil.virtual_memory()
        
        details = {
            "total_bytes": mem.total,
            "used_bytes": mem.used,
            "available_bytes": mem.available,
            "percent": mem.percent
        }
        
        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow(),
            resource_type=ResourceType.MEMORY,
            usage_percent=mem.percent,
            details=details
        )
        
        self._add_to_history(snapshot)
        return snapshot
    
    def get_disk_usage(self, path: Optional[str] = None) -> ResourceSnapshot:
        """
        获取磁盘使用率
        
        Args:
            path: 可选的磁盘路径，默认使用根目录
            
        Returns:
            磁盘使用率快照
        """
        if path is None:
            path = os.path.expanduser("~")
        
        disk = psutil.disk_usage(path)
        
        details = {
            "path": path,
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "percent": disk.percent
        }
        
        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow(),
            resource_type=ResourceType.DISK,
            usage_percent=disk.percent,
            details=details
        )
        
        self._add_to_history(snapshot)
        return snapshot
    
    def get_network_usage(self) -> ResourceSnapshot:
        """
        获取网络使用率（基于连接数）
        
        Returns:
            网络使用快照
        """
        connections = psutil.net_connections()
        io_counters = psutil.net_io_counters()
        
        # 使用连接数作为网络负载的近似指标
        active_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
        
        details = {
            "total_connections": len(connections),
            "active_connections": active_connections,
            "bytes_sent": io_counters.bytes_sent,
            "bytes_recv": io_counters.bytes_recv,
            "packets_sent": io_counters.packets_sent,
            "packets_recv": io_counters.packets_recv
        }
        
        # 使用活动连接数作为负载百分比（假设1000为最大负载）
        network_percent = min(100, (active_connections / 1000) * 100)
        
        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow(),
            resource_type=ResourceType.NETWORK,
            usage_percent=network_percent,
            details=details
        )
        
        self._add_to_history(snapshot)
        return snapshot
    
    def get_process_usage(self) -> ResourceSnapshot:
        """
        获取当前进程的资源使用情况
        
        Returns:
            进程资源使用快照
        """
        try:
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=None)
            memory_info = process.memory_info()
            num_threads = process.num_threads()
            num_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_rss_bytes": memory_info.rss,
                "memory_vms_bytes": memory_info.vms,
                "thread_count": num_threads,
                "fd_count": num_fds
            }
            
            snapshot = ResourceSnapshot(
                timestamp=datetime.utcnow(),
                resource_type=ResourceType.PROCESS,
                usage_percent=memory_info.rss / (1024 * 1024),  # MB作为百分比基准
                details=details
            )
            
            self._add_to_history(snapshot)
            return snapshot
        except Exception:
            return ResourceSnapshot(
                timestamp=datetime.utcnow(),
                resource_type=ResourceType.PROCESS,
                usage_percent=0,
                details={"error": "Failed to get process info"}
            )
    
    def get_thread_count(self) -> ResourceSnapshot:
        """
        获取线程数量
        
        Returns:
            线程数快照
        """
        try:
            process = psutil.Process()
            thread_count = process.num_threads()
            
            snapshot = ResourceSnapshot(
                timestamp=datetime.utcnow(),
                resource_type=ResourceType.THREAD,
                usage_percent=thread_count,
                details={"thread_count": thread_count}
            )
            
            self._add_to_history(snapshot)
            return snapshot
        except Exception:
            return ResourceSnapshot(
                timestamp=datetime.utcnow(),
                resource_type=ResourceType.THREAD,
                usage_percent=0,
                details={"error": "Failed to get thread count"}
            )
    
    def _add_to_history(self, snapshot: ResourceSnapshot):
        """添加快照到历史记录"""
        with self._lock:
            self._history[snapshot.resource_type].append(snapshot)
    
    def get_history(
        self, 
        resource_type: ResourceType, 
        limit: Optional[int] = None
    ) -> List[ResourceSnapshot]:
        """
        获取资源使用历史
        
        Args:
            resource_type: 资源类型
            limit: 返回的最大记录数
            
        Returns:
            资源使用历史记录列表
        """
        with self._lock:
            history = list(self._history[resource_type])
        
        if limit and limit > 0:
            history = history[-limit:]
        
        return history
    
    def get_average_usage(
        self, 
        resource_type: ResourceType, 
        window: int = 10
    ) -> float:
        """
        计算资源使用率平均值
        
        Args:
            resource_type: 资源类型
            window: 计算窗口大小
            
        Returns:
            平均使用率
        """
        history = self.get_history(resource_type, window)
        if not history:
            return 0.0
        
        return sum(s.usage_percent for s in history) / len(history)
    
    def get_trend(
        self, 
        resource_type: ResourceType, 
        window: int = 10
    ) -> str:
        """
        获取资源使用趋势
        
        Args:
            resource_type: 资源类型
            window: 分析窗口大小
            
        Returns:
            趋势方向: "up", "down", "stable"
        """
        history = self.get_history(resource_type, window)
        if len(history) < 3:
            return "stable"
        
        first_half = history[:len(history)//2]
        second_half = history[len(history)//2:]
        
        first_avg = sum(s.usage_percent for s in first_half) / len(first_half)
        second_avg = sum(s.usage_percent for s in second_half) / len(second_half)
        
        diff = second_avg - first_avg
        if diff > 2:
            return "up"
        elif diff < -2:
            return "down"
        else:
            return "stable"
    
    def add_alert_rule(self, rule: AlertRule):
        """
        添加告警规则
        
        Args:
            rule: 告警规则
        """
        self._alert_rules.append(rule)
    
    def remove_alert_rule(self, resource_type: ResourceType, level: AlertLevel):
        """移除指定资源类型和级别的告警规则"""
        self._alert_rules = [
            r for r in self._alert_rules 
            if not (r.resource_type == resource_type and r.level == level)
        ]
    
    def on_alert(self, callback: Callable[[AlertRule, ResourceSnapshot], None]):
        """
        注册告警回调函数
        
        Args:
            callback: 告警触发时的回调函数
        """
        self._alert_callbacks.append(callback)
    
    def _check_alerts(self):
        """检查所有告警规则"""
        current_time = datetime.utcnow()
        
        for rule in self._alert_rules:
            # 检查冷却时间
            alert_key = f"{rule.resource_type.value}_{rule.level.value}"
            last_time = self._last_alert_time.get(alert_key)
            if last_time:
                cooldown = (current_time - last_time).total_seconds()
                if cooldown < rule.cooldown_seconds:
                    continue
            
            # 获取当前使用率
            history = self.get_history(rule.resource_type, 1)
            if not history:
                continue
            
            current_usage = history[-1].usage_percent
            
            if rule.check(current_usage):
                self._trigger_alert(rule, history[-1])
                self._last_alert_time[alert_key] = current_time
    
    def _trigger_alert(self, rule: AlertRule, snapshot: ResourceSnapshot):
        """触发告警"""
        for callback in self._alert_callbacks:
            try:
                callback(rule, snapshot)
            except Exception:
                pass
    
    def register_custom_metric(
        self, 
        name: str, 
        callback: Callable[[], float]
    ):
        """
        注册自定义指标
        
        Args:
            name: 指标名称
            callback: 获取指标值的回调函数
        """
        self._custom_metrics[name] = callback
    
    def get_custom_metric(self, name: str) -> Optional[float]:
        """
        获取自定义指标值
        
        Args:
            name: 指标名称
            
        Returns:
            指标值，不存在返回None
        """
        callback = self._custom_metrics.get(name)
        if callback:
            return callback()
        return None
    
    def get_all_metrics(self) -> Dict[str, float]:
        """
        获取所有当前指标值
        
        Returns:
            包含所有指标值的字典
        """
        metrics = {}
        
        # 标准指标
        cpu = self.get_cpu_usage()
        mem = self.get_memory_usage()
        disk = self.get_disk_usage()
        network = self.get_network_usage()
        
        metrics["cpu_percent"] = cpu.usage_percent
        metrics["memory_percent"] = mem.usage_percent
        metrics["disk_percent"] = disk.usage_percent
        metrics["network_percent"] = network.usage_percent
        
        # 自定义指标
        for name, callback in self._custom_metrics.items():
            try:
                metrics[name] = callback()
            except Exception:
                metrics[name] = 0.0
        
        return metrics
    
    def is_healthy(self) -> bool:
        """
        检查系统是否健康（所有资源使用率低于阈值）
        
        Returns:
            是否健康
        """
        metrics = self.get_all_metrics()
        
        # 默认健康阈值
        healthy_thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 90.0,
            "disk_percent": 95.0,
            "network_percent": 80.0
        }
        
        for metric, value in metrics.items():
            if metric in healthy_thresholds:
                if value >= healthy_thresholds[metric]:
                    return False
        
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取资源监控摘要
        
        Returns:
            包含监控摘要的字典
        """
        return {
            "healthy": self.is_healthy(),
            "metrics": self.get_all_metrics(),
            "trends": {
                rt.value: self.get_trend(rt) for rt in ResourceType
            },
            "alert_rules_count": len(self._alert_rules),
            "monitoring": self._monitoring
        }


# 默认资源监控器实例
_default_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> ResourceMonitor:
    """获取默认资源监控器实例"""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = ResourceMonitor()
    return _default_monitor


def create_resource_monitor(history_size: int = 1000) -> ResourceMonitor:
    """
    创建资源监控器实例
    
    Args:
        history_size: 历史数据保存大小
        
    Returns:
        资源监控器实例
    """
    return ResourceMonitor(history_size)
