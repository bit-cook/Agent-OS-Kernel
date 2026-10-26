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

    # 创建速率限制器：每分钟 10 次，桶容量（突发）5 次
    limiter = RateLimiter(
        config=RateLimitConfig(
            requests_per_second=10 / 60,
            requests_per_minute=10,
            burst_size=5,
            window_seconds=60,
        ),
        name="demo",
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

    # 检查是否超限（不消耗令牌）
    print(f"\n当前是否在限制内: {await limiter.check_limit()}")

    # 等待获取许可：消耗完后等待下一个令牌
    print("\n等待获取下一个许可（最多等 10 秒）...")
    ok = await limiter.wait(timeout=10.0)
    print(f"  等待结果: {'成功获取' if ok else '超时失败'}")
    print(f"  当前剩余: {limiter.get_remaining()}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_rate_limiter())
