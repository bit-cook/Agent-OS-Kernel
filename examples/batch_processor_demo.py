"""
Agent-OS-Kernel 批处理演示

展示批处理的使用方法
"""

from agent_os_kernel.core.batch_processor import BatchProcessor, AggregationType


async def demo_batch():
    """演示批处理"""
    print("=" * 60)
    print("Agent-OS-Kernel 批处理演示")
    print("=" * 60)
    
    # 创建批处理器
    processor = BatchProcessor(
        batch_size=10,
        timeout_ms=1000,
        aggregation=AggregationType.SUM
    )
    
    # 添加任务
    print("\n添加任务...")
    for i in range(5):
        await processor.add_task({"id": i, "value": i + 1})
    
    # 获取统计
    stats = processor.get_statistics()
    print(f"\n批处理统计:")
    print(f"  批次数量: {stats.batch_count}")
    print(f"  处理数量: {stats.processed_count}")
    print(f"  失败数量: {stats.failed_count}")
    
    # 获取聚合结果
    if stats.total_processed > 0:
        print(f"  聚合值: {stats.aggregated_value}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_batch())
