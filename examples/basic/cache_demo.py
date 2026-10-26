"""
Agent-OS-Kernel 缓存系统演示

展示缓存系统的使用方法
"""

import asyncio
from datetime import datetime, timezone

from agent_os_kernel.core.cache_system import CacheEntry, CacheLevel, CacheSystem, EvictionPolicy


async def demo_cache():
    """演示缓存系统"""
    print("=" * 60)
    print("Agent-OS-Kernel 缓存系统演示")
    print("=" * 60)
    
    # 创建缓存系统
    # 注意：当前内核 CacheEntry.created_at 默认使用 naive UTC 时间戳，
    # 而 CacheEntry.is_expired() 用 aware UTC 做差，两者相减会抛 TypeError，
    # 因此只要条目带 TTL，get/exists 就会失败。这里用 default_ttl=0 关闭 TTL。
    # 淘汰策略用 FIFO：LRU 按 accessed_at 比较，touch() 写入 aware 时间戳、
    # 默认值是 naive，混用同样会抛 TypeError。
    cache = CacheSystem(
        max_size=3,
        default_ttl=0,
        eviction_policy=EvictionPolicy.FIFO
    )
    
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
    
    # 未命中走默认值
    missing = await cache.get("user:404", default={"name": "Unknown"})
    print(f"未命中取默认值: {missing}")
    
    # get_or_set：命中则返回缓存，未命中则执行工厂并回填
    calls = []
    
    async def load_profile():
        calls.append(1)
        return {"name": "Bob", "role": "editor"}
    
    profile = await cache.get_or_set("user:456", load_profile)
    print(f"get_or_set 首次: {profile} (工厂调用 {len(calls)} 次)")
    profile = await cache.get_or_set("user:456", load_profile)
    print(f"get_or_set 再次: {profile} (工厂调用 {len(calls)} 次)")
    
    # 触发淘汰（max_size=3，FIFO 淘汰最早写入的条目）
    await cache.set("user:789", {"name": "Carol"})
    await cache.set("user:999", {"name": "Dave"})
    print(f"\n写入 4 个键后，最早写入的 user:123 是否仍在: {await cache.exists('user:123')}")
    
    # 获取统计（get_stats 返回 dict，hit_rate 为百分比字符串）
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  命中率: {stats['hit_rate']}")
    print(f"  命中: {stats['hits']}")
    print(f"  未命中: {stats['misses']}")
    print(f"  写入: {stats['writes']}")
    print(f"  淘汰: {stats['evictions']}")
    print(f"  内存占用: {stats['memory_usage']}/{stats['max_size']}")
    
    # 删除缓存
    await cache.delete("user:456")
    print(f"\n删除 user:456 后存在: {await cache.exists('user:456')}")
    
    # 清空缓存
    await cache.clear(CacheLevel.MEMORY)
    print(f"清空后剩余条目: {cache.get_stats()['memory_usage']}")
    
    # TTL 过期判定（CacheEntry 为公开 dataclass，需显式传入 aware 时间戳）
    print("\nTTL 过期判定:")
    entry = CacheEntry(
        key="session",
        value="token",
        created_at=datetime.now(timezone.utc),
        ttl_seconds=0.2
    )
    print(f"  刚创建是否过期: {entry.is_expired()}")
    await asyncio.sleep(0.3)
    print(f"  0.3 秒后是否过期: {entry.is_expired()}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_cache())
