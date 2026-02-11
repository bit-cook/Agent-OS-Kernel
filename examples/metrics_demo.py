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
    
    # 记录指标
    collector.record_counter("requests_total", 1)
    collector.record_gauge("active_connections", 42)
    collector.record_histogram("request_duration_ms", 125.5)
    
    # 获取统计
    stats = collector.get_statistics()
    print(f"\n指标统计:")
    print(f"  计数器: {stats.counter_count}")
    print(f"  仪表: {stats.gauge_count}")
    print(f"  直方图: {stats.histogram_count}")
    
    # 获取所有指标
    metrics = collector.get_all_metrics()
    print(f"\n指标数量: {len(metrics)}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_metrics()
