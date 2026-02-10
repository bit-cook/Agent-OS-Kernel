"""
Claude API 集成示例

演示如何使用真实的 Claude API
"""

import sys
import os
sys.path.insert(0, '..')

from agent_os_kernel import ClaudeIntegratedKernel
from agent_os_kernel.tools.builtin import WebSearchTool, FileReadTool


def demo_with_claude():
    """使用 Claude API 的示例"""
    print("=" * 60)
    print("Claude API 集成示例")
    print("=" * 60)
    print()
    
    # 检查 API 密钥
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("⚠️  未找到 ANTHROPIC_API_KEY 环境变量")
        print("设置方法: export ANTHROPIC_API_KEY='your-key-here'")
        print("将使用模拟模式运行...\n")
    else:
        print("✓ 找到 API 密钥，将使用真实的 Claude API\n")
    
    # 创建内核
    kernel = ClaudeIntegratedKernel(api_key=api_key)
    
    # 注册额外工具
    kernel.tool_registry.register(WebSearchTool())
    kernel.tool_registry.register(FileReadTool())
    
    # 创建 Agent
    agent_pid = kernel.spawn_agent(
        name="ResearchAssistant",
        task="Find and summarize the key points about Agent OS design",
        priority=10
    )
    
    # 运行几步
    print("运行 Agent...\n")
    kernel.run(max_iterations=3)
    
    # 查看审计追踪
    print("\n" + "=" * 60)
    print("审计追踪")
    print("=" * 60)
    
    audit_trail = kernel.storage.get_audit_trail(agent_pid)
    for i, log in enumerate(audit_trail, 1):
        print(f"\n步骤 {i}:")
        print(f"  动作: {log.action_type}")
        print(f"  推理: {log.reasoning[:200]}...")
    
    kernel.shutdown()


def demo_multi_agent_collaboration():
    """多 Agent 协作示例"""
    print("\n" + "=" * 60)
    print("多 Agent 协作示例")
    print("=" * 60)
    print()
    
    kernel = ClaudeIntegratedKernel()
    
    # 创建一个"团队"
    agents = [
        ("Architect", "Design the system architecture", 20),
        ("Developer", "Implement the core functionality", 40),
        ("Tester", "Write and run tests", 60),
        ("Documenter", "Write documentation", 70),
    ]
    
    for name, task, priority in agents:
        kernel.spawn_agent(name, task, priority)
    
    print(f"创建了 {len(agents)} 个 Agent 的团队\n")
    
    # 运行一个完整的"sprint"
    kernel.run(max_iterations=len(agents) * 2)
    
    # 显示最终状态
    kernel.print_status()
    
    kernel.shutdown()


def demo_custom_prompt():
    """自定义系统提示词示例"""
    print("\n" + "=" * 60)
    print("自定义系统提示词示例")
    print("=" * 60)
    print()
    
    kernel = ClaudeIntegratedKernel()
    
    # 设置自定义提示词模板
    custom_template = """You are {name}, an expert software engineer.

Your current task: {task}

Available tools:
{tools}

Think carefully and act decisively.
Respond with a JSON object containing:
- reasoning: your thought process
- action: tool to use (if any)
- done: true when task is complete
"""
    kernel.set_system_template(custom_template)
    
    # 创建 Agent
    kernel.spawn_agent(
        name="SeniorDev",
        task="Review the code quality of a Python module",
        priority=10
    )
    
    kernel.run(max_iterations=3)
    kernel.print_status()
    
    kernel.shutdown()


if __name__ == "__main__":
    demo_with_claude()
    demo_multi_agent_collaboration()
    demo_custom_prompt()
    
    print("\n" + "=" * 60)
    print("所有示例完成!")
    print("=" * 60)
    print("\n下一步:")
    print("1. 设置 ANTHROPIC_API_KEY 以使用真实的 Claude API")
    print("2. 集成 PostgreSQL 以持久化存储")
    print("3. 配置 Docker 沙箱以实现安全隔离")
    print("=" * 60)
