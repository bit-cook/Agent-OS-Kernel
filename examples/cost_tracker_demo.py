"""
Agent-OS-Kernel 成本跟踪演示

展示成本跟踪功能的使用方法
"""

from agent_os_kernel.core.cost_tracker import CostTracker, CostBreakdown


async def demo_cost_tracker():
    """演示成本跟踪"""
    print("=" * 60)
    print("Agent-OS-Kernel 成本跟踪演示")
    print("=" * 60)
    
    # 创建成本跟踪器
    tracker = CostTracker()
    
    # 记录成本
    await tracker.record_cost(
        provider="openai",
        model="gpt-4",
        prompt_tokens=1000,
        completion_tokens=500,
        cost=0.03
    )
    
    await tracker.record_cost(
        provider="anthropic",
        model="claude-3",
        prompt_tokens=2000,
        completion_tokens=1000,
        cost=0.075
    )
    
    # 获取成本统计
    stats = tracker.get_statistics()
    print(f"\n成本统计:")
    print(f"  总成本: ${stats.total_cost:.4f}")
    print(f"  总Token: {stats.total_tokens}")
    print(f"  提供商数: {len(stats.provider_breakdown)}")
    
    # 获取详细分解
    breakdown = tracker.get_breakdown_by_provider()
    print(f"\n按提供商分解:")
    for provider, data in breakdown.items():
        print(f"  {provider}: ${data['cost']:.4f}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(cost_tracker_demo())
