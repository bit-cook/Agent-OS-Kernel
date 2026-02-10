"""
分布式和监控示例

展示：
1. 分布式调度器
2. Agent 热迁移
3. GPU 资源监控
4. 系统监控和告警
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel.distributed import (
    DistributedScheduler,
    AgentMigration,
    create_distributed_scheduler
)
from agent_os_kernel.resources import (
    GPUMonitor,
    GPUManager,
    SystemMonitor,
    MetricsCollector
)


async def demo_distributed_scheduler():
    """分布式调度器示例"""
    print("=" * 60)
    print("分布式调度器示例")
    print("=" * 60)
    
    # 创建调度器
    scheduler = create_distributed_scheduler(
        node_id="scheduler-1",
        host="localhost",
        port=8001
    )
    
    # 注册节点
    await scheduler.register_node(
        node_id="node-1",
        hostname="gpu-server-1",
        port=8002,
        capabilities=["gpu", "nvidia"],
        resources={"gpu_memory": 16000, "cost_per_hour": 2.0}
    )
    
    await scheduler.register_node(
        node_id="node-2",
        hostname="cpu-server-1",
        port=8003,
        capabilities=["cpu", "high_memory"],
        resources={"memory_gb": 64, "cost_per_hour": 0.5}
    )
    
    await scheduler.register_node(
        node_id="node-3",
        hostname="gpu-server-2",
        port=8004,
        capabilities=["gpu", "nvidia"],
        resources={"gpu_memory": 32000, "cost_per_hour": 3.0}
    )
    
    print("\n📊 节点注册完成")
    
    # 启动调度器
    await scheduler.start()
    
    # 提交任务
    tasks = [
        ("task-1", {"name": "GPU_Agent_1"}, "gpu-server"),
        ("task-2", {"name": "CPU_Agent_1"}, "cpu-server"),
        ("task-3", {"name": "GPU_Agent_2"}, "gpu-server"),
    ]
    
    for task_id, config, _ in tasks:
        await scheduler.submit_task(
            task_id=task_id,
            agent_config=config,
            priority=1
        )
    
    # 等待调度
    await asyncio.sleep(1)
    
    # 获取集群状态
    status = await scheduler.get_cluster_status()
    
    print(f"\n📈 集群状态:")
    print(f"   节点数: {status['total_nodes']}")
    print(f"   总 Agents: {status['total_agents']}")
    print(f"   平均负载: {status['avg_load']:.2f}")
    print(f"   待处理任务: {status['pending_tasks']}")
    
    for node in status["nodes"]:
        print(f"   - {node['node_id']}: {node['agents_count']} agents, load={node['load']:.2f}")
    
    await scheduler.stop()
    
    return scheduler


async def demo_agent_migration():
    """Agent 迁移示例"""
    print("\n" + "=" * 60)
    print("Agent 热迁移示例")
    print("=" * 60)
    
    # 创建迁移管理器
    migration = AgentMigration(storage_dir="./demo_migrations")
    
    # 模拟 Agent 状态
    agent_state = {
        "agent_id": "agent-demo-1",
        "name": "DemoAgent",
        "status": "running",
        "progress": 0.75
    }
    
    context = [
        {"role": "user", "content": "任务 1"},
        {"role": "assistant", "content": "回复 1"},
        {"role": "user", "content": "任务 2"},
    ]
    
    memory = {
        "learned_facts": ["fact1", "fact2"],
        "preferences": {"theme": "dark"}
    }
    
    tools_state = {
        "tool1": {"usage_count": 5},
        "tool2": {"usage_count": 3}
    }
    
    print("\n📝 创建检查点...")
    
    # 创建检查点
    checkpoint_id = await migration.create_checkpoint(
        agent_id="agent-demo-1",
        state=agent_state,
        context=context,
        memory=memory,
        tools_state=tools_state
    )
    
    print(f"   检查点: {checkpoint_id}")
    
    # 模拟迁移
    print("\n🚀 执行迁移...")
    result = await migration.migrate(
        agent_id="agent-demo-1",
        source_node="node-1",
        target_node="node-2",
        checkpoint_id=checkpoint_id
    )
    
    print(f"   迁移结果:")
    print(f"   - 成功: {result['success']}")
    print(f"   - 源节点: {result['source_node']}")
    print(f"   - 目标节点: {result['target_node']}")
    print(f"   - 耗时: {result['duration_seconds']}s")
    
    # 从检查点恢复
    print("\n📖 从检查点恢复...")
    restored = await migration.restore_from_checkpoint(checkpoint_id)
    
    if restored:
        print(f"   ✅ 恢复成功")
        print(f"   - Agent 状态: {restored['agent_state']['name']}")
        print(f"   - 上下文数: {len(restored['context'])}")
        print(f"   - 记忆项: {len(restored['memory'])}")
    
    # 列出检查点
    checkpoints = await migration.list_checkpoints()
    print(f"\n📋 检查点列表: {len(checkpoints)} 个")
    
    return migration


async def demo_gpu_monitor():
    """GPU 监控示例"""
    print("\n" + "=" * 60)
    print("GPU 资源监控示例")
    print("=" * 60)
    
    # 创建 GPU 管理器
    manager = GPUManager()
    
    print("\n🔍 检测 GPU 设备...")
    
    # 检测设备
    devices = await manager.monitor.detect_devices()
    
    if devices:
        print(f"   发现 {len(devices)} 个 GPU:")
        
        for device in devices:
            print(f"   - GPU {device.index}: {device.name}")
            print(f"     显存: {device.memory_used_mb}/{device.memory_total_mb} MB")
            print(f"     利用率: {device.utilization_percent}%")
            print(f"     温度: {device.temperature_c}°C")
        
        # 获取状态
        status = await manager.get_status()
        print(f"\n📊 GPU 状态:")
        print(f"   设备数: {status['devices_count']}")
        print(f"   初始化: {status['initialized']}")
    else:
        print("   ⚠️ 未检测到 GPU 设备 (可能没有 NVIDIA GPU)")
    
    return manager


async def demo_system_monitor():
    """系统监控示例"""
    print("\n" + "=" * 60)
    print("系统监控示例")
    print("=" * 60)
    
    # 创建监控器
    monitor = SystemMonitor()
    
    # 注册告警回调
    async def handle_alert(alert):
        print(f"   🔔 告警: {alert.title} - {alert.description}")
    
    monitor.on_alert(handle_alert)
    
    print("\n📊 采集系统指标...")
    
    # 采集指标
    metrics = await monitor.collect_metrics()
    
    print(f"   CPU: {metrics['cpu_percent']:.1f}%")
    print(f"   内存: {metrics['memory_percent']:.1f}% ({metrics['memory_used_mb']:.0f} MB)")
    print(f"   磁盘: {metrics['disk_usage_percent']:.1f}%")
    print(f"   进程数: {metrics['process_count']}")
    
    # 获取摘要
    summary = monitor.get_summary()
    
    print(f"\n📈 监控摘要:")
    print(f"   监控状态: {'运行中' if summary['monitoring'] else '未运行'}")
    print(f"   活跃告警: {summary['active_alerts']}")
    print(f"   规则数: {summary['rules_count']}")
    
    # 指标收集器
    collector = MetricsCollector()
    
    print(f"\n📉 指标收集:")
    collector.counter_inc("requests_total", 10)
    collector.counter_inc("requests_total", 5)
    collector.gauge_set("active_agents", 5)
    collector.histogramObserve("response_time_ms", 150)
    collector.histogramObserve("response_time_ms", 200)
    collector.histogramObserve("response_time_ms", 100)
    
    stats = collector.get_all()
    
    print(f"   请求数: {stats['counters']['requests_total']}")
    print(f"   活跃 Agents: {stats['gauges']['active_agents']}")
    hist_stats = stats['histograms']['response_time_ms']
    print(f"   响应时间:")
    print(f"     - 平均: {hist_stats.get('avg', 0):.1f}ms")
    print(f"     - P95: {hist_stats.get('p95', 0):.1f}ms")
    
    return monitor


async def demo_complete_pipeline():
    """完整流水线示例"""
    print("\n" + "=" * 60)
    print("完整监控流水线")
    print("=" * 60)
    
    # 创建组件
    scheduler = create_distributed_scheduler("main-scheduler")
    migration = AgentMigration()
    gpu_manager = GPUManager()
    monitor = SystemMonitor()
    collector = MetricsCollector()
    
    # 注册告警处理
    async def on_alert(alert):
        print(f"   🚨 [{alert.level.value.upper()}] {alert.title}")
    
    monitor.on_alert(on_alert)
    
    # 启动监控
    await monitor.start_monitoring()
    
    # 等待收集一些数据
    await asyncio.sleep(2)
    
    # 模拟负载
    collector.counter_inc("tasks_submitted", 10)
    collector.counter_inc("tasks_completed", 8)
    collector.gauge_set("cluster_nodes", 3)
    collector.histogramObserve("task_duration_s", 1.5)
    collector.histogramObserve("task_duration_s", 2.0)
    
    # 停止监控
    await monitor.stop_monitoring()
    
    # 导出指标
    export = monitor.export_metrics(300)
    
    print(f"\n📊 指标导出:")
    print(f"   指标类型: {len(export['metrics'])}")
    print(f"   持续时间: {export['duration_seconds']}s")
    
    # 获取告警
    alerts = monitor.get_alerts(unresolved=True)
    print(f"   未解决告警: {len(alerts)}")
    
    return {
        "scheduler": scheduler,
        "migration": migration,
        "gpu_manager": gpu_manager,
        "monitor": monitor,
        "collector": collector
    }


async def main():
    """主函数"""
    print("\n🚀 分布式和监控示例")
    print("=" * 60)
    
    # 1. 分布式调度器
    await demo_distributed_scheduler()
    
    # 2. Agent 迁移
    await demo_agent_migration()
    
    # 3. GPU 监控
    await demo_gpu_monitor()
    
    # 4. 系统监控
    await demo_system_monitor()
    
    # 5. 完整流水线
    await demo_complete_pipeline()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
