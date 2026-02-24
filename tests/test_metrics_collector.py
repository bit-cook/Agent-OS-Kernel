# -*- coding: utf-8 -*-
"""
Tests for Metrics Collector - Agent-OS-Kernel 指标收集器测试
"""

import time
import pytest
import threading
from agent_os_kernel.core.metrics_collector import (
    MetricType,
    ExportFormat,
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    MetricSample,
    create_metrics_registry,
    create_counter,
    create_gauge,
    create_histogram,
    counter,
    gauge,
    histogram,
    export_metrics,
    get_default_registry,
)


class TestCounter:
    """计数器测试"""
    
    def test_counter_basic(self):
        """测试基本计数器功能"""
        c = Counter("test_counter", "测试计数器")
        
        c.inc()
        assert c.value() == 1.0
        
        c.inc(5)
        assert c.value() == 6.0
        
        c.dec(2)
        assert c.value() == 4.0
    
    def test_counter_with_labels(self):
        """测试带标签的计数器"""
        c = Counter("test_counter_labels", "带标签的计数器", labels=["method", "status"])
        
        c.inc(label_values={"method": "GET", "status": "200"})
        c.inc(label_values={"method": "GET", "status": "200"})
        c.inc(label_values={"method": "POST", "status": "201"})
        
        assert c.value({"method": "GET", "status": "200"}) == 2.0
        assert c.value({"method": "POST", "status": "201"}) == 1.0
    
    def test_counter_non_negative(self):
        """测试计数器不能为负"""
        c = Counter("test_non_negative", "非负计数器")
        
        c.inc(5)
        c.dec(10)  # 尝试减少超过当前值
        
        assert c.value() == 0.0  # 应该保持为0
    
    def test_counter_reset(self):
        """测试计数器重置"""
        c = Counter("test_reset", "可重置计数器")
        
        c.inc(10)
        c.reset()
        
        assert c.value() == 0.0
    
    def test_counter_reset_with_labels(self):
        """测试带标签的计数器重置"""
        c = Counter("test_reset_labels", "带标签的可重置计数器", labels=["env"])
        
        c.inc(5, label_values={"env": "prod"})
        c.inc(3, label_values={"env": "dev"})
        
        c.reset(label_values={"env": "prod"})
        
        assert c.value({"env": "prod"}) == 0.0
        assert c.value({"env": "dev"}) == 3.0
    
    def test_counter_samples(self):
        """测试计数器样本生成"""
        c = Counter("test_samples", "样本测试计数器", labels=["type"])
        c.inc(2, label_values={"type": "A"})
        c.inc(3, label_values={"type": "B"})
        
        samples = c.samples()
        
        assert len(samples) == 2
        sample_map = {s.labels.get("type"): s.value for s in samples}
        assert sample_map.get("A") == 2.0
        assert sample_map.get("B") == 3.0
    
    def test_counter_thread_safety(self):
        """测试计数器线程安全"""
        c = Counter("test_thread_safe", "线程安全计数器")
        
        def increment():
            for _ in range(100):
                c.inc()
        
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 10个线程 * 100次 = 1000
        assert c.value() == 1000.0


class TestGauge:
    """仪表盘测试"""
    
    def test_gauge_basic(self):
        """测试基本仪表盘功能"""
        g = Gauge("test_gauge", "测试仪表盘")
        
        g.set(100)
        assert g.value() == 100.0
        
        g.set(50)
        assert g.value() == 50.0
    
    def test_gauge_inc_dec(self):
        """测试仪表盘增减"""
        g = Gauge("test_gauge_inc_dec", "增减测试仪表盘")
        
        g.set(10)
        g.inc(5)
        assert g.value() == 15.0
        
        g.dec(3)
        assert g.value() == 12.0
    
    def test_gauge_with_labels(self):
        """测试带标签的仪表盘"""
        g = Gauge("test_gauge_labels", "带标签的仪表盘", labels=["host"])
        
        g.set(80, label_values={"host": "server1"})
        g.set(90, label_values={"host": "server2"})
        
        assert g.value({"host": "server1"}) == 80.0
        assert g.value({"host": "server2"}) == 90.0
    
    def test_gauge_reset(self):
        """测试仪表盘重置"""
        g = Gauge("test_gauge_reset", "可重置仪表盘")
        
        g.set(100)
        g.reset()
        
        assert g.value() == 0.0
    
    def test_gauge_samples(self):
        """测试仪表盘样本生成"""
        g = Gauge("test_gauge_samples", "样本测试仪表盘", labels=["region"])
        g.set(75, label_values={"region": "us-east"})
        g.set(85, label_values={"region": "us-west"})
        
        samples = g.samples()
        
        assert len(samples) == 2
        sample_map = {s.labels.get("region"): s.value for s in samples}
        assert sample_map.get("us-east") == 75.0
        assert sample_map.get("us-west") == 85.0


