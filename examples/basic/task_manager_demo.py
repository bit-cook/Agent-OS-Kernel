"""
Agent-OS-Kernel 任务管理器演示

展示任务管理器的使用方法
"""

from agent_os_kernel.core.task_manager import TaskManager, ExecutionStatus


async def demo_task_manager():
    """演示任务管理器"""
    print("=" * 60)
    print("Agent-OS-Kernel 任务管理器演示")
    print("=" * 60)
    
    # 创建管理器
    manager = TaskManager(max_concurrent=3)
    
    # 执行任务
    print("\n执行任务...")
    
    async def process_data():
        await asyncio.sleep(0.1)
        return "processed"
    
    for i in range(5):
        try:
            execution = await manager.execute(
                execution_id=f"exec-{i}",
                task_id=f"task-{i}",
                agent_id="worker-1",
                handler=process_data
            )
            print(f"  ✅ 执行 {i}: {execution.status.value}")
        except Exception as e:
            print(f"  ❌ 执行 {i}: {e}")
    
    # 获取统计
    stats = manager.get_stats()
    print(f"\n管理器统计:")
    print(f"  活跃执行: {stats['active_executions']}")
    print(f"  成功: {stats['successful']}")
    print(f"  失败: {stats['failed']}")
    print(f"  可用槽位: {stats['available_slots']}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_task_manager())
