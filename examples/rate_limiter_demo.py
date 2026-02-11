"""
Agent-OS-Kernel 速率限制演示

展示速率限制的使用方法
"""

from agent_os_kernel.core.rate_limiter import RateLimiter


async def demo_rate_limiter():
    """演示速率限制"""
    print("=" * 60)
    print("Agent-OS-Kernel 速率限制演示")
    print("=" * 60)
    
    # 创建速率限制器
    limiter = RateLimiter(rate=10, period=60)  # 每60秒10次
    
    # 尝试获取许可
    print("\n尝试获取许可...")
    for i in range(15):
        acquired = await limiter.acquire()
        remaining = limiter.get_remaining()
        print(f"  请求{i+1}: {'✅' if acquired else '❌'} (剩余: {remaining})")
    
    # 获取统计
    stats = limiter.get_statistics()
    print(f"\n速率限制统计:")
    print(f"  速率: {stats.rate}/period")
    print(f"  已使用: {stats.used}")
    print(f"  剩余: {stats.remaining}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_rate_limiter())
