"""
Agent OS Kernel - Claude API Integration Example

演示如何将 Agent OS Kernel 与真实的 Claude API 集成
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from agent_os_kernel import (
    AgentOSKernel, AgentProcess, Tool, SimpleTool
)

# 检查是否安装了 anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package not installed. Using mock responses.")
    print("Install with: pip install anthropic")


class ClaudeIntegratedKernel(AgentOSKernel):
    """
    集成了 Claude API 的 Agent OS Kernel
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        
        # 初始化 Claude 客户端
        if ANTHROPIC_AVAILABLE and api_key:
            self.claude_client = anthropic.Anthropic(api_key=api_key)
            self.use_real_llm = True
            print("[Kernel] Using real Claude API")
        else:
            self.claude_client = None
            self.use_real_llm = False
            print("[Kernel] Using mock LLM responses")
        
        # 系统提示词模板
        self.system_prompt_template = """You are an AI agent running in an Agent OS Kernel environment.

Your capabilities:
{tools}

Current task: {task}

You should think step by step and decide which action to take.
Respond in the following JSON format:

{{
    "reasoning": "Your step-by-step thinking process",
    "action": {{
        "tool": "tool_name",
        "parameters": {{"param1": "value1"}}
    }},
    "done": false
}}

If the task is complete, set "done" to true and omit the "action" field.
"""
    
    def execute_agent_step(self, process: AgentProcess) -> dict:
        """
        执行 Agent 的一步推理（使用真实的 Claude API）
        """
        # 1. 准备上下文
        context = self._prepare_context(process)
        
        # 2. 调用 LLM（真实或模拟）
        if self.use_real_llm:
            response = self._call_claude(context)
        else:
            response = self._mock_llm_response(process)
        
        # 3. 解析响应
        try:
            parsed = json.loads(response)
            reasoning = parsed.get('reasoning', '')
            action = parsed.get('action')
            done = parsed.get('done', False)
        except json.JSONDecodeError:
            # 如果解析失败，尝试从文本中提取
            reasoning = response
            action = self._extract_action_from_text(response)
            done = "done" in response.lower() or "complete" in response.lower()
        
        # 4. 请求资源配额
        tokens_needed = len(response.split())
        if not self.scheduler.request_resources(process.pid, tokens_needed):
            print(f"[Agent {process.name}] Quota exceeded, waiting...")
            return {"done": False, "waiting": True}
        
        # 5. 执行工具调用
        result = None
        if action and not done:
            tool = self.tool_registry.get(action.get('tool'))
            if tool:
                print(f"[Agent {process.name}] Calling tool: {action['tool']}")
                result = tool.execute(**action.get('parameters', {}))
            else:
                result = {"success": False, "error": f"Tool {action.get('tool')} not found"}
        
        # 6. 记录审计日志
        self.storage.log_action(
            agent_pid=process.pid,
            action_type="llm_reasoning",
            input_data={"context": context[:500]},  # 截断以节省空间
            output_data={"result": result},
            reasoning=reasoning
        )
        
        # 7. 更新上下文
        if result:
            result_text = f"Tool: {action['tool']}\nResult: {result['data']}"
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
            "result": result
        }
    
    def _prepare_context(self, process: AgentProcess) -> str:
        """
        准备发送给 LLM 的完整上下文
        """
        # 获取工具列表
        tools_desc = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in self.tool_registry.list_tools()
        ])
        
        # 构建系统提示词
        system_prompt = self.system_prompt_template.format(
            tools=tools_desc,
            task=process.context.get('task', 'Unknown task')
        )
        
        # 获取历史上下文
        history = self.context_manager.get_agent_context(process.pid)
        
        # 组合
        full_context = f"{system_prompt}\n\nHistory:\n{history}"
        
        return full_context
    
    def _call_claude(self, context: str) -> str:
        """
        调用真实的 Claude API
        """
        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": context}
                ]
            )
            
            # 提取文本响应
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            return response_text
            
        except Exception as e:
            print(f"[Error] Claude API call failed: {e}")
            return self._mock_llm_response(None)
    
    def _mock_llm_response(self, process: Optional[AgentProcess]) -> str:
        """
        模拟 LLM 响应（当 API 不可用时）
        """
        task = process.context.get('task', 'unknown') if process else 'unknown'
        
        # 根据任务类型生成不同的模拟响应
        if 'code' in task.lower():
            return json.dumps({
                "reasoning": "I need to help with coding. Let me search for relevant information.",
                "action": {
                    "tool": "search",
                    "parameters": {"query": "Python best practices"}
                },
                "done": False
            })
        elif 'calculate' in task.lower() or 'math' in task.lower():
            return json.dumps({
                "reasoning": "I need to perform a calculation.",
                "action": {
                    "tool": "calculator",
                    "parameters": {"expression": "2 + 2"}
                },
                "done": False
            })
        else:
            return json.dumps({
                "reasoning": f"I will work on: {task}",
                "action": {
                    "tool": "search",
                    "parameters": {"query": task}
                },
                "done": False
            })
    
    def _extract_action_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取工具调用（如果 LLM 没有返回 JSON）
        """
        # 尝试匹配工具调用模式
        patterns = [
            r'tool[:\s]+["\']?(\w+)["\']?',
            r'use[:\s]+["\']?(\w+)["\']?',
            r'call[:\s]+["\']?(\w+)["\']?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tool_name = match.group(1)
                return {
                    "tool": tool_name,
                    "parameters": {}
                }
        
        return None


class FileSystemTool(Tool):
    """
    文件系统工具（示例）
    """
    
    def name(self) -> str:
        return "read_file"
    
    def description(self) -> str:
        return "Read contents of a file"
    
    def execute(self, filepath: str) -> Dict[str, Any]:
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            return {
                "success": True,
                "data": content[:1000],  # 限制返回长度
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }


class WebSearchTool(Tool):
    """
    网络搜索工具（模拟）
    """
    
    def name(self) -> str:
        return "web_search"
    
    def description(self) -> str:
        return "Search the web for information"
    
    def execute(self, query: str) -> Dict[str, Any]:
        # 这里应该集成真实的搜索 API
        # 为了演示，我们返回模拟结果
        return {
            "success": True,
            "data": {
                "query": query,
                "results": [
                    {
                        "title": f"Result 1 for: {query}",
                        "snippet": "This is a mock search result..."
                    },
                    {
                        "title": f"Result 2 for: {query}",
                        "snippet": "Another mock result..."
                    }
                ]
            },
            "error": None
        }


def demo_basic_usage():
    """
    基础使用示例
    """
    print("\n" + "=" * 60)
    print("Demo 1: Basic Agent Execution")
    print("=" * 60 + "\n")
    
    # 创建内核（不使用真实 API）
    kernel = ClaudeIntegratedKernel()
    
    # 注册额外的工具
    kernel.tool_registry.register(FileSystemTool())
    kernel.tool_registry.register(WebSearchTool())
    
    # 创建几个 Agent
    kernel.spawn_agent(
        name="CodeHelper",
        task="Help write a Python function to calculate fibonacci numbers",
        priority=30
    )
    
    kernel.spawn_agent(
        name="Researcher",
        task="Research the latest developments in LLM context management",
        priority=50
    )
    
    # 运行
    kernel.run(max_iterations=4)
    
    # 显示状态
    kernel.print_status()


def demo_with_real_api():
    """
    使用真实 Claude API 的示例
    """
    print("\n" + "=" * 60)
    print("Demo 2: Using Real Claude API")
    print("=" * 60 + "\n")
    
    # 从环境变量获取 API 密钥
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not found in environment variables")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("Falling back to mock mode...\n")
    
    # 创建内核
    kernel = ClaudeIntegratedKernel(api_key=api_key)
    
    # 注册工具
    kernel.tool_registry.register(WebSearchTool())
    
    # 创建一个 Agent
    agent_pid = kernel.spawn_agent(
        name="ResearchAssistant",
        task="Find and summarize the key points about Agent OS design",
        priority=10
    )
    
    # 运行几步
    print("Running agent for 3 iterations...\n")
    kernel.run(max_iterations=3)
    
    # 查看审计追踪
    print("\n" + "=" * 60)
    print("Audit Trail")
    print("=" * 60 + "\n")
    
    audit_trail = kernel.storage.get_audit_trail(agent_pid)
    for i, log in enumerate(audit_trail, 1):
        print(f"Step {i}:")
        print(f"  Action: {log['action_type']}")
        print(f"  Reasoning: {log['reasoning'][:200]}...")
        print()


def demo_multi_agent_collaboration():
    """
    多 Agent 协作示例
    """
    print("\n" + "=" * 60)
    print("Demo 3: Multi-Agent Collaboration")
    print("=" * 60 + "\n")
    
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
    
    print(f"Created a team of {len(agents)} agents\n")
    
    # 运行一个完整的"sprint"
    kernel.run(max_iterations=len(agents) * 2)
    
    # 显示最终状态
    kernel.print_status()


if __name__ == "__main__":
    # 运行所有演示
    demo_basic_usage()
    
    # 如果设置了 API 密钥，运行真实 API 演示
    if os.getenv("ANTHROPIC_API_KEY"):
        demo_with_real_api()
    
    # 多 Agent 协作演示
    demo_multi_agent_collaboration()
    
    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set ANTHROPIC_API_KEY to use real Claude API")
    print("2. Integrate with PostgreSQL for production storage")
    print("3. Add Docker sandbox for secure execution")
    print("4. Implement distributed scheduling")
    print("=" * 60)
