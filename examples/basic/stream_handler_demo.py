"""
Agent-OS-Kernel 流处理演示

展示流处理的使用方法
"""

from agent_os_kernel.core.stream_handler import StreamHandler, StreamManager, StreamType


async def demo_stream():
    """演示流处理"""
    print("=" * 60)
    print("Agent-OS-Kernel 流处理演示")
    print("=" * 60)

    # 创建流处理器（JSON 流，手动刷新以便观察缓冲区）
    handler = StreamHandler(
        stream_id="demo-stream",
        stream_type=StreamType.JSON,
        buffer_size=1000,
        auto_flush=False,
    )

    # 注册回调（回调是异步的）
    processed = []

    async def on_chunk(chunk):
        processed.append(chunk)
        print(f"  [on_chunk] 收到块 {chunk.chunk_index}: {chunk.data}")

    flushed_batches = []

    async def on_flush(chunks):
        flushed_batches.append(chunks)
        print(f"  [on_flush] 刷新 {len(chunks)} 个数据块")

    handler.on_chunk(on_chunk)
    handler.on_flush(on_flush)

    # 启动流
    await handler.start()
    print(f"\n流已启动: {handler.stream_id} (类型: {handler.stream_type.value})")

    # 发送数据
    print("\n发送数据...")
    for i in range(5):
        chunk_id = await handler.write_json({"id": i, "data": f"item-{i}"})
        print(f"  写入 item-{i} -> 块 ID: {chunk_id}")

    # 再发送一个事件
    event_id = await handler.write_event("task_finished", {"items": 5})
    print(f"  写入事件 -> 块 ID: {event_id}")

    # 获取统计
    stats = handler.get_stats()
    print(f"\n流统计（刷新前）:")
    print(f"  状态: {stats['status']}")
    print(f"  已接收块数: {stats['chunks_received']}")
    print(f"  已发送块数: {stats['chunks_sent']}")
    print(f"  缓冲区大小: {stats['buffer_size']}")
    print(f"  已发送字节: {stats['bytes_sent']}")

    # 使用异步迭代器消费缓冲区
    print("\n通过迭代器消费缓冲区:")
    count = 0
    async for chunk in handler.iterator():
        count += 1
        print(f"  块 {chunk.chunk_index}: {chunk.data}")
        if count >= 6:
            break

    # 手动刷新
    print("\n手动刷新...")
    await handler.flush()
    stats = handler.get_stats()
    print(f"\n流统计（刷新后）:")
    print(f"  已接收块数: {stats['chunks_received']}")
    print(f"  已发送块数: {stats['chunks_sent']}")
    print(f"  缓冲区大小: {stats['buffer_size']}")
    print(f"  on_chunk 回调次数: {len(processed)}")
    print(f"  on_flush 回调次数: {len(flushed_batches)}")

    # 再写入两个块后手动刷新，触发 on_flush 回调
    print("\n再次写入并手动刷新...")
    await handler.write_json({"id": 100, "data": "item-100"})
    await handler.write_json({"id": 101, "data": "item-101"})
    await handler.flush()
    print(f"  on_flush 回调次数: {len(flushed_batches)}")

    # 停止流
    await handler.stop()
    stats = handler.get_stats()
    print(f"\n流已停止，最终状态: {stats['status']}")

    # 通过流管理器管理多个流
    print("\n--- StreamManager ---")
    manager = StreamManager()
    s1 = manager.create_stream("stream-a", StreamType.TEXT)
    s2 = manager.create_stream("stream-b", StreamType.EVENTS)
    await s1.start()
    await s1.write("hello")
    await s2.start()
    await s2.write_event("ping", {})
    print(f"  所有流: {manager.list_streams()}")
    mstats = manager.get_stats()
    print(f"  流管理器统计: {mstats}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_stream())
