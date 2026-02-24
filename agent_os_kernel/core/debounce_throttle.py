"""
Debounce & Throttle 模块 - Agent OS Kernel

提供防抖（debounce）和节流（throttle）功能:
- debounce - 防抖函数
- throttle - 节流函数
- AsyncDebounce - 异步防抖
- AsyncThrottle - 异步节流
"""

import asyncio
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime

from .mixins import ThreadSafeMixin


@dataclass
class DebounceConfig:
    """防抖配置"""
    wait: float = 300  # 等待时间（毫秒）
    leading: bool = True  # 是否在延迟开始前执行
    trailing: bool = True  # 是否在延迟结束后执行
    max_wait: Optional[float] = None  # 最大等待时间


@dataclass
class ThrottleConfig:
    """节流配置"""
    interval: float = 300  # 执行间隔（毫秒）
    leading: bool = True  # 是否在开始时执行
    trailing: bool = True  # 是否在结束时执行


class DebounceManager(ThreadSafeMixin):
    """防抖管理器"""
    
    def __init__(self, config: Optional[DebounceConfig] = None):
        self.config = config or DebounceConfig()
        self._timers: Dict[str, Any] = {}
        self._last_call_time: Dict[str, float] = {}
        self._call_count: Dict[str, int] = {}
    
    def debounce(self, key: str, func: Callable, 
                 wait: Optional[float] = None,
                 leading: Optional[bool] = None,
                 trailing: Optional[bool] = None,
                 max_wait: Optional[float] = None) -> Callable:
        """创建防抖函数"""
        wait = wait or self.config.wait
        leading = leading if leading is not None else self.config.leading
        trailing = trailing if trailing is not None else self.config.trailing
        max_wait = max_wait or self.config.max_wait
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                current_time = time.time()
                last_time = self._last_call_time.get(key, 0)
                self._call_count[key] = self._call_count.get(key, 0) + 1
                
                # 清除之前的定时器
                if key in self._timers:
                    self._timers[key].cancel()
                
                # 计算剩余时间
                remaining = (wait / 1000) - (current_time - last_time)
                
                if leading and not self._timers:
                    # 立即执行
                    result = func(*args, **kwargs)
                    self._last_call_time[key] = current_time
                    return result
                
                if max_wait and remaining <= 0:
                    # 超过最大等待时间，立即执行
                    result = func(*args, **kwargs)
                    self._last_call_time[key] = current_time
                    self._timers.pop(key, None)
                    return result
                
                # 设置定时器
                def timer_callback():
                    with self.lock:
                        if trailing:
                            # 执行最后一次调用
                            func(*args, **kwargs)
                        self._last_call_time[key] = time.time()
                        self._timers.pop(key, None)
                
                timer = threading.Timer(remaining / 1000 if remaining > 0 else wait / 1000, timer_callback)
                self._timers[key] = timer
                timer.start()
                
                return None
        
        return wrapper
    
    def cancel(self, key: str) -> None:
        """取消防抖"""
        with self.lock:
            if key in self._timers:
                self._timers[key].cancel()
                del self._timers[key]
    
    def flush(self, key: str) -> None:
        """立即执行并清除定时器"""
        with self.lock:
            if key in self._timers:
                self._timers[key].cancel()
                del self._timers[key]
    
    def get_stats(self, key: str) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            return {
                'call_count': self._call_count.get(key, 0),
                'last_call_time': self._last_call_time.get(key),
                'has_pending': key in self._timers,
            }


class ThrottleManager(ThreadSafeMixin):
    """节流管理器"""
    
    def __init__(self, config: Optional[ThrottleConfig] = None):
        self.config = config or ThrottleConfig()
        self._last_exec_time: Dict[str, float] = {}
        self._call_count: Dict[str, int] = {}
        self._exec_history: Dict[str, list] = {}
    
    def throttle(self, key: str, func: Callable,
                 interval: Optional[float] = None,
                 leading: Optional[bool] = None,
                 trailing: Optional[bool] = None) -> Callable:
        """创建节流函数"""
        interval = interval or self.config.interval
        leading = leading if leading is not None else self.config.leading
        trailing = trailing if trailing is not None else self.config.trailing
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            last_time = self._last_exec_time.get(key, 0)
            elapsed = (current_time - last_time) * 1000  # 转换为毫秒
            
            with self.lock:
                if elapsed >= interval:
                    # 可以执行
                    if leading:
                        result = func(*args, **kwargs)
                        self._last_exec_time[key] = current_time
                        self._record_execution(key, current_time)
                        return result
                
                if trailing:
                    # 标记为待执行
                    if not hasattr(wrapper, '_pending'):
                        wrapper._pending = {}
                    wrapper._pending[key] = (args, kwargs)
            
            return None
        
        @wraps(func)
        def pending_executor():
            """执行待处理的调用"""
            with self.lock:
                if hasattr(wrapper, '_pending') and key in wrapper._pending:
                    args, kwargs = wrapper._pending.pop(key)
                    current_time = time.time()
                    result = func(*args, **kwargs)
                    self._last_exec_time[key] = current_time
                    self._record_execution(key, current_time)
                    return result
            return None
        
        # 附加pending_executor到wrapper
        wrapper.flush = lambda: pending_executor()
        
        return wrapper
    
    def _record_execution(self, key: str, timestamp: float) -> None:
        """记录执行历史"""
        if key not in self._exec_history:
            self._exec_history[key] = []
        self._exec_history[key].append(timestamp)
        # 只保留最近100次
        if len(self._exec_history[key]) > 100:
            self._exec_history[key] = self._exec_history[key][-100:]
    
    def get_stats(self, key: str) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            history = self._exec_history.get(key, [])
            now = time.time()
            recent_calls = sum(1 for t in history if (now - t) < 60)  # 最近1分钟
            
            return {
                'call_count': len(history),
                'last_exec_time': self._last_exec_time.get(key),
                'recent_calls_per_minute': recent_calls,
            }
    
    def reset(self, key: str) -> None:
        """重置节流状态"""
        with self.lock:
            self._last_exec_time.pop(key, None)
            self._call_count.pop(key, None)
            self._exec_history.pop(key, None)


