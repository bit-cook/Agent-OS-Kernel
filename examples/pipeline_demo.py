"""
Agent-OS-Kernel 管道演示

展示管道处理的使用方法
"""

from agent_os_kernel.core.pipeline import Pipeline, PipelineStage


async def demo_pipeline():
    """演示管道处理"""
    print("=" * 60)
    print("Agent-OS-Kernel 管道演示")
    print("=" * 60)
    
    # 创建管道
    pipeline = Pipeline(name="data-processing")
    
    # 添加阶段
    async def extract(data):
        print(f"  提取数据: {data}")
        return {"raw": data}
    
    async def transform(item):
        print(f"  转换数据: {item}")
        return {"processed": item.get("raw", "")}
    
    async def load(item):
        print(f"  加载数据: {item}")
        return {"loaded": True}
    
    pipeline.add_stage(PipelineStage(name="extract", handler=extract))
    pipeline.add_stage(PipelineStage(name="transform", handler=transform))
    pipeline.add_stage(PipelineStage(name="load", handler=load))
    
    # 执行管道
    print("\n执行管道...")
    result = await pipeline.execute({"input": "test-data"})
    print(f"\n结果: {result}")
    
    # 获取统计
    stats = pipeline.get_statistics()
    print(f"\n管道统计:")
    print(f"  总处理: {stats.total_processed}")
    print(f"  成功率: {stats.success_rate:.2%}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_pipeline())
