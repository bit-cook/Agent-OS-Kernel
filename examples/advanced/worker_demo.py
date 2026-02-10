# -*- coding: utf-8 -*-
"""工作池演示"""

import asyncio
from agent_os_kernel.core.worker import WorkerPool


async def main():
    print("="*60)
    print("Worker Pool Demo")
    print("="*60)
    
    # 创建工作池
    pool = WorkerPool(
        name="processing",
        max_workers=3,
        strategy="least_busy"
    )
    
    print("\n👷 添加工作节点:")
    
    # 添加工作节点
    for i in range(3):
        worker = pool.add_worker(
            worker_id=f"worker-{i}",
            name=f"Processor-{i}",
            metadata={"type": "cpu", "priority": i}
        )
        print(f"  ✅ 添加: {worker.name} ({worker.worker_id})")
    
    print(f"\n📊 工作节点列表:")
    workers = pool.list_workers()
    for w in workers:
        print(f"  {w.name}: {w.status.value}")
    
    print(f"\n📈 可用节点: {len(pool.get_available_workers())}")
    
    print("\n📦 提交任务:")
    
    async def process_item(item: int):
        """处理单个项目"""
        await asyncio.sleep(0.1)
        return {"item": item, "processed": True}
    
    # 提交多个任务
    task_ids = []
    for i in range(5):
        task_id = await pool.submit(
            task_id=f"task-{i}",
            func=process_item,
            item=i * 10
        )
        task_ids.append(task_id)
        print(f"  📤 提交: {task_id}")
    
    print(f"\n⏳ 等待任务完成...")
    await asyncio.sleep(0.5)
    
    print(f"\n✅ 获取结果:")
    for task_id in task_ids:
        try:
            result = await pool.get_result(task_id)
            print(f"  {task_id}: {result}")
        except Exception as e:
            print(f"  {task_id}: ❌ {e}")
    
    print(f"\n📊 工作池统计:")
    stats = pool.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n👷 工作节点状态:")
    for w in pool.list_workers():
        print(f"  {w.name}:")
        print(f"    状态: {w.status.value}")
        print(f"    任务数: {w.task_count}")
        print(f"    成功: {w.success_count}")
        print(f"    失败: {w.error_count}")
    
    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
