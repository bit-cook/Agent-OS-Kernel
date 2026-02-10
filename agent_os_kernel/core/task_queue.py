# -*- coding: utf-8 -*-
"""Task Queue - 任务队列"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4
import heapq

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class Task:
    task_id: str
    name: str
    priority: TaskPriority
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


class TaskQueue:
    def __init__(self, max_size: int = 10000, max_concurrent: int = 10, default_timeout: float = 300.0):
        self.max_size = max_size
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._queue: list = []
        self._running: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, Any] = {}
        self._stats = {"submitted": 0, "completed": 0, "failed": 0}
        self._lock = asyncio.Lock()
        logger.info(f"TaskQueue initialized: max_size={max_size}")
    
    async def submit(self, name: str, func: Callable, *args, priority: TaskPriority = TaskPriority.NORMAL,
                    max_retries: int = 3, retry_delay: float = 1.0, timeout: float = None, **kwargs) -> str:
        task_id = str(uuid4())
        task = Task(task_id=task_id, name=name, priority=priority, func=func, args=args, kwargs=kwargs,
                    max_retries=max_retries, retry_delay=retry_delay, timeout=timeout or self.default_timeout)
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise Exception("Queue full")
            heapq.heappush(self._queue, task)
            self._stats["submitted"] += 1
        await self._dispatch()
        return task_id
    
    async def _dispatch(self):
        async with self._lock:
            while self._queue and len(self._running) < self.max_concurrent:
                task = heapq.heappop(self._queue)
                if task.status == TaskStatus.CANCELLED:
                    continue
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                self._running[task.task_id] = asyncio.create_task(self._run_task(task))
    
    async def _run_task(self, task: Task):
        try:
            if asyncio.iscoroutinefunction(task.func):
                result = await asyncio.wait_for(task.func(*task.args, **task.kwargs), timeout=task.timeout)
            else:
                result = await asyncio.wait_for(asyncio.coroutine(task.func)(*task.args, **task.kwargs), timeout=task.timeout)
            task.result = result
            task.status = TaskStatus.COMPLETED
            self._stats["completed"] += 1
            self._results[task.task_id] = result
        except Exception as e:
            task.error = str(e)
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                async with self._lock:
                    heapq.heappush(self._queue, task)
            else:
                task.status = TaskStatus.FAILED
                self._stats["failed"] += 1
        finally:
            async with self._lock:
                self._running.pop(task.task_id, None)
                task.finished_at = datetime.utcnow()
            await self._dispatch()
    
    async def get_result(self, task_id: str) -> Any:
        return self._results.get(task_id)
    
    def get_stats(self) -> Dict:
        return {"queue_size": len(self._queue), "running": len(self._running),
                "submitted": self._stats["submitted"], "completed": self._stats["completed"],
                "failed": self._stats["failed"]}