class TestHistogram:
    """直方图测试"""
    
    def test_histogram_basic(self):
        """测试基本直方图功能"""
        h = Histogram("test_histogram", "测试直方图")
        
        h.observe(0.1)
        h.observe(0.2)
        h.observe(0.3)
        
        assert h.get_count() == 3
        assert h.get_sum() == 0.6
        
        percentiles = h.get_percentiles([0.5, 0.9])
        assert percentiles[0.5] == 0.2
        assert percentiles[0.9] == 0.3
    
    def test_histogram_with_labels(self):
        """测试带标签的直方图"""
        h = Histogram("test_histogram_labels", "带标签的直方图", labels=["operation"])
        
        h.observe(0.1, label_values={"operation": "read"})
        h.observe(0.2, label_values={"operation": "read"})
        h.observe(0.5, label_values={"operation": "write"})
        
        assert h.get_count({"operation": "read"}) == 2
        assert h.get_count({"operation": "write"}) == 1
        assert h.get_sum({"operation": "read"}) == 0.3
        assert h.get_sum({"operation": "write"}) == 0.5
    
    def test_histogram_bucket_counts(self):
        """测试直方图bucket计数"""
        h = Histogram("test_histogram_buckets", "Bucket测试直方图", buckets=(0.1, 0.5, 1.0, float('inf')))
        
        h.observe(0.05)  # bucket: 0.1
        h.observe(0.3)   # bucket: 0.5
        h.observe(0.8)   # bucket: 1.0
        h.observe(2.0)   # bucket: inf
        
        bucket_counts = h.get_bucket_counts()
        
        assert bucket_counts[0.1] == 1
        assert bucket_counts[0.5] == 2  # 0.05 + 0.3
        assert bucket_counts[1.0] == 3  # 0.05 + 0.3 + 0.8
        assert bucket_counts[float('inf')] == 4  # 所有值
    
    def test_histogram_percentiles(self):
        """测试直方图百分位数计算"""
        h = Histogram("test_histogram_percentiles", "百分位数测试直方图")
        
        # 添加100个观察值,值从1到100
        for i in range(1, 101):
            h.observe(float(i))
        
        percentiles = h.get_percentiles([0.5, 0.9, 0.95, 0.99])
        
        assert percentiles[0.5] == 50.0 or percentiles[0.5] == 51.0  # P50
        assert 90.0 <= percentiles[0.9] <= 91.0  # P90
        assert 95.0 <= percentiles[0.95] <= 96.0  # P95
        assert 99.0 <= percentiles[0.99] <= 100.0  # P99
    
    def test_histogram_reset(self):
        """测试直方图重置"""
        h = Histogram("test_histogram_reset", "可重置直方图")
        
        for i in range(10):
            h.observe(float(i))
        
        h.reset()
        
        assert h.get_count() == 0
        assert h.get_sum() == 0.0
    
    def test_histogram_samples(self):
        """测试直方图样本生成"""
        h = Histogram("test_histogram_samples", "样本测试直方图", buckets=(0.5, 1.0, float('inf')))
        
        h.observe(0.3)
        h.observe(0.7)
        h.observe(2.0)
        
        samples = h.samples()
        
        # 应该包含: _sum, _count, 和3个bucket
        assert len(samples) == 5
        
        sample_names = [s.name for s in samples]
        assert "test_histogram_samples_sum" in sample_names
        assert "test_histogram_samples_count" in sample_names
        assert "test_histogram_samples_bucket" in sample_names
    
    def test_histogram_empty(self):
        """测试空直方图"""
        h = Histogram("test_empty_histogram", "空直方图")
        
        assert h.get_count() == 0
        assert h.get_sum() == 0.0
        assert h.get_percentiles([0.5]) == {}


