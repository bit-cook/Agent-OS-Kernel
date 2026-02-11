"""
Agent-OS-Kernel Agent注册表演示

展示Agent注册表的使用方法
"""

from agent_os_kernel.core.agent_registry import AgentRegistry


def demo_agent_registry():
    """演示Agent注册表"""
    print("=" * 60)
    print("Agent-OS-Kernel Agent注册表演示")
    print("=" * 60)
    
    # 创建注册表
    registry = AgentRegistry()
    
    # 注册Agent
    print("\n注册Agent...")
    registry.register(
        agent_id="assistant",
        name="Assistant",
        version="1.0.0",
        capabilities=["chat", "reasoning"]
    )
    
    # 获取Agent
    agent = registry.get("assistant")
    print(f"   获取Agent: {agent.name if agent else 'Not found'}")
    
    # 获取所有Agent
    all_agents = registry.list_all()
    print(f"\n注册Agent数量: {len(all_agents)}")
    
    # 获取统计
    stats = registry.get_statistics()
    print(f"\n注册表统计:")
    print(f"  总数: {stats.total_agents}")
    print(f"  在线: {stats.online_agents}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_agent_registry()
