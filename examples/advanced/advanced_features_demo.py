"""
Advanced Features Demo

展示新增的高级功能:
- Agent 定义 (role/goal/backstory)
- Task 管理
- Checkpointer (时间旅行)
- 增强记忆
- 成本追踪
- 可观测性
"""

import asyncio
import copy
import sys
sys.path.insert(0, '.')


async def demo_agent_definition():
    """Agent 定义演示"""
    print("\n" + "=" * 60)
    print("Demo: Agent Definition")
    print("=" * 60)

    from agent_os_kernel.core.agent_definition import (
        AgentDefinition,
        AgentConstraints,
        TaskDefinition,
        CrewDefinition,
    )

    # 创建 Agent
    researcher = AgentDefinition(
        name="AI Researcher",
        role="Senior AI Researcher",
        goal="Discover and analyze cutting-edge AI technologies",
        backstory="PhD in Computer Science with 10 years of AI research experience",
        tools=["search", "browser", "document_reader"],
        constraints=AgentConstraints(
            max_iterations=100,
            max_cost_usd=50.0,
            require_approval=False
        )
    )

    writer = AgentDefinition(
        name="Technical Writer",
        role="Senior Technical Writer",
        goal="Create clear and comprehensive technical documentation",
        backstory="Technical writer with experience in AI and software documentation",
        tools=["document_writer", "editor"]
    )

    print(f"✓ Created agent: {researcher.name}")
    print(f"  Role: {researcher.role}")
    print(f"  Goal: {researcher.goal}")
    print(f"  Backstory: {researcher.backstory[:50]}...")

    # 创建 Task
    research_task = TaskDefinition(
        description="Research the latest developments in LLM agents",
        expected_output="Comprehensive report on LLM agent technologies",
        agent_name="AI Researcher",
        priority=30,
        timeout=600.0
    )

    write_task = TaskDefinition(
        description="Write a technical blog post about the research findings",
        expected_output="Well-structured blog post with code examples",
        agent_name="Technical Writer",
        priority=50,
        depends_on=["task-1"]
    )

    print(f"\n✓ Created tasks:")
    print(f"  - {research_task.description}")
    print(f"  - {write_task.description}")

    # 创建 Crew
    crew = CrewDefinition(
        name="AI Research Team",
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process_mode="sequential",
        memory_enabled=True
    )

    print(f"\n✓ Created crew: {crew.name}")
    print(f"  Agents: {len(crew.agents)}")
    print(f"  Tasks: {len(crew.tasks)}")
    print(f"  Process: {crew.process_mode}")


async def demo_task_manager():
    """Task 管理演示"""
    print("\n" + "=" * 60)
    print("Demo: Task Manager")
    print("=" * 60)

    from agent_os_kernel.core.task_manager import TaskManager

    manager = TaskManager(max_concurrent=3)

    # 任务规格：描述、执行 Agent、依赖关系
    task_specs = [
        {
            "task_id": "task-1",
            "description": "Gather information about AutoGPT",
            "expected_output": "Detailed notes on AutoGPT capabilities",
            "agent_name": "Researcher",
            "depends_on": [],
        },
        {
            "task_id": "task-2",
            "description": "Gather information about CrewAI",
            "expected_output": "Detailed notes on CrewAI capabilities",
            "agent_name": "Researcher",
            "depends_on": [],
        },
        {
            "task_id": "task-3",
            "description": "Write comparative analysis",
            "expected_output": "Comparison report between AutoGPT and CrewAI",
            "agent_name": "Writer",
            "depends_on": ["task-1", "task-2"],
        },
    ]

    async def research(topic: str):
        """模拟调研任务"""
        await asyncio.sleep(0.05)
        return f"Notes on {topic}"

    async def write_report():
        """模拟写作任务"""
        await asyncio.sleep(0.05)
        return "Comparison report: AutoGPT vs CrewAI"

    print(f"✓ Created {len(task_specs)} tasks")
    for spec in task_specs:
        deps = ", ".join(spec["depends_on"]) or "无"
        print(f"  - {spec['task_id']}: {spec['description']} (依赖: {deps})")

    # 按依赖顺序执行：先并发执行无依赖任务，再执行下游任务
    print(f"\nExecuting tasks...")

    async def run(spec):
        if spec["task_id"] == "task-3":
            handler = write_report
        else:
            topic = "AutoGPT" if spec["task_id"] == "task-1" else "CrewAI"
            handler = lambda: research(topic)

        return await manager.execute(
            execution_id=f"exec-{spec['task_id']}",
            task_id=spec["task_id"],
            agent_id=spec["agent_name"],
            handler=handler,
            timeout=10.0,
        )

    # 第一批：task-1 / task-2 并发执行（受 max_concurrent 限制）
    first_batch = [s for s in task_specs if not s["depends_on"]]
    await asyncio.gather(*[run(s) for s in first_batch])

    # 第二批：task-3 依赖前两个任务
    second_batch = [s for s in task_specs if s["depends_on"]]
    await asyncio.gather(*[run(s) for s in second_batch])

    # 列出任务执行状态
    print(f"\nTask Status:")
    for spec in task_specs:
        execution = manager.get_execution(f"exec-{spec['task_id']}")
        if execution is not None:
            duration = execution.get_duration()
            print(f"  - {spec['task_id']}: {execution.status.value} "
                  f"(agent={execution.agent_id}, {duration * 1000:.0f}ms)")

    stats = manager.get_stats()
    print(f"\nManager Stats: {stats['successful']}/{stats['total_executions']} succeeded, "
          f"max_concurrent={manager.max_concurrent}")


