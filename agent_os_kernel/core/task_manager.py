"""任务管理器"""

from datetime import datetime
from datetime import timezone, timezone
from typing import Dict, Optional, List, Callable
from enum import Enum
import asyncio


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Execution:
    """执行"""
    
    def __init__(
        self,
        execution_id: str,
        task_id: str,
        agent_id: str,
        handler: Callable
    ):
        self.execution_id = execution_id
        self.task_id = task_id
        self.agent_id = agent_id
        self.handler = handler
        self.status = ExecutionStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0
    
    def start(self):
        """开始执行"""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
    
    def complete(self, result):
        """完成执行"""
        self.status = ExecutionStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc)
    
    def fail(self, error):
        """执行失败"""
        self.status = ExecutionStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)
    
    def get_duration(self) -> float:
        """获取持续时间"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0


class TaskManager:
    """任务管理器"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._executions: Dict[str, Execution] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "cancelled": 0
        }
    
    async def execute(
        self,
        execution_id: str,
        task_id: str,
        agent_id: str,
        handler: Callable,
        timeout: Optional[float] = None
    ) -> Execution:
        """执行任务"""
        execution = Execution(execution_id, task_id, agent_id, handler)
        self._executions[execution_id] = execution
        self._stats["total_executions"] += 1
        
        async with self._semaphore:
            execution.start()
            
            try:
                if timeout:
                    result = await asyncio.wait_for(
                        handler(),
                        timeout=timeout
                    )
                else:
                    result = await handler()
                
                execution.complete(result)
                self._stats["successful"] += 1
                return execution
                
            except Exception as e:
                execution.fail(str(e))
                self._stats["failed"] += 1
                raise
    
    def get_execution(self, execution_id: str) -> Optional[Execution]:
        """获取执行"""
        return self._executions.get(execution_id)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "active_executions": len(self._executions),
            "available_slots": self.max_concurrent - self._semaphore._value,
            **self._stats
        }
