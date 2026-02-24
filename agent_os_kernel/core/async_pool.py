# -*- coding: utf-8 -*-
"""
Async Pool Module - 提供异步任务池功能

支持:
- 异步任务管理
- 任务并发控制
- 任务优先级
- 任务超时处理
- 任务结果收集
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Awaitable
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import threading


class PoolState(Enum):
    """池状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class PoolConfig:
    """池配置"""
    max_workers: int = 10
    min_workers: int = 2
    max_queue_size: int = 1000
    task_timeout: float = 300.0
    idle_timeout: float = 60.0
    heartbeat_interval: float = 10.0
    max_retries: int = 3
    retry_delay: float = 0.1


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    priority: TaskPriority
    created_time: float
    submitted_time: float
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    retry_count: int = 0
    error_count: int = 0
    
    def is_timed_out(self, current_time: float, timeout: float) -> bool:
        """检查任务是否超时"""
        return current_time - self.created_time > timeout


class AsyncPoolError(Exception):
    """异步池异常基类"""
    pass


class TaskSubmitError(AsyncPoolError):
    """任务提交失败异常"""
    pass


class TaskExecuteError(AsyncPoolError):
    """任务执行失败异常"""
    pass


class TaskTimeoutError(AsyncPoolError):
    """任务执行超时异常"""
    pass


class PoolFullError(AsyncPoolError):
    """池已满异常"""
    pass


class PoolTerminatedError(AsyncPoolError):
    """池已终止异常"""
    pass


T = TypeVar('T')
R = TypeVar('R')


class TaskWrapper:
    """任务包装器"""
    
    def __init__(
        self,
        task_id: str,
        func: Callable[..., Awaitable[R]],
        args: tuple,
        kwargs: dict,
        priority: TaskPriority,
        timeout: float,
        retries: int
    ):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.priority = priority
        self.timeout = timeout
        self.retries = retries
        self.created_time = time.time()
        self.submitted_time = time.time()
        self.started_time: Optional[float] = None
        self.completed_time: Optional[float] = None
        self.retry_count = 0
        self.error_count = 0
        self.result: Optional[R] = None
        self.error: Optional[Exception] = None
        self.future: Optional[asyncio.Future] = None
        self.done_event = asyncio.Event()
    
    async def execute(self) -> R:
        """执行任务"""
        self.started_time = time.time()
        try:
            if asyncio.iscoroutinefunction(self.func):
                self.result = await asyncio.wait_for(
                    self.func(*self.args, **self.kwargs),
                    timeout=self.timeout
                )
            else:
                loop = asyncio.get_event_loop()
                self.result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.func, *self.args, **self.kwargs),
                    timeout=self.timeout
                )
            self.completed_time = time.time()
            return self.result
        except asyncio.TimeoutError:
            self.error = TaskTimeoutError(f"Task {self.task_id} timed out")
            self.error_count += 1
            raise
        except Exception as e:
            self.error = TaskExecuteError(f"Task {self.task_id} failed: {str(e)}")
            self.error_count += 1
            raise
        finally:
            self.done_event.set()


class PriorityQueue:
    """优先级队列实现"""
    
    def __init__(self):
        self.queues: Dict[TaskPriority, deque] = {
            priority: deque() for priority in TaskPriority
        }
        self.priority_order = [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW
        ]
        self.total_size = 0
    
    def put(self, task: TaskWrapper) -> None:
        """添加任务"""
        self.queues[task.priority].append(task)
        self.total_size += 1
    
    def get(self) -> Optional[TaskWrapper]:
        """获取最高优先级的任务"""
        for priority in self.priority_order:
            if self.queues[priority]:
                task = self.queues[priority].popleft()
                self.total_size -= 1
                return task
        return None
    
    def qsize(self) -> int:
        """返回队列大小"""
        return self.total_size
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self.total_size == 0


