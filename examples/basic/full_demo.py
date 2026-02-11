"""
Agent-OS-Kernel 完整功能演示

展示所有核心模块的综合使用
"""

from agent_os_kernel import AgentOSKernel


async def demo_full():
    """完整演示"""
    print("=" * 70)
    print("Agent-OS-Kernel 完整功能演示")
    print("=" * 70)
    
    # 创建内核
    kernel = AgentOSKernel()
    print("\n✅ AgentOSKernel 创建成功")
    
    # 核心模块演示
    print("\n📦 核心模块:")
    
    from agent_os_kernel.core import (
        ContextManager,
        EventBus,
        StorageManager,
        CircuitBreaker
    )
    
    ctx = ContextManager()
    print("   ✅ ContextManager")
    
    bus = EventBus()
    print("   ✅ EventBus")
    
    storage = StorageManager()
    print("   ✅ StorageManager")
    
    cb = CircuitBreaker(name="demo")
    print("   ✅ CircuitBreaker")
    
    # LLM 模块演示
    print("\n🤖 LLM模块:")
    from agent_os_kernel.llm import MockProvider
    
    provider = MockProvider()
    print("   ✅ MockProvider")
    
    # Agent 模块演示
    print("\n👥 Agent模块:")
    from agent_os_kernel.core import AgentPool
    
    pool = AgentPool()
    print("   ✅ AgentPool")
    
    # 工具和可观测性演示
    print("\n🛠️ 工具和可观测性:")
    from agent_os_kernel.tools.registry import ToolRegistry
    from agent_os_kernel.core.observability import Observability
    
    registry = ToolRegistry()
    print("   ✅ ToolRegistry")
    
    obs = Observability()
    print("   ✅ Observability")
    
    print("\n" + "=" * 70)
    print("🎉 完整演示成功!")
    print("=" * 70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_full())