class AsyncDebounceManager:
    """异步防抖管理器"""
    
    def __init__(self, config: Optional[DebounceConfig] = None):
        self.config = config or DebounceConfig()
        self._timers: Dict[str, asyncio.Task] = {}
    
    async def debounce(self, key: str, func: Callable,
                       wait: Optional[float] = None,
                       leading: Optional[bool] = None,
                       trailing: Optional[bool] = None) -> Callable:
        """创建异步防抖函数"""
        wait = wait or self.config.wait
        leading = leading if leading is not None else self.config.leading
        trailing = trailing if trailing is not None else self.config.trailing
        
        async def wrapper(*args, **kwargs):
            # 取消之前的定时器
            if key in self._timers:
                self._timers[key].cancel()
            
            async def execute():
                if trailing:
                    await func(*args, **kwargs)
                self._timers.pop(key, None)
            
            if leading and key not in self._timers:
                # 立即执行
                await func(*args, **kwargs)
            
            # 设置新的定时器
            self._timers[key] = asyncio.create_task(
                asyncio.sleep(wait / 1000) if wait > 0 else asyncio.sleep(0)
            )
            self._timers[key].add_done_callback(
                lambda t: asyncio.create_task(execute()) if not t.cancelled() else None
            )
        
        return wrapper
    
    def cancel(self, key: str) -> None:
        """取消防抖"""
        if key in self._timers:
            self._timers[key].cancel()
            del self._timers[key]


class AsyncThrottleManager:
    """异步节流管理器"""
    
    def __init__(self, config: Optional[ThrottleConfig] = None):
        self.config = config or ThrottleConfig()
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_exec_time: Dict[str, float] = {}
    
    async def throttle(self, key: str, func: Callable,
                       interval: Optional[float] = None,
                       leading: Optional[bool] = None,
                       trailing: Optional[bool] = None) -> Callable:
        """创建异步节流函数"""
        interval = interval or self.config.interval
        leading = leading if leading is not None else self.config.leading
        trailing = trailing if trailing is not None else self.config.trailing
        
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        
        async def wrapper(*args, **kwargs):
            async with self._locks[key]:
                current_time = time.time()
                last_time = self._last_exec_time.get(key, 0)
                elapsed = (current_time - last_time) * 1000
                
                if elapsed >= interval or not self._last_exec_time.get(key):
                    # 可以执行
                    self._last_exec_time[key] = current_time
                    return await func(*args, **kwargs)
                
                if trailing:
                    # 延迟执行
                    await asyncio.sleep(interval / 1000 - elapsed / 1000)
                    self._last_exec_time[key] = time.time()
                    return await func(*args, **kwargs)
        
        return wrapper
    
    def reset(self, key: str) -> None:
        """重置节流状态"""
        self._last_exec_time.pop(key, None)


# 便捷函数
_default_debounce_manager = DebounceManager()
_default_throttle_manager = ThrottleManager()
_default_async_debounce_manager = AsyncDebounceManager()
_default_async_throttle_manager = AsyncThrottleManager()


def debounce(key: str, wait: float = 300, leading: bool = True, 
             trailing: bool = True) -> Callable:
    """防抖装饰器便捷函数"""
    def decorator(func: Callable) -> Callable:
        return _default_debounce_manager.debounce(
            key, func, wait, leading, trailing
        )
    return decorator


def throttle(key: str, interval: float = 300, leading: bool = True,
             trailing: bool = True) -> Callable:
    """节流装饰器便捷函数"""
    def decorator(func: Callable) -> Callable:
        return _default_throttle_manager.throttle(
            key, func, interval, leading, trailing
        )
    return decorator


# 创建函数
def create_debounce_manager(config: Optional[DebounceConfig] = None) -> DebounceManager:
    """创建防抖管理器"""
    return DebounceManager(config)


def create_throttle_manager(config: Optional[ThrottleConfig] = None) -> ThrottleManager:
    """创建节流管理器"""
    return ThrottleManager(config)


def create_async_debounce_manager(config: Optional[DebounceConfig] = None) -> AsyncDebounceManager:
    """创建异步防抖管理器"""
    return AsyncDebounceManager(config)


def create_async_throttle_manager(config: Optional[ThrottleConfig] = None) -> AsyncThrottleManager:
    """创建异步节流管理器"""
    return AsyncThrottleManager(config)
