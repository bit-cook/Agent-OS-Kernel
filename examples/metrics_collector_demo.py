# -*- coding: utf-8 -*-
"""
Metrics Collector Demo - Agent-OS-Kernel 指标收集器演示

演示指标收集器的使用方法,包括:
- 计数器 (Counter) 的创建和使用
- 仪表盘 (Gauge) 的创建和使用
- 直方图 (Histogram) 的创建和使用
- 指标导出功能
"""

import time
import random
import sys
import threading
from agent_os_kernel.core.metrics_collector import (
    MetricsRegistry,
    Counter,
    Gauge,
    Histogram,
    ExportFormat,
    create_metrics_registry,
    create_counter,
    create_gauge,
    create_histogram,
    counter,
    gauge,
    histogram,
    export_metrics,
)


def pause():
    """交互式运行时等待回车；非交互运行（管道/CI）时直接跳过"""
    if sys.stdin.isatty():
        input("\n按回车键继续...")
    else:
        print()


def demo_counter():
    """演示计数器功能"""
    print("\n" + "=" * 60)
    print("📊 计数器 (Counter) 演示")
    print("=" * 60)
    
    # 创建计数器
    request_counter = create_counter(
        "http_requests_total",
        "HTTP请求总数",
        labels=["method", "status"]
    )
    
    # 模拟一些请求
    methods = ["GET", "POST", "PUT", "DELETE"]
    statuses = ["200", "201", "400", "404", "500"]
    
    print("\n模拟HTTP请求:")
    for i in range(20):
        method = random.choice(methods)
        status = random.choice(statuses)
        request_counter.inc(label_values={"method": method, "status": status})
        print(f"  请求 {i+1}: {method} -> {status}")
    
    # 显示计数器值
    print("\n计数器统计:")
    print(f"  总请求数: {request_counter.value()}")
    
    # 显示按状态分组
    print("\n  按状态分组:")
    for status in statuses:
        value = request_counter.value({"status": status})
        if value > 0:
            print(f"    {status}: {int(value)}")
    
    # 显示按方法分组
    print("\n  按方法分组:")
    for method in methods:
        value = request_counter.value({"method": method})
        if value > 0:
            print(f"    {method}: {int(value)}")


def demo_gauge():
    """演示仪表盘功能"""
    print("\n" + "=" * 60)
    print("📈 仪表盘 (Gauge) 演示")
    print("=" * 60)
    
    # 创建仪表盘
    memory_gauge = create_gauge(
        "memory_usage_bytes",
        "内存使用量 (字节)",
        labels=["server"]
    )
    
    cpu_gauge = create_gauge(
        "cpu_usage_percent",
        "CPU使用率 (%)"
    )
    
    # 模拟服务器监控
    servers = ["server-1", "server-2", "server-3"]
    
    print("\n模拟服务器监控数据:")
    for server in servers:
        memory = random.randint(512, 2048) * 1024 * 1024  # 512MB - 2GB
        memory_gauge.set(memory, label_values={"server": server})
        print(f"  {server}: 内存 = {memory / (1024*1024):.0f} MB")
    
    # 模拟CPU使用率变化
    print("\nCPU使用率变化:")
    for i in range(5):
        cpu = random.randint(10, 90)
        cpu_gauge.set(cpu)
        print(f"  时刻 {i+1}: CPU = {cpu}%")
        time.sleep(0.5)
    
    print(f"\n最终CPU使用率: {cpu_gauge.value()}%")


