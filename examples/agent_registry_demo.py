"""
Agent-OS-Kernel Agent注册表演示

展示Agent注册表的使用方法
"""

import asyncio

from agent_os_kernel.core.agent_registry import AgentRegistry


async def demo_agent_registry():
    """演示Agent注册表"""
    print("=" * 60)
    print("Agent-OS-Kernel Agent注册表演示")
    print("=" * 60)

    # 创建注册表
    registry = AgentRegistry()
    await registry.initialize()

    # 注册Agent
    print("\n注册Agent...")
    agent = await registry.register(
        agent_id="assistant",
        name="Assistant",
        role="assistant",
        capabilities=["chat", "reasoning"]
    )
    print(f"   注册成功: {agent.name} (version: {agent.version})")

    # 发送心跳（保持在线状态）
    await registry.heartbeat("assistant")

    # 获取Agent
    agent = await registry.get("assistant")
    print(f"   获取Agent: {agent.name if agent else 'Not found'}")

    # 获取所有Agent
    all_agents = await registry.list_all()
    print(f"\n注册Agent数量: {len(all_agents)}")

    # 获取统计
    stats = registry.get_stats()
    print(f"\n注册表统计:")
    print(f"  总数: {stats['total_agents']}")
    print(f"  在线: {stats['active_agents']}")

    await registry.shutdown()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_agent_registry())
