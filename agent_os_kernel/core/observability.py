# -*- coding: utf-8 -*-
"""Observability - 可观测性

参考 AgentOps 设计，提供完整的可观测性功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta, timezone
from uuid import uuid4
import logging
from threading import Lock
import time
import json

logger = logging.getLogger(__name__)


class EventType:
    """事件类型"""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TASK_START = "task_start"
    TASK_END = "task_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    CHECKPOINT = "checkpoint"
    USER_ACTION = "user_action"


@dataclass
class Event:
    """事件"""
    
    id: str
    type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # 数据
    data: Dict[str, Any] = field(default_factory=dict)
    
    # 持续时间 (可选)
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "data": self.data,
            "duration_ms": self.duration_ms,
        }


@dataclass
class Session:
    """监控会话"""
    
    id: str
    name: str
    
    # 配置
    config: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # 状态
    status: str = "running"  # running, completed, failed
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    
    # 统计
    events_count: int = 0
    agents_count: int = 0
    tasks_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "config": self.config,
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "events_count": self.events_count,
            "agents_count": self.agents_count,
            "tasks_count": self.tasks_count,
        }


class CallbackHandler:
    """回调处理器基类"""
    
    @abstractmethod
    def on_event(self, event: Event):
        """处理事件"""
        pass
    
    def on_session_start(self, session: Session):
        """会话开始"""
        pass
    
    def on_session_end(self, session: Session):
        """会话结束"""
        pass


class FileCallbackHandler(CallbackHandler):
    """文件回调处理器"""
    
    def __init__(self, filepath: str = "./events.jsonl"):
        self.filepath = filepath
        self._lock = Lock()
        
        logger.info(f"FileCallbackHandler initialized: {filepath}")
    
    def on_event(self, event: Event):
        with self._lock:
            with open(self.filepath, 'a') as f:
                f.write(json.dumps(event.to_dict()) + '\n')
    
    def on_session_start(self, session: Session):
        pass
    
    def on_session_end(self, session: Session):
        pass


class PrintCallbackHandler(CallbackHandler):
    """打印回调处理器 (调试用)"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._lock = Lock()
    
    def on_event(self, event: Event):
        with self._lock:
            if event.duration_ms:
                logger.info(
                    f"[{event.type}] {event.agent_id or 'system'} - "
                    f"{event.duration_ms:.2f}ms"
                )
            else:
                logger.info(f"[{event.type}] {event.agent_id or 'system'}")
            
            if self.verbose and event.data:
                logger.debug(f"  Data: {event.data}")