def demo_histogram():
    """演示直方图功能"""
    print("\n" + "=" * 60)
    print("📉 直方图 (Histogram) 演示")
    print("=" * 60)
    
    # 创建直方图
    latency_histogram = create_histogram(
        "request_latency_seconds",
        "请求延迟 (秒)",
        labels=["endpoint"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, float('inf'))
    )
    
    endpoints = ["/api/users", "/api/orders", "/api/products"]
    
    print("\n模拟请求延迟数据:")
    for endpoint in endpoints:
        print(f"\n  端点: {endpoint}")
        for i in range(50):
            # 生成符合正态分布的延迟
            latency = max(0.01, random.gauss(0.5, 0.3))
            latency_histogram.observe(latency, label_values={"endpoint": endpoint})
        
        count = latency_histogram.get_count({"endpoint": endpoint})
        total = latency_histogram.get_sum({"endpoint": endpoint})
        avg = total / count if count > 0 else 0
        
        print(f"    请求数: {count}")
        print(f"    总延迟: {total:.2f}s")
        print(f"    平均延迟: {avg:.3f}s")
    
    # 显示百分位数
    print("\n请求延迟百分位数:")
    for endpoint in endpoints:
        percentiles = latency_histogram.get_percentiles(
            [0.5, 0.9, 0.95, 0.99],
            label_values={"endpoint": endpoint}
        )
        print(f"\n  {endpoint}:")
        print(f"    P50: {percentiles.get(0.5, 0):.3f}s")
        print(f"    P90: {percentiles.get(0.9, 0):.3f}s")
        print(f"    P95: {percentiles.get(0.95, 0):.3f}s")
        print(f"    P99: {percentiles.get(0.99, 0):.3f}s")
    
    # 显示bucket分布
    print("\n延迟分布 (Bucket):")
    bucket_counts = latency_histogram.get_bucket_counts({"endpoint": "/api/users"})
    bucket_labels = ["0.1s", "0.5s", "1.0s", "2.0s", "5.0s", "+Inf"]
    buckets = (0.1, 0.5, 1.0, 2.0, 5.0, float('inf'))
    print("  Bucket分布 (/api/users):")
    for label, bucket in zip(bucket_labels, buckets):
        count = bucket_counts.get(bucket, 0)
        print(f"    <= {label}: {count}")


def demo_metrics_export():
    """演示指标导出功能"""
    print("\n" + "=" * 60)
    print("📤 指标导出演示")
    print("=" * 60)
    
    # 创建演示用注册表
    demo_registry = create_metrics_registry("demo")
    
    # 添加一些指标
    demo_registry.create_counter("http_requests", "HTTP请求数", ["method"])
    demo_registry.create_gauge("active_connections", "活跃连接数")
    demo_registry.create_histogram("request_duration", "请求持续时间", ["endpoint"])
    
    # 填充数据
    c = demo_registry.get_counter("http_requests")
    c.inc(label_values={"method": "GET"})
    c.inc(5, label_values={"method": "POST"})
    
    g = demo_registry.get_gauge("active_connections")
    g.set(150)
    
    h = demo_registry.get_histogram("request_duration")
    h.observe(0.1, label_values={"endpoint": "/home"})
    h.observe(0.3, label_values={"endpoint": "/home"})
    h.observe(0.5, label_values={"endpoint": "/api"})
    
    # 导出为JSON
    print("\n1. JSON 格式导出:")
    print("-" * 40)
    json_output = demo_registry.export(ExportFormat.JSON)
    print(json_output[:500] + "..." if len(json_output) > 500 else json_output)
    
    # 导出为Prometheus
    print("\n2. Prometheus 格式导出:")
    print("-" * 40)
    prom_output = demo_registry.export(ExportFormat.PROMETHEUS)
    print(prom_output)
    
    # 导出为文本
    print("\n3. 文本格式导出:")
    print("-" * 40)
    text_output = demo_registry.export(ExportFormat.TEXT)
    print(text_output)


def demo_thread_safety():
    """演示线程安全"""
    print("\n" + "=" * 60)
    print("🧵 线程安全演示")
    print("=" * 60)
    
    # 创建共享计数器
    global_counter = Counter("global_counter", "全局计数器")
    
    def worker(thread_id: int):
        """工作线程"""
        for _ in range(100):
            global_counter.inc()
            time.sleep(0.001)
    
    print("\n启动10个线程,每个线程增加100次:")
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    
    start_time = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start_time
    
    print(f"  期望值: 1000")
    print(f"  实际值: {int(global_counter.value())}")
    print(f"  耗时: {elapsed:.3f}s")
    print(f"  线程安全: {'✓' if global_counter.value() == 1000 else '✗'}")


