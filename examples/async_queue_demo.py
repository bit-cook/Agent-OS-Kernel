"""
Agent-OS-Kernel 异步队列演示

展示异步队列的使用方法
"""

from agent_os_kernel.core.async_queue import AsyncQueue, Message, MessageStatus


async def demo_async_queue():
    """演示异步队列"""
    print("=" * 60)
    print("Agent-OS-Kernel 异步队列演示")
    print("=" * 60)
    
    # 创建队列
    queue = AsyncQueue(max_size=100)
    
    # 创建消息
    msg = Message(
        content={"task": "process", "data": "test"},
        priority=1
    )
    
    # 发送消息
    print("\n发送消息...")
    await queue.enqueue(msg)
    
    # 接收消息
    print("接收消息...")
    received = await queue.dequeue()
    print(f"   收到: {received.content}")
    
    # 获取统计
    stats = queue.get_statistics()
    print(f"\n队列统计:")
    print(f"  队列大小: {stats.size}")
    print(f"  已处理: {stats.processed_count}")
    print(f"  失败: {stats.failed_count}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_async_queue())