class Observability:
    """可观测性管理器
    
    功能:
    - 事件追踪
    - Session 管理
    - 回调处理
    - 时间线生成
    """
    
    def __init__(self, session_name: Optional[str] = None):
        """初始化可观测性系统"""
        self._session: Optional[Session] = None
        self._events: List[Event] = []
        self._callbacks: List[CallbackHandler] = []
        self._current_span: Optional[Event] = None
        self._lock = Lock()
        
        # 默认回调
        self.add_callback(PrintCallbackHandler())
        
        # 如果提供了 session_name，自动启动
        if session_name:
            self.start_session(session_name)
        
        logger.info("Observability initialized")
    
    def start_session(
        self,
        name: str,
        config: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Session:
        """启动会话"""
        with self._lock:
            self._session = Session(
                id=str(uuid4())[:8],
                name=name,
                config=config or {},
                tags=tags or [],
                status="running",
            )
            
            for callback in self._callbacks:
                callback.on_session_start(self._session)
            
            logger.info(f"Session started: {name} ({self._session.id})")
            return self._session
    
    def end_session(
        self, 
        status: str = "completed",
        reason: Optional[str] = None
    ) -> Session:
        """结束会话"""
        with self._lock:
            if self._session:
                self._session.status = status
                self._session.ended_at = datetime.now(timezone.utc)
                
                for callback in self._callbacks:
                    callback.on_session_end(self._session)
                
                logger.info(
                    f"Session ended: {self._session.name} "
                    f"(status={status}, events={self._session.events_count})"
                )
            
            return self._session
    
    def add_callback(self, handler: CallbackHandler):
        """添加回调处理器"""
        self._callbacks.append(handler)
        logger.debug(f"Callback added: {type(handler).__name__}")
    
    def record_event(
        self,
        type: str,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        data: Optional[Dict] = None,
        duration_ms: Optional[float] = None
    ) -> Event:
        """记录事件"""
        with self._lock:
            event = Event(
                id=str(uuid4())[:8],
                type=type,
                timestamp=datetime.now(timezone.utc),
                agent_id=agent_id,
                task_id=task_id,
                data=data or {},
                duration_ms=duration_ms,
            )
            
            self._events.append(event)
            
            if self._session:
                self._session.events_count += 1
            
            # 触发回调
            for callback in self._callbacks:
                try:
                    callback.on_event(event)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            return event
    
    def trace_agent(
        self,
        agent_id: str,
        task: str,
        func: Callable,
        *args,
        **kwargs
    ):
        """追踪 Agent 执行"""
        start_time = time.time()
        
        self.record_event(
            EventType.AGENT_START,
            agent_id=agent_id,
            data={"task": task}
        )
        
        try:
            result = func(*args, **kwargs)
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.record_event(
                EventType.AGENT_END,
                agent_id=agent_id,
                duration_ms=duration_ms,
                data={"status": "success"}
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            self.record_event(
                EventType.ERROR,
                agent_id=agent_id,
                duration_ms=duration_ms,
                data={
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            
            raise
    
    def trace_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ):
        """追踪 Task 执行"""
        start_time = time.time()
        
        self.record_event(
            EventType.TASK_START,
            task_id=task_id
        )
        
        try:
            result = func(*args, **kwargs)
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.record_event(
                EventType.TASK_END,
                task_id=task_id,
                duration_ms=duration_ms,
                data={"status": "success"}
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            self.record_event(
                EventType.ERROR,
                task_id=task_id,
                duration_ms=duration_ms,
                data={
                    "status": "error",
                    "error": str(e)
                }
            )
            
            raise
    
    def record_llm_call(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        """记录 LLM 调用"""
        self.record_event(
            EventType.LLM_REQUEST,
            agent_id=agent_id,
            task_id=task_id,
            data={
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
            }
        )
        
        self.record_event(
            EventType.LLM_RESPONSE,
            agent_id=agent_id,
            task_id=task_id,
            duration_ms=duration_ms,
            data={
                "provider": provider,
                "model": model,
                "output_tokens": output_tokens,
            }
        )
    
    def record_tool_call(
        self,
        tool_name: str,
        params: Dict,
        result: Any,
        agent_id: Optional[str] = None
    ):
        """记录工具调用"""
        self.record_event(
            EventType.TOOL_CALL,
            agent_id=agent_id,
            data={"tool": tool_name, "params": params}
        )
        
        self.record_event(
            EventType.TOOL_RESULT,
            agent_id=agent_id,
            data={"tool": tool_name, "result": str(result)[:1000]}
        )
    
    def get_timeline(self) -> List[Dict]:
        """获取时间线"""
        timeline = []
        
        for event in self._events:
            timeline.append({
                "id": event.id,
                "type": event.type,
                "timestamp": event.timestamp.isoformat(),
                "agent_id": event.agent_id,
                "task_id": event.task_id,
                "duration_ms": event.duration_ms,
            })
        
        return timeline
    
    def get_stats(self) -> Dict:
        """获取统计"""
        event_counts: Dict[str, int] = {}
        
        for event in self._events:
            event_counts[event.type] = event_counts.get(event.type, 0) + 1
        
        return {
            "session": self._session.to_dict() if self._session else None,
            "total_events": len(self._events),
            "event_counts": event_counts,
        }
    
    def export_events(self, filepath: str):
        """导出事件为 JSON"""
        with open(filepath, 'w') as f:
            json.dump(
                [e.to_dict() for e in self._events],
                f,
                indent=2
            )
        
        logger.info(f"Events exported to {filepath}")
    
    def clear(self):
        """清除所有事件"""
        with self._lock:
            self._events.clear()
            
            if self._session:
                self._session.events_count = 0
            
            logger.info("Observability cleared")


# 便捷函数
def observe_agent(agent_id: str, task: str):
    """装饰器：追踪 Agent"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            from .observability import get_observability
            obs = get_observability()
            return obs.trace_agent(agent_id, task, func, *args, **kwargs)
        return wrapper
    return decorator


# 全局可观测性实例
_observability: Optional[Observability] = None


def get_observability() -> Observability:
    """获取全局可观测性实例"""
    global _observability
    if _observability is None:
        _observability = Observability()
    return _observability


def init_observability(session_name: str) -> Observability:
    """初始化可观测性"""
    global _observability
    _observability = Observability(session_name)
    return _observability