class TestMetricsRegistry:
    """指标注册表测试"""
    
    def test_registry_create_counter(self):
        """测试注册表创建计数器"""
        registry = create_metrics_registry("test")
        
        c = registry.create_counter("requests", "请求计数")
        
        assert c.name == "requests"
        assert registry.get_counter("requests") is c
    
    def test_registry_create_gauge(self):
        """测试注册表创建仪表盘"""
        registry = create_metrics_registry("test")
        
        g = registry.create_gauge("memory_usage", "内存使用")
        
        assert g.name == "memory_usage"
        assert registry.get_gauge("memory_usage") is g
    
    def test_registry_create_histogram(self):
        """测试注册表创建直方图"""
        registry = create_metrics_registry("test")
        
        h = registry.create_histogram("request_latency", "请求延迟")
        
        assert h.name == "request_latency"
        assert registry.get_histogram("request_latency") is h
    
    def test_registry_duplicate_counter(self):
        """测试重复创建计数器"""
        registry = create_metrics_registry("test")
        
        registry.create_counter("dup", "重复计数器")
        
        with pytest.raises(ValueError):
            registry.create_counter("dup", "重复计数器")
    
    def test_registry_get_or_create(self):
        """测试获取或创建"""
        registry = create_metrics_registry("test")
        
        c1 = registry.counter("my_counter")
        c2 = registry.counter("my_counter")
        
        assert c1 is c2
    
    def test_registry_samples(self):
        """测试收集样本"""
        registry = create_metrics_registry("test")
        
        registry.create_counter("c1").inc()
        registry.create_gauge("g1").set(100)
        registry.create_histogram("h1").observe(0.5)
        
        samples = registry.samples()
        
        # 1 counter + 1 gauge + 3 histogram samples (_sum, _count, _bucket)
        assert len(samples) >= 5
    
    def test_registry_reset(self):
        """测试注册表重置"""
        registry = create_metrics_registry("test")
        
        c = registry.create_counter("c1")
        c.inc(10)
        
        g = registry.create_gauge("g1")
        g.set(100)
        
        h = registry.create_histogram("h1")
        h.observe(0.5)
        
        registry.reset()
        
        assert c.value() == 0.0
        assert g.value() == 0.0
        assert h.get_count() == 0
    
    def test_registry_list_metrics(self):
        """测试列出指标"""
        registry = create_metrics_registry("test")
        
        registry.create_counter("c1")
        registry.create_counter("c2")
        registry.create_gauge("g1")
        registry.create_histogram("h1")
        
        metrics = registry.list_metrics()
        
        assert len(metrics["counters"]) == 2
        assert len(metrics["gauges"]) == 1
        assert len(metrics["histograms"]) == 1


class TestMetricsExport:
    """指标导出测试"""
    
    def test_export_json(self):
        """测试JSON导出"""
        registry = create_metrics_registry("export_test")
        registry.create_counter("requests", "请求计数").inc(100)
        
        json_output = registry.export(ExportFormat.JSON)
        
        assert "requests" in json_output
        assert "100" in json_output
        assert '"type": "counter"' in json_output
    
    def test_export_prometheus(self):
        """测试Prometheus导出"""
        registry = create_metrics_registry("export_test")
        registry.create_gauge("cpu_usage", "CPU使用率").set(75.5)
        
        prom_output = registry.export(ExportFormat.PROMETHEUS)
        
        assert "cpu_usage" in prom_output
        assert "GAUGE" in prom_output
        assert "75.5" in prom_output
    
    def test_export_text(self):
        """测试文本导出"""
        registry = create_metrics_registry("export_test")
        registry.create_histogram("latency", "延迟").observe(0.1)
        
        text_output = registry.export(ExportFormat.TEXT)
        
        assert "latency" in text_output
        assert "HISTOGRAM" in text_output
    
    def test_export_with_labels(self):
        """测试带标签的导出"""
        registry = create_metrics_registry("export_test")
        c = registry.create_counter("requests", "请求计数", labels=["method"])
        c.inc(label_values={"method": "GET"})
        
        json_output = registry.export(ExportFormat.JSON)
        prom_output = registry.export(ExportFormat.PROMETHEUS)
        
        assert "method" in json_output
        assert "GET" in json_output
        assert 'method="GET"' in prom_output


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_create_functions(self):
        """测试创建函数"""
        c = create_counter("test_c", "测试")
        g = create_gauge("test_g", "测试")
        h = create_histogram("test_h", "测试")
        
        assert c.name == "test_c"
        assert g.name == "test_g"
        assert h.name == "test_h"
    
    def test_get_or_create_functions(self):
        """测试获取或创建函数"""
        # 重置默认注册表
        global _default_registry
        _default_registry = None
        
        c1 = counter("convenient_counter")
        c2 = counter("convenient_counter")
        
        assert c1 is c2
    
    def test_export_default(self):
        """测试默认导出"""
        # 重置默认注册表
        global _default_registry
        _default_registry = None
        
        create_counter("export_test_c").inc(42)
        
        output = export_metrics(ExportFormat.JSON)
        
        assert "export_test_c" in output
        assert "42" in output
    
    def test_get_default_registry(self):
        """测试获取默认注册表"""
        # 重置默认注册表
        global _default_registry
        _default_registry = None
        
        r1 = get_default_registry()
        r2 = get_default_registry()
        
        assert r1 is r2
