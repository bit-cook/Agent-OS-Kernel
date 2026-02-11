"""
Agent-OS-Kernel 缓存系统演示

展示缓存系统的使用方法
"""

from agent_os_kernel.core.cache_system import CacheSystem, CacheLevel


async def demo_cache():
    """演示缓存系统"""
    print("=" * 60)
    print("Agent-OS-Kernel 缓存系统演示")
    print("=" * 60)
    
    # 创建缓存系统
    cache = CacheSystem()
    
    # 设置缓存
    await cache.set(
        key="user:123",
        value={"name": "Alice", "role": "admin"},
        level=CacheLevel.MEMORY,
        ttl=3600
    )
    
    # 获取缓存
    result = await cache.get("user:123")
    print(f"\n获取用户: {result}")
    
    # 检查缓存
    exists = await cache.exists("user:123")
    print(f"缓存存在: {exists}")
    
    # 获取统计
    stats = cache.get_statistics()
    print(f"\n缓存统计:")
    print(f"  命中率: {stats.hit_rate:.2%}")
    print(f"  命中: {stats.hits}")
    print(f"  未命中: {stats.misses}")
    
    # 清除缓存
    await cache.delete("user:123")
    print("\n缓存已删除")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_cache())
