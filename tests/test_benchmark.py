# -*- coding: utf-8 -*-
"""
Tests for Performance Benchmark Tools - Agent-OS-Kernel 性能基准测试工具测试
"""

import time
import threading
import pytest
from agent_os_kernel.core.benchmark import (
    LatencyResult,
    ThroughputResult,
    ResourceUsage,
    LatencyBenchmark,
    ThroughputBenchmark,
    ResourceMonitor,
    PerformanceReport,
    PerformanceBenchmark,
    measure_latency,
    measure_throughput,
    monitor_resources,
)


class TestLatencyMeasurement:
    """延迟测量测试"""
    
    def test_latency_measurement_basic(self):
        """测试基本延迟测量"""
        def sample_function():
            time.sleep(0.001)  # 1ms
        
        benchmark = LatencyBenchmark(warmup_iterations=0)
        result = benchmark.measure(sample_function, iterations=10, warmup=False)
        
        assert isinstance(result, LatencyResult)
        assert result.iterations == 10
        assert result.mean_ms > 0.5
        assert result.mean_ms < 50.0  # 应该小于50ms
    
    def test_latency_measurement_with_args(self):
        """测试带参数的延迟测量"""
        def add_function(a, b):
            return a + b
        
        benchmark = LatencyBenchmark(warmup_iterations=0)
        result = benchmark.measure(
            add_function, iterations=5, warmup=False, a=1, b=2
        )
        
        assert result.iterations == 5
        assert result.mean_ms < 1.0  # 简单函数应该非常快
    
    def test_latency_measurement_warmup(self):
        """测试预热功能"""
        def sample_function():
            time.sleep(0.0005)
        
        benchmark = LatencyBenchmark(warmup_iterations=5)
        result = benchmark.measure(sample_function, iterations=10, warmup=True)
        
        assert result.iterations == 10
    
    def test_latency_statistics(self):
        """测试统计计算"""
        def fast_function():
            return 1 + 1
        
        benchmark = LatencyBenchmark(warmup_iterations=0)
        result = benchmark.measure(fast_function, iterations=20, warmup=False)
        
        assert result.min_ms >= 0
        assert result.max_ms >= result.min_ms
        assert result.median_ms >= 0
        assert result.p95_ms >= result.median_ms
        assert result.std_dev_ms >= 0
    
    def test_measure_latency_convenience_function(self):
        """测试便捷函数"""
        def test_func():
            return sum(range(100))
        
        result = measure_latency(test_func, iterations=5, warmup=False)
        
        assert isinstance(result, LatencyResult)
        assert result.iterations == 5


class TestThroughputMeasurement:
    """吞吐量测量测试"""
    
    def test_throughput_basic(self):
        """测试基本吞吐量测量"""
        def sample_operation():
            time.sleep(0.001)
        
        benchmark = ThroughputBenchmark(max_workers=2)
        result = benchmark.measure(
            sample_operation, total_operations=10, concurrency=1
        )
        
        assert isinstance(result, ThroughputResult)
        assert result.total_operations == 10
        assert result.success_count == 10
        assert result.error_count == 0
    
    def test_throughput_with_errors(self):
        """测试包含错误的吞吐量测量"""
        call_count = {"count": 0}
        
        def sometimes_fails():
            call_count["count"] += 1
            if call_count["count"] <= 3:
                raise ValueError("Test error")
            return True
        
        benchmark = ThroughputBenchmark()
        result = benchmark.measure(sometimes_fails, total_operations=5)
        
        assert result.total_operations == 5
        assert result.success_count == 2
        assert result.error_count == 3
    
    def test_measure_throughput_convenience_function(self):
        """测试便捷函数"""
        def simple_func():
            return sum(range(10))
        
        result = measure_throughput(
            simple_func, total_operations=20, concurrency=1
        )
        
        assert isinstance(result, ThroughputResult)
        assert result.total_operations == 20


