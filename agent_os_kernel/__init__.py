# -*- coding: utf-8 -*-
"""
Agent-OS-Kernel - AI Agent 的操作系统内核
"""

__version__ = "0.2.0"
__author__ = "Bit-Cook"
__license__ = "MIT"

# Core modules
from .core import (
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
    generate_report,
    # Optimizer模块有语法错误，暂时禁用
    # PoolConfig,
    # CacheConfig,
    # ConcurrencyConfig,
    # ConnectionPool,
    # LRUCache,
    # ThreadPoolOptimizer,
    # MemoryOptimizer,
    # ConcurrencyLimiter,
    # BatchProcessor,
    # create_connection_pool,
    # create_lru_cache,
    # create_thread_pool,
    # create_memory_pool,
    # create_concurrency_limiter,
    # create_batch_processor,
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    # Benchmark
    "LatencyResult",
    "ThroughputResult",
    "ResourceUsage",
    "LatencyBenchmark",
    "ThroughputBenchmark",
    "ResourceMonitor",
    "PerformanceReport",
    "PerformanceBenchmark",
    "measure_latency",
    "measure_throughput",
    "monitor_resources",
    "generate_report",
    # Optimizer (disabled due to syntax errors)
    # "PoolConfig",
    # "CacheConfig",
    # "ConcurrencyConfig",
    # "ConnectionPool",
    # "LRUCache",
    # "ThreadPoolOptimizer",
    # "MemoryOptimizer",
    # "ConcurrencyLimiter",
    # "BatchProcessor",
    # "create_connection_pool",
    # "create_lru_cache",
    # "create_thread_pool",
    # "create_memory_pool",
    # "create_concurrency_limiter",
    # "create_batch_processor",
]
