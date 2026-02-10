# -*- coding: utf-8 -*-
import logging
"""Enhanced Event Bus - 增强事件总线

完整的事件驱动架构实现。
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
from uuid import uuid4
import time

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    # Agent 事件
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_MESSAGE = "agent.message"
    
    # 任务事件
    TASK_SUBMITTED = "task.submitted"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    
    # 系统事件
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    
    # 自定义事件
    CUSTOM = "custom"


class EventPriority(Enum):
    """事件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """事件"""
    event_id: str
    event_type: EventType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.NORMAL
    source: str = ""
    target: str = ""
    metadata: Dict = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        payload: Dict = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "",
        target: str = ""
    ) -> "Event":
        """创建事件"""
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            payload=payload or {},
            priority=priority,
            source=source,
            target=target
        )


@dataclass
class Subscription:
    """订阅"""
    subscription_id: str
    event_type: EventType
    handler: Callable
    filter: Callable[[Event], bool] = None
    priority: int = 0
    active: bool = True


class EnhancedEventBus:
    """增强事件总线"""
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        enable_metrics: bool = True,
        auto_retry: bool = True
    ):
        """
        初始化事件总线
        
        Args:
            max_queue_size: 最大队列大小
            enable_metrics: 启用指标
            auto_retry: 自动重试
        """
        self.max_queue_size = max_queue_size
        self.enable_metrics = enable_metrics
        self.auto_retry = auto_retry
        
        # 订阅者
        self._subscribers: Dict[EventType, List[Subscription]] = defaultdict(list)
        self._wildcard_subscribers: List[Subscription] = []
        
        # 事件队列
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # 正在处理的事件
        self._processing: Set[str] = set()
        
        # 指标
        self._metrics = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_called": 0,
            "avg_processing_time_ms": 0.0
        }
        self._processing_times: List[float] = []
        
        # 运行状态
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        
        # 统计锁
        self._lock = asyncio.Lock()
        
        logger.info("EnhancedEventBus initialized")
    
    async def start(self):
        """启动事件总线"""
        if not self._running:
            self._running = True
            self._consumer_task = asyncio.create_task(self._consumer_loop())
            logger.info("EnhancedEventBus started")
    
    async def stop(self):
        """停止事件总线"""
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
        logger.info("EnhancedEventBus stopped")
    
    # ==================== 发布事件 ====================
    
    async def publish(self, event: Event) -> bool:
        """
        发布事件
        
        Args:
            event: 事件
            
        Returns:
            是否成功入队
        """
        if not self._running:
            await self.start()
        
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
    
    def publish_sync(self, event: Event):
        """同步发布事件"""
        # 直接处理，不入队
        asyncio.create_task(self._process_event(event))
    
    async def publish_event(
        self,
        event_type: EventType,
        payload: Dict = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "",
        target: str = ""
    ) -> bool:
        """
        便捷发布方法
        
        Returns:
            是否成功
        """
        event = Event.create(
            event_type=event_type,
            payload=payload,
            priority=priority,
            source=source,
            target=target
        )
        return await self.publish(event)
    
    # ==================== 订阅事件 ====================
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any],
        filter: Callable[[Event], bool] = None,
        priority: int = 0
    ) -> str:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数
            filter: 过滤器
            priority: 优先级（大的先调用）
            
        Returns:
            订阅 ID
        """
        subscription = Subscription(
            subscription_id=str(uuid4()),
            event_type=event_type,
            handler=handler,
            filter=filter,
            priority=priority
        )
        
        self._subscribers[event_type].append(subscription)
        self._subscribers[event_type].sort(key=lambda x: x.priority, reverse=True)
        
        logger.debug(f"Subscribed to {event_type.value}")
        
        return subscription.subscription_id
    
    def subscribe_all(self, handler: Callable[[Event], Any]) -> str:
        """
        订阅所有事件
        
        Returns:
            订阅 ID
        """
        subscription = Subscription(
            subscription_id=str(uuid4()),
            event_type=EventType.CUSTOM,
            handler=handler
        )
        
        self._wildcard_subscribers.append(subscription)
        
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅 ID
            
        Returns:
            是否成功
        """
        # 从类型订阅中移除
        for event_type, subs in self._subscribers.items():
            for sub in subs:
                if sub.subscription_id == subscription_id:
                    subs.remove(sub)
                    return True
        
        # 从通配符订阅中移除
        for sub in self._wildcard_subscribers:
            if sub.subscription_id == subscription_id:
                self._wildcard_subscribers.remove(sub)
                return True
        
        return False
    
    def unsubscribe_all(self, event_type: EventType = None):
        """取消所有订阅"""
        if event_type:
            self._subscribers[event_type].clear()
        else:
            self._subscribers.clear()
            self._wildcard_subscribers.clear()
    
    # ==================== 事件处理 ====================
    
    async def _consumer_loop(self):
        """消费者循环"""
        while self._running:
            try:
                event = await self._event_queue.get()
                
                if event.event_id not in self._processing:
                    asyncio.create_task(self._process_event(event))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
    
    async def _process_event(self, event: Event):
        """处理事件"""
        start_time = time.time()
        
        self._processing.add(event.event_id)
        
        try:
            # 获取订阅者
            subscribers = self._subscribers.get(event.event_type, []).copy()
            
            # 添加通配符订阅者
            subscribers.extend(self._wildcard_subscribers)
            
            # 按优先级排序
            subscribers.sort(key=lambda x: x.priority, reverse=True)
            
            # 调用处理函数
            for sub in subscribers:
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
                    
                    async with self._lock:
                        self._metrics["handlers_called"] += 1
                        
                except Exception as e:
                    logger.error(f"Handler error: {e}")
                    
                    if self.auto_retry:
                        await asyncio.sleep(0.1)
                        try:
                            if asyncio.iscoroutinefunction(sub.handler):
                                await sub.handler(event)
                            else:
                                sub.handler(event)
                        except:
                            pass
            
            async with self._lock:
                self._metrics["events_processed"] += 1
            
        except Exception as e:
            logger.error(f"Process event error: {e}")
            async with self._lock:
                self._metrics["events_failed"] += 1
        
        finally:
            self._processing.discard(event.event_id)
            
            # 记录处理时间
            elapsed = (time.time() - start_time) * 1000
            self._processing_times.append(elapsed)
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]
    
    # ==================== 工具方法 ====================
    
    def get_subscribers(self, event_type: EventType = None) -> List[Subscription]:
        """获取订阅者"""
        if event_type:
            return self._subscribers.get(event_type, []).copy()
        return list(self._wildcard_subscribers)
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self._event_queue.qsize()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        avg_time = (
            sum(self._processing_times) / len(self._processing_times)
            if self._processing_times else 0.0
        )
        
        return {
            "events_published": self._metrics["events_published"],
            "events_processed": self._metrics["events_processed"],
            "events_failed": self._metrics["events_failed"],
            "handlers_called": self._metrics["handlers_called"],
            "avg_processing_time_ms": avg_time,
            "queue_size": self.get_queue_size(),
            "subscribers_count": sum(len(s) for s in self._subscribers.values()),
            "wildcard_subscribers_count": len(self._wildcard_subscribers)
        }
    
    def reset_metrics(self):
        """重置指标"""
        self._metrics = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_called": 0,
            "avg_processing_time_ms": 0.0
        }
        self._processing_times.clear()


# 全局事件总线
_event_bus: Optional[EnhancedEventBus] = None


def get_event_bus() -> EnhancedEventBus:
    """获取全局事件总线"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EnhancedEventBus()
    return _event_bus
