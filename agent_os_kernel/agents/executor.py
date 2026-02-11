# -*- coding: utf-8 -*-
"""Agent Executor - Agent 执行器

负责 Agent 的实际执行逻辑
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from datetime import timezone, timezone
from uuid import uuid4

from .base import BaseAgent, AgentConfig, AgentState
from ..llm import LLMProviderFactory
from ..core.events import EventBus, EventType
from ..core.cost_tracker import CostTracker
from ..core.observability import Observability

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Agent 执行器
    
    负责:
    - Agent 生命周期管理
    - 任务执行
    - 状态追踪
    - 错误处理
    """
    
    def __init__(
        self,
        agent: BaseAgent,
        event_bus: Optional[EventBus] = None,
        cost_tracker: Optional[CostTracker] = None,
        observability: Optional[Observability] = None
    ):
        """初始化执行器"""
        self.agent = agent
        self.event_bus = event_bus or EventBus()
        self.cost_tracker = cost_tracker or CostTracker()
        self.observability = observability or Observability()
        
        self._running = False
        self._current_task: Optional[Dict] = None
        
        logger.info(f"AgentExecutor initialized for {agent.config.name}")
    
    async def start(self) -> bool:
        """启动 Agent"""
        if self._running:
            logger.warning(f"Agent {self.agent.config.name} already running")
            return False
        
        self._running = True
        
        # 发送启动事件
        self.event_bus.publish(EventType.AGENT_STARTED, {
            "agent_id": self.agent.agent_id,
            "agent_name": self.agent.config.name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # 更新状态
        self.agent.state = AgentState.RUNNING
        
        logger.info(f"Agent {self.agent.config.name} started")
        return True
    
    async def stop(self, reason: str = "user_request") -> bool:
        """停止 Agent"""
        if not self._running:
            return True
        
        self._running = False
        
        # 发送停止事件
        self.event_bus.publish(EventType.AGENT_STOPPED, {
            "agent_id": self.agent.agent_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # 更新状态
        self.agent.state = AgentState.STOPPED
        
        logger.info(f"Agent {self.agent.config.name} stopped: {reason}")
        return True
    
    async def execute_task(
        self,
        task: str,
        context: Optional[Dict] = None,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """执行任务
        
        Args:
            task: 任务描述
            context: 上下文
            callback: 回调函数
            
        Returns:
            执行结果
        """
        if not self._running:
            await self.start()
        
        self._current_task = {
            "task": task,
            "context": context or {},
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        # 发送任务开始事件
        self.event_bus.publish(EventType.TASK_STARTED, {
            "agent_id": self.agent.agent_id,
            "task": task,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            # 执行任务
            result = await self._execute_with_retry(task, context)
            
            # 记录成本
            if hasattr(result, "usage"):
                self.cost_tracker.record(
                    provider=result.get("provider", "unknown"),
                    model=result.get("model", "unknown"),
                    input_tokens=result.get("input_tokens", 0),
                    output_tokens=result.get("output_tokens", 0),
                    agent_id=self.agent.agent_id
                )
            
            # 发送任务完成事件
            self.event_bus.publish(EventType.TASK_COMPLETED, {
                "agent_id": self.agent.agent_id,
                "task": task,
                "result": "success",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # 调用回调
            if callback:
                callback(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Task failed: {e}")
            
            # 发送任务失败事件
            self.event_bus.publish(EventType.TASK_FAILED, {
                "agent_id": self.agent.agent_id,
                "task": task,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            raise
    
    async def _execute_with_retry(
        self,
        task: str,
        context: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """带重试的执行"""
        retries = 0
        
        while retries < max_retries:
            try:
                return await self._execute_single(task, context)
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    raise
                logger.warning(f"Retry {retries}/{max_retries}: {e}")
                await asyncio.sleep(2 ** retries)  # 指数退避
    
    async def _execute_single(
        self,
        task: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """单次执行"""
        # 构建消息
        messages = self._build_messages(task, context)
        
        # 发送 LLM 请求
        start_time = datetime.now(timezone.utc)
        
        provider = self.agent.llm_provider
        
        # 调用 LLM
        response = await provider.chat(messages)
        
        # 计算成本
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # 记录可观测性
        self.observability.record_llm_call(
            provider=provider.provider_name,
            model=getattr(provider, "model", "unknown"),
            input_tokens=response.get("input_tokens", 0),
            output_tokens=response.get("output_tokens", 0),
            duration_ms=duration_ms,
            agent_id=self.agent.agent_id
        )
        
        return {
            "response": response.get("content", ""),
            "provider": provider.provider_name,
            "model": getattr(provider, "model", "unknown"),
            "input_tokens": response.get("input_tokens", 0),
            "output_tokens": response.get("output_tokens", 0),
            "duration_ms": duration_ms
        }
    
    def _build_messages(
        self,
        task: str,
        context: Optional[Dict] = None
    ) -> list:
        """构建消息"""
        messages = []
        
        # 系统消息
        system_prompt = self._build_system_prompt()
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 上下文
        if context:
            context_text = self._format_context(context)
            messages.append({
                "role": "user",
                "content": f"Context:\n{context_text}\n\nTask: {task}"
            })
        else:
            messages.append({
                "role": "user",
                "content": task
            })
        
        return messages
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        parts = [
            f"You are {self.agent.config.name}.",
            f"Role: {self.agent.config.role or 'General Assistant'}.",
        ]
        
        if self.agent.config.goal:
            parts.append(f"Goal: {self.agent.config.goal}")
        
        if self.agent.config.backstory:
            parts.append(f"Background: {self.agent.config.backstory}")
        
        if self.agent.config.constraints:
            parts.append(f"Constraints: {self.agent.config.constraints}")
        
        return "\n".join(parts)
    
    def _format_context(self, context: Dict) -> str:
        """格式化上下文"""
        parts = []
        
        for key, value in context.items():
            if isinstance(value, list):
                value = "\n".join(str(v) for v in value)
            parts.append(f"- {key}: {value}")
        
        return "\n".join(parts)
    
    def get_status(self) -> Dict[str, Any]:
        """获取执行器状态"""
        return {
            "agent_id": self.agent.agent_id,
            "agent_name": self.agent.config.name,
            "running": self._running,
            "current_task": self._current_task,
            "state": self.agent.state.value if hasattr(self.agent.state, 'value') else str(self.agent.state),
            "cost": self.cost_tracker.get_global_stats(),
        }
    
    async def stream_execute(
        self,
        task: str,
        context: Optional[Dict] = None
    ):
        """流式执行 (生成器)"""
        if not self._running:
            await self.start()
        
        messages = self._build_messages(task, context)
        provider = self.agent.llm_provider
        
        async for chunk in provider.stream_chat(messages):
            yield chunk


class MultiAgentExecutor:
    """多 Agent 执行器"""
    
    def __init__(self, executors: Dict[str, AgentExecutor]):
        """初始化"""
        self.executors = executors
        self._running = set()
    
    def add_executor(self, name: str, executor: AgentExecutor):
        """添加执行器"""
        self.executors[name] = executor
    
    def remove_executor(self, name: str):
        """移除执行器"""
        if name in self.executors:
            del self.executors[name]
    
    async def execute_parallel(
        self,
        tasks: Dict[str, str],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """并行执行多个 Agent"""
        import asyncio
        
        async def run_agent(name: str, task: str):
            executor = self.executors.get(name)
            if executor:
                return await executor.execute_task(task, context)
            return {"error": f"Executor {name} not found"}
        
        results = await asyncio.gather(*[
            run_agent(name, task) for name, task in tasks.items()
        ])
        
        return dict(zip(tasks.keys(), results))
    
    async def execute_sequential(
        self,
        tasks: list,
        initial_context: Optional[Dict] = None
    ) -> list:
        """顺序执行多个 Agent"""
        results = []
        context = initial_context or {}
        
        for task_spec in tasks:
            name = task_spec.get("agent")
            task = task_spec.get("task")
            
            executor = self.executors.get(name)
            if executor:
                result = await executor.execute_task(task, context)
                results.append(result)
                
                # 更新上下文
                context[task_spec.get("output_key", name)] = result
            
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有执行器状态"""
        return {
            name: executor.get_status()
            for name, executor in self.executors.items()
        }
