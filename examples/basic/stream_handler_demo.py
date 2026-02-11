"""
Agent-OS-Kernel 流处理演示

展示流处理的使用方法
"""

from agent_os_kernel.core.stream_handler import StreamHandler, StreamType


async def demo_stream():
    """演示流处理"""
    print("=" * 60)
    print("Agent-OS-Kernel 流处理演示")
    print("=" * 60)
    
    # 创建流处理器
    handler = StreamHandler(
        stream_type=StreamType.REAL_TIME,
        buffer_size=1000
    )
    
    # 注册处理器
    async def process_item(item):
        print(f"处理: {item}")
        return {"result": item}
    
    handler.register_processor("data", process_item)
    
    # 发送数据
    print("\n发送数据...")
    for i in range(5):
        await handler.send({"id": i, "data": f"item-{i}"})
    
    # 获取统计
    stats = handler.get_statistics()
    print(f"\n流统计:")
    print(f"  处理数量: {stats.processed_count}")
    print(f"  缓冲区大小: {stats.buffer_size}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_stream())
