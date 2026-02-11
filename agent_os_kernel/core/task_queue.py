"""任务队列"""

from datetime import datetime
from datetime import timezone, timezone, timedelta, timezone
from typing import Dict, Optional, List
from enum import Enum
import asyncio


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Task:
    """任务"""
    
    def __init__(
        self,
        task_id: str,
        name: str,
        handler: callable,
        priority: int = 0,
        timeout: Optional[float] = None
    ):
        self.task_id = task_id
        self.name = name
        self.handler = handler
        self.priority = priority
        self.timeout = timeout
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.finished_at = None
        self.retry_count = 0
    
    def start(self):
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
    
    def complete(self, result):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.finished_at = datetime.now(timezone.utc)
    
    def fail(self, error):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.finished_at = datetime.now(timezone.utc)


class TaskQueue:
    """任务队列"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(max_size)
        self._running: Dict[str, Task] = {}
        self._completed: Dict[str, Task] = {}
        self._stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0
        }
    
    async def submit(
        self,
        task_id: str,
        name: str,
        handler: callable,
        priority: int = 0,
        timeout: Optional[float] = None
    ) -> Task:
        """提交任务"""
        task = Task(task_id, name, handler, priority, timeout)
        await self._queue.put((-priority, task_id, task))
        self._stats["total_submitted"] += 1
        return task
    
    async def get(self) -> Task:
        """获取任务"""
        _, _, task = await self._queue.get()
        return task
    
    def start_task(self, task: Task):
        """开始任务"""
        task.start()
        self._running[task.task_id] = task
    
    def complete_task(self, task: Task, result):
        """完成任务"""
        task.complete(result)
        self._running.pop(task.task_id, None)
        self._completed[task.task_id] = task
        self._stats["total_completed"] += 1
    
    def fail_task(self, task: Task, error):
        """任务失败"""
        task.fail(error)
        self._running.pop(task.task_id, None)
        self._completed[task.task_id] = task
        self._stats["total_failed"] += 1
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "queue_size": self._queue.qsize(),
            "running_count": len(self._running),
            "completed_count": len(self._completed),
            **self._stats
        }