class AsyncPool:
    """
    异步任务池
    
    提供异步任务的管理和执行，支持:
    - 任务优先级
    - 任务超时
    - 任务重试
    - 并发控制
    - 任务结果收集
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig()
        self.state = PoolState.IDLE
        self.workers: Set[asyncio.Task] = set()
        self.task_queue = PriorityQueue()
        self.results: Dict[str, TaskWrapper] = {}
        self.submitted_tasks: Dict[str, TaskWrapper] = {}
        self._shutdown_event = asyncio.Event()
        self._worker_count = 0
        self._lock = threading.Lock()
        self._stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retried": 0,
            "total_timed_out": 0,
            "current_queue_size": 0,
            "current_workers": 0,
            "start_time": 0,
            "uptime": 0
        }
    
    def start(self) -> None:
        """启动异步池"""
        if self.state != PoolState.IDLE:
            raise AsyncPoolError(f"Cannot start pool from state: {self.state}")
        
        self.state = PoolState.RUNNING
        self._stats["start_time"] = time.time()
        
        # 启动工作协程
        for _ in range(self.config.min_workers):
            self._add_worker()
    
    def _add_worker(self) -> asyncio.Task:
        """添加工作协程"""
        worker = asyncio.create_task(self._worker_loop())
        self.workers.add(worker)
        self._worker_count += 1
        self._stats["current_workers"] = self._worker_count
        return worker
    
    async def _worker_loop(self) -> None:
        """工作协程主循环"""
        while self.state == PoolState.RUNNING:
            try:
                # 尝试获取任务
                task = self.task_queue.get()
                if task is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # 更新统计
                self._stats["current_queue_size"] = self.task_queue.qsize()
                
                # 执行任务
                await self._execute_task(task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                pass
    
    async def _execute_task(self, task: TaskWrapper) -> R:
        """执行单个任务"""
        self.submitted_tasks[task.task_id] = task
        task.future = asyncio.current_task()
        
        try:
            result = await task.execute()
            self.results[task.task_id] = task
            self._stats["total_completed"] += 1
            return result
        except Exception as e:
            task.error = e
            
            # 检查是否需要重试
            if task.retry_count < task.retries:
                task.retry_count += 1
                self._stats["total_retried"] += 1
                await asyncio.sleep(self.config.retry_delay)
                # 重新入队
                self.task_queue.put(task)
            else:
                self._stats["total_failed"] += 1
                raise
    
    async def submit(
        self,
        func: Callable[..., Awaitable[R]],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        **kwargs
    ) -> TaskWrapper:
        """
        提交异步任务
        
        Args:
            func: 异步函数
            *args: 函数位置参数
            priority: 任务优先级
            timeout: 任务超时时间
            retries: 最大重试次数
            **kwargs: 函数关键字参数
        
        Returns:
            TaskWrapper: 任务包装器
        
        Raises:
            PoolFullError: 队列已满
            PoolTerminatedError: 池已终止
        """
        if self.state != PoolState.RUNNING:
            raise PoolTerminatedError(f"Pool is not running: {self.state}")
        
        if self.task_queue.qsize() >= self.config.max_queue_size:
            raise PoolFullError(f"Task queue is full: {self.task_queue.qsize()}")
        
        task_id = str(uuid.uuid4())
        task_timeout = timeout if timeout is not None else self.config.task_timeout
        task_retries = retries if retries is not None else self.config.max_retries
        
        task = TaskWrapper(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=task_timeout,
            retries=task_retries
        )
        
        self.task_queue.put(task)
        self.submitted_tasks[task_id] = task
        self._stats["total_submitted"] += 1
        self._stats["current_queue_size"] = self.task_queue.qsize()
        
        # 自动扩展工作协程
        self._maybe_scale_workers()
        
        return task
    
    def _maybe_scale_workers(self) -> None:
        """根据队列情况自动扩展工作协程"""
        queue_size = self.task_queue.qsize()
        target_workers = min(
            self.config.max_workers,
            self.config.min_workers + max(0, queue_size // 5)
        )
        
        if self._worker_count < target_workers:
            for _ in range(target_workers - self._worker_count):
                self._add_worker()
    
    async def submit_sync(
        self,
        func: Callable[..., R],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        **kwargs
    ) -> R:
        """
        提交同步任务（在线程池中执行）
        
        Args:
            func: 同步函数
            *args: 函数位置参数
            priority: 任务优先级
            timeout: 任务超时时间
            **kwargs: 函数关键字参数
        
        Returns:
            R: 函数执行结果
        """
        if self.state != PoolState.RUNNING:
            raise PoolTerminatedError(f"Pool is not running: {self.state}")
        
        task_id = str(uuid.uuid4())
        task_timeout = timeout if timeout is not None else self.config.task_timeout
        
        # 使用线程池执行
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, func, *args, **kwargs),
                timeout=task_timeout
            )
        
        return result
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            timeout: 超时时间
        
        Returns:
            Any: 任务结果
        
        Raises:
            asyncio.TimeoutError: 获取超时
        """
        if task_id not in self.submitted_tasks:
            raise KeyError(f"Task not found: {task_id}")
        
        task = self.submitted_tasks[task_id]
        wait_timeout = timeout if timeout is not None else task.timeout
        
        try:
            await asyncio.wait_for(task.done_event.wait(), timeout=wait_timeout)
            if task.error:
                raise task.error
            return task.result
        except asyncio.TimeoutError:
            raise TaskTimeoutError(f"Getting result for task {task_id} timed out")
    
    async def wait_for_tasks(self, timeout: Optional[float] = None) -> None:
        """等待所有任务完成"""
        if not self.submitted_tasks:
            return
        
        async def wait_all():
            for task_id, task in list(self.submitted_tasks.items()):
                if task.completed_time is None:
                    await task.done_event.wait()
        
        wait_timeout = timeout if timeout is not None else self.config.task_timeout * 2
        try:
            await asyncio.wait_for(wait_all(), timeout=wait_timeout)
        except asyncio.TimeoutError:
            pass
    
    def get_pending_tasks(self) -> List[TaskInfo]:
        """获取待处理任务列表"""
        pending = []
        for task_id, task in self.submitted_tasks.items():
            if task.completed_time is None:
                info = TaskInfo(
                    task_id=task.task_id,
                    priority=task.priority,
                    created_time=task.created_time,
                    submitted_time=task.submitted_time,
                    started_time=task.started_time,
                    retry_count=task.retry_count,
                    error_count=task.error_count
                )
                pending.append(info)
        return pending
    
    def get_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        self._stats["current_queue_size"] = self.task_queue.qsize()
        self._stats["current_workers"] = self._worker_count
        self._stats["uptime"] = time.time() - self._stats["start_time"]
        return self._stats.copy()
    
    async def pause(self) -> None:
        """暂停池"""
        if self.state != PoolState.RUNNING:
            raise AsyncPoolError(f"Cannot pause pool from state: {self.state}")
        self.state = PoolState.PAUSED
    
    async def resume(self) -> None:
        """恢复池"""
        if self.state != PoolState.PAUSED:
            raise AsyncPoolError(f"Cannot resume pool from state: {self.state}")
        self.state = PoolState.RUNNING
    
    async def shutdown(self, graceful: bool = True) -> None:
        """
        关闭异步池
        
        Args:
            graceful: 是否优雅关闭（等待任务完成）
        """
        if self.state in (PoolState.SHUTTING_DOWN, PoolState.TERMINATED):
            return
        
        self.state = PoolState.SHUTTING_DOWN
        
        if graceful:
            await self.wait_for_tasks(timeout=30.0)
        
        # 取消所有工作协程
        for worker in self.workers:
            worker.cancel()
        
        # 等待工作协程结束
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        self._worker_count = 0
        self.state = PoolState.TERMINATED
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否成功取消
        """
        if task_id not in self.submitted_tasks:
            return False
        
        task = self.submitted_tasks[task_id]
        if task.future and not task.future.done():
            task.future.cancel()
            return True
        return False


def create_async_pool(
    max_workers: int = 10,
    min_workers: int = 2,
    max_queue_size: int = 1000,
    task_timeout: float = 300.0,
    **kwargs
) -> AsyncPool:
    """
    创建异步任务池的便捷函数
    
    Args:
        max_workers: 最大工作协程数
        min_workers: 最小工作协程数
        max_queue_size: 最大队列大小
        task_timeout: 任务超时时间
        **kwargs: 其他配置参数
    
    Returns:
        AsyncPool: 异步任务池实例
    """
    config = PoolConfig(
        max_workers=max_workers,
        min_workers=min_workers,
        max_queue_size=max_queue_size,
        task_timeout=task_timeout,
        **kwargs
    )
    return AsyncPool(config)
