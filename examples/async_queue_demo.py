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
        msg_id="msg-001",
        topic="demo",
        payload={"task": "process", "data": "test"},
        priority=1
    )

    # 发送消息
    print("\n发送消息...")
    await queue.publish(msg.topic, msg.payload, priority=msg.priority)

    # 接收消息
    print("接收消息...")
    received = await queue.get(msg.topic)
    print(f"   收到: {received.payload}")

    # 获取统计
    stats = queue.get_stats()
    print(f"\n队列统计:")
    print(f"  已发布: {stats['published']}")
    print(f"  已消费: {stats['consumed']}")
    print(f"  失败: {stats['failed']}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_async_queue())
