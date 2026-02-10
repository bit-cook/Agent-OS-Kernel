# -*- coding: utf-8 -*-
"""测试监控系统"""

import pytest
from agent_os_kernel.core.monitoring import Monitor, HealthStatus


class TestMonitor:
    """Monitor 测试类"""
    
    @pytest.fixture
    def monitor(self):
        """创建监控器"""
        return Monitor(name="test")
    
    def test_initialization(self, monitor):
        """测试初始化"""
        assert monitor.name == "test"
        assert len(monitor._health_checks) >= 3  # 默认检查
    
    def test_record_metric(self, monitor):
        """测试记录指标"""
        monitor.record_metric("test_metric", 100)
        monitor.record_metric("test_metric", 200, labels={"type": "demo"})
        
        metrics = monitor.get_metrics("test_metric")
        assert len(metrics) == 2
    
    def test_get_overall_status(self, monitor):
        """测试整体状态"""
        status = monitor.get_overall_status()
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
    
    def test_get_system_info(self, monitor):
        """测试系统信息"""
        info = monitor.get_system_info()
        
        assert "hostname" in info
        assert "cpu_count" in info
        assert "memory_total" in info
    
    def test_get_stats(self, monitor):
        """测试统计"""
        stats = monitor.get_stats()
        
        assert "name" in stats
        assert "health_checks_count" in stats
        assert "metrics_count" in stats
        assert "overall_status" in stats
    
    def test_alerts(self, monitor):
        """测试告警"""
        alerts = []
        
        def callback(alert):
            alerts.append(alert)
        
        monitor.on_alert(callback)
        monitor.trigger_alert("test", "测试告警", severity="info")
        
        assert len(alerts) == 1
        assert alerts[0]["name"] == "test"
    
    def test_clear_alerts(self, monitor):
        """测试清除告警"""
        monitor.trigger_alert("test1", "告警1")
        monitor.trigger_alert("test2", "告警2")
        
        assert len(monitor.get_alerts()) == 2
        
        monitor.clear_alerts()
        
        assert len(monitor.get_alerts()) == 0
