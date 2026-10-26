"""
Agent-OS-Kernel 批处理演示

展示批处理的使用方法
"""

import asyncio

from agent_os_kernel.core.batch_processor import AggregationType, BatchProcessor


async def demo_batch():
    """演示批处理"""
    print("=" * 60)
    print("Agent-OS-Kernel 批处理演示")
    print("=" * 60)
    
    # 创建批处理器（batch_size=3：满 3 条自动触发一批）
    processor = BatchProcessor(
        batch_size=3,
        timeout_ms=1000,
        aggregation=AggregationType.SUM
    )
    
    # 添加任务（满一批即自动处理）
    print("\n添加任务（每 3 条自动成批）...")
    for i in range(7):
        batch_id = await processor.add_task({"id": i, "value": i + 1}, batch_id="demo")
        stats = processor.get_statistics()
        print(f"   任务 {i} 已加入批次 {batch_id} | 累计批次: {stats['batch_count']}, 累计处理: {stats['processed_count']}")
    
    # 手动刷新剩余未成批的数据
    print("\n刷新剩余批次...")
    await processor.flush()
    
    # 获取统计（get_statistics 返回 dict）
    stats = processor.get_statistics()
    print(f"\n批处理统计:")
    print(f"  批次数量: {stats['batch_count']}")
    print(f"  处理数量: {stats['processed_count']}")
    print(f"  失败数量: {stats['failed_count']}")
    print(f"  活跃批次: {stats['active_batches']}")
    
    # 聚合值（SUM 模式对 results 求和，未填充 results 时为 None）
    print(f"  聚合值: {stats['aggregated_value']}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_batch())
