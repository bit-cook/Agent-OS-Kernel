# -*- coding: utf-8 -*-
"""
Event System - 事件系统

支持：
1. 事件发布/订阅
2. 事件类型过滤
3. 异步事件处理
4. 事件优先级
5. 事件历史
"""

import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    # Agent 事件
    AGENT_CREATED = "agent_created"
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    AGENT_COMPLETED = "agent_completed"
    
    # 上下文事件
    CONTEXT_ALLOCATED = "context_allocated"
    CONTEXT_ACCESSED = "context_accessed"
    CONTEXT_EVICTED = "context_evicted"
    
    # 调度事件
    SCHEDULER_TICK = "scheduler_tick"
    SCHEDULER_SWITCH = "scheduler_switch"
    
    # 存储事件
    STORAGE_SAVED = "storage_saved"
    STORAGE_LOADED = "storage_loaded"
    CHECKPOINT_CREATED = "checkpoint_created"
    
    # 系统事件
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    HEARTBEAT = "heartbeat"


@dataclass
class Event:
    """事件"""
    event_id: str
    event_type: EventType
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict = field(default_factory=dict)
    priority: int = 0
    handled: bool = False
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        source: str,
        data: Dict = None,
        priority: int = 0
    ) -> 'Event':
        return cls(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            source=source,
            data=data or {},
            priority=priority
        )


class EventHandler:
    """事件处理器"""
    
    def __init__(self, handler_id: str, callback: Callable, event_types: List[EventType] = None):
        self.handler_id = handler_id
        self.callback = callback
        self.event_types = event_types or []
        self.enabled = True
    
    def matches(self, event: Event) -> bool:
        if not self.enabled:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        return True


class EventBus:
    """
    事件总线
    
    支持：
    - 发布/订阅模式
    - 事件类型过滤
    - 异步处理
    - 优先级排序
    """
    
    def __init__(self, max_history: int = 1000):
        self._handlers: List[EventHandler] = []
        self._history: List[Event] = []
        self._max_history = max_history
        self._running = False
        self._queue: asyncio.Queue = None
    
    async def start(self):
        """启动事件总线"""
        self._running = True
        self._queue = asyncio.Queue()
        asyncio.create_task(self._process_events())
        logger.info("EventBus started")
    
    async def stop(self):
        """停止事件总线"""
        self._running = False
        logger.info("EventBus stopped")
    
    def subscribe(
        self,
        handler_id: str,
        callback: Callable,
        event_types: List[EventType] = None
    ) -> EventHandler:
        """订阅事件"""
        handler = EventHandler(handler_id, callback, event_types)
        self._handlers.append(handler)
        logger.info(f"Handler subscribed: {handler_id}")
        return handler
    
    def unsubscribe(self, handler_id: str):
        """取消订阅"""
        self._handlers = [h for h in self._handlers if h.handler_id != handler_id]
    
    async def publish(self, event: Event):
        """发布事件"""
        self._add_to_history(event)
        await self._queue.put(event)
    
    async def _process_events(self):
        """处理事件"""
        while self._running:
            try:
                event = await self._queue.get()
                
                # 按优先级排序处理
                handlers = sorted(
                    [h for h in self._handlers if h.matches(event)],
                    key=lambda h: h.handler_id
                )
                
                for handler in handlers:
                    try:
                        await handler.callback(event)
                        event.handled = True
                    except Exception as e:
                        logger.error(f"Handler error: {e}")
                
                if not event.handled:
                    logger.warning(f"Unhandled event: {event.event_type}")
                
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    def _add_to_history(self, event: Event):
        """添加到历史"""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_history(
        self,
        event_type: EventType = None,
        source: str = None,
        limit: int = 100
    ) -> List[Event]:
        """获取历史"""
        result = self._history
        
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        if source:
            result = [e for e in result if e.source == source]
        
        return result[-limit:]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "handlers": len(self._handlers),
            "history_size": len(self._history),
            "queue_size": self._queue.qsize() if self._queue else 0,
            "running": self._running
        }


# 便捷函数
def create_event_bus(max_history: int = 1000) -> EventBus:
    """创建事件总线"""
    return EventBus(max_history)
