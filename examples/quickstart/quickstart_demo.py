"""
Quick Start Demo - 快速开始演示

5分钟学会使用 Agent OS Kernel
"""

import asyncio
import sys
sys.path.insert(0, '.')


async def step1_init():
    """步骤 1: 初始化"""
    print("\n" + "=" * 60)
    print("Step 1: Initialize")
    print("=" * 60)
    
    from agent_os_kernel import AgentOSKernel
    
    kernel = AgentOSKernel()
    print("✅ Kernel initialized!")
    print(f"   Version: {kernel.VERSION}")
    
    return kernel


async def step2_spawn(kernel):
    """步骤 2: 创建 Agent"""
    print("\n" + "=" * 60)
    print("Step 2: Spawn Agent")
    print("=" * 60)
    
    agent_id = kernel.spawn_agent(
        name="Assistant",
        task="Help users with their questions",
        priority=50
    )
    
    print(f"✅ Agent spawned!")
    print(f"   Agent ID: {agent_id}")
    
    return agent_id


async def step3_tools(kernel):
    """步骤 3: 使用工具"""
    print("\n" + "=" * 60)
    print("Step 3: Use Tools")
    print("=" * 60)
    
    registry = kernel.tool_registry
    tools = registry.get_stats()
    print(f"✅ Available tools: {tools['total_tools']}")
    
    for name in list(registry.tools.keys())[:3]:
        print(f"   - {name}")


async def step4_memory(kernel):
    """步骤 4: 使用记忆"""
    print("\n" + "=" * 60)
    print("Step 4: Use Memory")
    print("=" * 60)
    
    from agent_os_kernel.core.enhanced_memory import EnhancedMemory, MemoryType
    
    memory = EnhancedMemory()
    
    # 添加短期记忆
    memory.add(
        "User prefers concise answers",
        memory_type=MemoryType.SHORT_TERM,
        importance=0.8
    )
    
    # 添加长期记忆
    memory.add(
        "User is working on AI agent development",
        memory_type=MemoryType.LONG_TERM,
        importance=0.9
    )
    
    print("✅ Memories added!")
    
    # 搜索
    results = memory.search("AI")
    print(f"✅ Search results: {len(results)} memories found")


async def step5_metrics(kernel):
    """步骤 5: 查看指标"""
    print("\n" + "=" * 60)
    print("Step 5: View Metrics")
    print("=" * 60)
    
    stats = kernel.get_stats()
    print(f"✅ Stats:")
    print(f"   Total Agents: {stats['total_agents']}")
    print(f"   Active Agents: {stats['active_agents']}")


async def demo_basic():
    """基本演示"""
    print("\n" + "=" * 60)
    print("🚀 Basic Demo")
    print("=" * 60)
    
    kernel = await step1_init()
    agent_id = await step2_spawn(kernel)
    await step3_tools(kernel)
    await step4_memory(kernel)
    await step5_metrics(kernel)
    
    print("\n✅ Basic demo complete!")
    return kernel


async def demo_with_llm():
    """LLM 演示"""
    print("\n" + "=" * 60)
    print("🚀 LLM Demo")
    print("=" * 60)
    
    from agent_os_kernel.llm import create_mock_provider
    from agent_os_kernel.llm.provider import ChatMessage

    provider = create_mock_provider()
    print(f"✅ Provider created: {provider.provider_name}")

    messages = [ChatMessage(role="user", content="Hello!")]
    result = await provider.chat(messages)
    print(f"✅ Response: {result.get('content', '')[:50]}...")
    
    # 成本追踪
    from agent_os_kernel.core.cost_tracker import CostTracker
    tracker = CostTracker()
    tracker.record("mock", "test", 10, 20)
    stats = tracker.get_global_stats()
    print(f"✅ Cost: ${stats['total_cost']:.4f}")


async def demo_observability():
    """可观测性演示"""
    print("\n" + "=" * 60)
    print("🚀 Observability Demo")
    print("=" * 60)
    
    from agent_os_kernel.core.observability import Observability

    obs = Observability()
    session = obs.start_session(name="QuickStart", tags=["demo"])
    print(f"✅ Session started: {session.id}")

    obs.record_event("agent_start")
    obs.record_event("task_start")
    obs.record_event("task_complete")
    obs.record_event("agent_end")
    
    timeline = obs.get_timeline()
    print(f"✅ Events recorded: {len(timeline)}")
    
    obs.end_session(status="completed")
    print("✅ Session ended")


async def demo_configuration():
    """配置演示"""
    print("\n" + "=" * 60)
    print("🚀 Configuration Demo")
    print("=" * 60)
    
    import yaml
    
    # 示例配置
    config = {
        "kernel": {
            "max_agents": 10,
            "default_priority": 50
        },
        "llm": {
            "default_provider": "mock",
            "models": [
                {"name": "assistant", "provider": "mock"}
            ]
        },
        "storage": {
            "backend": "memory"
        }
    }
    
    print("📄 Example Configuration:")
    print(yaml.dump(config, default_flow_style=False))
    
    print("✅ Configuration demo complete!")


async def main():
    """运行所有演示"""
    print("=" * 60)
    print("🚀 Agent OS Kernel - Quick Start Demo")
    print("=" * 60)
    print("\nLearn in 5 minutes!")
    
    await demo_basic()
    await demo_with_llm()
    await demo_observability()
    await demo_configuration()
    
    print("\n" + "=" * 60)
    print("✅ Quick Start Complete!")
    print("=" * 60)
    print("\n📚 Next Steps:")
    print("   1. Read: docs/quickstart.md")
    print("   2. Explore: examples/")
    print("   3. Learn: docs/local-models.md")
    print("   4. Deploy: examples/distributed.py")


if __name__ == "__main__":
    asyncio.run(main())
