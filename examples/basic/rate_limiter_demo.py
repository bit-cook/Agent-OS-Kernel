"""
Agent-OS-Kernel 速率限制演示

展示速率限制的使用方法
"""

from agent_os_kernel.core.rate_limiter import RateLimiter, RateLimitConfig


async def demo_rate_limiter():
    """演示速率限制"""
    print("=" * 60)
    print("Agent-OS-Kernel 速率限制演示")
    print("=" * 60)

    # 创建速率限制器：每 60 秒 10 次
    limiter = RateLimiter(
        config=RateLimitConfig(
            requests_per_second=10 / 60,
            requests_per_minute=10,
            burst_size=5,
            window_seconds=60,
        )
    )

    # 尝试获取许可
    print("\n尝试获取许可...")
    for i in range(15):
        acquired, wait_time = await limiter.acquire()
        remaining = limiter.get_remaining()
        print(
            f"  请求{i+1}: {'✅' if acquired else '❌'} "
            f"(剩余: {remaining}, 需等待: {wait_time:.2f}s)"
        )

    # 获取统计
    stats = limiter.get_stats()
    print(f"\n速率限制统计:")
    print(f"  速率: {stats['rps']:.3f} 次/秒 ({stats['rpm']} 次/分钟)")
    print(f"  桶容量: {stats['limit']}")
    print(f"  剩余: {stats['remaining']}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_rate_limiter())
