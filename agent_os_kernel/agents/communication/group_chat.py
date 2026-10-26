# -*- coding: utf-8 -*-
"""Group Chat - Agent 群聊协作

支持：
1. 群聊管理
2. 角色分配
3. 轮流发言
4. 话题控制
5. 决策共识
"""

import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ChatRole(Enum):
    """聊天角色"""
    MODERATOR = "moderator"    # 主持人
    SPEAKER = "speaker"       # 发言者
    LISTENER = "listener"      # 听众
    EXPERT = "expert"         # 专家
    RECORDER = "recorder"     # 记录员


class ChatPhase(Enum):
    """聊天阶段"""
    INTRO = "intro"           # 介绍
    DISCUSSION = "discussion"  # 讨论
    EXPERT_REVIEW = "expert_review"  # 专家评审
    CONSENSUS = "consensus"    # 共识
    CONCLUSION = "conclusion"  # 总结


@dataclass
class ChatMember:
    """聊天成员"""
    agent_id: str
    agent_name: str
    role: ChatRole
    joined_at: datetime = field(default_factory=datetime.now)
    last_spoke: Optional[datetime] = None
    message_count: int = 0
    expertise: List[str] = field(default_factory=list)


@dataclass
class ChatMessage:
    """聊天消息"""
    msg_id: str
    member_id: str
    member_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    phase: ChatPhase = ChatPhase.DISCUSSION
    reply_to: Optional[str] = None
    consensus_score: float = 0.0  # 共识分数


