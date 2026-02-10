# -*- coding: utf-8 -*-
"""ReAct Agent - 思考-行动-观察模式

参考 ReAct (Reason + Act) 论文实现。

论文: "ReAct: Synergizing Reasoning and Acting in Language Models"
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """动作类型"""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    FINISH = "finish"


@dataclass
class ReActStep:
    """ReAct 步骤"""
    step_num: int
    thought: str
    action_type: ActionType
    action: Optional[Dict] = None
    observation: Optional[str] = None
    confidence: float = 0.5


class ReActAgent:
    """
    ReAct Agent 实现
    
    支持三种模式：
    1. standard: 标准 ReAct (思考 -> 行动 -> 观察)
    2. concise: 简洁模式 (减少思考)
    3. verbose: 详细模式 (更多推理)
    """
    
    def __init__(
        self,
        name: str,
        system_prompt: str = None,
        max_steps: int = 10,
        llm = None,
        tools: List[Dict] = None,
        mode: str = "standard"
    ):
        self.name = name
        self.system_prompt = system_prompt or self._default_prompt()
        self.max_steps = max_steps
        self.llm = llm
        self.tools = tools or []
        self.mode = mode
        
        self.steps: List[ReActStep] = []
        self.history: List[Dict] = []
    
    def _default_prompt(self) -> str:
        """默认系统提示"""
        return """你是一个使用 ReAct (Reason + Act) 模式的 AI 助手。

对于每个问题，你需要遵循以下步骤：
1. 思考 (think): 分析问题，制定计划
2. 行动 (act): 执行工具调用
3. 观察 (observe): 分析结果
4. 决定是否继续或结束 (finish)

请按照以下格式回复：
- thought: <你的思考>
- action: <工具调用，JSON格式>
- observation: <执行结果>

如果问题已解决，回复：
- thought: 问题已解决
- action: null
- observation: 最终答案

如果无法解决，回复：
- thought: 无法继续
- action: null
- observation: 解释原因"""
    
    async def run(self, query: str) -> Dict[str, Any]:
        """
        运行 Agent
        
        Args:
            query: 用户查询
            
        Returns:
            结果字典
        """
        self.steps.clear()
        self.history.clear()
        
        # 初始化
        context = {
            "query": query,
            "history": [],
            "tools": self.tools
        }
        
        # 主循环
        for step_num in range(self.max_steps):
            # 1. 思考
            thought = await self._think(query, context)
            
            # 2. 决定动作
            action = await self._decide_action(thought, context)
            
            step = ReActStep(
                step_num=step_num,
                thought=thought,
                action_type=ActionType.THINK if not action else ActionType.ACT
            )
            
            # 3. 执行动作
            if action:
                result = await self._execute_action(action)
                step.action = action
                step.observation = result.get("observation", "")
                context["history"].append({
                    "action": action,
                    "result": result
                })
            
            self.steps.append(step)
            
            # 4. 检查是否结束
            if self._should_finish(thought, result if action else None):
                step.action_type = ActionType.FINISH
                break
        
        # 生成最终回复
        final_answer = self._generate_final_answer(context)
        
        return {
            "success": True,
            "answer": final_answer,
            "steps": len(self.steps),
            "thoughts": [s.thought for s in self.steps],
            "actions": [s.action for s in self.steps if s.action],
            "history": self.history
        }
    
    async def _think(self, query: str, context: Dict) -> str:
        """思考步骤"""
        if self.llm:
            # 使用 LLM 生成思考
            prompt = self._build_thought_prompt(query, context)
            response = await self.llm.complete(prompt)
            return response.content
        
        # 默认思考
        return f"我需要解决用户的问题: {query}"
    
    def _build_thought_prompt(self, query: str, context: Dict) -> str:
        """构建思考提示"""
        history_text = ""
        for h in context.get("history", [])[-3:]:
            history_text += f"行动: {h['action']}\n结果: {h['result']}\n"
        
        return f"""{self.system_prompt}

当前问题: {query}

历史 (最近 3 步):
{history_text}

请按照 ReAct 格式回复你的思考。"""
    
    async def _decide_action(self, thought: str, context: Dict) -> Optional[Dict]:
        """决定动作"""
        # 检查是否应该结束
        if any(kw in thought.lower() for kw in ["已解决", "finished", "complete", "solved"]):
            return None
        
        # 检查是否需要工具调用
        for tool in self.tools:
            if tool["name"] in thought.lower():
                return {
                    "type": "tool",
                    "tool": tool["name"],
                    "params": self._extract_params(thought, tool)
                }
        
        # 默认生成回复
        return {
            "type": "reply",
            "content": thought
        }
    
    async def _execute_action(self, action: Dict) -> Dict[str, Any]:
        """执行动作"""
        action_type = action.get("type", "reply")
        
        if action_type == "tool":
            tool_name = action.get("tool")
            params = action.get("params", {})
            
            # 模拟工具执行
            result = await self._call_tool(tool_name, params)
            
            return {
                "observation": f"工具 {tool_name} 返回: {result}",
                "success": True
            }
        
        elif action_type == "reply":
            return {
                "observation": action.get("content", ""),
                "success": True
            }
        
        else:
            return {
                "observation": "未知动作类型",
                "success": False
            }
    
    async def _call_tool(self, tool_name: str, params: Dict) -> str:
        """调用工具 (模拟)"""
        # 模拟工具调用
        await asyncio.sleep(0.1)
        
        if tool_name == "search":
            return f"搜索 '{params.get('query', '')}' 的结果"
        elif tool_name == "calculator":
            return f"计算结果: {params.get('expression', '')}"
        else:
            return f"工具 {tool_name} 执行完成"
    
    def _extract_params(self, thought: str, tool: Dict) -> Dict:
        """提取参数"""
        schema = tool.get("parameters", {})
        properties = schema.get("properties", {})
        
        params = {}
        for param_name, param_info in properties.items():
            if param_name in thought:
                params[param_name] = thought
        
        return params
    
    def _should_finish(self, thought: str, result: Dict = None) -> bool:
        """检查是否应该结束"""
        finish_keywords = ["已解决", "finished", "complete", "solved"]
        
        if any(kw in thought.lower() for kw in finish_keywords):
            return True
        
        return False
    
    def _generate_final_answer(self, context: Dict) -> str:
        """生成最终答案"""
        if not self.steps:
            return "未能生成回答"
        
        last_step = self.steps[-1]
        
        if last_step.action_type == ActionType.FINISH:
            return last_step.thought
        
        # 从历史中提取答案
        for h in reversed(context.get("history", [])):
            if h["result"].get("success"):
                return h["result"].get("observation", "")
        
        return last_step.observation or last_step.thought
    
    def get_trace(self) -> List[Dict]:
        """获取执行轨迹"""
        return [
            {
                "step": s.step_num,
                "thought": s.thought,
                "action": s.action,
                "observation": s.observation
            }
            for s in self.steps
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "total_steps": len(self.steps),
            "tools_used": sum(1 for s in self.steps if s.action and s.action.get("type") == "tool"),
            "duration": "N/A"
        }
