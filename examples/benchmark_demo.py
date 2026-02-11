# -*- coding: utf-8 -*-
"""
Benchmark Demo - Agent-OS-Kernel 性能基准测试演示

演示性能测试工具和优化器的使用方法。
"""

import time
import random
from typing import Dict, Any
from agent_os_kernel.core.benchmark import (
    LatencyBenchmark,
    ThroughputBenchmark,
    ResourceMonitor,
    PerformanceReport,
    PerformanceBenchmark,
    LatencyResult,
    ThroughputResult,
    ResourceUsage,
)
from agent_os_kernel.core.optimizer import (
    ConnectionPool,
    LRUCache,
    ThreadPoolOptimizer,
    MemoryOptimizer,
    ConcurrencyLimiter,
    BatchProcessor,
    PoolConfig,
    CacheConfig,
    ConcurrencyConfig,
)


def demo_latency_measurement():
    """演示延迟测量"""
    print("\n" + "=" * 60)
    print("📊 延迟测量演示")
    print("=" * 60)
    
    # 创建基准测试器
    benchmark = LatencyBenchmark(warmup_iterations=5)
    
    # 测试不同类型的函数
    def fast_operation():
        return sum(range(100))
    
    def medium_operation():
        time.sleep(0.001)
        data = [i * 2 for i in range(1000)]
        return sum(data)
    
    def slow_operation():
        time.sleep(0.005)
        result = 0
        for i in range(10000):
            result += i ** 2
        return result
    
    # 测量各个函数
    for name, func in [
        ("快速操作", fast_operation),
        ("中等操作", medium_operation),
        ("慢速操作", slow_operation),
    ]:
        print(f"\n测试: {name}")
        result = benchmark.measure(func, iterations=20, warmup=True)
        
        print(f"  平均延迟: {result.mean_ms:.4f}ms")
        print(f"  P95延迟:  {result.p95_ms:.4f}ms")
        print(f"  P99延迟:  {result.p99_ms:.4f}ms")
        print(f"  标准差:   {result.std_dev_ms:.4f}ms")


def demo_throughput_measurement():
    """演示吞吐量测量"""
    print("\n" + "=" * 60)
    print("📈 吞吐量测量演示")
    print("=" * 60)
    
    # 模拟一个简单的处理函数
    def process_item(item: int) -> Dict[str, int]:
        return {"processed": item, "value": item * 2}
    
    # 单线程吞吐量
    print("\n单线程吞吐量测试:")
    single_benchmark = ThroughputBenchmark(max_workers=1)
    result = single_benchmark.measure(
        lambda: process_item(random.randint(0, 1000)),
        total_operations=100,
        concurrency=1
    )
    
    print(f"  总操作数:   {result.total_operations}")
    print(f"  成功数:     {result.success_count}")
    print(f"  总耗时:     {result.total_time_ms:.2f}ms")
    print(f"  吞吐量:     {result.operations_per_second:.2f} ops/s")
    print(f"  平均延迟:   {result.avg_latency_ms:.4f}ms")
    
    # 并发吞吐量
    print("\n并发吞吐量测试:")
    concurrent_benchmark = ThroughputBenchmark(max_workers=4)
    result = concurrent_benchmark.measure(
        lambda: process_item(random.randint(0, 1000)),
        total_operations=200,
        concurrency=4
    )
    
    print(f"  总操作数:   {result.total_operations}")
    print(f"  吞吐量:     {result.operations_per_second:.2f} ops/s")


def demo_resource_monitoring():
    """演示资源监控"""
    print("\n" + "=" * 60)
    print("💻 资源使用监控演示")
    print("=" * 60)
    
    # 创建监控器
    monitor = ResourceMonitor(sample_interval=0.05)
    
    # 捕获基准资源使用
    print("\n空闲状态资源使用:")
    baseline = monitor.capture()
    print(f"  CPU: {baseline.cpu_percent:.1f}%")
    print(f"  内存: {baseline.memory_mb:.2f} MB")
    
    # 启动监控并进行一些操作
    print("\n监控高负载状态...")
    monitor.start(duration_seconds=2.0)
    
    # 模拟一些CPU密集型操作
    def cpu_intensive_task():
        start = time.time()
        while time.time() - start < 0.1:
            sum(i ** 2 for i in range(10000))
    
    benchmark = ThroughputBenchmark(max_workers=2)
    benchmark.measure(cpu_intensive_task, total_operations=20, concurrency=2)
    
    # 获取监控统计
    stats = monitor.get_stats()
    
    print(f"\n监控期间统计:")
    print(f"  采样数: {stats['samples_count']}")
    print(f"  CPU 平均: {stats['cpu_percent']['mean']:.1f}%")
    print(f"  CPU 最大: {stats['cpu_percent']['max']:.1f}%")
    print(f"  内存平均: {stats['memory_mb']['mean']:.2f} MB")
    print(f"  内存最大: {stats['memory_mb']['max']:.2f} MB")


