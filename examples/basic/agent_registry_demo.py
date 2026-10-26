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
    
    # 注册Agent（异步方法，role 为必填）
    print("\n注册Agent...")
    agent = await registry.register(
        agent_id="assistant",
        name="Assistant",
        role="Chat Assistant",
        capabilities=["chat", "reasoning"]
    )
    print(f"   已注册: {agent.name} (role: {agent.role}, status: {agent.status})")
    
    # 获取Agent
    found = await registry.get("assistant")
    print(f"   获取Agent: {found.name if found else 'Not found'}")
    
    # 获取所有Agent
    all_agents = await registry.list_all()
    print(f"\n注册Agent数量: {len(all_agents)}")
    for a in all_agents:
        print(f"   - {a.agent_id}: {a.name} [{a.status}]")
    
    # 心跳
    alive = await registry.heartbeat("assistant")
    print(f"\n心跳更新: {'成功' if alive else '失败'}")
    
    # 注销
    removed = await registry.unregister("assistant")
    print(f"注销Agent: {'成功' if removed else '失败'}")
    print(f"剩余Agent数量: {len(await registry.list_all())}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_agent_registry())
