# -*- coding: utf-8 -*-
"""Worker - 工作池

支持工作进程池、任务分发、负载均衡。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from uuid import uuid4
import multiprocessing

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    """工作节点状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class Worker:
    """工作节点"""
    worker_id: str
    name: str
    status: WorkerStatus = WorkerStatus.IDLE
    current_task_id: Optional[str] = None
    task_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_active: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self.status == WorkerStatus.IDLE


class WorkerPool:
    """工作池"""
    
    def __init__(
        self,
        name: str = "default",
        max_workers: int = None,
        strategy: str = "round_robin"
    ):
        """
        初始化工作池
        
        Args:
            name: 池名称
            max_workers: 最大工作节点数
            strategy: 分配策略 (round_robin, least_busy, random)
        """
        self.name = name
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.strategy = strategy
        
        self._workers: Dict[str, Worker] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._running = False
        
        logger.info(f"WorkerPool initialized: {name}, max_workers={self.max_workers}")
    
    def add_worker(
        self,
        worker_id: str = None,
        name: str = None,
        metadata: Dict = None
    ) -> Worker:
        """添加工作节点"""
        worker_id = worker_id or str(uuid4())
        name = name or f"worker-{len(self._workers) + 1}"
        
        worker = Worker(
            worker_id=worker_id,
            name=name,
            metadata=metadata or {}
        )
        
        self._workers[worker_id] = worker
        
        logger.info(f"Worker added: {name}")
        
        return worker
    
    def remove_worker(self, worker_id: str) -> bool:
        """移除工作节点"""
        if worker_id in self._workers:
            del self._workers[worker_id]
            logger.info(f"Worker removed: {worker_id}")
            return True
        return False
    
    async def submit(
        self,
        task_id: str,
        func: Callable,
        *args,
        worker_id: str = None,
        **kwargs
    ) -> str:
        """
        提交任务
        
        Args:
            task_id: 任务 ID
            func: 可执行函数
            *args: 位置参数
            worker_id: 指定工作节点
            **kwargs: 关键字参数
            
        Returns:
            任务 ID
        """
        async with self._lock:
            # 选择工作节点
            if worker_id and worker_id in self._workers:
                worker = self._workers[worker_id]
            else:
                worker = self._select_worker()
            
            if not worker:
                raise NoAvailableWorkerError("No available workers")
            
            # 标记为忙碌
            worker.status = WorkerStatus.BUSY
            worker.current_task_id = task_id
            worker.last_active = datetime.now(timezone.utc)
            
            # 创建任务
            task = asyncio.create_task(
                self._execute_task(task_id, worker, func, *args, **kwargs)
            )
            self._tasks[task_id] = task
        
        logger.debug(f"Task submitted: {task_id} to {worker.name}")
        
        return task_id
    
    def _select_worker(self) -> Optional[Worker]:
        """选择工作节点"""
        available = [w for w in self._workers.values() if w.is_available()]
        
        if not available:
            return None
        
        if self.strategy == "round_robin":
            return available[len(self._results) % len(available)]
        elif self.strategy == "least_busy":
            return min(available, key=lambda w: w.task_count)
        else:  # random
            import random
            return random.choice(available)
    
    async def _execute_task(
        self,
        task_id: str,
        worker: Worker,
        func: Callable,
        *args,
        **kwargs
    ):
        """执行任务"""
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._results[task_id] = result
            
            worker.success_count += 1
            worker.task_count += 1
            worker.status = WorkerStatus.IDLE
            worker.current_task_id = None
            
            logger.debug(f"Task completed: {task_id}")
            
        except Exception as e:
            logger.error(f"Task failed: {task_id} - {e}")
            
            worker.error_count += 1
            worker.task_count += 1
            worker.status = WorkerStatus.IDLE
            worker.current_task_id = None
            
            self._results[task_id] = {"error": str(e)}
    
    async def get_result(self, task_id: str, timeout: float = None) -> Any:
        """获取结果"""
        if task_id not in self._results:
            if task_id in self._tasks:
                await asyncio.wait_for(self._tasks[task_id], timeout=timeout)
            else:
                raise KeyError(f"Task not found: {task_id}")
        
        return self._results.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].cancel()
                del self._tasks[task_id]
                
                # 重置工作节点
                for worker in self._workers.values():
                    if worker.current_task_id == task_id:
                        worker.status = WorkerStatus.IDLE
                        worker.current_task_id = None
                
                return True
        return False
    
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """获取工作节点"""
        return self._workers.get(worker_id)
    
    def list_workers(self) -> list:
        """列出所有工作节点"""
        return list(self._workers.values())
    
    def get_available_workers(self) -> list:
        """获取可用工作节点"""
        return [w for w in self._workers.values() if w.is_available()]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total_tasks = sum(w.task_count for w in self._workers.values())
        success_tasks = sum(w.success_count for w in self._workers.values())
        
        return {
            "name": self.name,
            "total_workers": len(self._workers),
            "available_workers": len(self.get_available_workers()),
            "total_tasks": total_tasks,
            "success_tasks": success_tasks,
            "failed_tasks": total_tasks - success_tasks,
            "strategy": self.strategy,
            "max_workers": self.max_workers
        }


class NoAvailableWorkerError(Exception):
    """无可用工作节点异常"""
    pass
