# -*- coding: utf-8 -*-
"""监控系统演示"""

import asyncio
from agent_os_kernel.core.monitoring import Monitor, HealthStatus


async def main():
    print("="*60)
    print("Monitoring Demo")
    print("="*60)
    
    # 创建监控器
    monitor = Monitor(
        name="agent-os-demo",
        collect_interval=5.0
    )
    
    print("\n📊 系统信息:")
    info = monitor.get_system_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n🔍 健康检查:")
    results = await monitor.check_health()
    for name, check in results.items():
        emoji = "✅" if check.status == HealthStatus.HEALTHY else ("⚠️" if check.status == HealthStatus.DEGRADED else "❌")
        print(f"  {emoji} {name}: {check.status.value}")
        print(f"     {check.message}")
        print(f"     延迟: {check.latency_ms:.2f}ms")
    
    print(f"\n🎯 整体状态: {monitor.get_overall_status().value}")
    
    print("\n📈 记录指标:")
    monitor.record_metric("requests_total", 1000)
    monitor.record_metric("requests_active", 50)
    monitor.record_metric("response_time_ms", 125.5)
    
    metrics = monitor.get_metrics("requests_total", limit=5)
    print(f"  指标数量: {len(metrics)}")
    
    print("\n🔔 告警系统:")
    def handle_alert(alert):
        print(f"  🚨 告警: {alert['name']} - {alert['message']}")
    
    monitor.on_alert(handle_alert)
    
    # 触发告警
    monitor.trigger_alert(
        name="test_alert",
        message="测试告警",
        severity="info"
    )
    
    print(f"  告警数量: {len(monitor.get_alerts())}")
    
    print("\n📊 统计信息:")
    stats = monitor.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
