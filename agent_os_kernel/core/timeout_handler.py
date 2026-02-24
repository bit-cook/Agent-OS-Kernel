# -*- coding: utf-8 -*-
"""
超时处理器模块 - Timeout Handler

提供超时管理、超时回调、超时取消和超时事件处理等功能。

功能:
- 超时管理 (Timeout Management)
- 超时回调 (Timeout Callbacks)
- 超时取消 (Timeout Cancellation)
- 超时事件处理 (Timeout Event Handling)
"""

import asyncio
import functools
import time
import threading
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class TimeoutState(Enum):
    """超时状态枚举"""
    PENDING = "pending"      # 等待超时
    TRIGGERED = "triggered" # 已触发
    CANCELLED = "cancelled" # 已取消
    COMPLETED = "completed" # 已完成（正常完成）


class TimeoutError(Exception):
    """超时异常"""
    
    def __init__(self, message: str, timeout_duration: float, handler_name: Optional[str] = None):
        super().__init__(message)
        self.timeout_duration = timeout_duration
        self.handler_name = handler_name


class TimeoutEventHandler(ABC):
    """超时事件处理器基类"""
    
    @abstractmethod
    def on_timeout(self, timeout_handler: 'TimeoutHandler') -> None:
        """超时触发时的处理"""
        pass
    
    @abstractmethod
    def on_cancel(self, timeout_handler: 'TimeoutHandler') -> None:
        """取消时的处理"""
        pass


class DefaultTimeoutEventHandler(TimeoutEventHandler):
    """默认超时事件处理器"""
    
    def on_timeout(self, timeout_handler: 'TimeoutHandler') -> None:
        """默认超时处理：抛出TimeoutError"""
        raise TimeoutError(
            f"Timeout exceeded for handler '{timeout_handler.name}'",
            timeout_handler.timeout_duration,
            timeout_handler.name
        )
    
    def on_cancel(self, timeout_handler: 'TimeoutHandler') -> None:
        """默认取消处理：记录日志"""
        pass


@dataclass
class TimeoutConfig:
    """超时配置"""
    timeout_duration: float = 30.0      # 超时时间（秒）
    callback: Optional[Callable] = None  # 超时回调函数
    cancel_callback: Optional[Callable] = None  # 取消回调函数
    exception_on_timeout: bool = True   # 超时时是否抛出异常
    repeat: bool = False               # 是否重复超时
    repeat_interval: Optional[float] = None  # 重复间隔


