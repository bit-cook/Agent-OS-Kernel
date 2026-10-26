"""
Agent-OS-Kernel 异步队列演示

展示异步队列的使用方法
"""

import asyncio

from agent_os_kernel.core.async_queue import AsyncQueue, MessageStatus, QueueType


async def demo_async_queue():
    """演示异步队列"""
    print("=" * 60)
    print("Agent-OS-Kernel 异步队列演示")
    print("=" * 60)
    
    # 创建队列（FIFO 模式，容量 100）
    queue = AsyncQueue(name="demo", queue_type=QueueType.FIFO, max_size=100)
    
    # 订阅主题，注册回调消费者
    received = []
    seen = set()
    
    async def process_message(msg):
        # 该队列为 at-least-once 投递，按 msg_id 去重
        if msg.msg_id in seen:
            return
        seen.add(msg.msg_id)
        print(f"   处理消息: {msg.topic} -> {msg.payload}")
        received.append(msg.payload)
        msg.status = MessageStatus.COMPLETED
    
    print("\n订阅主题 'tasks'...")
    await queue.subscribe("tasks", process_message)
    
    # 发布消息
    print("发布消息...")
    for i in range(3):
        msg_id = await queue.publish(
            topic="tasks",
            payload={"task": "process", "data": f"item-{i}"},
            priority=1
        )
        print(f"   已发布: {msg_id[:8]}...")
        await asyncio.sleep(0.05)
    
    # 等待消费者处理
    await asyncio.sleep(0.3)
    
    # 手动拉取一条消息（不经订阅者）
    print("\n手动拉取消息...")
    await queue.publish("manual", {"task": "manual-pull", "data": "test"})
    msg = await queue.get("manual", timeout=1.0)
    if msg:
        print(f"   收到: {msg.payload} (状态: {msg.status.value})")
        await queue.ack(msg.msg_id)
    
    # 队列剩余情况
    print(f"\n'tasks' 队列剩余: {queue.get_queue_size('tasks')}")
    print(f"主题列表: {queue.list_topics()}")
    print(f"去重后收到 {len(received)} 条消息")
    
    # 获取统计
    stats = queue.get_stats()
    print(f"\n队列统计:")
    print(f"  已发布: {stats['published']}")
    print(f"  已消费: {stats['consumed']}")
    print(f"  失败: {stats['failed']}")
    print(f"  主题数: {stats['topics']}")
    print(f"  订阅者数: {stats['subscribers']}")
    
    # 停止队列
    await queue.stop()
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_async_queue())
