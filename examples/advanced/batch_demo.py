# -*- coding: utf-8 -*-

"""批处理演示"""

import asyncio
from agent_os_kernel.core.batch_processor import BatchProcessor, Batch, AggregationType


async def main():
    print("="*60)
    print("Batch Processing Demo")
    print("="*60)

    print("\n📦 自动批处理（数据量达到 batch_size 时自动处理）...")

    # 创建批处理器（按 value 求和聚合）
    processor = BatchProcessor(
        batch_size=10,
        timeout_ms=500,
        aggregation=AggregationType.SUM
    )

    # 添加数据：正好填满一个批次，触发自动处理
    for i in range(10):
        await processor.add_task(
            {"value": i * 10, "score": 100 - i},
            batch_id="metrics"
        )
        await asyncio.sleep(0.02)

    stats = processor.get_statistics()
    print(f"  📊 自动处理: {stats['batch_count']} 批次, {stats['processed_count']} 条数据")

    print("\n📦 手动 flush（处理不满一批的数据）...")

    # 不满一批时不会自动处理，需要手动 flush
    partial = BatchProcessor(
        batch_size=10,
        timeout_ms=500,
        aggregation=AggregationType.SUM
    )
    for i in range(5):
        await partial.add_task(
            {"value": i * 10, "score": 100 - i},
            batch_id="metrics"
        )
        await asyncio.sleep(0.02)

    stats = partial.get_statistics()
    print(f"  📊 flush 前: {stats['batch_count']} 批次, {stats['processed_count']} 条数据")

    await partial.flush()

    stats = partial.get_statistics()
    print(f"  📊 flush 后: {stats['batch_count']} 批次, {stats['processed_count']} 条数据")

    print("\n🧮 聚合类型演示（value / count / score）:")

    data = [{"value": i * 10, "score": 100 - i} for i in range(25)]

    for field, aggregation in [
        ("value", AggregationType.SUM),
        ("count", AggregationType.COUNT),
        ("score", AggregationType.AVG),
    ]:
        batch = Batch(batch_id=field, aggregation=aggregation)
        for item in data:
            batch.add(item[field] if field != "count" else item)
        # 聚合作用于批次结果
        batch.results.extend(batch.items)
        aggregated = batch.get_aggregated_value()
        print(f"  {field:6} -> {aggregation.value:5} = {aggregated}")

    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
