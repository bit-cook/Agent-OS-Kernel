# -*- coding: utf-8 -*-

"""任务队列演示"""

import asyncio
from agent_os_kernel.core.task_queue import TaskQueue, TaskPriority, TaskStatus


async def main():
    print("="*60)
    print("Task Queue Demo")
    print("="*60)
    
    # 创建任务队列
    queue = TaskQueue()
    
    results = []
    
    async def process_data(data: int):
        """处理数据"""
        await asyncio.sleep(0.1)
        result = data * 2
        results.append(result)
        return result
    
    async def worker(worker_id: int):
        """工作协程: 从队列取任务并执行"""
        while True:
            task = await queue.get()
            if task is None:  # 毒丸任务: 结束 worker
                break
            queue.start_task(task)
            try:
                result = await task.handler()
                queue.complete_task(task, result)
                print(f"  [worker-{worker_id}] {task.task_id} 完成 -> {result}")
            except Exception as e:
                queue.fail_task(task, e)
                print(f"  [worker-{worker_id}] {task.task_id} 失败: {e}")
    
    print("\n📤 提交任务...")
    
    # 提交多个任务
    for i in range(5):
        await queue.submit(
            f"task_{i}",
            f"Process data {i}",
            lambda i=i: process_data(i),
            priority=TaskPriority.NORMAL.value
        )
    
    stats = queue.get_stats()
    print(f"📤 已提交 {stats['total_submitted']} 个任务")
    
    # 投递毒丸任务, 确保每个 worker 都能退出
    for _ in range(3):
        await queue._queue.put((0, "__stop__", None))
    
    # 启动 3 个并发 worker 处理任务
    await asyncio.gather(*(worker(w) for w in range(3)))
    
    print(f"\n✅ 完成: {queue.get_stats()['total_completed']}")
    print(f"❌ 失败: {queue.get_stats()['total_failed']}")
    print(f"📊 结果: {sorted(results)}")
    
    # 统计
    stats = queue.get_stats()
    print(f"\n📈 队列统计: {stats}")
    
    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