class GroupChatManager:
    """
    Agent 群聊管理器
    
    功能：
    1. 创建和管理群聊
    2. 成员管理
    3. 轮流发言控制
    4. 话题管理
    5. 共识决策
    """
    
    def __init__(self, messenger=None):
        self.messenger = messenger
        self._chats: Dict[str, Dict] = {}
        self._active_chat: Optional[str] = None
        self._callbacks: Dict[str, Callable] = {}
    
    def create_chat(
        self,
        chat_id: str,
        topic: str,
        max_members: int = 10
    ) -> str:
        """创建群聊"""
        self._chats[chat_id] = {
            "chat_id": chat_id,
            "topic": topic,
            "phase": ChatPhase.INTRO,
            "members": {},
            "messages": [],
            "max_members": max_members,
            "created_at": datetime.now(),
            "round": 0,
            "consensus_threshold": 0.7,
            "max_rounds": 20
        }
        
        logger.info(f"Chat created: {chat_id} (topic: {topic})")
        return chat_id
    
    async def join_chat(
        self,
        chat_id: str,
        agent_id: str,
        agent_name: str,
        role: ChatRole = ChatRole.SPEAKER,
        expertise: List[str] = None
    ) -> bool:
        """加入群聊"""
        if chat_id not in self._chats:
            logger.warning(f"Chat not found: {chat_id}")
            return False
        
        chat = self._chats[chat_id]
        
        if len(chat["members"]) >= chat["max_members"]:
            logger.warning(f"Chat full: {chat_id}")
            return False
        
        member = ChatMember(
            agent_id=agent_id,
            agent_name=agent_name,
            role=role,
            expertise=expertise or []
        )
        
        chat["members"][agent_id] = member
        
        logger.info(f"Member joined: {agent_name} -> {chat_id}")
        
        return True
    
    async def leave_chat(self, chat_id: str, agent_id: str) -> bool:
        """离开群聊"""
        if chat_id not in self._chats:
            return False
        
        if agent_id in self._chats[chat_id]["members"]:
            del self._chats[chat_id]["members"][agent_id]
            logger.info(f"Member left: {agent_id}")
            return True
        
        return False
    
    async def send_message(
        self,
        chat_id: str,
        agent_id: str,
        content: str,
        reply_to: str = None
    ) -> Optional[ChatMessage]:
        """发送消息"""
        if chat_id not in self._chats:
            return None
        
        chat = self._chats[chat_id]
        
        if agent_id not in chat["members"]:
            return None
        
        member = chat["members"][agent_id]
        
        msg = ChatMessage(
            msg_id=f"msg_{len(chat['messages'])}",
            member_id=agent_id,
            member_name=member.agent_name,
            content=content,
            reply_to=reply_to,
            phase=chat["phase"]
        )
        
        chat["messages"].append(msg)
        member.last_spoke = datetime.now()
        member.message_count += 1
        
        # 检查是否达成共识
        await self._check_consensus(chat_id, msg)
        
        # 更新阶段
        await self._update_phase(chat_id)
        
        return msg
    
    async def _check_consensus(self, chat_id: str, message: ChatMessage):
        """检查共识"""
        # 简单共识检查：包含"同意"或"共识"的消息
        if any(kw in message.content.lower() for kw in ["agree", "同意", "consensus", "共识"]):
            message.consensus_score = 0.9
            logger.info(f"Consensus detected in {chat_id}")
    
    async def _update_phase(self, chat_id: str):
        """更新聊天阶段"""
        chat = self._chats[chat_id]
        
        # 基于消息数量更新阶段
        msg_count = len(chat["messages"])
        
        if msg_count < 3:
            chat["phase"] = ChatPhase.INTRO
        elif msg_count < 10:
            chat["phase"] = ChatPhase.DISCUSSION
        elif msg_count < 20:
            chat["phase"] = ChatPhase.EXPERT_REVIEW
        elif msg_count < 30:
            chat["phase"] = ChatPhase.CONSENSUS
        else:
            chat["phase"] = ChatPhase.CONCLUSION
    
    async def next_round(self, chat_id: str) -> bool:
        """下一轮"""
        if chat_id not in self._chats:
            return False
        
        chat = self._chats[chat_id]
        
        if chat["round"] >= chat["max_rounds"]:
            logger.warning(f"Max rounds reached: {chat_id}")
            return False
        
        chat["round"] += 1
        chat["phase"] = ChatPhase.DISCUSSION
        
        logger.info(f"Next round: {chat_id} (round {chat['round']})")
        
        return True
    
    async def assign_role(
        self,
        chat_id: str,
        agent_id: str,
        role: ChatRole
    ) -> bool:
        """分配角色"""
        if chat_id not in self._chats:
            return False
        
        if agent_id in self._chats[chat_id]["members"]:
            self._chats[chat_id]["members"][agent_id].role = role
            return True
        
        return False
    
    def get_members(self, chat_id: str) -> List[Dict]:
        """获取成员列表"""
        if chat_id not in self._chats:
            return []
        
        return [
            {
                "agent_id": m.agent_id,
                "name": m.agent_name,
                "role": m.role.value,
                "messages": m.message_count,
                "expertise": m.expertise
            }
            for m in self._chats[chat_id]["members"].values()
        ]
    
    def get_messages(
        self,
        chat_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """获取消息历史"""
        if chat_id not in self._chats:
            return []
        
        messages = self._chats[chat_id]["messages"][-limit:]
        
        return [
            {
                "id": m.msg_id,
                "member": m.member_name,
                "content": m.content[:100],
                "phase": m.phase.value,
                "timestamp": m.timestamp.isoformat()
            }
            for m in messages
        ]
    
    def get_status(self, chat_id: str) -> Dict:
        """获取群聊状态"""
        if chat_id not in self._chats:
            return {}
        
        chat = self._chats[chat_id]
        
        return {
            "chat_id": chat_id,
            "topic": chat["topic"],
            "phase": chat["phase"].value,
            "round": chat["round"],
            "members_count": len(chat["members"]),
            "messages_count": len(chat["messages"]),
            "created_at": chat["created_at"].isoformat()
        }
    
    def list_chats(self) -> List[Dict]:
        """列出所有群聊"""
        return [self.get_status(chat_id) for chat_id in self._chats]
    
    async def end_chat(self, chat_id: str) -> Dict:
        """结束群聊"""
        if chat_id not in self._chats:
            return {}
        
        chat = self._chats[chat_id]
        
        # 生成总结
        summary = {
            "chat_id": chat_id,
            "topic": chat["topic"],
            "total_messages": len(chat["messages"]),
            "total_members": len(chat["members"]),
            "total_rounds": chat["round"],
            "final_phase": chat["phase"].value
        }
        
        # 保存到历史
        if self._active_chat == chat_id:
            self._active_chat = None
        
        del self._chats[chat_id]
        
        logger.info(f"Chat ended: {chat_id}")
        
        return summary


# 便捷函数
def create_group_chat_manager(messenger=None) -> GroupChatManager:
    """创建群聊管理器"""
    return GroupChatManager(messenger)
