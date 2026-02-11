# -*- coding: utf-8 -*-
"""
Performance Benchmark Tools - Agent-OS-Kernel 性能基准测试工具

提供延迟测量、吞吐量测量、资源监控和性能报告生成功能。
"""

import time
import statistics
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime
import json


@dataclass
class LatencyResult:
    """延迟测量结果"""
    min_ms: float = 0.0
    max_ms: float = 0.0
    mean_ms: float = 0.0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    std_dev_ms: float = 0.0
    iterations: int = 0
    samples: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "std_dev_ms": self.std_dev_ms,
            "iterations": self.iterations,
        }


@dataclass
class ThroughputResult:
    """吞吐量测量结果"""
    total_operations: int = 0
    total_time_ms: float = 0.0
    operations_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_operations": self.total_operations,
            "total_time_ms": self.total_time_ms,
            "operations_per_second": self.operations_per_second,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (
                self.success_count / self.total_operations * 100 
                if self.total_operations > 0 else 0
            ),
        }


@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    thread_count: int = 0
    timestamp: str = ""
    
    @classmethod
    def capture(cls, process: Optional[psutil.Process] = None) -> "ResourceUsage":
        """捕获当前资源使用情况"""
        if process is None:
            process = psutil.Process()
        
        try:
            io_counters = process.io_counters()
            net_counters = process.net_io_counters()
        except (AttributeError, psutil.AccessDenied):
            io_counters = None
            net_counters = None
        
        return cls(
            cpu_percent=process.cpu_percent(),
            memory_mb=process.memory_info().rss / (1024 * 1024),
            memory_percent=process.memory_percent(),
            disk_read_mb=(
                io_counters.read_bytes / (1024 * 1024) 
                if io_counters else 0
            ),
            disk_write_mb=(
                io_counters.write_bytes / (1024 * 1024) 
                if io_counters else 0
            ),
            network_sent_mb=(
                net_counters.bytes_sent / (1024 * 1024) 
                if net_counters else 0
            ),
            network_recv_mb=(
                net_counters.bytes_recv / (1024 * 1024) 
                if net_counters else 0
            ),
            thread_count=process.num_threads(),
            timestamp=datetime.now().isoformat(),
        )


class LatencyBenchmark:
    """延迟基准测试工具"""
    
    def __init__(self, warmup_iterations: int = 10):
        self.warmup_iterations = warmup_iterations
        self._process = psutil.Process()
    
    def measure(
        self,
        func: Callable,
        iterations: int = 100,
        warmup: bool = True,
        *args,
        **kwargs
    ) -> LatencyResult:
        """
        测量函数执行延迟
        
        Args:
            func: 要测量的函数
            iterations: 迭代次数
            warmup: 是否进行预热
            *args, **kwargs: 传递给函数的参数
        
        Returns:
            LatencyResult: 延迟测量结果
        """
        samples = []
        
        # 预热阶段
        if warmup:
            for _ in range(self.warmup_iterations):
                try:
                    func(*args, **kwargs)
                except Exception:
                    pass
        
        # 正式测量
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                func(*args, **kwargs)
                success = True
            except Exception:
                success = False
            end = time.perf_counter()
            
            latency_ms = (end - start) * 1000
            samples.append(latency_ms)
        
        return self._calculate_stats(samples)
    
    def measure_context(
        self,
        context_name: str,
        iterations: int = 100
    ) -> LatencyResult:
        """
        使用上下文管理器测量延迟
        
        Args:
            context_name: 上下文名称
            iterations: 迭代次数
        
        Returns:
            LatencyResult: 延迟测量结果
        """
        samples = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            yield
            end = time.perf_counter()
            samples.append((end - start) * 1000)
        
        return self._calculate_stats(samples)
    
    def _calculate_stats(self, samples: List[float]) -> LatencyResult:
        """计算统计结果"""
        if not samples:
            return LatencyResult()
        
        sorted_samples = sorted(samples)
        n = len(samples)
        
        return LatencyResult(
            min_ms=min(samples),
            max_ms=max(samples),
            mean_ms=statistics.mean(samples),
            median_ms=statistics.median(samples),
            p95_ms=sorted_samples[int(n * 0.95)],
            p99_ms=sorted_samples[int(n * 0.99)] if n > 1 else max(samples),
            std_dev_ms=(
                statistics.stdev(samples) if n > 1 else 0
            ),
            iterations=n,
            samples=samples,
        )


