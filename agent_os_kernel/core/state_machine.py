# -*- coding: utf-8 -*-
"""State Machine - 状态机

支持有限状态机、层次状态机、状态转换。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timezone
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    ENTER = "enter"
    EXIT = "exit"
    TRANSITION = "transition"
    CUSTOM = "custom"


@dataclass
class Transition:
    """状态转换"""
    from_state: str
    to_state: str
    event: str
    guard: Callable = None
    action: Callable = None


@dataclass
class State:
    """状态"""
    name: str
    on_enter: Callable = None
    on_exit: Callable = None
    on_event: Dict[str, Callable] = field(default_factory=dict)
    is_initial: bool = False
    is_final: bool = False


class StateMachine:
    """状态机"""
    
    def __init__(
        self,
        name: str = "default",
        context: Dict = None
    ):
        """
        初始化状态机
        
        Args:
            name: 状态机名称
            context: 上下文数据
        """
        self.name = name
        self.context = context or {}
        
        self._states: Dict[str, State] = {}
        self._transitions: Dict[str, Dict[str, Transition]] = {}  # event -> state -> transition
        self._current_state: Optional[State] = None
        self._history: List[Dict] = []
        self._lock = asyncio.Lock()
        self._running = False
        
        logger.info(f"StateMachine initialized: {name}")
    
    def add_state(
        self,
        name: str,
        on_enter: Callable = None,
        on_exit: Callable = None,
        is_initial: bool = False,
        is_final: bool = False
    ):
        """添加状态"""
        state = State(
            name=name,
            on_enter=on_enter,
            on_exit=on_exit,
            is_initial=is_initial,
            is_final=is_final
        )
        
        self._states[name] = state
        self._transitions[name] = {}
        
        if is_initial:
            self._current_state = state
        
        logger.debug(f"State added: {name}")
    
    def add_transition(
        self,
        from_state: str,
        to_state: str,
        event: str,
        guard: Callable = None,
        action: Callable = None
    ):
        """添加转换"""
        if from_state not in self._states or to_state not in self._states:
            raise ValueError("Invalid state")
        
        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            event=event,
            guard=guard,
            action=action
        )
        
        if event not in self._transitions[from_state]:
            self._transitions[from_state][event] = {}
        
        self._transitions[from_state][event][to_state] = transition
        
        logger.debug(f"Transition added: {from_state} -> {to_state} on {event}")
    
    def on(self, event: str, from_state: str = None):
        """装饰器添加转换"""
        def decorator(func):
            state = from_state or (self._current_state.name if self._current_state else None)
            if state:
                self.add_transition(state, event, func.__name__, action=func)
            return func
        return decorator
    
    async def start(self):
        """启动状态机"""
        self._running = True
        
        if self._current_state and self._current_state.on_enter:
            if asyncio.iscoroutinefunction(self._current_state.on_enter):
                await self._current_state.on_enter()
            else:
                self._current_state.on_enter()
        
        self._log_event(EventType.ENTER, self._current_state.name)
        
        logger.info(f"StateMachine started: {self.name}")
    
    async def stop(self):
        """停止状态机"""
        if self._current_state and self._current_state.on_exit:
            if asyncio.iscoroutinefunction(self._current_state.on_exit):
                await self._current_state.on_exit()
            else:
                self._current_state.on_exit()
        
        self._running = False
        
        logger.info(f"StateMachine stopped: {self.name}")
    
    async def send_event(self, event: str, data: Any = None) -> bool:
        """
        发送事件
        
        Args:
            event: 事件名称
            data: 事件数据
            
        Returns:
            是否成功转换
        """
        if not self._current_state:
            return False
        
        async with self._lock:
            current_name = self._current_state.name
            
            # 检查当前状态的事件处理
            if event in self._current_state.on_event:
                handler = self._current_state.on_event[event]
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
                return True
            
            # 检查转换
            if current_name in self._transitions:
                for to_state, transition in self._transitions[current_name].get(event, {}).items():
                    # 检查 guard
                    if transition.guard:
                        if asyncio.iscoroutinefunction(transition.guard):
                            if not await transition.guard(data):
                                continue
                        else:
                            if not transition.guard(data):
                                continue
                    
                    # 执行转换
                    await self._transition_to(to_state, event, data, transition)
                    return True
            
            logger.debug(f"No transition for event {event} from state {current_name}")
            return False
    
    async def _transition_to(self, to_state: str, event: str, data: Any, transition: Transition):
        """执行转换"""
        old_state = self._current_state
        
        # 记录历史
        self._history.append({
            "from": old_state.name,
            "to": to_state,
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # 退出旧状态
        if old_state.on_exit:
            if asyncio.iscoroutinefunction(old_state.on_exit):
                await old_state.on_exit()
            else:
                old_state.on_exit()
        
        # 执行动作
        if transition.action:
            if asyncio.iscoroutinefunction(transition.action):
                await transition.action(data)
            else:
                transition.action(data)
        
        # 进入新状态
        self._current_state = self._states[to_state]
        
        if self._current_state.on_enter:
            if asyncio.iscoroutinefunction(self._current_state.on_enter):
                await self._current_state.on_enter()
            else:
                self._current_state.on_enter()
        
        # 记录转换
        self._log_event(EventType.TRANSITION, f"{old_state.name} -> {to_state}")
        
        logger.info(f"State transition: {old_state.name} -> {to_state} on {event}")
    
    def _log_event(self, event_type: EventType, state: str):
        """记录事件"""
        logger.debug(f"Event: {event_type.value} -> {state}")
    
    def get_state(self) -> Optional[str]:
        """获取当前状态"""
        return self._current_state.name if self._current_state else None
    
    def is_in_state(self, state_name: str) -> bool:
        """检查是否在指定状态"""
        return self._current_state and self._current_state.name == state_name
    
    def is_final_state(self) -> bool:
        """检查是否在最终状态"""
        return self._current_state and self._current_state.is_final
    
    def get_history(self) -> List[Dict]:
        """获取历史记录"""
        return list(self._history)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "name": self.name,
            "current_state": self.get_state(),
            "states_count": len(self._states),
            "transitions_count": sum(len(t) for t in self._transitions.values()),
            "history_length": len(self._history),
            "is_running": self._running
        }