class TestResourceMonitoring:
    """资源监控测试"""
    
    def test_resource_usage_capture(self):
        """测试资源使用捕获"""
        usage = ResourceUsage.capture()
        
        assert isinstance(usage, ResourceUsage)
        assert usage.timestamp != ""
        assert usage.memory_mb >= 0
        assert usage.cpu_percent >= 0
    
    def test_resource_monitor_start_stop(self):
        """测试监控器启动和停止"""
        monitor = ResourceMonitor(sample_interval=0.05)
        
        # 开始监控
        monitor.start(duration_seconds=0.3)
        
        # 停止并获取数据
        samples = monitor.stop()
        
        assert len(samples) > 0
        for sample in samples:
            assert isinstance(sample, ResourceUsage)
    
    def test_resource_monitor_stats(self):
        """测试资源统计计算"""
        monitor = ResourceMonitor(sample_interval=0.05)
        
        monitor.start(duration_seconds=0.2)
        stats = monitor.get_stats()
        
        assert "cpu_percent" in stats
        assert "memory_mb" in stats
        assert "samples_count" in stats
    
    def test_monitor_resources_convenience_function(self):
        """测试便捷函数"""
        results = monitor_resources(duration_seconds=0.1, interval=0.02)
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, ResourceUsage) for r in results)


class TestPerformanceReport:
    """性能报告测试"""
    
    def test_report_creation(self):
        """测试报告创建"""
        report = PerformanceReport("Test Report")
        
        assert report.title == "Test Report"
        assert report.timestamp != ""
        assert len(report.sections) == 0
    
    def test_add_latency_result(self):
        """测试添加延迟结果"""
        report = PerformanceReport("Test Report")
        
        latency_result = LatencyResult(
            min_ms=1.0,
            max_ms=5.0,
            mean_ms=2.5,
            median_ms=2.4,
            p95_ms=4.5,
            p99_ms=4.9,
            std_dev_ms=0.5,
            iterations=100
        )
        
        report.add_latency_result("Test Latency", latency_result)
        
        assert len(report.sections) == 1
        assert report.sections[0]["name"] == "Test Latency"
    
    def test_add_throughput_result(self):
        """测试添加吞吐量结果"""
        report = PerformanceReport("Test Report")
        
        throughput_result = ThroughputResult(
            total_operations=1000,
            total_time_ms=500.0,
            operations_per_second=2000.0,
            avg_latency_ms=0.5,
            min_latency_ms=0.1,
            max_latency_ms=1.0,
            success_count=1000,
            error_count=0
        )
        
        report.add_throughput_result("Test Throughput", throughput_result)
        
        assert len(report.sections) == 1
        assert report.sections[0]["name"] == "Test Throughput"
    
    def test_generate_text_report(self):
        """测试生成文本报告"""
        report = PerformanceReport("Test Report")
        
        latency_result = LatencyResult(
            min_ms=1.0, max_ms=5.0, mean_ms=2.5,
            median_ms=2.4, p95_ms=4.5, p99_ms=4.9,
            std_dev_ms=0.5, iterations=100
        )
        
        report.add_latency_result("Test", latency_result)
        
        text = report.generate_text()
        
        assert "Test Report" in text
        assert "Test" in text
        assert "mean_ms" in text
        assert "2.5" in text
    
    def test_generate_json_report(self):
        """测试生成JSON报告"""
        report = PerformanceReport("Test Report")
        
        latency_result = LatencyResult(
            min_ms=1.0, max_ms=5.0, mean_ms=2.5,
            median_ms=2.4, p95_ms=4.5, p99_ms=4.9,
            std_dev_ms=0.5, iterations=100
        )
        
        report.add_latency_result("Test", latency_result)
        
        json_str = report.generate_json()
        
        # 应该可以解析为JSON
        import json
        data = json.loads(json_str)
        
        assert data["title"] == "Test Report"
        assert len(data["sections"]) == 1
    
    def test_save_report(self):
        """测试保存报告"""
        import tempfile
        import os
        
        report = PerformanceReport("Test Report")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            filepath = f.name
        
        try:
            report.save(filepath, format="text")
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            assert "Test Report" in content
        finally:
            os.unlink(filepath)


class TestPerformanceBenchmark:
    """综合性能基准测试"""
    
    def test_benchmark_function(self):
        """测试函数基准测试"""
        def slow_function():
            time.sleep(0.01)
            return sum(range(100))
        
        benchmark = PerformanceBenchmark(iterations=5)
        result = benchmark.benchmark_function("slow_test", slow_function)
        
        assert result["name"] == "slow_test"
        assert "latency" in result
        assert "throughput" in result
    
    def test_run_comparison(self):
        """测试对比测试"""
        def fast_func():
            return sum(range(10))
        
        def slow_func():
            time.sleep(0.001)
            return sum(range(100))
        
        benchmarks = {
            "fast": fast_func,
            "slow": slow_func,
        }
        
        benchmark = PerformanceBenchmark(iterations=10)
        result = benchmark.run_comparison(benchmarks)
        
        assert "results" in result
        assert "best_latency" in result
        assert result["best_latency"]["name"] == "fast"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