def demo_real_world_scenario():
    """演示真实场景 - Web服务监控"""
    print("\n" + "=" * 60)
    print("🌐 真实场景: Web服务监控")
    print("=" * 60)
    
    # 创建服务监控注册表
    service_registry = create_metrics_registry("web_service")
    
    # 定义指标
    requests_total = service_registry.create_counter(
        "http_server_requests_total",
        "HTTP服务器请求总数",
        ["method", "endpoint", "status"]
    )
    
    request_duration = service_registry.create_histogram(
        "http_server_request_duration_seconds",
        "HTTP请求持续时间",
        ["method", "endpoint"],
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf'))
    )
    
    active_connections = service_registry.create_gauge(
        "http_server_active_connections",
        "活跃连接数"
    )
    
    in_flight_requests = service_registry.create_gauge(
        "http_server_requests_in_flight",
        "处理中的请求数"
    )
    
    print("\n模拟Web服务请求流:")
    
    endpoints = ["/", "/api/users", "/api/products", "/api/orders"]
    methods = ["GET", "POST", "PUT", "DELETE"]
    
    for i in range(30):
        # 模拟新请求
        endpoint = random.choice(endpoints)
        method = random.choice(methods)
        in_flight_requests.inc()
        active_connections.inc()
        
        # 模拟请求处理延迟
        latency = random.gauss(0.2, 0.1)
        time.sleep(0.05)
        
        # 请求完成
        status = random.choices(
            ["200", "201", "400", "404", "500"],
            weights=[60, 15, 15, 8, 2],
            k=1,
        )[0]
        in_flight_requests.dec()
        
        # 记录指标
        requests_total.inc(label_values={
            "method": method,
            "endpoint": endpoint,
            "status": status
        })
        request_duration.observe(latency, label_values={
            "method": method,
            "endpoint": endpoint
        })
        
        if (i + 1) % 10 == 0:
            print(f"  已处理 {i + 1} 个请求...")
    
    # 显示监控结果
    print("\n监控统计:")
    print(f"  活跃连接: {int(active_connections.value())}")
    print(f"  处理中请求: {int(in_flight_requests.value())}")
    
    print("\n请求统计:")
    requests = requests_total.get_all_values()
    for (method, endpoint, status), count in requests.items():
        print(f"    {method} {endpoint} -> {status}: {int(count)}")
    
    print("\n延迟统计:")
    print("  （延迟指标带有 method/endpoint 两个标签，查询时需给出完整标签组合）")
    for endpoint in endpoints:
        count = 0
        total = 0.0
        for method in methods:
            label_values = {"method": method, "endpoint": endpoint}
            count += request_duration.get_count(label_values)
            total += request_duration.get_sum(label_values)
        if count > 0:
            percentiles = request_duration.get_percentiles(
                [0.5, 0.9, 0.95],
                label_values={"method": methods[0], "endpoint": endpoint},
            )
            print(f"  {endpoint}:")
            print(f"    请求数: {count}")
            print(f"    平均: {total/count:.3f}s")
            print(f"    P50 ({methods[0]}): {percentiles.get(0.5, 0):.3f}s")
            print(f"    P90 ({methods[0]}): {percentiles.get(0.9, 0):.3f}s")
            print(f"    P95: {percentiles.get(0.95, 0):.3f}s")
    
    # 导出Prometheus格式
    print("\nPrometheus指标格式:")
    print("-" * 40)
    print(service_registry.export(ExportFormat.PROMETHEUS))


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 指标收集器 (Metrics Collector) 演示")
    print("=" * 60)
    
    # 运行各个演示
    demo_counter()
    pause()
    
    demo_gauge()
    pause()
    
    demo_histogram()
    pause()
    
    demo_metrics_export()
    pause()
    
    demo_thread_safety()
    pause()
    
    demo_real_world_scenario()
    
    print("\n" + "=" * 60)
    print("✅ 演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
