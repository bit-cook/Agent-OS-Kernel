"""
Advanced Features Tests - 高级功能测试
"""

import sys
sys.path.insert(0, '.')

import asyncio


async def test_local_models():
    """测试本地模型"""
    print("\n" + "=" * 60)
    print("Test: Local Models")
    print("=" * 60)
    
    from agent_os_kernel.llm import LLMProviderFactory
    
    factory = LLMProviderFactory()
    providers = factory.list_providers()
    
    print(f"✓ Total providers: {len(providers)}")
    
    # 检查本地 Provider
    local = [p for p in providers if p.local]
    print(f"✓ Local providers: {len(local)}")
    
    for p in local:
        print(f"  🏠 {p.name}: {p.default_model}")
    
    return True


async def test_memory_types():
    """测试记忆类型"""
    print("\n" + "=" * 60)
    print("Test: Memory Types")
    print("=" * 60)
    
    from agent_os_kernel.core.enhanced_memory import (
        EnhancedMemory,
        ShortTermMemory,
        LongTermMemory,
        MemoryType
    )
    
    # 短期记忆
    short = ShortTermMemory(max_entries=10)
    short.add("test1", importance=0.8)
    short.add("test2", importance=0.6)
    print(f"✓ Short-term: {short.get_stats()['count']} items")
    
    # 长期记忆
    long = LongTermMemory(max_entries=100)
    long.add("important fact", importance=0.9)
    print(f"✓ Long-term: {long.get_stats()['count']} items")
    
    # 增强记忆
    memory = EnhancedMemory()
    memory.add("user preference", MemoryType.SHORT_TERM)
    memory.add("key insight", MemoryType.LONG_TERM)
    print(f"✓ Enhanced: working")
    
    return True


async def test_cost_tracker():
    """测试成本追踪"""
    print("\n" + "=" * 60)
    print("Test: Cost Tracker")
    print("=" * 60)
    
    from agent_os_kernel.core.cost_tracker import CostTracker
    
    tracker = CostTracker()
    
    # 记录多个 Provider
    tracker.record("openai", "gpt-4o", 100, 200)
    tracker.record("deepseek", "deepseek-chat", 500, 1000)
    tracker.record("anthropic", "claude", 200, 400)
    
    stats = tracker.get_global_stats()
    print(f"✓ Total cost: ${stats['total_cost']:.4f}")
    print(f"✓ Total requests: {stats['total_requests']}")
    
    return True


async def test_checkpointer():
    """测试检查点"""
    print("\n" + "=" * 60)
    print("Test: Checkpointer")
    print("=" * 60)
    
    from agent_os_kernel.core.checkpointer import Checkpointer
    
    cp = Checkpointer()
    
    # 保存多个检查点
    cp1 = cp.save({"step": 0, "data": "initial"}, thread_id="test")
    cp2 = cp.save({"step": 1, "data": "updated"}, thread_id="test")
    cp3 = cp.save({"step": 2, "data": "final"}, thread_id="test")
    
    print(f"✓ Checkpoints created: 3")
    
    # 获取历史
    history = cp.history(thread_id="test")
    print(f"✓ History: {len(history)} checkpoints")
    
    # 恢复
    restored = cp.restore(cp1.id)
    print(f"✓ Restored to step: {restored['step']}")
    
    return True


async def test_observability():
    """测试可观测性"""
    print("\n" + "=" * 60)
    print("Test: Observability")
    print("=" * 60)
    
    from agent_os_kernel.core.observability import (
        Observability,
        EventType
    )
    
    obs = Observability()
    
    # 启动会话
    session = obs.start_session(name="Test Session")
    print(f"✓ Session: {session.id}")
    
    # 记录事件
    obs.record_event(EventType.AGENT_START)
    obs.record_event(EventType.TASK_START)
    obs.record_event(EventType.TASK_END)
    obs.record_event(EventType.AGENT_END)
    
    timeline = obs.get_timeline()
    print(f"✓ Events: {len(timeline)}")
    
    stats = obs.get_stats()
    print(f"✓ Status: {stats['session']['status']}")
    
    return True


async def test_task_manager():
    """测试任务管理"""
    print("\n" + "=" * 60)
    print("Test: Task Manager")
    print("=" * 60)
    
    from agent_os_kernel.core.task_manager import TaskManager
    
    manager = TaskManager(max_workers=5)
    
    # 创建任务
    task1 = manager.create_task(
        description="Research AI",
        expected_output="Report",
        agent_name="Researcher",
        priority=30
    )
    
    task2 = manager.create_task(
        description="Write report",
        expected_output="Document",
        agent_name="Writer",
        priority=50,
        depends_on=[task1]
    )
    
    print(f"✓ Tasks created: {manager.get_stats()['total_tasks']}")
    
    # 获取统计
    stats = manager.get_stats()
    print(f"✓ Pending: {stats['pending']}")
    print(f"✓ Blocked: {stats['blocked']}")
    
    return True


async def test_agent_definition():
    """测试 Agent 定义"""
    print("\n" + "=" * 60)
    print("Test: Agent Definition")
    print("=" * 60)
    
    from agent_os_kernel.core.agent_definition import (
        AgentDefinition,
        AgentConstraints,
        TaskDefinition,
        CrewDefinition
    )
    
    # Agent
    agent = AgentDefinition(
        name="Researcher",
        role="Senior Researcher",
        goal="Discover breakthroughs",
        backstory="10 years experience",
        constraints=AgentConstraints(max_iterations=100)
    )
    print(f"✓ Agent: {agent.name} ({agent.role})")
    
    # Task
    task = TaskDefinition(
        description="Research AI trends",
        expected_output="Report",
        agent_name="Researcher"
    )
    print(f"✓ Task: {task.description[:30]}...")
    
    # Crew
    crew = CrewDefinition(
        name="Team",
        agents=[agent],
        tasks=[task]
    )
    print(f"✓ Crew: {crew.name} ({len(crew.agents)} agents)")
    
    return True


async def test_kernel_integration():
    """测试内核集成"""
    print("\n" + "=" * 60)
    print("Test: Kernel Integration")
    print("=" * 60)
    
    from agent_os_kernel import AgentOSKernel
    
    kernel = AgentOSKernel()
    print("✓ Kernel initialized")
    
    # 创建 Agent
    agent_id = kernel.spawn_agent(
        name="TestAgent",
        task="Testing",
        priority=50
    )
    print(f"✓ Agent created: {agent_id}")
    
    # 统计
    stats = kernel.get_stats()
    print(f"✓ Total agents: {stats['total_agents']}")
    
    # 工具
    tools = kernel.tool_registry.get_stats()
    print(f"✓ Tools: {tools['total_tools']}")
    
    return True


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 Agent OS Kernel - Advanced Tests")
    print("=" * 60)
    
    tests = [
        ("Local Models", test_local_models),
        ("Memory Types", test_memory_types),
        ("Cost Tracker", test_cost_tracker),
        ("Checkpointer", test_checkpointer),
        ("Observability", test_observability),
        ("Task Manager", test_task_manager),
        ("Agent Definition", test_agent_definition),
        ("Kernel Integration", test_kernel_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = await test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
