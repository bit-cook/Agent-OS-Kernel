# -*- coding: utf-8 -*-
"""Optimized Scheduler - MemScheduler 理念借鉴

借鉴 MemOS 的 MemScheduler 思路，优化任务调度。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from uuid import uuid4
import heapq

logger = logging.getLogger(__name__)


class Priority(Enum):
    """任务优先级 (借鉴 MemScheduler)"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_delay: float = 0.0
    max_retries: int = 3
    retry_count: int = 0
    timeout: float = 300.0
    quota: str = "default"
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


class OptimizedScheduler:
    """优化调度器 - 借鉴 MemScheduler 思路"""
    
    def __init__(
        self,
        max_concurrent: int = 10,
        default_timeout: float = 300.0,
        quota_managed: bool = True
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.quota_managed = quota_managed
        
        self._queue: list = []
        self._running: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, Any] = {}
        self._quotas: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self._running_flag = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        logger.info(f"OptimizedScheduler initialized")
    
    def _init_quota(self, quota_name: str, max_tasks: int = 100):
        if quota_name not in self._quotas:
            self._quotas[quota_name] = {
                "max_tasks": max_tasks,
                "current_tasks": 0
            }
    
    async def schedule(
        self,
        name: str,
        func: Callable,
        *args,
        priority: Priority = Priority.NORMAL,
        delay_seconds: float = 0.0,
        quota: str = "default",
        max_retries: int = 3,
        timeout: float = None,
        **kwargs
    ) -> str:
        task_id = str(uuid4())
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_delay=delay_seconds,
            quota=quota,
            max_retries=max_retries,
            timeout=timeout or self.default_timeout
        )
        
        if self.quota_managed:
            self._init_quota(quota)
        
        async with self._lock:
            heapq.heappush(self._queue, task)
        
        if not self._running_flag:
            await self.start()
        
        return task_id
    
    async def start(self):
        if not self._running_flag:
            self._running_flag = True
            self._scheduler_task = asyncio.create_task(self._run())
            logger.info("OptimizedScheduler started")
    
    async def stop(self):
        self._running_flag = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
        logger.info("OptimizedScheduler stopped")
    
    async def _run(self):
        while self._running_flag:
            try:
                await asyncio.sleep(0.01)
                
                if len(self._running) >= self.max_concurrent:
                    continue
                
                async with self._lock:
                    if not self._queue:
                        continue
                    
                    task = heapq.heappop(self._queue)
                    
                    if self.quota_managed:
                        quota = self._quotas.get(task.quota, {})
                        if quota.get("current_tasks", 0) >= quota.get("max_tasks", 100):
                            heapq.heappush(self._queue, task)
                            continue
                        
                        quota["current_tasks"] = quota.get("current_tasks", 0) + 1
                    
                    if task.scheduled_delay > 0:
                        await asyncio.sleep(task.scheduled_delay)
                    
                    self._running[task.task_id] = asyncio.create_task(
                        self._execute(task)
                    )
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    async def _execute(self, task: ScheduledTask):
        try:
            if asyncio.iscoroutinefunction(task.func):
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.coroutine(task.func)(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            
            self._results[task.task_id] = result
            
        except asyncio.TimeoutError:
            await self._handle_failure(task, "Timeout")
        except Exception as e:
            await self._handle_failure(task, str(e))
        finally:
            async with self._lock:
                self._running.pop(task.task_id, None)
                
                if self.quota_managed:
                    quota = self._quotas.get(task.quota, {})
                    quota["current_tasks"] = max(0, quota.get("current_tasks", 1) - 1)
    
    async def _handle_failure(self, task: ScheduledTask, error: str):
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.scheduled_delay = min(task.scheduled_delay * 2, 60)
            
            async with self._lock:
                heapq.heappush(self._queue, task)
        else:
            self._results[task.task_id] = {"error": error}
    
    async def get_result(self, task_id: str) -> Any:
        return self._results.get(task_id)
    
    def get_stats(self) -> Dict:
        return {
            "queue_size": len(self._queue),
            "running": len(self._running),
            "quotas": self._quotas
        }
    
    def get_quota_status(self, quota_name: str) -> Dict:
        quota = self._quotas.get(quota_name, {})
        return {
            "name": quota_name,
            "max_tasks": quota.get("max_tasks", 100),
            "current_tasks": quota.get("current_tasks", 0)
        }
