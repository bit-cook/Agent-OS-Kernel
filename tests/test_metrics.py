# -*- coding: utf-8 -*-
"""测试指标收集器"""

import pytest
import asyncio
from agent_os_kernel.core.metrics import MetricsCollector, Metric, MetricType


class TestMetricsCollector:
    """MetricsCollector 测试类"""
    
    @pytest.fixture
    def collector(self):
        """创建指标收集器"""
        return MetricsCollector()
    
    def test_counter(self, collector):
        """测试计数器"""
        collector.counter("test_counter", 1)
        collector.counter("test_counter", 2)
        
        assert collector.get_value("test_counter") == 3
    
    def test_gauge(self, collector):
        """测试仪表"""
        collector.gauge("test_gauge", 100)
        collector.gauge("test_gauge", 200)
        
        assert collector.get_value("test_gauge") == 200
    
    def test_histogram(self, collector):
        """测试直方图"""
        collector.histogram("test_histogram", 10)
        collector.histogram("test_histogram", 20)
        collector.histogram("test_histogram", 30)
        
        stats = collector.get_histogram_stats("test_histogram")
        assert stats["count"] == 3
        assert stats["sum"] == 60
    
    def test_get_stats(self, collector):
        """测试统计"""
        collector.counter("test", 1)
        collector.gauge("test_gauge", 100)
        
        stats = collector.get_stats()
        
        assert "metrics_count" in stats
        assert "total_samples" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
