# -*- coding: utf-8 -*-
"""Agent Messenger - Agent 消息传递系统

支持：
1. 点对点消息
2. 广播消息
3. 主题订阅
4. 消息优先级
5. 消息持久化
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import hashlib

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""

    # 基础消息
    CHAT = "chat"  # 聊天消息
    TASK = "task"  # 任务消息
    QUERY = "query"  # 查询消息
    RESPONSE = "response"  # 响应消息
    NOTIFICATION = "notification"  # 通知消息

    # 学习相关
    KNOWLEDGE = "knowledge"  # 知识共享
    EXPERIENCE = "experience"  # 经验分享
    FEEDBACK = "feedback"  # 反馈消息

    # 系统消息
    HEARTBEAT = "heartbeat"  # 心跳
    STATUS = "status"  # 状态更新
    SYNC = "sync"  # 同步请求


@dataclass
class Message:
    """消息"""

    msg_id: str
    msg_type: MessageType
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0  # 0-100, 越高越优先
    topic: Optional[str] = None
    receiver_id: Optional[str] = None  # None 表示广播
    metadata: Dict = field(default_factory=dict)
    reply_to: Optional[str] = None  # 关联的消息ID
    ttl_seconds: int = 3600  # 存活时间

    @classmethod
    def create(
        cls,
        msg_type: MessageType,
        sender_id: str,
        sender_name: str,
        content: str,
        receiver_id: str = None,
        topic: str = None,
        priority: int = 0,
    ) -> "Message":
        """创建消息"""
        return cls(
            msg_id=str(uuid.uuid4()),
            msg_type=msg_type,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            receiver_id=receiver_id,
            topic=topic,
            priority=priority,
        )

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "topic": self.topic,
            "receiver_id": self.receiver_id,
            "metadata": self.metadata,
            "reply_to": self.reply_to,
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        """从字典恢复"""
        data["msg_type"] = MessageType(data["msg_type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

    def get_hash(self) -> str:
        """获取消息哈希"""
        content = f"{self.sender_id}:{self.content}:{self.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()


class MessageHandler:
    """消息处理器"""

    def __init__(self, handler_id: str, callback: Callable):
        self.handler_id = handler_id
        self.callback = callback
        self.filters: List[Callable] = []

    def add_filter(self, filter_fn: Callable[[Message], bool]):
        """添加过滤器"""
        self.filters.append(filter_fn)

    def matches(self, message: Message) -> bool:
        """检查是否匹配"""
        for filter_fn in self.filters:
            if not filter_fn(message):
                return False
        return True


class AgentMessenger:
    """
    Agent 消息传递系统

    功能：
    1. 点对点消息
    2. 广播消息
    3. 主题订阅
    4. 消息优先级
    5. 消息持久化
    """

    def __init__(self, storage_dir: str = "./messages"):
        self.storage_dir = storage_dir
        self._inbox: Dict[str, asyncio.Queue] = {}  # Agent 收件箱
        self._topics: Dict[str, set] = {}  # 主题订阅
        self._handlers: List[MessageHandler] = []  # 消息处理器
        self._history: List[Message] = []  # 消息历史
        self._max_history = 10000
        self._lock = asyncio.Lock()

        import os

        os.makedirs(storage_dir, exist_ok=True)

    async def register_agent(self, agent_id: str, agent_name: str):
        """注册 Agent"""
        async with self._lock:
            if agent_id not in self._inbox:
                self._inbox[agent_id] = asyncio.Queue(maxsize=1000)
                logger.info(f"Agent registered: {agent_id} ({agent_name})")
            else:
                logger.warning(f"Agent already registered: {agent_id}")

    async def unregister_agent(self, agent_id: str):
        """注销 Agent"""
        async with self._lock:
            if agent_id in self._inbox:
                del self._inbox[agent_id]
                logger.info(f"Agent unregistered: {agent_id}")

    async def send(self, message: Message, store: bool = True) -> bool:
        """发送消息"""
        # 保存到历史
        if store:
            self._add_to_history(message)

        # 点对点消息
        if message.receiver_id:
            return await self._send_direct(message)

        # 广播消息
        else:
            return await self._broadcast(message)

    async def _send_direct(self, message: Message) -> bool:
        """直接发送消息"""
        async with self._lock:
            if message.receiver_id not in self._inbox:
                logger.warning(f"Agent not found: {message.receiver_id}")
                return False

            try:
                await self._inbox[message.receiver_id].put(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                return False

    async def _broadcast(self, message: Message) -> bool:
        """广播消息"""
        sent_count = 0

        async with self._lock:
            receivers = list(self._inbox.keys())

        # 发送给所有 Agent (除了发送者)
        for agent_id in receivers:
            if agent_id != message.sender_id:
                message.receiver_id = agent_id
                if await self._send_direct(message):
                    sent_count += 1

        logger.info(f"Broadcast to {sent_count} agents")
        return sent_count > 0

    async def receive(self, agent_id: str, timeout: float = None) -> Optional[Message]:
        """接收消息 (阻塞)"""
        if agent_id not in self._inbox:
            logger.warning(f"Agent not found: {agent_id}")
            return None

        try:
            if timeout:
                return await asyncio.wait_for(self._inbox[agent_id].get(), timeout=timeout)
            else:
                return await self._inbox[agent_id].get()
        except asyncio.TimeoutError:
            return None

    async def receive_batch(
        self, agent_id: str, max_count: int = 10, timeout: float = 5.0
    ) -> List[Message]:
        """批量接收消息"""
        messages = []
        end_time = asyncio.get_event_loop().time() + timeout

        while len(messages) < max_count:
            remaining = end_time - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            msg = await self.receive(agent_id, timeout=remaining)
            if msg:
                messages.append(msg)
            else:
                break

        return messages

    def subscribe(self, agent_id: str, topic: str):
        """订阅主题"""
        if topic not in self._topics:
            self._topics[topic] = set()
        self._topics[topic].add(agent_id)
        logger.info(f"Agent {agent_id} subscribed to topic: {topic}")

    def unsubscribe(self, agent_id: str, topic: str):
        """取消订阅"""
        if topic in self._topics:
            self._topics[topic].discard(agent_id)

    async def send_to_topic(self, topic: str, message: Message):
        """发送到主题"""
        if topic in self._topics:
            message.topic = topic
            for agent_id in self._topics[topic]:
                if agent_id != message.sender_id:
                    await self._send_direct(message)

    def add_handler(self, handler: MessageHandler):
        """添加消息处理器"""
        self._handlers.append(handler)

    async def process_messages(self):
        """处理消息 (后台任务)"""
        while True:
            try:
                for handler in self._handlers:
                    # 检查每个 Agent 的消息
                    for agent_id in self._inbox.keys():
                        msg = await self.receive(agent_id, timeout=0.1)
                        if msg and handler.matches(msg):
                            await handler.callback(msg)
            except Exception as e:
                logger.error(f"Message processing error: {e}")
            await asyncio.sleep(0.1)

    def _add_to_history(self, message: Message):
        """添加到历史"""
        self._history.append(message)

        # 限制历史长度
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_history(
        self,
        agent_id: str = None,
        msg_type: MessageType = None,
        topic: str = None,
        limit: int = 100,
    ) -> List[Message]:
        """获取消息历史"""
        result = self._history

        if agent_id:
            result = [m for m in result if m.sender_id == agent_id or m.receiver_id == agent_id]

        if msg_type:
            result = [m for m in result if m.msg_type == msg_type]

        if topic:
            result = [m for m in result if m.topic == topic]

        return result[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "registered_agents": len(self._inbox),
            "topics": len(self._topics),
            "total_messages": len(self._history),
            "handlers": len(self._handlers),
            "topic_subscriptions": sum(len(s) for s in self._topics.values()),
        }

    async def clear(self, agent_id: str = None):
        """清空消息"""
        async with self._lock:
            if agent_id:
                if agent_id in self._inbox:
                    while not self._inbox[agent_id].empty():
                        try:
                            self._inbox[agent_id].get_nowait()
                        except asyncio.QueueEmpty:
                            break
            else:
                for agent_id in self._inbox:
                    while not self._inbox[agent_id].empty():
                        try:
                            self._inbox[agent_id].get_nowait()
                        except asyncio.QueueEmpty:
                            break
                self._history.clear()

        logger.info(f"Messages cleared for: {agent_id or 'all'}")


# 便捷函数
def create_messenger(storage_dir: str = "./messages") -> AgentMessenger:
    """创建消息系统"""
    return AgentMessenger(storage_dir)