class TimeoutHandler:
    """
    超时处理器类
    
    用于管理单个超时任务，支持同步和异步操作。
    
    Attributes:
        name: 处理器名称
        timeout_duration: 超时时间（秒）
        state: 当前状态
        remaining_time: 剩余时间
        callback: 超时回调函数
        cancel_callback: 取消回调函数
        event_handler: 超时事件处理器
    """
    
    def __init__(
        self,
        name: str = "default",
        config: Optional[TimeoutConfig] = None,
        event_handler: Optional[TimeoutEventHandler] = None,
    ):
        """
        初始化超时处理器
        
        Args:
            name: 处理器名称
            config: 超时配置
            event_handler: 超时事件处理器
        """
        self.name = name
        self.config = config or TimeoutConfig()
        self.event_handler = event_handler or DefaultTimeoutEventHandler()
        
        self._state = TimeoutState.PENDING
        self._remaining_time = self.config.timeout_duration
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._callback = self.config.callback
        self._cancel_callback = self.config.cancel_callback
        self._lock = threading.Lock()
        self._repeat_count = 0
        self._async_task: Optional[asyncio.Task] = None
    
    @property
    def state(self) -> TimeoutState:
        """获取当前状态"""
        return self._state
    
    @property
    def timeout_duration(self) -> float:
        """获取超时时间"""
        return self.config.timeout_duration
    
    @property
    def remaining_time(self) -> float:
        """获取剩余时间"""
        if self._state == TimeoutState.PENDING and self._start_time is not None:
            elapsed = time.time() - self._start_time
            return max(0, self.config.timeout_duration - elapsed)
        return self._remaining_time
    
    @property
    def is_active(self) -> bool:
        """是否处于活动状态"""
        return self._state == TimeoutState.PENDING
    
    def start(self) -> 'TimeoutHandler':
        """
        启动超时计时器
        
        Returns:
            self
        """
        with self._lock:
            if self._state != TimeoutState.PENDING:
                raise RuntimeError(f"Cannot start timeout handler in state: {self._state}")
            
            self._state = TimeoutState.PENDING
            self._start_time = time.time()
            self._end_time = self._start_time + self.config.timeout_duration
        
        return self
    
    def cancel(self) -> 'TimeoutHandler':
        """
        取消超时
        
        Returns:
            self
        """
        with self._lock:
            if self._state == TimeoutState.PENDING:
                self._state = TimeoutState.CANCELLED
                self._remaining_time = self.remaining_time
                
                if self._cancel_callback:
                    self._cancel_callback(self)
                
                if self.event_handler:
                    try:
                        self.event_handler.on_cancel(self)
                    except Exception:
                        pass
        
        return self
    
    def _trigger(self):
        """内部触发超时处理"""
        with self._lock:
            if self._state != TimeoutState.PENDING:
                return
            
            self._state = TimeoutState.TRIGGERED
            self._repeat_count += 1
            
            if self._callback:
                try:
                    self._callback(self)
                except Exception:
                    pass
            
            if self.event_handler:
                try:
                    self.event_handler.on_timeout(self)
                except Exception:
                    pass
            
            # 处理重复超时
            if self.config.repeat:
                self._start_time = time.time()
                self._end_time = self._start_time + (
                    self.config.repeat_interval or self.config.timeout_duration
                )
                self._state = TimeoutState.PENDING
    
    def check_timeout(self) -> bool:
        """
        检查是否超时
        
        Returns:
            是否已超时
        """
        with self._lock:
            if self._state != TimeoutState.PENDING:
                return False
            
            current_time = time.time()
            if current_time >= self._end_time:
                self._trigger()
                return True
            
            return False
    
    def execute_with_timeout(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        同步执行带超时的函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            TimeoutError: 超时
        """
        self.start()
        
        def run_with_monitor():
            result = None
            exception = None
            
            def target():
                nonlocal result, exception
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            
            # 等待线程完成或超时
            thread.join(timeout=self.remaining_time)
            
            if thread.is_alive():
                # 线程仍在运行，超时
                self._trigger()
                if self.config.exception_on_timeout:
                    raise TimeoutError(
                        f"Function execution timeout",
                        self.timeout_duration,
                        self.name
                    )
                return None
            
            if exception:
                raise exception
            
            return result
        
        return run_with_monitor()
    
    async def execute_async_with_timeout(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        异步执行带超时的函数
        
        Args:
            func: 异步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            TimeoutError: 超时
        """
        self.start()
        
        loop = asyncio.get_event_loop()
        
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.remaining_time
            )
            return result
        except asyncio.TimeoutError:
            self._trigger()
            if self.config.exception_on_timeout:
                raise TimeoutError(
                    f"Async function execution timeout",
                    self.timeout_duration,
                    self.name
                )
            return None
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取处理器信息
        
        Returns:
            包含状态信息的字典
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "timeout_duration": self.timeout_duration,
            "remaining_time": self.remaining_time,
            "is_active": self.is_active,
            "repeat": self.config.repeat,
            "repeat_interval": self.config.repeat_interval,
            "callback": self._callback.__name__ if self._callback else None,
        }
    
    def reset(self) -> 'TimeoutHandler':
        """
        重置处理器到初始状态
        
        Returns:
            self
        """
        with self._lock:
            self._state = TimeoutState.PENDING
            self._start_time = None
            self._end_time = None
            self._remaining_time = self.config.timeout_duration
            self._repeat_count = 0
        
        return self


