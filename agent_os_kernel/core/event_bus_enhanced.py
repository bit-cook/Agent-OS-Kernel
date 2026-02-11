# -*- coding: utf-8 -*-
"""Enhanced Event Bus - 增强型事件总线

完整的发布/订阅事件系统，支持优先级、通配符、持久化。
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class EventType(Enum):
    """事件类型"""
    # 任务事件
    TASK_CREATED = "task:created"
    TASK_STARTED = "task:started"
    TASK_COMPLETED = "task:completed"
    TASK_FAILED = "task:failed"
    TASK_CANCELLED = "task:cancelled"
    
    # Agent 事件
    AGENT_CREATED = "agent:created"
    AGENT_STARTED = "agent:started"
    AGENT_STOPPED = "agent:stopped"
    AGENT_ERROR = "agent:error"
    
    # 系统事件
    SYSTEM_START = "system:start"
    SYSTEM_STOP = "system:stop"
    SYSTEM_ERROR = "system:error"
    HEALTH_CHECK = "health:check"
    
    # 工具事件
    TOOL_CALL = "tool:call"
    TOOL_RESULT = "tool:result"
    TOOL_ERROR = "tool:error"
    
    # 内存事件
    MEMORY_STORED = "memory:stored"
    MEMORY_RETRIEVED = "memory:retrieved"
    MEMORY_ERROR = "memory:error"


@dataclass
class Event:
    """事件"""
    event_id: str
    event_type: EventType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    correlation_id: Optional[str] = None
    
    @classmethod
    def create(cls, event_type: EventType, payload: Dict = None, **kwargs) -> "Event":
        """创建事件"""
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            payload=payload or {},
            **kwargs
        )


@dataclass
class Subscription:
    """订阅"""
    subscription_id: str
    event_type: EventType
    handler: Callable
    priority: EventPriority = EventPriority.NORMAL
    filter: Optional[Callable[[Event], bool]] = None
    active: bool = True


class EnhancedEventBus:
    """增强型事件总线"""
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        auto_retry: bool = False,
        max_retries: int = 3
    ):
        """
        初始化事件总线
        
        Args:
            max_queue_size: 最大队列大小
            auto_retry: 自动重试
            max_retries: 最大重试次数
        """
        self.max_queue_size = max_queue_size
        self.auto_retry = auto_retry
        self.max_retries = max_retries
        
        self._subscriptions: Dict[EventType, List[Subscription]] = {}
        self._wildcard_subscriptions: List[Subscription] = []
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # 指标
        self._metrics = {
            "events_published": 0,
            "events_processed": 0,
            "handlers_called": 0,
            "errors": 0
        }
        
        logger.info("EnhancedEventBus initialized")
    
    async def initialize(self):
        """初始化"""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_events())
            logger.info("EnhancedEventBus started")
    
    async def shutdown(self):
        """关闭"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("EnhancedEventBus shutdown")
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        filter: Optional[Callable[[Event], bool]] = None
    ) -> str:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数
            priority: 优先级
            filter: 过滤器
            
        Returns:
            订阅 ID
        """
        subscription = Subscription(
            subscription_id=str(uuid4()),
            event_type=event_type,
            handler=handler,
            priority=priority,
            filter=filter
        )
        
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []
        
        self._subscriptions[event_type].append(subscription)
        self._subscriptions[event_type].sort(
            key=lambda s: s.priority.value,
            reverse=True
        )
        
        logger.debug(f"Subscribed to {event_type.value}")
        
        return subscription.subscription_id
    
    def subscribe_wildcard(self, handler: Callable) -> str:
        """订阅所有事件"""
        subscription = Subscription(
            subscription_id=str(uuid4()),
            event_type=None,
            handler=handler
        )
        self._wildcard_subscriptions.append(subscription)
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        # 检查类型订阅
        for event_type, subs in self._subscriptions.items():
            for sub in subs:
                if sub.subscription_id == subscription_id:
                    subs.remove(sub)
                    return True
        
        # 检查通配符订阅
        for sub in self._wildcard_subscriptions:
            if sub.subscription_id == subscription_id:
                self._wildcard_subscriptions.remove(sub)
                return True
        
        return False
    
    async def publish(self, event: Event) -> bool:
        """发布事件"""
        if not self._running:
            await self.initialize()
        
        try:
            await asyncio.wait_for(
                self._event_queue.put(event),
                timeout=1.0
            )
            
            async with self._lock:
                self._metrics["events_published"] += 1
            
            return True
            
        except asyncio.TimeoutError:
            logger.warning("Event queue full, event dropped")
            return False
    
    async def publish_event(
        self,
        event_type: EventType,
        payload: Dict = None,
        priority: EventPriority = EventPriority.NORMAL,
        **kwargs
    ) -> bool:
        """便捷发布方法"""
        event = Event.create(event_type, payload, priority=priority, **kwargs)
        return await self.publish(event)
    
    async def _process_events(self):
        """处理事件"""
        while self._running:
            try:
                event = await self._event_queue.get()
                asyncio.create_task(self._dispatch_event(event))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    async def _dispatch_event(self, event: Event):
        """分发事件"""
        handlers_called = 0
        
        try:
            # 获取订阅者
            subs = self._subscriptions.get(event.event_type, []).copy()
            
            # 添加通配符订阅者
            subs.extend(self._wildcard_subscriptions)
            
            # 调用处理函数
            for sub in subs:
                if not sub.active:
                    continue
                
                # 检查过滤器
                if sub.filter and not sub.filter(event):
                    continue
                
                try:
                    if asyncio.iscoroutinefunction(sub.handler):
                        await sub.handler(event)
                    else:
                        sub.handler(event)
                    
                    handlers_called += 1
                    
                except Exception as e:
                    logger.error(f"Handler error: {e}")
                    
                    if self.auto_retry:
                        for retry_count in range(self.max_retries):
                            await asyncio.sleep(0.1 * (retry_count + 1))
                            try:
                                if asyncio.iscoroutinefunction(sub.handler):
                                    await sub.handler(event)
                                else:
                                    sub.handler(event)
                                handlers_called += 1
                                break
                            except Exception as retry_error:
                                logger.warning(f"Retry {retry_count + 1} failed: {retry_error}")
            
            async with self._lock:
                self._metrics["events_processed"] += 1
                self._metrics["handlers_called"] += handlers_called
        
        except Exception as e:
            logger.error(f"Dispatch event error: {e}")
            async with self._lock:
                self._metrics["errors"] += 1
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "events_published": self._metrics["events_published"],
            "events_processed": self._metrics["events_processed"],
            "handlers_called": self._metrics["handlers_called"],
            "errors": self._metrics["errors"],
            "subscribers_count": sum(len(s) for s in self._subscriptions.values()),
            "wildcard_subscribers": len(self._wildcard_subscriptions),
            "queue_size": self._event_queue.qsize()
        }
    
    def get_subscribers(self, event_type: EventType = None) -> List[Subscription]:
        """获取订阅者"""
        if event_type:
            return self._subscriptions.get(event_type, []).copy()
        return list(self._wildcard_subscriptions)


# 全局事件总线实例
_event_bus: Optional[EnhancedEventBus] = None


def get_event_bus() -> EnhancedEventBus:
    """获取全局事件总线实例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EnhancedEventBus()
    return _event_bus


def set_event_bus(bus: EnhancedEventBus):
    """设置全局事件总线实例"""
    global _event_bus
    _event_bus = bus
