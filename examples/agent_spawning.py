"""
Agent 生命周期管理示例

展示如何创建、管理和终止 Agent：
1. Spawn Agent
2. 状态管理
3. 检查点创建与恢复
4. 资源配额控制
"""

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.types import AgentState


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
    
    # 查看状态
    status = kernel.get_agent_status(pid)
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
    print(f"Active agents: {len(kernel.scheduler.get_active_processes())}")
    
    # Terminate 一个 Agent
    kernel.terminate_agent(pids[0])
    print(f"\nTerminated {pids[0]}")
    print(f"Active after terminate: {len(kernel.scheduler.get_active_processes())}")


def demo_checkpoints():
    """演示检查点机制"""
    
    kernel = AgentOSKernel()
    
    # 创建 Agent
    pid = kernel.spawn_agent(
        name="LongRunningTask",
        task="A long-running computation that needs checkpointing"
    )
    
    # 运行几次迭代
    for i in range(3):
        print(f"Running iteration {i+1}...")
        # 模拟一些工作
        kernel.context_manager.add_page(
            agent_pid=pid,
            content=f"Iteration {i+1} results...",
            tokens=5,
            importance_score=0.5
        )
    
    # 创建检查点
    checkpoint_id = kernel.create_checkpoint(
        pid,
        description=f"Checkpoint after {3} iterations"
    )
    print(f"Checkpoint created: {checkpoint_id}")
    
    # 添加更多内容
    kernel.context_manager.add_page(
        agent_pid=pid,
        content="Additional work after checkpoint",
        tokens=5,
        importance_score=0.5
    )
    
    # 从检查点恢复（模拟恢复到之前状态）
    new_pid = kernel.restore_checkpoint(checkpoint_id)
    print(f"Restored from checkpoint as new agent: {new_pid}")
    
    # 验证恢复的 Agent
    status = kernel.get_agent_status(new_pid)
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
    
    # 获取所有 Agent
    agents = kernel.scheduler.get_active_processes()
    
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
    
    # 手动设置配额
    kernel.scheduler.processes[pid1].quota.max_tokens = 50000
    kernel.scheduler.processes[pid1].quota.max_iterations = 500
    
    # 检查配额
    quota = kernel.scheduler.processes[pid1].quota
    print(f"Max tokens: {quota.max_tokens}")
    print(f"Max iterations: {quota.max_iterations}")
    
    # 模拟使用资源
    kernel.context_manager.add_page(
        agent_pid=pid1,
        content="x" * 10000,  # 消耗 tokens
        tokens=10000,
        importance_score=0.5
    )
    
    # 检查配额是否超限
    can_use = quota.check_tokens(10000)
    print(f"Can use 10000 more tokens: {can_use}")


def demo_kernel_statistics():
    """演示内核统计"""
    
    kernel = AgentOSKernel()
    
    # 创建一些 Agent
    for i in range(3):
        kernel.spawn_agent(name=f"Agent-{i}", task=f"Task {i}")
    
    # 获取统计
    stats = kernel.get_statistics()
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