def demo_performance_report():
    """演示性能报告生成"""
    print("\n" + "=" * 60)
    print("📝 性能报告生成演示")
    print("=" * 60)
    
    # 创建综合基准测试
    benchmark = PerformanceBenchmark(iterations=50)
    
    def test_function_1():
        return sum(i * 2 for i in range(500))
    
    def test_function_2():
        time.sleep(0.001)
        return [i ** 2 for i in range(200)]
    
    # 运行对比测试
    results = benchmark.run_comparison({
        "快速求和": test_function_1,
        "带延迟列表": test_function_2,
    })
    
    # 生成报告
    report = PerformanceReport("性能基准测试报告")
    
    report.add_section("测试说明", {
        "iterations": 50,
        "warmup": True,
    })
    
    for name, data in results["results"].items():
        report.add_latency_result(f"{name}_latency", LatencyResult(**data["latency"]))
    
    report.add_section("最佳性能", results["best_latency"])
    
    # 生成并显示文本报告
    print("\n生成的性能报告:")
    print("-" * 40)
    print(report.generate_text())
    
    # 保存报告
    print("\n报告已生成，可以调用 report.save() 保存到文件。")


def demo_optimizer_connection_pool():
    """演示连接池优化"""
    print("\n" + "=" * 60)
    print("🔄 连接池优化演示")
    print("=" * 60)
    
    # 创建模拟连接工厂
    connection_id = {"counter": 0}
    
    def create_connection():
        connection_id["counter"] += 1
        return {"id": connection_id["counter"], "created_at": time.time()}
    
    # 创建连接池
    config = PoolConfig(min_size=2, max_size=5, checkout_timeout=5.0)
    pool = ConnectionPool(create_connection, config)
    
    print(f"\n连接池初始状态: {pool.status()}")
    
    # 获取并使用连接
    conn1 = pool.acquire()
    print(f"获取连接1: {conn1}")
    
    conn2 = pool.acquire()
    print(f"获取连接2: {conn2}")
    
    print(f"获取后状态: {pool.status()}")
    
    # 释放连接
    pool.release(conn1)
    pool.release(conn2)
    
    print(f"释放后状态: {pool.status()}")
    
    # 关闭连接池
    pool.close()
    print("连接池已关闭")


def demo_optimizer_lru_cache():
    """演示LRU缓存优化"""
    print("\n" + "=" * 60)
    print("💾 LRU缓存优化演示")
    print("=" * 60)
    
    # 创建缓存
    config = CacheConfig(max_size=5, ttl_seconds=10.0)
    cache = LRUCache(config)
    cache.start()
    
    # 添加缓存项
    print("\n添加缓存项:")
    for i in range(6):
        cache.set(f"key_{i}", f"value_{i}")
        print(f"  设置 key_{i} = value_{i}")
    
    # 检查自动淘汰
    print(f"\n缓存统计: {cache.stats()}")
    
    # 访问缓存项（触发LRU）
    print(f"\n访问 key_0 (触发LRU移动)")
    value = cache.get("key_0")
    print(f"  获取 key_0: {value}")
    
    # 添加新项触发淘汰
    print("\n添加新项 key_6 (触发LRU淘汰)")
    cache.set("key_6", "value_6")
    
    print(f"缓存统计: {cache.stats()}")
    
    # 停止缓存
    cache.stop()


def demo_optimizer_thread_pool():
    """演示线程池优化"""
    print("\n" + "=" * 60)
    print("🧵 线程池优化演示")
    print("=" * 60)
    
    # 创建线程池
    config = ConcurrencyConfig(max_workers=2, queue_size=10)
    pool = ThreadPoolOptimizer(config)
    
    print(f"\n线程池状态: {pool.stats()}")
    
    # 提交任务
    def task(task_id: int) -> str:
        time.sleep(0.05)
        return f"task_{task_id}_completed"
    
    print("\n提交任务:")
    for i in range(3):
        success = pool.submit(f"task_{i}", task, i)
        print(f"  提交 task_{i}: {'成功' if success else '失败'}")
    
    print(f"提交后状态: {pool.stats()}")
    
    # 获取结果
    for i in range(3):
        result = pool.get_result(f"task_{i}", timeout=2.0)
        print(f"  获取 task_{i}: {result}")
    
    # 关闭线程池
    pool.shutdown()
    print("\n线程池已关闭")


def demo_optimizer_memory_pool():
    """演示内存优化"""
    print("\n" + "=" * 60)
    print("🧠 内存优化演示")
    print("=" * 60)
    
    # 创建内存池
    pool = MemoryOptimizer(max_pool_size=10)
    
    # 创建对象工厂
    object_counter = {"counter": 0}
    
    def create_object(value: int):
        object_counter["counter"] += 1
        return {"id": object_counter["counter"], "value": value}
    
    print("\n使用内存池:")
    
    # 获取对象
    for i in range(5):
        obj = pool.get_or_create(f"type_{i % 2}", lambda: create_object(i))
        print(f"  获取对象: {obj}")
        pool.release(f"type_{i % 2}", obj)
    
    print(f"\n内存池统计: {pool.get_stats()}")
    
    # 清空池
    pool.clear_all_pools()
    print("所有池已清空")


