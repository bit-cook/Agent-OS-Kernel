"""
基础使用示例

演示 Agent OS Kernel 的基本功能
"""

import sys
sys.path.insert(0, '..')

from agent_os_kernel import AgentOSKernel


def demo_basic_usage():
    """基础使用演示"""
    print("=" * 60)
    print("示例 1: 基础使用")
    print("=" * 60)
    print()
    
    # 初始化内核
    kernel = AgentOSKernel()
    
    # 创建几个 Agent
    kernel.spawn_agent(
        name="CodeAssistant",
        task="Help write Python code",
        priority=30
    )
    
    kernel.spawn_agent(
        name="ResearchAssistant",
        task="Research AI papers",
        priority=50
    )
    
    kernel.spawn_agent(
        name="DataAnalyst",
        task="Analyze sales data",
        priority=40
    )
    
    # 运行主循环
    print("运行内核...")
    kernel.run(max_iterations=5)
    
    # 打印最终状态
    kernel.print_status()
    
    # 查看审计日志
    print("\n" + "=" * 60)
    print("第一个 Agent 的审计日志")
    print("=" * 60)
    
    first_agent_pid = list(kernel.scheduler.processes.keys())[0]
    audit_trail = kernel.storage.get_audit_logs(first_agent_pid)

    for i, log in enumerate(audit_trail[:3], 1):
        print(f"\n步骤 {i}:")
        print(f"  动作: {log['action']}")
        print(f"  详情: {str(log['details'])[:100]}...")
    
    # 清理
    kernel.shutdown()


def demo_checkpoints():
    """检查点功能演示"""
    print("\n" + "=" * 60)
    print("示例 2: 检查点功能")
    print("=" * 60)
    print()
    
    kernel = AgentOSKernel()
    
    # 创建 Agent
    agent_pid = kernel.spawn_agent(
        name="LongRunningTask",
        task="Perform a long running analysis",
        priority=20
    )
    
    # 运行几步
    print("运行 Agent...")
    kernel.run(max_iterations=2)
    
    # 创建检查点
    print("\n创建检查点...")
    checkpoint_id = kernel.create_checkpoint(agent_pid, "Before critical operation")
    print(f"检查点 ID: {checkpoint_id}")
    
    # 继续运行
    print("\n继续运行...")
    kernel.run(max_iterations=2)
    
    # 从检查点恢复
    print("\n从检查点恢复...")
    new_pid = kernel.restore_checkpoint(checkpoint_id)
    print(f"恢复的 Agent PID: {new_pid}")
    
    # 查看状态
    kernel.print_status()
    
    kernel.shutdown()


def demo_resource_quota():
    """资源配额演示"""
    print("\n" + "=" * 60)
    print("示例 3: 资源配额")
    print("=" * 60)
    print()
    
    from agent_os_kernel.core.scheduler import ResourceQuota

    # 创建带严格配额的调度器
    quota = ResourceQuota(
        max_tokens_per_window=5000,
        max_api_calls_per_window=10
    )
    
    kernel = AgentOSKernel()
    kernel.scheduler.quota_manager.quota = quota
    
    # 创建多个 Agent
    for i in range(5):
        kernel.spawn_agent(
            name=f"Agent-{i+1}",
            task=f"Task {i+1}",
            priority=50 + i
        )
    
    print("运行内核（配额限制：5000 tokens, 10 API calls）...")
    kernel.run(max_iterations=10)
    
    # 显示配额使用情况
    stats = kernel.scheduler.get_process_stats()
    print(f"\n配额使用: {stats['quota_usage']}")
    
    kernel.shutdown()


if __name__ == "__main__":
    demo_basic_usage()
    demo_checkpoints()
    demo_resource_quota()
    
    print("\n" + "=" * 60)
    print("所有示例完成!")
    print("=" * 60)
