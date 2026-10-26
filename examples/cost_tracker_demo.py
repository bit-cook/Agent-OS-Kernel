"""
Agent-OS-Kernel 成本跟踪演示

展示成本跟踪功能的使用方法
"""

from agent_os_kernel.core.cost_tracker import CostTracker

def demo_cost_tracker():
    """演示成本跟踪"""
    print("=" * 60)
    print("Agent-OS-Kernel 成本跟踪演示")
    print("=" * 60)
    
    # 创建成本跟踪器
    tracker = CostTracker()
    
    # 记录成本（成本按内置定价表自动计算）
    tracker.record(
        provider="openai",
        model="gpt-4",
        input_tokens=1000,
        output_tokens=500
    )
    
    tracker.record(
        provider="anthropic",
        model="claude-3",
        input_tokens=2000,
        output_tokens=1000
    )
    
    # 获取成本统计
    stats = tracker.get_global_stats()
    print(f"\n成本统计:")
    print(f"  总成本: ${stats['total_cost']:.4f}")
    print(f"  总Token: {stats['total_tokens']}")
    print(f"  总请求: {stats['total_requests']}")
    print(f"  提供商数: {len(stats['by_provider'])}")
    
    # 获取详细分解
    print(f"\n按提供商分解:")
    for provider, data in stats['by_provider'].items():
        print(f"  {provider}: ${data['cost']:.4f} ({data['requests']} 次请求, {data['tokens']} tokens)")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_cost_tracker()
