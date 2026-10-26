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
    pipeline = Pipeline(name="data-processing")

    # 添加阶段（阶段函数签名为 func(data, results)：
    # data 为入口数据，results 为前面各阶段的输出）
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

    # 执行管道
    print("\n执行管道...")
    result = await pipeline.process({"input": "test-data"})
    print(f"\n结果: {result.results}")
    print(f"状态: {result.stage.value}")

    # 获取统计
    stats = pipeline.get_stats()
    print(f"\n管道统计:")
    print(f"  总项目: {stats['total_items']}")
    print(f"  完成: {stats['completed']}")
    print(f"  失败: {stats['failed']}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_pipeline())
