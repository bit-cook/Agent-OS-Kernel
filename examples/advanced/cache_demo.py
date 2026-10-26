# -*- coding: utf-8 -*-

"""缓存系统演示"""

import asyncio
from datetime import datetime, timezone

from agent_os_kernel.core.cache_system import CacheSystem, CacheEntry


# 兼容层：当前内核的 CacheEntry 用 naive datetime（utcnow）创建，
# 而 is_expired() 用 aware datetime（now(timezone.utc)）比较，
# 导致任何带 TTL 的缓存读取都抛 TypeError。示例中统一为 aware UTC 时间，
# 使 TTL 过期逻辑可以真实运行（库代码本身不做改动）。
def _is_expired(self):
    if self.ttl_seconds is None:
        return False
    created = self.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created).total_seconds() > self.ttl_seconds


CacheEntry.is_expired = _is_expired


async def main():
    print("="*60)
    print("Cache System Demo")
    print("="*60)

    # 创建缓存
    cache = CacheSystem(
        max_size=100,
        default_ttl=60.0
    )

    print("\n📦 基本操作...")

    # 设置缓存
    await cache.set("user:001", {"name": "Alice", "age": 30})
    await cache.set("user:002", {"name": "Bob", "age": 25})
    await cache.set("temp", "data", ttl_seconds=5)

    # 获取缓存
    user = await cache.get("user:001")
    print(f"  用户: {user}")

    # 获取或设置
    value = await cache.get_or_set(
        "computed",
        lambda: "expensive_result",
        ttl_seconds=10
    )
    print(f"  计算值: {value}")

    # 再次获取（命中缓存，不再计算）
    value = await cache.get_or_set(
        "computed",
        lambda: "recomputed_result",
        ttl_seconds=10
    )
    print(f"  再次获取计算值（缓存命中）: {value}")

    # 检查存在
    exists = await cache.exists("user:001")
    print(f"  用户存在: {exists}")
    exists = await cache.exists("missing")
    print(f"  缺失键存在: {exists}")

    # 统计
    stats = cache.get_stats()
    print(f"\n📊 缓存统计:")
    print(f"  命中: {stats['hits']}")
    print(f"  未命中: {stats['misses']}")
    print(f"  命中率: {stats['hit_rate']}")
    print(f"  内存使用: {stats['memory_usage']}/{stats['max_size']}")

    # 删除
    deleted = await cache.delete("user:002")
    print(f"\n🗑️ 删除 user:002: {deleted}")
    print(f"  删除后获取: {await cache.get('user:002')}")

    # TTL 过期演示
    print("\n⏰ TTL 过期演示...")
    await cache.set("ttl:test", "short_lived", ttl_seconds=1)
    print(f"  立即获取: {await cache.get('ttl:test')}")
    await asyncio.sleep(1.1)
    print(f"  1 秒后获取: {await cache.get('ttl:test')}")

    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
