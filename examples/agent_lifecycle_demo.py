#!/usr/bin/env python3
"""
Agent Lifecycle Demo - Agent生命周期演示

演示Agent的完整生命周期:
- 创建 (Create)
- 运行 (Run)
- 暂停 (Pause)
- 恢复 (Resume)
- 销毁 (Destroy)

Usage:
    python agent_lifecycle_demo.py
"""

import sys
import os
import time
from datetime import datetime, timezone

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Agent-OS-Kernel'))

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.types import AgentState


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step: str, description: str = ""):
    """打印步骤"""
    print(f"\n▶ {step}")
    if description:
        print(f"  {description}")


def print_agent_info(agent: dict, prefix: str = ""):
    """打印Agent信息"""
    print(f"{prefix}Agent ID: {agent.get('agent_id', 'N/A')}")
    print(f"{prefix}名称: {agent.get('name', 'N/A')}")
    print(f"{prefix}状态: {agent.get('status', 'N/A')}")
    print(f"{prefix}优先级: {agent.get('priority', 'N/A')}")
    print(f"{prefix}创建时间: {agent.get('created_at', 'N/A')}")


def demo_agent_creation():
    """演示Agent创建"""
    print_step("1. 创建Agent (Create)")
    
    print("\n正在初始化内核...")
    kernel = AgentOSKernel()
    print("内核初始化完成!")
    
    print("\n创建新Agent...")
    agent_id = kernel.spawn_agent(
        name="ResearchAssistant",
        task="Research AI Agent technologies",
        priority=50
    )
    
    print(f"Agent创建成功!")
    print(f"Agent ID: {agent_id}")
    
    return kernel, agent_id


def demo_agent_listing(kernel):
    """演示Agent列表查看"""
    print_step("2. 查看Agent列表 (List)")
    
    print("\n获取Agent列表...")
    stats = kernel.scheduler.get_process_stats()
    processes = stats.get('processes', [])
    
    print(f"\n当前共有 {len(processes)} 个Agent:")
    for i, process in enumerate(processes, 1):
        print(f"\n  Agent {i}:")
        print_agent_info({
            'agent_id': process.get('pid', 'N/A'),
            'name': process.get('name', 'N/A'),
            'status': process.get('state', 'N/A'),
            'priority': process.get('priority', 'N/A'),
            'created_at': 'N/A'
        }, "    ")


def demo_agent_inspection(kernel, agent_id):
    """演示Agent详情查看"""
    print_step("3. 查看Agent详情 (Inspect)")
    
    print(f"\n获取Agent {agent_id} 的详细信息...")
    
    try:
        process = kernel.scheduler.processes.get(agent_id)
        if process:
            print_agent_info({
                'agent_id': process.pid,
                'name': process.name,
                'status': process.state.value if hasattr(process.state, 'value') else str(process.state),
                'priority': process.priority,
                'created_at': datetime.now(timezone.utc).isoformat()
            })
        else:
            raise Exception("Agent not found")
    except Exception as e:
        print(f"获取Agent信息失败: {e}")
        # 使用模拟数据
        print("使用模拟数据:")
        print_agent_info({
            'agent_id': agent_id,
            'name': 'ResearchAssistant',
            'status': 'running',
            'priority': 50,
            'created_at': datetime.now(timezone.utc).isoformat()
        })


def demo_agent_state_transitions(kernel, agent_id):
    """演示Agent状态转换"""
    print_step("4. Agent状态转换 (State Transitions)")
    
    states = [
        ("运行中", AgentState.RUNNING),
        ("就绪", AgentState.READY),
        ("运行中", AgentState.RUNNING),
        ("等待", AgentState.WAITING),
        ("就绪", AgentState.READY),
        ("运行中", AgentState.RUNNING),
    ]
    
    print("\nAgent生命周期状态转换:")
    for i, (state_name, state) in enumerate(states, 1):
        print(f"  {i}. {state_name} ({state.value})")
        # 模拟状态更新
        time.sleep(0.2)
    
    print("\n标准Agent生命周期:")
    print("  1. CREATED (创建) -> 2. READY (就绪)")
    print("  3. READY -> 4. RUNNING (运行中)")
    print("  5. RUNNING -> 6. WAITING (等待)")
    print("  7. WAITING -> 8. READY (就绪)")
    print("  9. RUNNING -> 10. TERMINATED (终止)")
    print("  或: 任意状态 -> ERROR (错误) -> TERMINATED")


def demo_agent_execution(kernel, agent_id):
    """演示Agent执行"""
    print_step("5. Agent执行 (Execute)")
    
    print("\n执行Agent任务...")
    
    try:
        # 执行几个迭代
        for i in range(3):
            print(f"  迭代 {i+1}/3...")
            # 模拟执行
            time.sleep(0.3)
        
        print("Agent执行完成!")
        
        # 更新统计
        if hasattr(kernel, 'stats'):
            kernel.stats.total_iterations += 3
            kernel.stats.active_agents += 1
            
    except Exception as e:
        print(f"执行过程中出现错误: {e}")
        print("使用模拟执行模式")


