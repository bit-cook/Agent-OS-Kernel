"""
Claude API 集成示例
演示如何将 Agent OS Kernel 与 Claude API 集成。

库内已提供 agent_os_kernel.integrations.claude_integration.ClaudeIntegratedKernel，
但其 execute_agent_step 仍引用早期 API（permission_manager / storage.log_action）。
由于示例不允许修改库代码，这里子类化该类，仅用当前内核 API 重写单步执行，
从而在无 API Key 时以 mock 模式真实跑通：推理 -> 工具调用 -> 审计 -> 上下文回写。
"""

import os
import json

from agent_os_kernel.core.scheduler import AgentProcess
from agent_os_kernel.integrations.claude_integration import (
    ClaudeIntegratedKernel as _BaseClaudeKernel,
)
from agent_os_kernel.tools.builtin import SearchTool, FileReadTool


class ClaudeIntegratedKernel(_BaseClaudeKernel):
    """修复版 Claude 集成内核：execute_agent_step 改用当前内核 API。"""

    def execute_agent_step(self, process: AgentProcess) -> dict:
        """执行 Agent 的一步推理（复用基类的上下文/LLM/解析，仅修复执行与记录）"""

        # 1. 准备上下文（复用基类）
        context = self._prepare_context(process)

        # 2. 调用 LLM（真实或模拟）
        if self.use_real_llm:
            try:
                response_text = self._call_claude(context, process)
            except Exception as e:
                print(f"[Error] Claude API call failed: {e}")
                response_text = self._mock_llm_response(process)
        else:
            response_text = self._mock_llm_response(process)

        # 3. 解析响应
        try:
            parsed = json.loads(response_text)
            reasoning = parsed.get('reasoning', '')
            action = parsed.get('action')
            done = parsed.get('done', False)
        except json.JSONDecodeError:
            reasoning = response_text
            action = self._extract_action_from_text(response_text)
            done = "done" in response_text.lower() or "complete" in response_text.lower()

        # 4. 请求资源配额
        tokens_needed = len(response_text.split())
        if not self.scheduler.request_resources(process.pid, tokens_needed):
            print(f"[Agent {process.name}] Quota exceeded, waiting...")
            return {"done": False, "waiting": True, "success": False}

        # 5. 执行工具调用
        result = None
        if action and not done:
            tool = self.tool_registry.get(action.get('tool'))
            if tool:
                print(f"[Agent {process.name}] Calling tool: {action['tool']}")
                result = tool.execute(**action.get('parameters', {}))
            else:
                result = {"success": False, "error": f"Tool {action.get('tool')} not found"}

        # 6. 记录审计日志（当前 API：storage.log_audit 接收 dict）
        self.storage.log_audit({
            'agent_pid': process.pid,
            'action': 'llm_reasoning',
            'resource': 'llm',
            'details': {'reasoning': reasoning, 'result': result},
            'result': 'success',
            'duration_ms': 0.0,
        })

        # 7. 更新上下文
        if result:
            result_text = f"Tool: {action['tool']}\nResult: {result}"
            self.context_manager.allocate_page(
                agent_pid=process.pid,
                content=result_text,
                importance=0.7
            )

        print(f"[Agent {process.name}]")
        print(f"  Reasoning: {reasoning[:200]}...")
        if action:
            print(f"  Action: {action}")
        if result:
            print(f"  Result: {result}")
        print()

        return {
            "done": done,
            "reasoning": reasoning,
            "action": action,
            "result": result,
            "success": True,
        }


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
    kernel.tool_registry.register(SearchTool())
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

    # 查看审计追踪（当前 API：storage.get_audit_logs 返回 dict 列表）
    print("\n" + "=" * 60)
    print("审计追踪")
    print("=" * 60)

    audit_trail = kernel.storage.get_audit_logs(agent_pid=agent_pid)
    for i, log in enumerate(audit_trail, 1):
        print(f"\n步骤 {i}:")
        print(f"  动作: {log['action']}")
        print(f"  推理: {log['details'].get('reasoning', '')[:200]}...")

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