async def demo_checkpointer():
    """Checkpointer 演示"""
    print("\n" + "=" * 60)
    print("Demo: Checkpointer (Time Travel)")
    print("=" * 60)

    from agent_os_kernel.core.checkpointer import Checkpointer

    # 创建检查点管理器
    checkpointer = Checkpointer(max_checkpoints=5)

    # 模拟工作流状态
    state = {
        "step": 0,
        "data": [],
        "progress": 0.0
    }

    # 保存初始状态
    cp1 = await checkpointer.create(
        name="workflow-1",
        state=copy.deepcopy(state),
        tag="initial",
        metadata={"notes": "Initial"}
    )
    print(f"✓ Saved checkpoint: {cp1[:8]}")

    # 更新状态
    state["step"] = 1
    state["data"].append("item1")
    state["progress"] = 0.25
    cp2 = await checkpointer.create(
        name="workflow-1",
        state=copy.deepcopy(state),
        metadata={"notes": "Step 1"}
    )

    state["step"] = 2
    state["data"].append("item2")
    state["progress"] = 0.50
    cp3 = await checkpointer.create(
        name="workflow-1",
        state=copy.deepcopy(state),
        metadata={"notes": "Step 2"}
    )

    print(f"✓ Saved 3 checkpoints")

    # 获取历史
    history = await checkpointer.list_checkpoints(name="workflow-1", limit=10)
    print(f"\nCheckpoint History:")
    for cp in history:
        print(f"  - {cp.checkpoint_id[:8]}: {cp.metadata.get('notes')} (step={cp.state['step']})")

    # 时间旅行 - 恢复到早期状态
    print(f"\nTime Traveling to {cp2[:8]}...")
    restored = await checkpointer.restore(cp2)
    print(f"  Restored state: step={restored['step']}, items={len(restored['data'])}")

    # 按标签检索
    tagged = await checkpointer.get_by_tag("initial")
    if tagged is not None:
        print(f"  Tagged checkpoint 'initial': step={tagged.state['step']}")


async def demo_memory():
    """增强记忆演示"""
    print("\n" + "=" * 60)
    print("Demo: Enhanced Memory")
    print("=" * 60)

    from agent_os_kernel.core.enhanced_memory import EnhancedMemory, MemoryType

    # 创建记忆系统
    memory = EnhancedMemory(short_term_max=20, long_term_max=1000)

    # 添加短期记忆 - 对话历史
    print("Adding short-term memories (conversation):")
    memory.add(
        "User asked about creating AI agents",
        memory_type=MemoryType.SHORT_TERM,
        importance=0.8,
        tags=["conversation", "ai"]
    )
    memory.add(
        "User mentioned preference for Python",
        memory_type=MemoryType.SHORT_TERM,
        importance=0.6,
        tags=["conversation", "python"]
    )

    # 添加长期记忆 - 重要事实
    print("\nAdding long-term memories (important facts):")
    memory.add(
        "AutoGPT is an autonomous AI agent that can pursue complex goals",
        memory_type=MemoryType.LONG_TERM,
        importance=0.9,
        tags=["autogpt", "autonomous"]
    )
    memory.add(
        "CrewAI enables multi-agent collaboration with role-based agents",
        memory_type=MemoryType.LONG_TERM,
        importance=0.85,
        tags=["crewai", "multi-agent"]
    )

    # 搜索记忆
    print("\nSearching memories for 'agent':")
    results = memory.search("agent", limit=5)
    for item in results:
        print(f"  - [{item.memory_type}] {item.content[:60]}...")

    # 获取统计
    stats = memory.get_stats()
    print(f"\nMemory Stats:")
    print(f"  Short-term: {stats['short_term']['count']} items")
    print(f"  Long-term: {stats['long_term']['count']} items")