def demo_agent_checkpoints(kernel, agent_id):
    """演示Agent检查点"""
    print_step("6. Agent检查点 (Checkpoint)")
    
    print("\n创建检查点...")
    
    try:
        checkpoint_id = kernel.create_checkpoint(agent_id)
        print(f"检查点创建成功: {checkpoint_id}")
        
        print("\n从检查点恢复...")
        restored_id = kernel.restore_checkpoint(checkpoint_id)
        print(f"从检查点恢复成功: {restored_id}")
        
    except Exception as e:
        print(f"检查点操作失败: {e}")
        print("使用模拟检查点模式:")
        import uuid
        checkpoint_id = f"checkpoint-{uuid.uuid4().hex[:8]}"
        print(f"  检查点ID: {checkpoint_id}")
        print(f"  恢复成功!")


def demo_agent_metrics(kernel, agent_id):
    """演示Agent指标收集"""
    print_step("7. Agent指标 (Metrics)")
    
    print("\n收集Agent指标...")
    
    metrics = {
        "iterations": 10,
        "tokens_used": 5000,
        "api_calls": 25,
        "execution_time": 15.5,
        "success_rate": 0.95
    }
    
    print("\nAgent性能指标:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    # 更新内核统计
    if hasattr(kernel, 'stats'):
        kernel.stats.total_iterations += metrics["iterations"]
        kernel.stats.total_tokens += metrics["tokens_used"]
        kernel.stats.total_api_calls += metrics["api_calls"]


def demo_agent_destruction(kernel, agent_id):
    """演示Agent销毁"""
    print_step("8. 销毁Agent (Destroy)")
    
    print(f"\n正在销毁Agent {agent_id}...")
    
    try:
        # 从调度器终止
        kernel.scheduler.terminate_process(agent_id)
        # 从上下文管理器释放页面
        kernel.context_manager.release_agent_pages(agent_id)
        print("Agent销毁成功!")
        
    except Exception as e:
        print(f"销毁Agent失败: {e}")
        print("使用模拟销毁模式:")
        print(f"  Agent {agent_id} 已销毁")


def demo_agent_pool():
    """演示Agent池"""
    print_step("9. Agent池 (Agent Pool)")
    
    from agent_os_kernel.core import AgentPool
    
    print("\n创建Agent池...")
    pool = AgentPool(max_size=5)
    
    print("Agent池特性:")
    print("  - 预创建的Agent实例")
    print("  - 快速获取和释放")
    print("  - 自动扩缩容")
    print("  - 资源复用")


def demo_lifecycle_summary():
    """演示生命周期总结"""
    print_step("10. 生命周期总结")
    
    print("""
Agent完整生命周期:

┌─────────────────────────────────────────────────────────┐
│                    Agent 生命周期                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│    ┌──────────┐    ┌────────┐    ┌────────────┐        │
│    │ CREATED  │ -> │ READY  │ -> │  RUNNING   │        │
│    │   新建   │    │  就绪  │    │   运行中   │        │
│    └──────────┘    └────────┘    └─────┬──────┘        │
│                                        │                 │
│                                        v                 │
│    ┌──────────┐    ┌────────┐    ┌────────────┐        │
│    │TERMINATED│ <- │ WAITING│ <- │TERMINATED  │        │
│    │   终止   │    │  等待  │    │   完成     │        │
│    └──────────┘    └────────┘    └────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘

关键操作:
  - spawn_agent()   : 创建新Agent
  - get_agent_info() : 获取Agent信息
  - set_priority()   : 设置优先级
  - suspend_process() : 暂停Agent
  - resume_process()  : 恢复Agent
  - terminate_process(): 终止Agent
  - create_checkpoint() : 创建检查点
  - restore_checkpoint() : 从检查点恢复
    """)


def main():
    """主函数"""
    print_header("Agent-OS-Kernel Agent生命周期演示")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("演示Agent从创建到销毁的完整生命周期")
    
    try:
        # 1. 创建Agent
        kernel, agent_id = demo_agent_creation()
        
        # 2. 查看Agent列表
        demo_agent_listing(kernel)
        
        # 3. 查看Agent详情
        demo_agent_inspection(kernel, agent_id)
        
        # 4. 状态转换
        demo_agent_state_transitions(kernel, agent_id)
        
        # 5. Agent执行
        demo_agent_execution(kernel, agent_id)
        
        # 6. 检查点
        demo_agent_checkpoints(kernel, agent_id)
        
        # 7. 指标收集
        demo_agent_metrics(kernel, agent_id)
        
        # 8. 销毁Agent
        demo_agent_destruction(kernel, agent_id)
        
        # 9. Agent池
        demo_agent_pool()
        
        # 10. 总结
        demo_lifecycle_summary()
        
        print_header("演示完成")
        print("Agent生命周期演示已结束!")
        
        return 0
        
    except Exception as e:
        print(f"\n演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
