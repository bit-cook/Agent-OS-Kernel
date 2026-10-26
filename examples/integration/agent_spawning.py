"""
Agent 生命周期管理示例

展示如何创建、管理和终止 Agent：
1. Spawn Agent
2. 状态管理
3. 检查点创建与恢复
4. 资源配额控制
"""

from agent_os_kernel import AgentOSKernel


def _active_processes(kernel):
    """当前活跃的 Agent 进程列表（基于当前内核 API）。"""
    return [p for p in kernel.scheduler.processes.values() if p.is_active()]


def demo_basic_agent_lifecycle():
    """演示 Agent 基本生命周期"""

    kernel = AgentOSKernel()

    # Spawn 一个 Agent
    print("Spawning agent...")
    pid = kernel.spawn_agent(
        name="ResearchAgent",
        task="Research the latest AI developments",
        priority=50
    )
    print(f"Agent spawned with PID: {pid}")

    # 查看状态（当前 API：get_agent 返回 dict）
    status = kernel.get_agent(pid)
    print(f"Initial state: {status['state']}")

    # 多次 Spawn
    pids = []
    for i in range(5):
        pid = kernel.spawn_agent(
            name=f"Worker-{i}",
            task=f"Task {i}",
            priority=30
        )
        pids.append(pid)

    print(f"\nTotal agents spawned: {len(pids)}")
    print(f"Active agents: {len(_active_processes(kernel))}")

    # Terminate 一个 Agent
    kernel.terminate_agent(pids[0])
    print(f"\nTerminated {pids[0]}")
    print(f"Active after terminate: {len(_active_processes(kernel))}")


def demo_checkpoints():
    """演示检查点机制"""

    kernel = AgentOSKernel()

    # 创建 Agent
    pid = kernel.spawn_agent(
        name="LongRunningTask",
        task="A long-running computation that needs checkpointing"
    )

    # 运行几次迭代（当前 API：context_manager.allocate_page）
    for i in range(3):
        print(f"Running iteration {i+1}...")
        # 模拟一些工作
        kernel.context_manager.allocate_page(
            agent_pid=pid,
            content=f"Iteration {i+1} results...",
            importance=0.5
        )

    # 创建检查点
    checkpoint_id = kernel.create_checkpoint(
        pid,
        description="Checkpoint after 3 iterations"
    )
    print(f"Checkpoint created: {checkpoint_id}")

    # 添加更多内容
    kernel.context_manager.allocate_page(
        agent_pid=pid,
        content="Additional work after checkpoint",
        importance=0.5
    )

    # 从检查点恢复（模拟恢复到之前状态）
    new_pid = kernel.restore_checkpoint(checkpoint_id)
    print(f"Restored from checkpoint as new agent: {new_pid}")

    # 验证恢复的 Agent
    status = kernel.get_agent(new_pid)
    print(f"Restored agent state: {status['state']}")


def demo_priority_scheduling():
    """演示优先级调度"""

    kernel = AgentOSKernel()

    # 创建不同优先级的 Agent
    low_priority = kernel.spawn_agent(
        name="LowPriority",
        task="Background task",
        priority=10
    )

    medium_priority = kernel.spawn_agent(
        name="MediumPriority",
        task="Normal task",
        priority=50
    )

    high_priority = kernel.spawn_agent(
        name="HighPriority",
        task="Urgent task",
        priority=90
    )

    # 获取所有活跃 Agent
    agents = _active_processes(kernel)

    # 按优先级排序
    sorted_agents = sorted(
        agents,
        key=lambda p: p.priority,
        reverse=True
    )

    print("Agents by priority (highest first):")
    for agent in sorted_agents:
        print(f"  {agent.name}: priority={agent.priority}")


def demo_resource_quotas():
    """演示资源配额"""

    kernel = AgentOSKernel()

    # 创建 Agent（使用默认配额）
    pid1 = kernel.spawn_agent(
        name="DefaultQuota",
        task="Uses default quotas"
    )

    # 查看默认配额（当前 API：配额由调度器的 ResourceQuotaManager 统一管理）
    quota = kernel.scheduler.quota_manager.quota
    print(f"Max tokens per window: {quota.max_tokens_per_window}")
    print(f"Max tokens per request: {quota.max_tokens_per_request}")
    print(f"Window seconds: {quota.window_seconds}")

    # 请求资源（会真实校验配额）
    can_use = kernel.scheduler.request_resources(pid1, tokens=10000)
    print(f"Can request 10000 tokens: {can_use}")

    # 查看当前用量
    usage = kernel.scheduler.quota_manager.get_usage_stats()
    print(f"Global token usage: {usage['global_usage']['tokens']} "
          f"({usage['usage_percent']['tokens']:.1f}% of limit)")


def demo_kernel_statistics():
    """演示内核统计"""

    kernel = AgentOSKernel()

    # 创建一些 Agent
    for i in range(3):
        kernel.spawn_agent(name=f"Agent-{i}", task=f"Task {i}")

    # 获取统计（当前 API：get_stats）
    stats = kernel.get_stats()
    print("Kernel Statistics:")
    print(f"  Version: {stats['version']}")
    print(f"  Total agents: {stats['total_agents']}")
    print(f"  Active agents: {stats['active_agents']}")
    print(f"  Total iterations: {stats['total_iterations']}")


if __name__ == "__main__":
    print("=" * 50)
    print("Agent 生命周期管理示例")
    print("=" * 50)

    print("\n1. 基本生命周期：")
    demo_basic_agent_lifecycle()

    print("\n2. 检查点机制：")
    demo_checkpoints()

    print("\n3. 优先级调度：")
    demo_priority_scheduling()

    print("\n4. 资源配额：")
    demo_resource_quotas()

    print("\n5. 内核统计：")
    demo_kernel_statistics()

    print("\n✓ 示例完成！")
