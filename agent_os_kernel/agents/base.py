# -*- coding: utf-8 -*-
"""Base Agent - Agent 抽象基类

参考 AutoGen 架构设计，提供统一的 Agent 接口。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent 状态"""
    CREATED = "created"
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str
    system_prompt: str = ""
    max_iterations: int = 100
    timeout_seconds: int = 300
    retry_on_error: int = 3
    human_input_mode: str = "never"  # never, always, approved
    auto_reply: bool = True
    tools: List[Dict] = field(default_factory=list)
    memory: Dict = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Agent 基类
    
    参考 AutoGen Agent 设计，提供统一的接口。
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.state = AgentState.CREATED
        self.pid: Optional[str] = None
        self._created_at = datetime.now()
        self._messages: List[Dict] = []
        self._task_history: List[Dict] = []
        self._memory: Dict = {}
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent 类型标识"""
        pass
    
    @property
    def name(self) -> str:
        """Agent 名称"""
        return self.config.name
    
    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self.state == AgentState.RUNNING
    
    @property
    def is_terminated(self) -> bool:
        """是否已终止"""
        return self.state == AgentState.TERMINATED
    
    async def start(self, task: str) -> str:
        """启动 Agent"""
        self.pid = f"{self.agent_type}_{self.name}_{int(datetime.now().timestamp())}"
        self.state = AgentState.IDLE
        
        logger.info(f"Agent started: {self.pid}")
        
        return self.pid
    
    async def run(self, task: str) -> Dict[str, Any]:
        """运行 Agent"""
        self.state = AgentState.RUNNING
        start_time = datetime.now()
        
        try:
            # 执行主循环
            for iteration in range(self.config.max_iterations):
                if self.state == AgentState.TERMINATED:
                    break
                
                # 生成回复
                response = await self._think(task)
                
                if response.get("stop"):
                    break
                
                # 执行动作
                if response.get("action"):
                    result = await self._execute(response["action"])
                    response["result"] = result
                
                # 更新状态
                task = response.get("result", "")
            
            # 返回结果
            return {
                "success": True,
                "iterations": iteration + 1,
                "duration": (datetime.now() - start_time).total_seconds(),
                "messages": self._messages
            }
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "success": False,
                "error": str(e),
                "iterations": iteration + 1 if 'iteration' in locals() else 0
            }
        finally:
            self.state = AgentState.IDLE
    
    @abstractmethod
    async def _think(self, task: str) -> Dict[str, Any]:
        """思考步骤 - 生成回复或动作"""
        pass
    
    async def _execute(self, action: Dict) -> Dict[str, Any]:
        """执行动作"""
        return {"success": True, "result": "executed"}
    
    async def terminate(self, reason: str = "normal"):
        """终止 Agent"""
        self.state = AgentState.TERMINATED
        logger.info(f"Agent terminated: {self.pid}, reason: {reason}")
    
    def send_message(self, message: Dict):
        """发送消息"""
        self._messages.append({
            "timestamp": datetime.now().isoformat(),
            **message
        })
    
    def receive_message(self, message: Dict) -> str:
        """接收消息"""
        self._messages.append({
            "timestamp": datetime.now().isoformat(),
            **message
        })
        return self._messages[-1].get("content", "")
    
    def get_history(self) -> List[Dict]:
        """获取历史"""
        return self._task_history
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "pid": self.pid,
            "name": self.name,
            "type": self.agent_type,
            "state": self.state.value,
            "created_at": self._created_at.isoformat(),
            "iterations": len(self._task_history),
            "messages_count": len(self._messages)
        }
    
    def save_memory(self, key: str, value: Any):
        """保存记忆"""
        self._memory[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    
    def load_memory(self, key: str) -> Optional[Any]:
        """加载记忆"""
        if key in self._memory:
            return self._memory[key]["value"]
        return None
    
    def clear_memory(self):
        """清空记忆"""
        self._memory.clear()
    
    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "config": {
                "name": self.config.name,
                "system_prompt": self.config.system_prompt,
                "max_iterations": self.config.max_iterations,
                "timeout_seconds": self.config.timeout_seconds
            },
            "state": self.state.value,
            "pid": self.pid,
            "created_at": self._created_at.isoformat(),
            "memory_keys": list(self._memory.keys())
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BaseAgent':
        """从字典恢复"""
        config = AgentConfig(
            name=data["config"]["name"],
            system_prompt=data["config"]["system_prompt"],
            max_iterations=data["config"]["max_iterations"],
            timeout_seconds=data["config"]["timeout_seconds"]
        )
        agent = cls(config)
        agent.state = AgentState(data["state"])
        agent.pid = data["pid"]
        return agent


class ConversableAgent(BaseAgent):
    """
    可对话 Agent
    
    支持多轮对话，参考 AutoGen ConversableAgent。
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._llm = None
        self._tools = []
    
    def set_llm(self, llm):
        """设置 LLM"""
        self._llm = llm
    
    def register_tool(self, tool: Callable):
        """注册工具"""
        self._tools.append(tool)
    
    async def generate_reply(
        self,
        messages: List[Dict],
        sender: Optional[BaseAgent] = None
    ) -> str:
        """生成回复"""
        if self._llm:
            # 使用 LLM 生成
            response = await self._llm.complete(messages)
            return response.content
        
        # 默认回复
        return "我理解了你的消息。"
    
    async def send(
        self,
        message: str,
        recipient: BaseAgent,
        request_reply: bool = True
    ):
        """发送消息给其他 Agent"""
        recipient.receive_message({
            "content": message,
            "sender": self.name
        })
        
        if request_reply:
            reply = await recipient.generate_reply(
                recipient._messages,
                sender=self
            )
            return reply
    
    async def _think(self, task: str) -> Dict[str, Any]:
        """思考"""
        messages = self._messages + [{"role": "user", "content": task}]
        
        reply = await self.generate_reply(messages)
        
        return {
            "content": reply,
            "stop": True  # 对话模式默认停止
        }


class AssistantAgent(ConversableAgent):
    """
    助手 Agent
    
    参考 AutoGen AssistantAgent 设计。
    """
    
    @property
    def agent_type(self) -> str:
        return "assistant"
    
    async def _think(self, task: str) -> Dict[str, Any]:
        """思考"""
        messages = self._messages + [{"role": "user", "content": task}]
        
        reply = await self.generate_reply(messages)
        
        return {
            "content": reply,
            "stop": True
        }


class UserProxyAgent(ConversableAgent):
    """
    用户代理 Agent
    
    参考 AutoGen UserProxyAgent 设计。
    """
    
    @property
    def agent_type(self) -> str:
        return "user_proxy"
    
    async def _think(self, task: str) -> Dict[str, Any]:
        """思考"""
        # 用户代理直接执行任务
        return {
            "content": task,
            "action": {"type": "execute", "task": task}
        }
    
    async def execute_task(self, task: str) -> Dict[str, Any]:
        """执行任务"""
        return await self.run(task)


# 注册
from .react import ReActAgent
from .autogen_bridge import AutoGenBridge
from .workflow_agent import WorkflowAgent