class TimeoutManager:
    """
    超时管理器
    
    用于管理多个超时处理器。
    """
    
    def __init__(self):
        self._handlers: Dict[str, TimeoutHandler] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
    
    def create(
        self,
        name: str,
        config: Optional[TimeoutConfig] = None,
        event_handler: Optional[TimeoutEventHandler] = None,
    ) -> TimeoutHandler:
        """
        创建超时处理器
        
        Args:
            name: 处理器名称
            config: 超时配置
            event_handler: 事件处理器
            
        Returns:
            TimeoutHandler实例
        """
        with self._lock:
            if name in self._handlers:
                raise ValueError(f"Timeout handler '{name}' already exists")
            
            handler = TimeoutHandler(name=name, config=config, event_handler=event_handler)
            self._handlers[name] = handler
            return handler
    
    def get(self, name: str) -> Optional[TimeoutHandler]:
        """
        获取超时处理器
        
        Args:
            name: 处理器名称
            
        Returns:
            TimeoutHandler实例或None
        """
        return self._handlers.get(name)
    
    def remove(self, name: str) -> bool:
        """
        移除超时处理器
        
        Args:
            name: 处理器名称
            
        Returns:
            是否成功移除
        """
        with self._lock:
            if name in self._handlers:
                handler = self._handlers[name]
                if handler.is_active:
                    handler.cancel()
                del self._handlers[name]
                return True
            return False
    
    def cancel_all(self):
        """取消所有活动超时"""
        with self._lock:
            for handler in self._handlers.values():
                if handler.is_active:
                    handler.cancel()
    
    def start_monitoring(self, interval: float = 0.1):
        """
        启动监控线程
        
        Args:
            interval: 检查间隔（秒）
        """
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(interval,),
                daemon=True
            )
            self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控线程"""
        with self._lock:
            self._running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while True:
            with self._lock:
                if not self._running:
                    break
            
            for handler in list(self._handlers.values()):
                handler.check_timeout()
            
            time.sleep(interval)
    
    def get_all_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有处理器信息
        
        Returns:
            包含所有处理器信息的字典
        """
        with self._lock:
            return {
                name: handler.get_info()
                for name, handler in self._handlers.items()
            }


# 全局超时管理器实例
timeout_manager = TimeoutManager()


def timeout(
    duration: float,
    name: Optional[str] = None,
    callback: Optional[Callable] = None,
    exception_on_timeout: bool = True,
):
    """
    超时装饰器
    
    Args:
        duration: 超时时间（秒）
        name: 处理器名称
        callback: 超时回调函数
        exception_on_timeout: 超时时是否抛出异常
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        handler_name = name or func.__name__
        
        config = TimeoutConfig(
            timeout_duration=duration,
            callback=callback,
            exception_on_timeout=exception_on_timeout,
        )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            handler = TimeoutHandler(name=handler_name, config=config)
            if asyncio.iscoroutinefunction(func):
                return _async_wrapper(handler, func, *args, **kwargs)
            return _sync_wrapper(handler, func, *args, **kwargs)
        
        async def _async_wrapper(handler: TimeoutHandler, f: Callable, *a, **kw):
            return await handler.execute_async_with_timeout(f, *a, **kw)
        
        def _sync_wrapper(handler: TimeoutHandler, f: Callable, *a, **kw):
            return handler.execute_with_timeout(f, *a, **kw)
        
        return sync_wrapper
    
    return decorator


def create_timeout_handler(
    name: str,
    duration: float,
    callback: Optional[Callable] = None,
    event_handler: Optional[TimeoutEventHandler] = None,
) -> TimeoutHandler:
    """
    创建超时处理器的便捷函数
    
    Args:
        name: 处理器名称
        duration: 超时时间（秒）
        callback: 超时回调函数
        event_handler: 事件处理器
        
    Returns:
        TimeoutHandler实例
    """
    config = TimeoutConfig(
        timeout_duration=duration,
        callback=callback,
    )
    return TimeoutHandler(name=name, config=config, event_handler=event_handler)
