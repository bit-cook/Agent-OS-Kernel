# -*- coding: utf-8 -*-
"""AutoGen Bridge - AutoGen 框架桥接

参考 AutoGen 架构设计，支持：
1. 群聊模式
2. 代理选择机制
3. 工具调用
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AutoGenRole(Enum):
    """AutoGen Agent 角色"""
    ASSISTANT = "assistant"
    USER_PROXY = "user_proxy"
    GROUP_ADMIN = "group_admin"


@dataclass
class AutoGenConfig:
    """AutoGen 配置"""
    role: AutoGenRole
    llm_config: Dict = None
    system_message: str = ""
    human_input_mode: str = "never"
    max_consecutive_auto_reply: int = 10


class AutoGenBridge:
    """
    AutoGen 框架桥接器
    
    提供与 AutoGen 兼容的接口。
    """
    
    def __init__(self):
        self._agents: Dict[str, Dict] = {}
        self._group_chats: Dict[str, List[str]] = {}
        self._message_queue: asyncio.Queue = None
        self._running = False
    
    def create_assistant(
        self,
        name: str,
        system_message: str = None,
        llm_config: Dict = None
    ) -> str:
        """创建助手 Agent"""
        agent_id = f"assistant_{name}"
        
        self._agents[agent_id] = {
            "name": name,
            "type": "assistant",
            "role": AutoGenRole.ASSISTANT,
            "system_message": system_message or f"你是 {name}，一个专业助手。",
            "llm_config": llm_config,
            "messages": [],
            "state": "idle"
        }
        
        logger.info(f"Created AutoGen assistant: {name}")
        return agent_id
    
    def create_user_proxy(
        self,
        name: str,
        human_input_mode: str = "never",
        system_message: str = None
    ) -> str:
        """创建用户代理"""
        agent_id = f"user_proxy_{name}"
        
        self._agents[agent_id] = {
            "name": name,
            "type": "user_proxy",
            "role": AutoGenRole.USER_PROXY,
            "system_message": system_message or "代表用户执行任务。",
            "human_input_mode": human_input_mode,
            "messages": [],
            "state": "idle"
        }
        
        logger.info(f"Created AutoGen user proxy: {name}")
        return agent_id
    
    def create_group_chat(
        self,
        name: str,
        agents: List[str],
        admin_name: str = None
    ) -> str:
        """创建群聊"""
        chat_id = f"group_chat_{name}"
        
        self._group_chats[chat_id] = {
            "name": name,
            "agents": agents,
            "admin": admin_name or agents[0] if agents else None,
            "messages": [],
            "current_speaker": None,
            "max_round": 20
        }
        
        logger.info(f"Created group chat: {name} with {len(agents)} agents")
        return chat_id
    
    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        message: str
    ) -> str:
        """发送消息"""
        if sender_id not in self._agents:
            raise ValueError(f"Unknown sender: {sender_id}")
        
        if recipient_id not in self._agents:
            raise ValueError(f"Unknown recipient: {recipient_id}")
        
        # 记录消息
        msg = {
            "from": sender_id,
            "to": recipient_id,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self._agents[recipient_id]["messages"].append(msg)
        
        logger.info(f"Message from {sender_id} to {recipient_id}")
        
        return message
    
    async def run_group_chat(
        self,
        chat_id: str,
        initial_message: str,
        max_rounds: int = None
    ) -> Dict[str, Any]:
        """运行群聊"""
        if chat_id not in self._group_chats:
            raise ValueError(f"Unknown group chat: {chat_id}")
        
        chat = self._group_chats[chat_id]
        chat["messages"].append({
            "role": "user",
            "content": initial_message,
            "sender": "user"
        })
        
        max_rounds = max_rounds or chat["max_round"]
        
        results = []
        
        for round_num in range(max_rounds):
            # 选择下一个发言者
            speaker = self._select_speaker(chat, round_num)
            
            if not speaker:
                break
            
            chat["current_speaker"] = speaker
            
            # 生成回复
            reply = await self._generate_reply(speaker, chat["messages"][-5:])
            
            # 添加到群聊
            chat["messages"].append({
                "role": "assistant",
                "content": reply,
                "sender": speaker
            })
            
            results.append({
                "round": round_num + 1,
                "speaker": speaker,
                "reply": reply[:100] + "..."
            })
            
            # 检查是否结束
            if self._should_end_group_chat(reply, chat):
                break
        
        return {
            "success": True,
            "rounds": len(results),
            "messages": chat["messages"],
            "summary": self._summarize_group_chat(results)
        }
    
    def _select_speaker(self, chat: Dict, round_num: int) -> Optional[str]:
        """选择发言者"""
        agents = chat["agents"]
        
        if not agents:
            return None
        
        if round_num == 0:
            return agents[0]
        
        # 轮询选择
        return agents[round_num % len(agents)]
    
    async def _generate_reply(
        self,
        agent_id: str,
        context: List[Dict]
    ) -> str:
        """生成回复"""
        agent = self._agents.get(agent_id)
        
        if not agent:
            return "[错误: Agent 不存在]"
        
        # 检查是否有 LLM 配置
        if agent.get("llm_config"):
            # 使用 LLM 生成 (模拟)
            return f"[{agent['name']}] {self._simulate_llm_reply(context)}"
        
        # 默认回复
        return f"[{agent['name']}] 收到消息。"
    
    def _simulate_llm_reply(self, context: List[Dict]) -> str:
        """模拟 LLM 回复"""
        last_msg = context[-1] if context else {}
        content = last_msg.get("content", "")
        
        return f"我理解了: {content[:50]}..."
    
    def _should_end_group_chat(self, reply: str, chat: Dict) -> bool:
        """检查群聊是否结束"""
        end_phrases = ["任务完成", "finished", "done", "结束"]
        
        for phrase in end_phrases:
            if phrase.lower() in reply.lower():
                return True
        
        return False
    
    def _summarize_group_chat(self, results: List[Dict]) -> str:
        """总结群聊"""
        if not results:
            return "没有生成回复"
        
        speakers = set(r["speaker"] for r in results)
        
        return f"群聊完成 {len(results)} 轮，{len(speakers)} 个 Agent 参与。"
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """获取 Agent"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[Dict]:
        """列出所有 Agent"""
        return [
            {
                "id": aid,
                "name": info["name"],
                "type": info["type"],
                "messages_count": len(info["messages"])
            }
            for aid, info in self._agents.items()
        ]
    
    def get_chat_history(self, chat_id: str) -> List[Dict]:
        """获取群聊历史"""
        if chat_id in self._group_chats:
            return self._group_chats[chat_id]["messages"]
        return []
    
    def clear_all(self):
        """清空所有"""
        self._agents.clear()
        self._group_chats.clear()


class GroupChatManager:
    """群聊管理器"""
    
    def __init__(self, bridge: AutoGenBridge):
        self.bridge = bridge
    
    async def start_discussion(
        self,
        topic: str,
        agents: List[str],
        strategy: str = "round_robin"
    ) -> Dict[str, Any]:
        """开始讨论"""
        chat_id = self.bridge.create_group_chat(
            name=f"discussion_{int(datetime.now().timestamp())}",
            agents=agents
        )
        
        return await self.bridge.run_group_chat(chat_id, topic)


# 便捷函数
def create_autogen_bridge() -> AutoGenBridge:
    """创建 AutoGen 桥接器"""
    return AutoGenBridge()
