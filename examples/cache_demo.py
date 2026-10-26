"""
Agent-OS-Kernel 缓存系统演示

展示缓存系统的使用方法
"""

import time
from datetime import datetime, timezone

from agent_os_kernel.core.cache_system import CacheSystem, CacheEntry, CacheLevel

async def demo_cache():
    """演示缓存系统"""
    print("=" * 60)
    print("Agent-OS-Kernel 缓存系统演示")
    print("=" * 60)

    # 创建缓存系统（default_ttl=0 表示条目不过期；
    # 当前版本 CacheEntry.is_expired 对带 TTL 条目存在 naive/aware 时间比较问题）
    cache = CacheSystem(default_ttl=0)

    # 设置缓存
    await cache.set(
        key="user:123",
        value={"name": "Alice", "role": "admin"},
        level=CacheLevel.MEMORY
    )

    # 获取缓存
    result = await cache.get("user:123")
    print(f"\n获取用户: {result}")

    # 检查缓存
    exists = await cache.exists("user:123")
    print(f"缓存存在: {exists}")

    # 获取统计
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  命中率: {stats['hit_rate']}")
    print(f"  命中: {stats['hits']}")
    print(f"  未命中: {stats['misses']}")
    print(f"  写入: {stats['writes']}")
    print(f"  内存占用: {stats['memory_usage']}/{stats['max_size']}")

    # TTL 过期演示（CacheEntry 直接演示 TTL 语义）
    print("\nTTL过期演示...")
    entry = CacheEntry(key="ttl-demo", value="data", ttl_seconds=1)
    # is_expired() 内部使用 aware datetime 比较，这里显式使用 aware 时间戳
    entry.created_at = datetime.now(timezone.utc)
    print(f"  刚创建: 过期={entry.is_expired()}")
    time.sleep(1.1)
    print(f"  1秒后: 过期={entry.is_expired()}")

    # 清除缓存
    await cache.delete("user:123")
    print("\n缓存已删除")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_cache())
