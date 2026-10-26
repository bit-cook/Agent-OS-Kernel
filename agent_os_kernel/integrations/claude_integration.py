# -*- coding: utf-8 -*-
"""
Claude Integration - Claude API 集成

演示如何将 Agent OS Kernel 与真实的 Claude API 集成
"""

import os
import json
import re
import time
import logging
from typing import Dict, Any, Optional, List

from ..kernel import AgentOSKernel
from ..core.scheduler import AgentProcess
from ..llm.provider import LLMResponse
from ..tools.base import Tool


logger = logging.getLogger(__name__)


# 检查是否安装了 anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not installed. Claude integration will use mock mode.")
    logger.warning("Install with: pip install anthropic")


class ClaudeIntegratedKernel(AgentOSKernel):
    """
    集成了 Claude API 的 Agent OS Kernel
    
    示例用法：
        >>> kernel = ClaudeIntegratedKernel(api_key="your-api-key")
        >>> agent_pid = kernel.spawn_agent("Assistant", "Help me code")
        >>> kernel.run(max_iterations=10)
    """
    
    DEFAULT_SYSTEM_TEMPLATE = """You are an AI agent running in an Agent OS Kernel environment.

Your name: {name}
Your task: {task}

Available tools:
{tools}

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
    
    def __init__(self, api_key: Optional[str] = None, 
                 model: str = "claude-sonnet-4-20250514",
                 **kwargs):
        """
        初始化 Claude 集成内核
        
        Args:
            api_key: Claude API 密钥，默认从环境变量获取
            model: Claude 模型名称
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        
        # 初始化 Claude 客户端
        self.model = model
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if ANTHROPIC_AVAILABLE and api_key:
            self.claude_client = anthropic.Anthropic(api_key=api_key)
            self.use_real_llm = True
            logger.info("[Kernel] Using real Claude API")
        else:
            self.claude_client = None
            self.use_real_llm = False
            if not api_key:
                logger.warning("[Kernel] No API key provided, using mock LLM")
            logger.info("[Kernel] Using mock LLM responses")
        
        # 系统提示词模板
        self.system_template = self.DEFAULT_SYSTEM_TEMPLATE
        
        # 对话历史缓存（用于优化 KV-Cache）
        self.conversation_cache: Dict[str, List[Dict]] = {}
        
        logger.info("[Kernel] Claude integration ready")
    
    def execute_agent_step(self, process: AgentProcess) -> Dict[str, Any]:
        """
        执行 Agent 的一步推理（使用真实的 Claude API）
        
        Args:
            process: Agent 进程
        
        Returns:
            执行结果
        """
        start_time = time.time()
        
        # 1. 准备上下文
        context = self._prepare_context(process)
        
        # 2. 调用 LLM
        if self.use_real_llm:
            try:
                response_text = self._call_claude(context, process)
            except Exception as e:
                logger.error(f"Claude API call failed: {e}")
                response_text = self._mock_llm_response(process)
        else:
            response_text = self._mock_llm_response(process)
        
        # 3. 解析响应
        try:
            parsed = self._parse_response(response_text)
            reasoning = parsed.get('reasoning', '')
            action = parsed.get('action')
            done = parsed.get('done', False)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            reasoning = response_text
            action = self._extract_action_from_text(response_text)
            done = "done" in response_text.lower() or "complete" in response_text.lower()
        
        # 4. 请求资源配额
        tokens_needed = len(response_text.split()) + len(context.split())
        if not self.scheduler.request_resources(process.pid, tokens_needed):
            logger.warning(f"[Agent {process.name}] Quota exceeded, waiting...")
            return {"done": False, "waiting": True}
        
        # 5. 执行工具调用
        result = None
        if action and not done:
            tool_name = action.get('tool')
            
            # 检查权限（进程级安全策略：spawn 时挂载于 context；
            # 无策略=允许，与内核 spawn_agent 语义一致。
            # 原实现调用不存在的 self.permission_manager，每步必 AttributeError）
            policy = process.context.get('security_policy') or {}
            allowed = policy.get('allowed_tools')
            blocked = policy.get('blocked_tools') or []
            if (allowed and tool_name not in allowed) or tool_name in blocked:
                result = {
                    "success": False,
                    "error": f"Tool '{tool_name}' is not allowed for this agent"
                }
            else:
                tool = self.tool_registry.get(tool_name)
                if tool:
                    logger.info(f"[Agent {process.name}] Calling tool: {tool_name}")
                    result = tool.execute(**action.get('parameters', {}))
                else:
                    result = {"success": False, "error": f"Tool '{tool_name}' not found"}
        
        # 6. 记录审计日志（真实方法 log_audit，dict 契约；
        # 原实现调用不存在的 storage.log_action 每步必错）
        duration_ms = (time.time() - start_time) * 1000
        self.storage.log_audit({
            'agent_pid': process.pid,
            'action': 'llm_reasoning',
            'resource': f"llm:{self.model}",
            'details': {
                'context': context[:500],   # 截断以节省空间
                'result': result,
                'reasoning': reasoning,
            },
            'result': 'success',
            'duration_ms': duration_ms,
        })
        
        # 7. 更新上下文
        if result:
            result_text = f"Tool: {action['tool']}\nResult: {json.dumps(result['data']) if result.get('success') else result.get('error')}"
            self.context_manager.allocate_page(
                agent_pid=process.pid,
                content=result_text,
                importance=0.7,
                page_type="tool_result"
            )
            
            # 更新对话缓存
            self._update_conversation_cache(process.pid, context, response_text)
        
        logger.info(f"[Agent {process.name}]")
        logger.info(f"  Reasoning: {reasoning[:200]}...")
        if action:
            logger.info(f"  Action: {action}")
        if result:
            logger.info(f"  Result: {result}")
        logger.info("")
        
        return {
            "done": done,
            "reasoning": reasoning,
            "action": action,
            "result": result
        }
    
    def _prepare_context(self, process: AgentProcess) -> str:
        """
        准备发送给 LLM 的完整上下文
        
        Args:
            process: Agent 进程
        
        Returns:
            格式化的上下文字符串
        """
        # 获取工具列表
        tools_desc = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in self.tool_registry.list_tools()
        ])
        
        # 构建系统提示词
        system_prompt = self.system_template.format(
            name=process.name,
            task=process.context.get('task', 'Unknown task'),
            tools=tools_desc
        )
        
        # 获取历史上下文
        history = self.context_manager.get_agent_context(process.pid)
        
        # 组合
        full_context = f"{system_prompt}\n\nHistory:\n{history}"
        
        return full_context
    
    def _call_claude(self, context: str, process: AgentProcess) -> str:
        """
        调用真实的 Claude API
        
        Args:
            context: 完整上下文
            process: Agent 进程
        
        Returns:
            LLM 响应文本
        """
        try:
            # 构建消息
            messages = [{"role": "user", "content": context}]
            
            # 添加对话历史（如果有）
            cache = self.conversation_cache.get(process.pid, [])
            if cache:
                messages = cache + messages
            
            message = self.claude_client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=messages
            )
            
            # 提取文本响应
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            # 记录 token 使用
            if hasattr(message, 'usage'):
                usage = message.usage
                process.token_usage += usage.input_tokens + usage.output_tokens
            
            return response_text
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    def _mock_llm_response(self, process: AgentProcess) -> str:
        """
        模拟 LLM 响应（当 API 不可用时）
        
        Args:
            process: Agent 进程
        
        Returns:
            JSON 格式的模拟响应
        """
        task = process.context.get('task', 'unknown') if process else 'unknown'
        task_lower = task.lower()
        
        # 根据任务类型生成不同的模拟响应
        if any(word in task_lower for word in ['code', 'program', 'function']):
            return json.dumps({
                "reasoning": "I need to help with coding. Let me search for relevant information first.",
                "action": {
                    "tool": "search",
                    "parameters": {"query": "Python best practices"}
                },
                "done": False
            })
        elif any(word in task_lower for word in ['calculate', 'math', 'compute']):
            return json.dumps({
                "reasoning": "I need to perform a calculation.",
                "action": {
                    "tool": "calculator",
                    "parameters": {"expression": "2 + 2"}
                },
                "done": False
            })
        elif any(word in task_lower for word in ['read', 'file', 'open']):
            return json.dumps({
                "reasoning": "I need to read a file to complete this task.",
                "action": {
                    "tool": "read_file",
                    "parameters": {"filepath": "/workspace/example.txt"}
                },
                "done": False
            })
        else:
            return json.dumps({
                "reasoning": f"I will work on the task: {task}. Let me search for relevant information.",
                "action": {
                    "tool": "search",
                    "parameters": {"query": task[:100]}
                },
                "done": False
            })
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """
        解析 LLM 响应
        
        Args:
            text: 响应文本
        
        Returns:
            解析后的字典
        """
        # 尝试直接解析 JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 代码块
        json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
        
        # 如果都没成功，返回原始文本
        return {"reasoning": text, "done": False}
    
    def _extract_action_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取工具调用（如果 LLM 没有返回 JSON）
        
        Args:
            text: 响应文本
        
        Returns:
            动作字典或 None
        """
        # 尝试匹配工具调用模式
        patterns = [
            r'["\']?tool["\']?\s*:\s*["\']?(\w+)["\']?',
            r'["\']?action["\']?\s*:\s*["\']?(\w+)["\']?',
            r'use\s+["\']?(\w+)["\']?',
            r'call\s+["\']?(\w+)["\']?',
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
    
    def _update_conversation_cache(self, agent_pid: str, 
                                   user_msg: str, 
                                   assistant_msg: str):
        """
        更新对话缓存（用于优化 KV-Cache）
        
        Args:
            agent_pid: Agent PID
            user_msg: 用户消息
            assistant_msg: 助手消息
        """
        if agent_pid not in self.conversation_cache:
            self.conversation_cache[agent_pid] = []
        
        cache = self.conversation_cache[agent_pid]
        cache.append({"role": "user", "content": user_msg[:1000]})  # 限制长度
        cache.append({"role": "assistant", "content": assistant_msg[:1000]})
        
        # 保持缓存大小（最近 10 轮对话）
        if len(cache) > 20:
            cache = cache[-20:]
        
        self.conversation_cache[agent_pid] = cache
    
    def set_system_template(self, template: str):
        """
        设置自定义的系统提示词模板
        
        Args:
            template: 模板字符串，可用变量：{name}, {task}, {tools}
        """
        self.system_template = template
        logger.info("Updated system prompt template")


class OpenAIIntegratedKernel(AgentOSKernel):
    """
    OpenAI API 集成（示例）
    
    可以类似方式集成 OpenAI GPT API
    """
    
    def __init__(self, api_key: Optional[str] = None, 
                 model: str = "gpt-4",
                 **kwargs):
        super().__init__(**kwargs)
        
        self.model = model
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if api_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=api_key)
                self.use_real_llm = True
                logger.info("[Kernel] Using OpenAI API")
            except ImportError:
                logger.warning("openai package not installed")
                self.openai_client = None
                self.use_real_llm = False
        else:
            self.openai_client = None
            self.use_real_llm = False
    
    def execute_agent_step(self, process: AgentProcess) -> Dict[str, Any]:
        """使用 OpenAI API 执行步骤"""
        # 类似 Claude 的实现...
        # 这里省略具体实现，遵循相同的模式
        pass
