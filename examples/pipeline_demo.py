"""
Agent-OS-Kernel 管道演示

展示管道处理的使用方法
"""

from agent_os_kernel.core.pipeline import Pipeline


async def demo_pipeline():
    """演示管道处理"""
    print("=" * 60)
    print("Agent-OS-Kernel 管道演示")
    print("=" * 60)

    # 创建管道
    pipeline = Pipeline(name="data-processing", max_concurrent=5)

    # 添加阶段（每个阶段函数签名为 func(data, results)，
    # data 是管道入口数据，results 收集前面各阶段的输出）
    async def extract(data, results):
        print(f"  提取数据: {data}")
        return {"raw": data.get("input", "")}

    async def transform(data, results):
        item = results.get("extract", {})
        print(f"  转换数据: {item}")
        return {"processed": item.get("raw", "").upper()}

    async def load(data, results):
        item = results.get("transform", {})
        print(f"  加载数据: {item}")
        return {"loaded": True}

    pipeline.add_stage("extract", extract)
    pipeline.add_stage("transform", transform)
    pipeline.add_stage("load", load)

    # 注册完成回调（回调是异步的）
    async def on_complete(item):
        print(f"  [回调] 管道项目 {item.item_id[:8]}... 处理完成")

    pipeline.on_complete(on_complete)

    # 执行管道
    print("\n执行管道...")
    result = await pipeline.process({"input": "test-data"})
    print(f"\n结果: {result.results}")
    print(f"最终状态: {result.stage.value}")

    # 获取统计
    stats = pipeline.get_stats()
    print(f"\n管道统计:")
    print(f"  总项目: {stats['total_items']}")
    print(f"  完成: {stats['completed']}")
    print(f"  失败: {stats['failed']}")
    print(f"  阶段数: {stats['stages']}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_pipeline())