def demo_concurrency_limiter():
    """演示并发限制器"""
    print("\n" + "=" * 60)
    print("🚦 并发限制器演示")
    print("=" * 60)
    
    # 创建限制器
    limiter = ConcurrencyLimiter(max_concurrent=2)
    
    def critical_section(task_id: int):
        with limiter.limit():
            print(f"  任务 {task_id} 进入临界区")
            time.sleep(0.1)
            print(f"  任务 {task_id} 离开临界区")
            return task_id
    
    print("\n并发执行任务 (最大2个并发):")
    
    # 提交多个任务
    results = []
    for i in range(4):
        result = limiter.limit()
        # 模拟任务
        critical_section(i)
    
    print(f"\n并发限制器状态: {limiter.stats()}")


def demo_batch_processor():
    """演示批处理器"""
    print("\n" + "=" * 60)
    print("📦 批处理器演示")
    print("=" * 60)
    
    processed_batches = []
    
    def batch_processor(items: list):
        processed_batches.append({
            "count": len(items),
            "timestamp": time.time(),
            "items": items[:3],  # 只保留前3个示例
        })
    
    # 创建批处理器
    processor = BatchProcessor(
        batch_size=5,
        flush_interval=1.0,
        processor=batch_processor
    )
    
    processor.start()
    
    print("\n添加项目到批次:")
    for i in range(12):
        success = processor.add(f"item_{i}")
        status = "✓" if success else "✗ (队列满)"
        print(f"  添加 item_{i}: {status}")
    
    print(f"\n批处理器统计: {processor.stats()}")
    
    # 停止处理器
    processor.stop(timeout=2.0)
    
    print(f"\n处理的批次数: {len(processed_batches)}")
    for batch in processed_batches:
        print(f"  批次: {batch['count']} 个项目")


def demo_comparison_before_after():
    """演示优化前后的对比"""
    print("\n" + "=" * 60)
    print("📊 优化效果对比演示")
    print("=" * 60)
    
    # 模拟数据库查询
    class OldDatabase:
        """旧版数据库（无优化）"""
        
        def query(self, sql: str):
            # 模拟数据库延迟
            time.sleep(0.01)
            return [{"id": 1, "data": "result"}]
    
    class OptimizedDatabase:
        """优化版数据库（使用连接池）"""
        
        def __init__(self):
            self.pool = ConnectionPool(
                lambda: {"id": 0, "connected": True},
                PoolConfig(min_size=2, max_size=5)
            )
        
        def query(self, sql: str):
            conn = self.pool.acquire()
            try:
                time.sleep(0.001)  # 优化后延迟降低
                return [{"id": 1, "data": "result", "conn": conn["id"]}]
            finally:
                self.pool.release(conn)
        
        def close(self):
            self.pool.close()
    
    # 测试旧版本
    print("\n测试旧版数据库 (无连接池):")
    old_db = OldDatabase()
    benchmark = LatencyBenchmark(warmup_iterations=0)
    old_result = benchmark.measure(
        lambda: old_db.query("SELECT * FROM users"),
        iterations=20, warmup=False
    )
    print(f"  平均延迟: {old_result.mean_ms:.4f}ms")
    
    # 测试优化版本
    print("\n测试优化版数据库 (连接池):")
    new_db = OptimizedDatabase()
    new_result = benchmark.measure(
        lambda: new_db.query("SELECT * FROM users"),
        iterations=20, warmup=False
    )
    print(f"  平均延迟: {new_result.mean_ms:.4f}ms")
    
    # 计算改进
    improvement = (old_result.mean_ms - new_result.mean_ms) / old_result.mean_ms * 100
    print(f"\n性能改进: {improvement:.1f}%")
    print(f"延迟降低: {old_result.mean_ms - new_result.mean_ms:.4f}ms")
    
    new_db.close()


def main():
    """运行所有演示"""
    print("\n" + "🌟" * 30)
    print("Agent-OS-Kernel 性能基准测试和优化工具演示")
    print("🌟" * 30)
    
    # 基础演示
    demo_latency_measurement()
    demo_throughput_measurement()
    demo_resource_monitoring()
    demo_performance_report()
    
    # 优化演示
    demo_optimizer_connection_pool()
    demo_optimizer_lru_cache()
    demo_optimizer_thread_pool()
    demo_optimizer_memory_pool()
    demo_concurrency_limiter()
    demo_batch_processor()
    
    # 综合演示
    demo_comparison_before_after()
    
    print("\n" + "=" * 60)
    print("✅ 所有演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