async def demo_cost_tracker():
    """成本追踪演示"""
    print("\n" + "=" * 60)
    print("Demo: Cost Tracker")
    print("=" * 60)

    from agent_os_kernel.core.cost_tracker import CostTracker, CostLimit

    # 创建成本追踪器
    tracker = CostTracker(limits=CostLimit(max_cost_usd=100.0))

    # 记录 API 调用
    print("Recording API calls:")

    entry1 = tracker.record(
        provider="openai",
        model="gpt-4o",
        input_tokens=150,
        output_tokens=300,
        agent_id="researcher",
        task_id="task-1"
    )
    print(f"  OpenAI GPT-4o: ${entry1.total_cost:.4f}")

    entry2 = tracker.record(
        provider="deepseek",
        model="deepseek-chat",
        input_tokens=500,
        output_tokens=1000,
        agent_id="researcher",
        task_id="task-2"
    )
    print(f"  DeepSeek Chat: ${entry2.total_cost:.4f}")

    entry3 = tracker.record(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=200,
        output_tokens=400,
        agent_id="writer",
        task_id="task-3"
    )
    print(f"  Claude Sonnet: ${entry3.total_cost:.4f}")

    # 获取全局统计
    stats = tracker.get_global_stats()
    print(f"\nCost Summary:")
    print(f"  Total Cost: ${stats['total_cost']:.4f}")
    print(f"  Total Tokens: {stats['total_tokens']:,}")
    print(f"  Total Requests: {stats['total_requests']}")

    print(f"\nBy Provider:")
    for provider, data in stats.get("by_provider", {}).items():
        print(f"  - {provider}: ${data['cost']:.4f} ({data['requests']} calls)")

    # 按 Agent 统计
    print(f"\nBy Agent:")
    for agent_id in ["researcher", "writer"]:
        data = tracker.get_agent_stats(agent_id)
        if data:
            print(f"  - {agent_id}: ${data.get('cost', 0.0):.4f} ({data.get('requests', 0)} calls)")


async def demo_observability():
    """可观测性演示"""
    print("\n" + "=" * 60)
    print("Demo: Observability")
    print("=" * 60)

    from agent_os_kernel.core.observability import (
        Observability,
        EventType,
    )

    # 创建可观测性系统
    obs = Observability()

    # 启动会话
    session = obs.start_session(
        name="Research Project",
        config={"model": "gpt-4o"},
        tags=["research", "demo"]
    )
    print(f"✓ Started session: {session.id}")

    # 模拟 Agent 执行
    print("\nSimulating agent execution:")

    obs.record_event(
        EventType.AGENT_START,
        agent_id="researcher",
        data={"task": "Research AI agents"}
    )
    print(f"  ✓ Agent started: researcher")

    obs.record_event(
        EventType.LLM_REQUEST,
        agent_id="researcher",
        data={"provider": "openai", "model": "gpt-4o"}
    )

    obs.record_event(
        EventType.LLM_RESPONSE,
        agent_id="researcher",
        data={"provider": "openai", "output_tokens": 500},
        duration_ms=1250.0
    )
    print(f"  ✓ LLM call completed: 1.25s")

    obs.record_event(
        EventType.TOOL_CALL,
        agent_id="researcher",
        data={"tool": "browser", "url": "https://github.com"}
    )

    obs.record_event(
        EventType.TOOL_RESULT,
        agent_id="researcher",
        data={"tool": "browser", "result": "success"}
    )
    print(f"  ✓ Tool call completed")

    obs.record_event(
        EventType.AGENT_END,
        agent_id="researcher",
        data={"status": "completed"}
    )
    print(f"  ✓ Agent completed")

    # 获取时间线
    timeline = obs.get_timeline()
    print(f"\nExecution Timeline ({len(timeline)} events):")
    for event in timeline:
        duration = f"{event['duration_ms']:.2f}ms" if event['duration_ms'] else ""
        print(f"  - [{event['type']}] {duration}")

    # 结束会话
    obs.end_session(status="completed")
    print(f"\n✓ Session ended")

    # 统计
    stats = obs.get_stats()
    print(f"  Total events: {stats.get('total_events', len(timeline))}")


async def main():
    print("=" * 60)
    print("🚀 Agent OS Kernel - Advanced Features Demo")
    print("=" * 60)

    await demo_agent_definition()
    await demo_task_manager()
    await demo_checkpointer()
    await demo_memory()
    await demo_cost_tracker()
    await demo_observability()

    print("\n" + "=" * 60)
    print("✅ All demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
