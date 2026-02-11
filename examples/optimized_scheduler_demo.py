#!/usr/bin/env python3
"""OptimizedScheduler 使用示例"""

import asyncio
from agent_os_kernel.core.optimized_scheduler import (
    OptimizedScheduler, Priority
)


async def main():
    print("="*50)
    print("OptimizedScheduler 示例")
    print("="*50)
    
    # 1. 创建调度器
    print("\n1. 创建调度器")
    
    scheduler = OptimizedScheduler(max_concurrent=3, quota_managed=True)
    print(f"   最大并发: 3")
    print(f"   配额管理: 启用")
    
    # 2. 定义任务
    print("\n2. 定义任务")
    
    results = []
    
    async def task(name, delay=0.1):
        await asyncio.sleep(delay)
        results.append(name)
        return f"{name} 完成"
    
    # 3. 提交任务
    print("\n3. 提交任务")
    
    await scheduler.schedule("task-1", task, "任务1", delay=0.1)
    await scheduler.schedule("task-2", task, "任务2", delay=0.15)
    await scheduler.schedule("task-3", task, "任务3", delay=0.2)
    
    print("   ✓ 提交了3个任务")
    
    # 4. 等待完成
    print("\n4. 等待任务完成")
    
    await asyncio.sleep(0.5)
    
    print(f"   完成的任务: {len(results)}")
    print(f"   任务列表: {results}")
    
    # 5. 统计
    print("\n5. 获取统计")
    
    stats = scheduler.get_stats()
    print(f"   队列大小: {stats['queue_size']}")
    print(f"   运行中: {stats['running']}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