class ThroughputBenchmark:
    """吞吐量基准测试工具"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._process = psutil.Process()
    
    def measure(
        self,
        func: Callable,
        total_operations: int = 1000,
        concurrency: int = 1,
        *args,
        **kwargs
    ) -> ThroughputResult:
        """
        测量函数吞吐量
        
        Args:
            func: 要测量的函数
            total_operations: 总操作次数
            concurrency: 并发数
            *args, **kwargs: 传递给函数的参数
        
        Returns:
            ThroughputResult: 吞吐量测量结果
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        latencies = []
        success_count = 0
        error_count = 0
        
        start_time = time.perf_counter()
        
        if concurrency > 1:
            with ThreadPoolExecutor(max_workers=min(concurrency, self.max_workers)) as executor:
                futures = [
                    executor.submit(func, *args, **kwargs) 
                    for _ in range(total_operations)
                ]
                
                for future in as_completed(futures):
                    latency = time.perf_counter() - start_time
                    latencies.append(latency * 1000)
                    try:
                        future.result()
                        success_count += 1
                    except Exception:
                        error_count += 1
        else:
            for _ in range(total_operations):
                op_start = time.perf_counter()
                try:
                    func(*args, **kwargs)
                    success_count += 1
                except Exception:
                    error_count += 1
                latencies.append((time.perf_counter() - op_start) * 1000)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        return ThroughputResult(
            total_operations=total_operations,
            total_time_ms=total_time_ms,
            operations_per_second=(
                total_operations / (total_time_ms / 1000) 
                if total_time_ms > 0 else 0
            ),
            avg_latency_ms=(
                statistics.mean(latencies) if latencies else 0
            ),
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            success_count=success_count,
            error_count=error_count,
        )


