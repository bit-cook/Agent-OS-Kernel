"""
Agent-OS-Kernel 成本跟踪演示

展示成本跟踪功能的使用方法
"""

from agent_os_kernel.core.cost_tracker import CostLimit, CostTracker


def demo_cost_tracker():
    """演示成本跟踪"""
    print("=" * 60)
    print("Agent-OS-Kernel 成本跟踪演示")
    print("=" * 60)
    
    # 创建成本跟踪器（带预算上限）
    tracker = CostTracker(
        limits=CostLimit(max_cost_usd=1.0, max_tokens=100000)
    )
    
    # 记录成本（成本由内置 PRICING 表按 provider/model 自动计算）
    print("\n记录成本...")
    entry1 = tracker.record(
        provider="openai",
        model="gpt-4",
        input_tokens=1000,
        output_tokens=500,
        agent_id="researcher",
        session_id="session-001"
    )
    print(f"  {entry1.provider}/{entry1.model}: ${entry1.total_cost:.4f}")
    
    entry2 = tracker.record(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=2000,
        output_tokens=1000,
        agent_id="writer",
        session_id="session-001"
    )
    print(f"  {entry2.provider}/{entry2.model}: ${entry2.total_cost:.4f}")
    
    entry3 = tracker.record(
        provider="openai",
        model="gpt-4o",
        input_tokens=500,
        output_tokens=200,
        agent_id="researcher",
        session_id="session-001"
    )
    print(f"  {entry3.provider}/{entry3.model}: ${entry3.total_cost:.4f}")
    
    # 单独试算一次成本（不落账）
    est = tracker.calculate_cost("deepseek", "deepseek-chat", 10000, 2000)
    print(f"\n试算 deepseek/deepseek-chat (10k in / 2k out): ${est['total_cost']:.4f}")
    
    # 获取全局统计（get_global_stats 返回 dict）
    stats = tracker.get_global_stats()
    print(f"\n成本统计:")
    print(f"  总成本: ${stats['total_cost']:.4f}")
    print(f"  总Token: {stats['total_tokens']}")
    print(f"  请求数: {stats['total_requests']}")
    print(f"  会话数: {stats['total_sessions']}")
    print(f"  Agent数: {stats['total_agents']}")
    print(f"  预算上限: ${stats['limits']['max_cost_usd']:.2f}")
    
    # 按提供商分解
    print(f"\n按提供商分解:")
    for provider, data in stats["by_provider"].items():
        print(f"  {provider}: ${data['cost']:.4f} ({data['requests']} 次, {data['tokens']} tokens)")
    
    # 按 Agent / 会话分解
    print(f"\n按 Agent 分解:")
    for agent_id in ("researcher", "writer"):
        agent_stats = tracker.get_agent_stats(agent_id)
        if agent_stats:
            print(f"  {agent_id}: ${agent_stats['cost']:.4f} ({agent_stats['requests']} 次)")
    
    session_stats = tracker.get_session_stats("session-001")
    print(f"\n会话 session-001: ${session_stats['cost']:.4f} ({session_stats['requests']} 次)")
    
    # 生成文本报告
    print(f"\n报告:")
    print(tracker.get_report(agent_id="researcher"))
    
    # 导出 CSV
    import os
    import tempfile
    csv_path = os.path.join(tempfile.gettempdir(), "cost_tracker_demo.csv")
    tracker.export_csv(csv_path)
    print(f"已导出 CSV: {csv_path} ({os.path.getsize(csv_path)} 字节)")
    
    # 重置（不带参数时为空操作，需指定 session 或 agent）
    tracker.reset(session_id="session-001")
    print(f"\n按会话重置后总成本: ${tracker.get_global_stats()['total_cost']:.4f}")
    tracker.reset(agent_id="researcher")
    print(f"按 Agent 重置后总成本: ${tracker.get_global_stats()['total_cost']:.4f}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_cost_tracker()
