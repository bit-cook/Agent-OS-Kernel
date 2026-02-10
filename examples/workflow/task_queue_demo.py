# -*- coding: utf-8 -*-
"""任务队列演示"""

import asyncio
from agent_os_kernel.core.task_queue import TaskQueue, TaskPriority


async def main():
    print("="*60)
    print("Task Queue Demo")
    print("="*60)
    
    # 创建任务队列
    queue = TaskQueue(max_concurrent=3)
    
    results = []
    
    async def process_data(data: int):
        """处理数据"""
        await asyncio.sleep(0.1)
        result = data * 2
        results.append(result)
        return result
    
    print("\n📤 提交任务...")
    
    # 提交多个任务
    for i in range(5):
        await queue.submit(
            f"task_{i}",
            process_data,
            i,
            priority=TaskPriority.NORMAL
        )
    
    print(f"📤 已提交 {queue._stats['submitted']} 个任务")
    
    # 等待完成
    await asyncio.sleep(1)
    
    print(f"\n✅ 完成: {queue._stats['completed']}")
    print(f"❌ 失败: {queue._stats['failed']}")
    print(f"📊 结果: {results}")
    
    # 统计
    stats = queue.get_stats()
    print(f"\n📈 队列统计: {stats}")
    
    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
