"""库 bug 修复回归测试（示例翻修时子代理发现、本轮修复的 6 项）

每个用例对应一个真实缺陷的复现与防回归。
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from agent_os_kernel.core.cache_system import CacheEntry, CacheSystem
from agent_os_kernel.core.optimization.compressor import (
    CompressionStrategy,
    ContextCompressor,
)
from agent_os_kernel.core.batch_processor import BatchProcessor
from agent_os_kernel.core.async_queue import AsyncQueue
from agent_os_kernel.core.lock_manager import LockManager, async_lock


class TestCacheTTL:
    """#1 CacheEntry naive/aware datetime 混用：带 TTL 的读取必崩"""

    @pytest.mark.asyncio
    async def test_ttl_read_write_cycle(self):
        cache = CacheSystem(default_ttl=3600)   # 原来这样构造后 get 必 TypeError
        await cache.set("k", "v")
        assert await cache.get("k") == "v"
        assert await cache.exists("k")

    def test_is_expired_with_aware_timestamps(self):
        entry = CacheEntry(
            key="x", value=1, ttl_seconds=0.001,
            created_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert entry.is_expired() is True

    def test_touch_keeps_aware(self):
        entry = CacheEntry(key="x", value=1)
        entry.touch()
        assert entry.accessed_at.tzinfo is not None


class TestCompressorImportanceFilter:
    """#2 _filter_by_importance 排序键返回 dict：保留 >=2 条消息必崩"""

    def test_importance_filter_multiple_messages(self):
        from agent_os_kernel.core.optimization.compressor import CompressionConfig
        c = ContextCompressor(CompressionConfig(max_tokens=10000))
        msgs = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "重要：生产数据库密码已轮换"},
            {"role": "assistant", "content": "好的，已记录。"},
            {"role": "user", "content": "谢谢"},
        ]
        result = c.compress_messages(msgs, strategy=CompressionStrategy.IMPORTANCE_FILTER)
        assert len(result) >= 2                      # 原来这里就崩
        assert [m["content"] for m in result] == [m["content"] for m in msgs]  # 顺序保持


class TestBatchProcessorFlush:
    """#3 flush 不清 items：重复 flush 双重计数"""

    @pytest.mark.asyncio
    async def test_flush_is_idempotent(self):
        p = BatchProcessor(batch_size=3)
        for i in range(7):
            await p.add_task({"n": i})
        assert p.get_statistics()["processed_count"] == 6   # 两个满批
        await p.flush()
        assert p.get_statistics()["processed_count"] == 7   # 余 1
        await p.flush()
        assert p.get_statistics()["processed_count"] == 7   # 原来这里变 8+


class TestAsyncQueueSingleDelivery:
    """#4 subscribe 双集合注册：每条消息投递两次"""

    @pytest.mark.asyncio
    async def test_no_double_delivery(self):
        q = AsyncQueue()
        received = []
        await q.subscribe("news", lambda m: received.append(m.msg_id))
        await q.start()
        try:
            for i in range(3):
                await q.publish("news", {"i": i})
            await asyncio.sleep(0.5)
            assert len(received) == 3                  # 原来 6
        finally:
            await q.stop()


class TestSemaphoreMultiHolder:
    """#5 acquire_semaphore 覆盖 _locks[name]：只有最后持有者能 release"""

    @pytest.mark.asyncio
    async def test_every_holder_can_release(self):
        m = LockManager()
        results = [await m.acquire_semaphore("pool", f"w{i}", max_concurrent=3) for i in range(3)]
        assert all(results)
        assert await m.acquire_semaphore("pool", "w4", max_concurrent=3) is False
        releases = [await m.release("pool", f"w{i}") for i in range(3)]
        assert all(releases)                           # 原来后两个 False
        assert not m.is_locked("pool")


class TestAsyncLockOwnerId:
    """#6 async_lock 硬编码 owner_id：传 owner_id 必 TypeError"""

    @pytest.mark.asyncio
    async def test_owner_id_parameter(self):
        m = LockManager()
        async with async_lock(m, "res", owner_id="worker-7") as lock:
            assert lock.owner_id == "worker-7"
        assert not m.is_locked("res")

    @pytest.mark.asyncio
    async def test_default_owner(self):
        m = LockManager()
        async with async_lock(m, "res2") as lock:
            assert lock.owner_id == "context"
