"""测试指标收集器"""

import pytest


class TestMetricsCollectorExists:
    """测试指标收集器存在"""
    
    def test_import(self):
        from agent_os_kernel.core.metrics import MetricsCollector
        assert MetricsCollector is not None
    
    def test_type_import(self):
        from agent_os_kernel.core.metrics import MetricType
        assert MetricType is not None
