# -*- coding: utf-8 -*-
"""Async Queue - 异步队列

高性能异步消息队列，支持发布/订阅模式。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from uuid import uuid4
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class QueueType(Enum):
    """队列类型"""
    FIFO = "fifo"
    LIFO = "lifo"
    PRIORITY = "priority"
    DELAY = "delay"


class MessageStatus(Enum):
    """消息状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ACKED = "acked"


@dataclass
class Message:
    """消息"""
    msg_id: str
    topic: str
    payload: Dict[str, Any]
    status: MessageStatus = MessageStatus.PENDING
    priority: int = 5
    delay_seconds: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps({
            "msg_id": self.msg_id,
            "topic": self.topic,
            "payload": self.payload,
            "priority": self.priority,
            "created_at": self.created_at.isoformat()
        })


class AsyncQueue:
    """异步消息队列"""
    
    def __init__(
        self,
        name: str = "default",
        queue_type: QueueType = QueueType.FIFO,
        max_size: int = 10000,
        ttl: int = 3600
    ):
        """
        初始化异步队列
        
        Args:
            name: 队列名称
            queue_type: 队列类型
            max_size: 最大容量
            ttl: 消息存活时间（秒）
        """
        self.name = name
        self.queue_type = queue_type
        self.max_size = max_size
        self.ttl = ttl
        
        self._queues: Dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue(maxsize=max_size))
        self._topics: Set[str] = set()
        self._subscribers: Dict[str, Set[Callable]] = defaultdict(set)
        self._callbacks: Dict[str, Set[Callable]] = defaultdict(set)
        self._running = False
        self._worker_tasks: Dict[str, asyncio.Task] = {}
        self._stats = {
            "published": 0,
            "consumed": 0,
            "failed": 0
        }
        
        logger.info(f"AsyncQueue initialized: {name}, type={queue_type.value}")
    
    async def start(self):
        """启动队列"""
        self._running = True
        logger.info(f"AsyncQueue started: {self.name}")
    
    async def stop(self):
        """停止队列"""
        self._running = False
        for task in self._worker_tasks.values():
            task.cancel()
        logger.info(f"AsyncQueue stopped: {self.name}")
    
    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        priority: int = 5,
        delay_seconds: float = 0.0
    ) -> str:
        """
        发布消息
        
        Args:
            topic: 主题
            payload: 消息内容
            priority: 优先级 (1-10)
            delay_seconds: 延迟时间
            
        Returns:
            消息 ID
        """
        msg_id = str(uuid4())
        
        msg = Message(
            msg_id=msg_id,
            topic=topic,
            payload=payload,
            priority=priority,
            delay_seconds=delay_seconds
        )
        
        self._topics.add(topic)
        
        if delay_seconds > 0:
            asyncio.create_task(self._delayed_publish(msg))
        else:
            await self._queues[topic].put(msg)
        
        self._stats["published"] += 1
        
        logger.debug(f"Published message: {topic} -> {msg_id}")
        
        # 通知订阅者
        await self._notify_subscribers(topic, msg)
        
        return msg_id
    
    async def _delayed_publish(self, msg: Message):
        """延迟发布"""
        await asyncio.sleep(msg.delay_seconds)
        await self._queues[msg.topic].put(msg)
    
    async def subscribe(
        self,
        topic: str,
        callback: Callable[[Message], Any],
        ordered: bool = True
    ):
        """
        订阅主题
        
        Args:
            topic: 主题
            callback: 回调函数
            ordered: 是否有序消费
        """
        self._subscribers[topic].add(callback)
        self._callbacks[topic].add(callback)
        
        if not self._running:
            await self.start()
        
        if topic not in self._worker_tasks:
            self._worker_tasks[topic] = asyncio.create_task(
                self._consumer(topic, ordered)
            )
        
        logger.info(f"Subscribed to topic: {topic}")
    
    async def unsubscribe(self, topic: str, callback: Callable):
        """取消订阅"""
        self._subscribers[topic].discard(callback)
        self._callbacks[topic].discard(callback)
    
    async def _consumer(self, topic: str, ordered: bool):
        """消费者"""
        queue = self._queues[topic]
        
        while self._running:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                for callback in list(self._callbacks[topic]):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(msg)
                        else:
                            callback(msg)
                        
                        msg.status = MessageStatus.COMPLETED
                        self._stats["consumed"] += 1
                        
                    except Exception as e:
                        logger.error(f"Consumer error: {e}")
                        msg.status = MessageStatus.FAILED
                        self._stats["failed"] += 1
                        
                        if msg.retry_count < msg.max_retries:
                            msg.retry_count += 1
                            await queue.put(msg)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue error: {e}")
    
    async def _notify_subscribers(self, topic: str, msg: Message):
        """通知订阅者"""
        for callback in self._subscribers.get(topic, set()):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(msg))
                else:
                    callback(msg)
            except Exception as e:
                logger.error(f"Notify error: {e}")
    
    async def get(self, topic: str, timeout: float = 5.0) -> Optional[Message]:
        """获取消息"""
        try:
            return await asyncio.wait_for(
                self._queues[topic].get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    async def ack(self, msg_id: str):
        """确认消息"""
        # 实际实现需要跟踪消息状态
        logger.debug(f"Acked message: {msg_id}")
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "published": self._stats["published"],
            "consumed": self._stats["consumed"],
            "failed": self._stats["failed"],
            "topics": len(self._topics),
            "subscribers": sum(len(s) for s in self._subscribers.values())
        }
    
    def list_topics(self) -> list:
        """列出所有主题"""
        return list(self._topics)
    
    def get_queue_size(self, topic: str) -> int:
        """获取队列大小"""
        return self._queues[topic].qsize()


# 全局异步队列
_async_queue: Optional[AsyncQueue] = None


def get_async_queue() -> AsyncQueue:
    """获取全局异步队列"""
    global _async_queue
    if _async_queue is None:
        _async_queue = AsyncQueue()
    return _async_queue
