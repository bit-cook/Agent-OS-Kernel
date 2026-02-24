# -*- coding: utf-8 -*-
"""
倒计时计时器模块 - Agent-OS-Kernel

提供倒计时功能、定时提醒、多次提醒和异步支持。
适用于需要时间管理的各种场景。
"""

from typing import Dict, List, Any, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import uuid

logger = logging.getLogger(__name__)


class TimerState(Enum):
    """计时器状态枚举"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TimerAlert:
    """定时提醒配置"""
    alert_id: str
    trigger_at: float  # 倒计时开始的秒数后触发
    callback: Callable
    callback_args: tuple = ()
    callback_kwargs: dict = field(default_factory=dict)
    repeat: bool = False
    repeat_interval: Optional[float] = None
    max_repeats: Optional[int] = None
    _trigger_count: int = 0
    
    def should_trigger(self, elapsed_seconds: float) -> bool:
        """检查是否应该触发"""
        if self.trigger_at <= elapsed_seconds:
            self._trigger_count += 1
            if self.max_repeats and self._trigger_count >= self.max_repeats:
                return False
            if self.repeat and self.repeat_interval:
                # 计算下一次触发时间
                next_trigger = self.trigger_at + (self._trigger_count * self.repeat_interval)
                if elapsed_seconds < next_trigger:
                    return False
            return True
        return False


@dataclass
class CountdownTimer:
    """倒计时计时器"""
    timer_id: str
    name: str
    duration_seconds: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: TimerState = TimerState.STOPPED
    alerts: List[TimerAlert] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    auto_start: bool = False
    on_complete: Optional[Callable] = None
    on_complete_args: tuple = ()
    on_complete_kwargs: dict = field(default_factory=dict)
    paused_elapsed: float = 0.0
    _remaining_seconds: float = 0.0
    
    def __post_init__(self):
        if self.auto_start:
            self.start()
    
    @property
    def remaining_seconds(self) -> float:
        """获取剩余秒数"""
        if self.state == TimerState.RUNNING:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            return max(0, self.duration_seconds - elapsed - self.paused_elapsed)
        elif self.state == TimerState.PAUSED:
            return max(0, self.duration_seconds - self.paused_elapsed)
        elif self.state == TimerState.STOPPED:
            return self.duration_seconds
        return 0.0
    
    @property
    def progress(self) -> float:
        """获取进度 (0.0 - 1.0)"""
        if self.duration_seconds <= 0:
            return 1.0
        return min(1.0, (self.duration_seconds - self.remaining_seconds) / self.duration_seconds)
    
    @property
    def elapsed_seconds(self) -> float:
        """获取已过秒数"""
        return self.duration_seconds - self.remaining_seconds
    
    def add_alert(self, alert: TimerAlert) -> str:
        """添加提醒"""
        self.alerts.append(alert)
        return alert.alert_id
    
    def add_alert_at(self, seconds: float, callback: Callable, 
                     repeat: bool = False, repeat_interval: Optional[float] = None,
                     max_repeats: Optional[int] = None,
                     *args, **kwargs) -> str:
        """便捷方法：添加提醒"""
        alert = TimerAlert(
            alert_id=str(uuid.uuid4())[:8],
            trigger_at=seconds,
            callback=callback,
            callback_args=args,
            callback_kwargs=kwargs,
            repeat=repeat,
            repeat_interval=repeat_interval,
            max_repeats=max_repeats
        )
        return self.add_alert(alert)
    
    def start(self) -> bool:
        """启动计时器"""
        if self.state == TimerState.RUNNING:
            return False
        
        if self.state == TimerState.PAUSED:
            self.start_time = datetime.now()
            self.state = TimerState.RUNNING
        else:
            self.start_time = datetime.now()
            self.end_time = None
            self.paused_elapsed = 0.0
            self.state = TimerState.RUNNING
        
        return True
    
    def pause(self) -> bool:
        """暂停计时器"""
        if self.state != TimerState.RUNNING:
            return False
        
        self.paused_elapsed = self.elapsed_seconds
        self.state = TimerState.PAUSED
        return True
    
    def stop(self) -> bool:
        """停止计时器"""
        self.state = TimerState.STOPPED
        self.paused_elapsed = 0.0
        return True
    
    def reset(self) -> bool:
        """重置计时器"""
        self.state = TimerState.STOPPED
        self.paused_elapsed = 0.0
        self.start_time = None
        self.end_time = None
        return True
    
    def cancel(self) -> bool:
        """取消计时器"""
        self.state = TimerState.CANCELLED
        return True
    
    def get_remaining_time_string(self) -> str:
        """获取剩余时间字符串 (HH:MM:SS)"""
        seconds = int(self.remaining_seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class CountdownTimerManager:
    """倒计时计时器管理器"""
    
    def __init__(self, max_workers: int = 4):
        self.timers: Dict[str, CountdownTimer] = {}
        self._running_timers: Set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = asyncio.Lock()
        self._running = False
    
    async def create_timer(self, name: str, duration_seconds: float,
                          auto_start: bool = False,
                          on_complete: Optional[Callable] = None,
                          **kwargs) -> CountdownTimer:
        """创建并返回计时器"""
        timer = CountdownTimer(
            timer_id=str(uuid.uuid4())[:8],
            name=name,
            duration_seconds=duration_seconds,
            auto_start=auto_start,
            on_complete=on_complete,
            **kwargs
        )
        async with self._lock:
            self.timers[timer.timer_id] = timer
        return timer
    
    async def delete_timer(self, timer_id: str) -> bool:
        """删除计时器"""
        async with self._lock:
            if timer_id in self.timers:
                del self.timers[timer_id]
                self._running_timers.discard(timer_id)
                return True
        return False
    
    async def get_timer(self, timer_id: str) -> Optional[CountdownTimer]:
        """获取计时器"""
        return self.timers.get(timer_id)
    
    async def list_timers(self) -> List[CountdownTimer]:
        """列出所有计时器"""
        return list(self.timers.values())
    
    async def start_timer(self, timer_id: str) -> bool:
        """启动计时器"""
        timer = self.timers.get(timer_id)
        if timer and timer.start():
            self._running_timers.add(timer_id)
            return True
        return False
    
    async def pause_timer(self, timer_id: str) -> bool:
        """暂停计时器"""
        timer = self.timers.get(timer_id)
        if timer and timer.pause():
            self._running_timers.discard(timer_id)
            return True
        return False
    
    async def stop_timer(self, timer_id: str) -> bool:
        """停止计时器"""
        timer = self.timers.get(timer_id)
        if timer and timer.stop():
            self._running_timers.discard(timer_id)
            return True
        return False
    
    async def cancel_timer(self, timer_id: str) -> bool:
        """取消计时器"""
        timer = self.timers.get(timer_id)
        if timer and timer.cancel():
            self._running_timers.discard(timer_id)
            return True
        return False
    
    async def add_alert(self, timer_id: str, alert: TimerAlert) -> Optional[str]:
        """为计时器添加提醒"""
        timer = self.timers.get(timer_id)
        if timer:
            return timer.add_alert(alert)
        return None
    
    def get_timer_status(self, timer_id: str) -> Optional[Dict[str, Any]]:
        """获取计时器状态"""
        timer = self.timers.get(timer_id)
        if timer:
            return {
                "timer_id": timer.timer_id,
                "name": timer.name,
                "state": timer.state.value,
                "duration_seconds": timer.duration_seconds,
                "remaining_seconds": timer.remaining_seconds,
                "progress": timer.progress,
                "elapsed_seconds": timer.elapsed_seconds,
                "remaining_time_string": timer.get_remaining_time_string(),
                "alerts_count": len(timer.alerts),
                "start_time": timer.start_time.isoformat() if timer.start_time else None,
                "end_time": timer.end_time.isoformat() if timer.end_time else None
            }
        return None
    
    async def run_countdown_async(self, timer_id: str, 
                                  check_interval: float = 0.1) -> None:
        """异步运行计时器（阻塞）"""
        timer = self.timers.get(timer_id)
        if not timer or not timer.start():
            return
        
        self._running_timers.add(timer_id)
        triggered_alerts = set()
        
        while timer.state == TimerState.RUNNING:
            elapsed = timer.elapsed_seconds
            
            # 检查是否完成
            if elapsed >= timer.duration_seconds:
                timer.state = TimerState.COMPLETED
                timer.end_time = datetime.now()
                if timer.on_complete:
                    timer.on_complete(*timer.on_complete_args, **timer.on_complete_kwargs)
                self._running_timers.discard(timer_id)
                break
            
            # 检查提醒
            for alert in timer.alerts:
                if alert.alert_id in triggered_alerts:
                    continue
                if alert.should_trigger(elapsed):
                    try:
                        if asyncio.iscoroutinefunction(alert.callback):
                            await alert.callback(*alert.callback_args, **alert.callback_kwargs)
                        else:
                            loop = asyncio.get_event_loop()
                            loop.run_in_executor(self._executor, 
                                                alert.callback, 
                                                *alert.callback_args, 
                                                **alert.callback_kwargs)
                    except Exception as e:
                        logger.error(f"Error triggering alert {alert.alert_id}: {e}")
                    
                    triggered_alerts.add(alert.alert_id)
            
            await asyncio.sleep(check_interval)
    
    def run_countdown_sync(self, timer_id: str, 
                          check_interval: float = 0.1) -> None:
        """同步运行计时器（阻塞）"""
        timer = self.timers.get(timer_id)
        if not timer or not timer.start():
            return
        
        self._running_timers.add(timer_id)
        triggered_alerts = set()
        start_time = datetime.now()
        
        while timer.state == TimerState.RUNNING:
            elapsed = (datetime.now() - start_time).total_seconds() + timer.paused_elapsed
            
            # 检查是否完成
            if elapsed >= timer.duration_seconds:
                timer.state = TimerState.COMPLETED
                timer.end_time = datetime.now()
                if timer.on_complete:
                    timer.on_complete(*timer.on_complete_args, **timer.on_complete_kwargs)
                self._running_timers.discard(timer_id)
                break
            
            # 检查提醒
            for alert in timer.alerts:
                if alert.alert_id in triggered_alerts:
                    continue
                if alert.should_trigger(elapsed):
                    try:
                        alert.callback(*alert.callback_args, **alert.callback_kwargs)
                    except Exception as e:
                        logger.error(f"Error triggering alert {alert.alert_id}: {e}")
                    triggered_alerts.add(alert.alert_id)
            
            import time
            time.sleep(check_interval)
    
    def shutdown(self):
        """关闭管理器"""
        self._running = False
        for timer_id in list(self._running_timers):
            self.timers[timer_id].cancel()
        self._running_timers.clear()
        self._executor.shutdown(wait=False)
