"""
Agent-OS-Kernel 任务队列演示

展示任务队列的使用方法
"""

from agent_os_kernel.core.task_queue import TaskQueue, TaskStatus, TaskPriority


async def demo_task_queue():
    """演示任务队列"""
    print("=" * 60)
    print("Agent-OS-Kernel 任务队列演示")
    print("=" * 60)
    
    # 创建队列
    queue = TaskQueue(max_size=100)
    
    # 提交任务
    print("\n提交任务...")
    for i in range(5):
        async def task():
            return f"result-{i}"
        
        task_obj = await queue.submit(
            task_id=f"task-{i}",
            name=f"Task {i}",
            handler=task,
            priority=TaskPriority.NORMAL.value
        )
        print(f"  ✅ 提交任务: task-{i}")
    
    # 获取任务
    print("\n获取任务...")
    for i in range(3):
        task = await queue.get()
        queue.start_task(task)
        print(f"  📦 开始执行: {task.name}")
        queue.complete_task(task, f"result-{i}")
    
    # 获取统计
    stats = queue.get_stats()
    print(f"\n队列统计:")
    print(f"  队列大小: {stats['queue_size']}")
    print(f"  运行中: {stats['running_count']}")
    print(f"  已完成: {stats['completed_count']}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_task_queue())
