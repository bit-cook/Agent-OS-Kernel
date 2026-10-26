"""
Agent-OS-Kernel 指标收集演示

展示指标收集的使用方法
"""

from agent_os_kernel.core.metrics import MetricsCollector, MetricType


def demo_metrics():
    """演示指标收集"""
    print("=" * 60)
    print("Agent-OS-Kernel 指标收集演示")
    print("=" * 60)

    # 创建收集器
    collector = MetricsCollector()

    # 记录指标（counter 累加、gauge 覆盖、histogram 记录分布）
    collector.counter("requests_total", 1)
    collector.counter("requests_total", 1)
    collector.gauge("active_connections", 42)
    collector.histogram("request_duration_ms", 125.5)

    # 获取统计
    stats = collector.get_stats()
    print(f"\n指标统计:")
    print(f"  指标总数: {stats['total_metrics']}")

    # 按指标类型统计
    type_counts = {}
    for info in stats["metrics"].values():
        type_counts[info["type"]] = type_counts.get(info["type"], 0) + 1
    print(f"  计数器: {type_counts.get('counter', 0)}")
    print(f"  仪表: {type_counts.get('gauge', 0)}")
    print(f"  直方图: {type_counts.get('histogram', 0)}")

    # 获取所有指标
    metrics = collector.get_all()
    print(f"\n指标数量: {len(metrics)}")

    print(f"\n刚记录的指标:")
    for name in ("requests_total", "active_connections", "request_duration_ms"):
        metric = metrics.get(name)
        if metric is not None:
            print(
                f"  {name}: 类型={metric.metric_type.value}, "
                f"当前值={metric.value}, 采样数={metric.count}"
            )

    # 导出 Prometheus 格式（展示前几行）
    print(f"\nPrometheus 导出（前 3 行）:")
    for line in collector.export_prometheus().splitlines()[:3]:
        print(f"  {line}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_metrics()
