# -*- coding: utf-8 -*-

"""指标收集器演示"""

import asyncio
import time

from agent_os_kernel.core.metrics_collector import (
    create_metrics_registry,
    MetricsExporter,
    MetricType,
)


async def main():
    print("="*60)
    print("Metrics Collector Demo")
    print("="*60)

    # 创建指标注册表
    registry = create_metrics_registry("demo")

    # 记录指标
    print("\n📊 记录指标...")

    # 计数器（声明标签维度）
    requests = registry.create_counter("http_requests_total", labels=["method"])
    requests.inc(1, {"method": "GET"})
    requests.inc(1, {"method": "POST"})
    requests.inc(2, {"method": "PUT"})

    # 仪表盘（瞬时值）
    registry.gauge("active_connections").set(150)
    registry.gauge("memory_usage_mb").set(512)

    # 直方图（延迟分布）
    latency = registry.create_histogram("request_latency_seconds", labels=["endpoint"])
    start = time.time()
    time.sleep(0.1)  # 模拟工作
    latency.observe(time.time() - start, {"endpoint": "/api/users"})
    latency.observe(0.05, {"endpoint": "/api/users"})
    latency.observe(0.25, {"endpoint": "/api/users"})

    print("\n✅ 指标已记录")

    # 获取所有指标
    samples = registry.samples()
    counters = [s for s in samples if s.metric_type == MetricType.COUNTER]
    gauges = [s for s in samples if s.metric_type == MetricType.GAUGE]
    histograms = [s for s in samples if s.metric_type == MetricType.HISTOGRAM]

    print(f"\n📈 计数器:")
    for s in counters:
        print(f"  {s.name}{s.labels} = {s.value}")
    print(f"📈 仪表:")
    for s in gauges:
        print(f"  {s.name} = {s.value}")
    print(f"📈 直方图:")
    for s in histograms:
        print(f"  {s.name}{s.labels} = {s.value:.4f}")

    # 延迟分位数
    latency_metric = registry.get_histogram("request_latency_seconds")
    if latency_metric is not None:
        percentiles = latency_metric.get_percentiles(
            [0.5, 0.9, 0.99], label_values={"endpoint": "/api/users"})
        print(f"\n📈 延迟分位数: " +
              ", ".join(f"p{int(p*100)}={v:.4f}s" for p, v in percentiles.items()))

    # 导出 Prometheus 格式
    exporter = MetricsExporter(registry)
    prometheus_output = exporter.export_prometheus()
    print(f"\n📊 Prometheus 格式输出:")
    print(prometheus_output[:500])

    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
