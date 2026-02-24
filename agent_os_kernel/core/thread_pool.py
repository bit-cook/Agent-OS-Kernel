# -*- coding: utf-8 -*-
"""
Thread Pool Module - 提供线程池功能

支持:
- 任务提交与执行
- 固定数量工作线程
- 任务队列管理
- 异步/同步任务支持
- 优雅关闭
- 运行指标统计
"""

import asyncio
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import Future
from collections import deque


class ThreadPoolState(Enum):
    """线程池状态"""
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """任务"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    submitted_time: float
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    result: Any = None
    exception: Optional[Exception] = None
    
    def __lt__(self, other):
        """优先级比较，优先级高的任务排在前面"""
        if not isinstance(other, Task):
            return NotImplemented
        return self.priority.value > other.priority.value


@dataclass
class ThreadPoolConfig:
    """线程池配置"""
    min_workers: int = 2
    max_workers: int = 10
    max_queue_size: int = 100
    thread_prefix: str = "worker"
    daemon: bool = True
    idle_timeout: float = 60.0


@dataclass
class ThreadPoolMetrics:
    """线程池指标"""
    submitted_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_workers: int = 0
    queued_tasks: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    peak_queued_tasks: int = 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "submitted_tasks": self.submitted_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "active_workers": self.active_workers,
            "queued_tasks": self.queued_tasks,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.average_execution_time,
            "peak_queued_tasks": self.peak_queued_tasks,
        }


class ThreadPool:
    """
    线程池管理器
    
    支持任务提交、队列管理、工作线程调度和优雅关闭。
    """
    
    def __init__(self, config: Optional[ThreadPoolConfig] = None):
        """
        初始化线程池
        
        Args:
            config: 线程池配置
        """
        self.config = config or ThreadPoolConfig()
        self._state = ThreadPoolState.RUNNING
        
        # 任务队列 (优先级队列)
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue(
            maxsize=self.config.max_queue_size
        )
        
        # 正在执行的任务
        self._running_tasks: Dict[str, Task] = {}
        self._running_lock = threading.Lock()
        
        # 工作线程
        self._workers: List[threading.Thread] = []
        self._worker_ids: Set[str] = set()
        self._worker_counter = 0
        
        # 指标
        self._metrics = ThreadPoolMetrics()
        self._metrics_lock = threading.Lock()
        
        # 启动工作线程
        self._start_workers()
    
    def _generate_worker_id(self) -> str:
        """生成工作线程ID"""
        self._worker_counter += 1
        return f"{self.config.thread_prefix}_{self._worker_counter}"
    
    def _start_workers(self):
        """启动工作线程"""
        for _ in range(self.config.min_workers):
            self._spawn_worker()
    
    def _spawn_worker(self):
        """创建并启动单个工作线程"""
        worker_id = self._generate_worker_id()
        thread = threading.Thread(
            target=self._worker_loop,
            args=(worker_id,),
            daemon=self.config.daemon,
            name=worker_id
        )
        thread.start()
        self._workers.append(thread)
        self._worker_ids.add(worker_id)
    
    def _worker_loop(self, worker_id: str):
        """工作线程主循环"""
        self._update_metric("active_workers", 1)
        
        while self._should_continue(worker_id):
            try:
                task = self._get_task(timeout=1.0)
                if task is None:
                    continue
                
                self._execute_task(task, worker_id)
            except queue.Empty:
                continue
            except Exception as e:
                pass  # 静默处理
        
        self._update_metric("active_workers", -1)
    
    def _should_continue(self, worker_id: str) -> bool:
        """检查是否继续运行"""
        if self._state == ThreadPoolState.TERMINATED:
            return False
        
        if self._state == ThreadPoolState.SHUTTING_DOWN:
            # 关闭时，如果队列为空则退出
            try:
                return not self._task_queue.empty()
            except:
                return False
        
        return True
    
    def _get_task(self, timeout: float) -> Optional[Task]:
        """从队列获取任务"""
        try:
            # 使用 get_nowait 避免阻塞
            return self._task_queue.get_nowait()
        except queue.Empty:
            return None
    
    def _execute_task(self, task: Task, worker_id: str):
        """执行任务"""
        task.started_time = time.time()
        
        with self._running_lock:
            self._running_tasks[task.task_id] = task
        
        try:
            task.result = task.func(*task.args, **task.kwargs)
            task.completed_time = time.time()
            self._update_metric("completed_tasks", 1)
            
            execution_time = task.completed_time - task.started_time
            self._update_execution_time(execution_time)
            
        except Exception as e:
            task.completed_time = time.time()
            task.exception = e
            self._update_metric("failed_tasks", 1)
        
        finally:
            with self._running_lock:
                self._running_tasks.pop(task.task_id, None)
    
    def _update_metric(self, metric: str, delta: int = 0):
        """更新指标"""
        with self._metrics_lock:
            if delta != 0:
                setattr(self._metrics, metric, getattr(self._metrics, metric) + delta)
            
            # 更新峰值
            if metric == "queued_tasks":
                queued = self._task_queue.qsize()
                self._metrics.queued_tasks = queued
                if queued > self._metrics.peak_queued_tasks:
                    self._metrics.peak_queued_tasks = queued
    
    def _update_execution_time(self, execution_time: float):
        """更新执行时间统计"""
        with self._metrics_lock:
            self._metrics.total_execution_time += execution_time
            completed = self._metrics.completed_tasks
            if completed > 0:
                self._metrics.average_execution_time = (
                    self._metrics.total_execution_time / completed
                )
    
    def submit(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ) -> str:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            priority: 任务优先级
            **kwargs: 关键字参数
            
        Returns:
            任务ID
            
        Raises:
            RuntimeError: 线程池已关闭
            queue.Full: 队列已满
        """
        if self._state != ThreadPoolState.RUNNING:
            raise RuntimeError("Thread pool is not running")
        
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            submitted_time=time.time()
        )
        
        self._task_queue.put(task)
        self._update_metric("submitted_tasks", 1)
        self._update_metric("queued_tasks", 1)
        
        # 动态扩展工作线程
        self._maybe_expand_workers()
        
        return task_id
    
    def _maybe_expand_workers(self):
        """动态扩展工作线程"""
        current_workers = len(self._workers)
        queue_size = self._task_queue.qsize()
        
        # 如果队列积压且有可用扩展空间，则添加工作线程
        if (queue_size > current_workers and 
            current_workers < self.config.max_workers):
            self._spawn_worker()
    
    def submit_nowait(self, func: Callable, *args, **kwargs) -> Optional[str]:
        """
        非阻塞提交任务（不等待队列空间）
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            任务ID，如果队列满则返回None
        """
        if self._state != ThreadPoolState.RUNNING:
            return None
        
        try:
            return self.submit(func, *args, **kwargs)
        except queue.Full:
            return None
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果（需要自行检查异常）"""
        with self._running_lock:
            task = self._running_tasks.get(task_id)
        
        if task is None:
            # 任务已完成但不在运行字典中
            # 注意：这里简化处理，实际应用中需要额外的完成队列
            return None
        
        return task.result
    
    def get_metrics(self) -> Dict:
        """获取线程池指标"""
        self._update_metric("queued_tasks")
        return self._metrics.to_dict()
    
    def get_state(self) -> ThreadPoolState:
        """获取线程池状态"""
        return self._state
    
    def get_active_task_count(self) -> int:
        """获取正在执行的任务数量"""
        with self._running_lock:
            return len(self._running_tasks)
    
    def get_queued_task_count(self) -> int:
        """获取队列中等待的任务数量"""
        try:
            return self._task_queue.qsize()
        except:
            return 0
    
    def get_worker_count(self) -> int:
        """获取工作线程数量"""
        return len(self._workers)
    
    def shutdown(self, wait: bool = True, timeout: Optional[float] = None):
        """
        优雅关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
            timeout: 等待超时时间
        """
        self._state = ThreadPoolState.SHUTTING_DOWN
        
        # 等待运行中的任务完成
        if wait:
            self._wait_for_tasks(timeout)
        
        # 标记为终止
        self._state = ThreadPoolState.TERMINATED
        
        # 清理资源
        self._task_queue = queue.Queue()
    
    def _wait_for_tasks(self, timeout: Optional[float] = None):
        """等待所有运行中的任务完成"""
        start_time = time.time()
        
        while True:
            with self._running_lock:
                running_count = len(self._running_tasks)
            
            if running_count == 0:
                break
            
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    break
            
            time.sleep(0.1)
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown(wait=True)
        return False
    
    def __del__(self):
        """析构函数"""
        if self._state == ThreadPoolState.RUNNING:
            self.shutdown(wait=False)
