"""
Agent-OS-Kernel 分布式演示

展示分布式功能的使用方法
"""

from agent_os_kernel.core.distributed_scheduler import (
    DistributedScheduler,
    NodeInfo,
    TaskInfo
)


async def demo_distributed():
    """演示分布式功能"""
    print("=" * 60)
    print("Agent-OS-Kernel 分布式演示")
    print("=" * 60)
    
    # 创建分布式调度器
    scheduler = DistributedScheduler(scheduler_id="demo-scheduler")
    
    # 注册节点
    node = NodeInfo(
        node_id="demo-node-01",
        hostname="localhost",
        port=50051,
        cpu_count=8,
        memory_mb=16384,
        gpu_count=1
    )
    scheduler.register_node(node)
    print(f"   节点已注册: {node.node_id} ({node.hostname}:{node.port})")
    
    # 获取集群状态
    stats = scheduler.get_stats()
    print(f"\n集群状态:")
    print(f"  节点数: {stats['nodes']}")
    print(f"  调度器状态: {stats['state']}")
    
    # 提交任务
    task = TaskInfo(
        task_id="demo-task-01",
        name="demo-task",
        priority=5,
        cpu_needed=2,
        memory_mb=2048,
        gpu_needed=0
    )
    await scheduler.submit_task(task)
    print(f"\n任务已提交: {task.task_id}")
    
    # 执行调度
    await scheduler.schedule()
    print(f"   任务状态: {task.status}")
    print(f"   分配节点: {task.node_id}")
    
    # 调度后统计
    stats = scheduler.get_stats()
    print(f"\n调度后统计:")
    print(f"  活动任务: {stats['active_tasks']}")
    print(f"  待处理任务: {stats['pending_tasks']}")
    print(f"  故障转移: {'启用' if stats['failover_enabled'] else '禁用'}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_distributed())