class ResourceMonitor:
    """资源使用监控器"""
    
    def __init__(self, sample_interval: float = 0.1):
        self.sample_interval = sample_interval
        self._process = psutil.Process()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._samples: List[ResourceUsage] = []
        self._lock = threading.Lock()
    
    def start(self, duration_seconds: Optional[float] = None):
        """开始监控"""
        self._samples = []
        self._running = True
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(duration_seconds,)
        )
        self._monitor_thread.start()
    
    def stop(self) -> List[ResourceUsage]:
        """停止监控并返回采样数据"""
        self._running = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        
        with self._lock:
            return self._samples.copy()
    
    def capture(self) -> ResourceUsage:
        """捕获当前资源使用情况"""
        return ResourceUsage.capture(self._process)
    
    def _monitor_loop(self, duration_seconds: Optional[float]):
        """监控循环"""
        start_time = time.time()
        
        while self._running:
            sample = ResourceUsage.capture(self._process)
            
            with self._lock:
                self._samples.append(sample)
            
            elapsed = time.time() - start_time
            
            if duration_seconds and elapsed >= duration_seconds:
                break
            
            time.sleep(self.sample_interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取资源使用统计"""
        samples = self.stop()
        
        if not samples:
            return {}
        
        cpu_values = [s.cpu_percent for s in samples]
        memory_values = [s.memory_mb for s in samples]
        
        return {
            "cpu_percent": {
                "mean": statistics.mean(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values),
            },
            "memory_mb": {
                "mean": statistics.mean(memory_values),
                "max": max(memory_values),
                "min": min(memory_values),
            },
            "samples_count": len(samples),
        }


class PerformanceReport:
    """性能报告生成器"""
    
    def __init__(self, title: str = "Performance Report"):
        self.title = title
        self.timestamp = datetime.now().isoformat()
        self.sections: List[Dict[str, Any]] = []
    
    def add_section(
        self,
        name: str,
        data: Dict[str, Any],
        description: str = ""
    ):
        """添加报告章节"""
        self.sections.append({
            "name": name,
            "data": data,
            "description": description,
        })
    
    def add_latency_result(self, name: str, result: LatencyResult):
        """添加延迟测试结果"""
        self.add_section(
            name,
            result.to_dict(),
            f"基于 {result.iterations} 次测试的延迟统计"
        )
    
    def add_throughput_result(self, name: str, result: ThroughputResult):
        """添加吞吐量测试结果"""
        self.add_section(
            name,
            result.to_dict(),
            f"总操作数: {result.total_operations}"
        )
    
    def add_resource_stats(self, name: str, stats: Dict[str, Any]):
        """添加资源统计"""
        self.add_section(name, stats, "资源使用统计")
    
    def generate_text(self) -> str:
        """生成文本报告"""
        lines = [
            "=" * 60,
            self.title,
            "=" * 60,
            f"生成时间: {self.timestamp}",
            "",
        ]
        
        for section in self.sections:
            lines.append(f"【{section['name']}】")
            if section['description']:
                lines.append(f"  {section['description']}")
            
            for key, value in section['data'].items():
                if isinstance(value, float):
                    lines.append(f"  {key}: {value:.4f}")
                else:
                    lines.append(f"  {key}: {value}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("报告结束")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def generate_json(self) -> str:
        """生成JSON报告"""
        return json.dumps(
            {
                "title": self.title,
                "timestamp": self.timestamp,
                "sections": self.sections,
            },
            indent=2,
            ensure_ascii=False,
        )
    
    def save(self, filepath: str, format: str = "text"):
        """保存报告到文件"""
        if format == "json":
            content = self.generate_json()
        else:
            content = self.generate_text()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


class PerformanceBenchmark:
    """综合性能基准测试工具"""
    
    def __init__(self, iterations: int = 100):
        self.iterations = iterations
        self.latency_benchmark = LatencyBenchmark()
        self.throughput_benchmark = ThroughputBenchmark()
        self.resource_monitor = ResourceMonitor()
    
    def benchmark_function(
        self,
        name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """基准测试单个函数"""
        # 延迟测试
        latency_result = self.latency_benchmark.measure(
            func, self.iterations, True, *args, **kwargs
        )
        
        # 资源监控
        self.resource_monitor.start(duration_seconds=2.0)
        throughput_result = self.throughput_benchmark.measure(
            func, total_operations=self.iterations,
            *args, **kwargs
        )
        resource_stats = self.resource_monitor.get_stats()
        
        return {
            "name": name,
            "latency": latency_result.to_dict(),
            "throughput": throughput_result.to_dict(),
            "resources": resource_stats,
        }
    
    def run_comparison(
        self,
        benchmarks: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """
        运行多个函数的对比测试
        
        Args:
            benchmarks: {名称: 函数} 的字典
        
        Returns:
            Dict: 对比测试结果
        """
        results = {}
        
        for name, func in benchmarks.items():
            results[name] = self.benchmark_function(name, func)
        
        # 找出最佳
        if results:
            best_latency = min(
                results.items(),
                key=lambda x: x[1]['latency']['mean_ms']
            )
            
            return {
                "results": results,
                "best_latency": {
                    "name": best_latency[0],
                    "mean_ms": best_latency[1]['latency']['mean_ms'],
                },
            }
        
        return {"results": results}


# 便捷函数
def measure_latency(
    func: Callable,
    iterations: int = 100,
    warmup: bool = True
) -> LatencyResult:
    """测量函数延迟"""
    benchmark = LatencyBenchmark()
    return benchmark.measure(func, iterations, warmup)


def measure_throughput(
    func: Callable,
    total_operations: int = 1000,
    concurrency: int = 1
) -> ThroughputResult:
    """测量函数吞吐量"""
    benchmark = ThroughputBenchmark()
    return benchmark.measure(func, total_operations, concurrency)


def monitor_resources(
    duration_seconds: float = 5.0,
    interval: float = 0.1
) -> List[ResourceUsage]:
    """监控资源使用"""
    monitor = ResourceMonitor(sample_interval=interval)
    monitor.start(duration_seconds)
    return monitor.stop()


def generate_report(
    title: str,
    *results: Dict[str, Any]
) -> PerformanceReport:
    """生成性能报告"""
    report = PerformanceReport(title)
    
    for result in results:
        if 'latency' in result:
            report.add_latency_result(result['name'], result['latency'])
        if 'throughput' in result:
            report.add_throughput_result(result['name'], result['throughput'])
        if 'resources' in result:
            report.add_resource_stats(f"{result['name']}_resources", result['resources'])
    
    return report
