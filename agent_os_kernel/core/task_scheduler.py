# -*- coding: utf-8 -*-
"""
任务调度器模块 - Agent-OS-Kernel

提供定时任务、周期性任务、任务优先级和任务依赖管理功能。
支持cron表达式调度、间隔执行和任务链执行。
"""

from typing import Dict, List, Any, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import asyncio
import re
import logging
from datetime import datetime, timedelta
from croniter import croniter
import uuid

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class SchedulerState(Enum):
    """调度器状态枚举"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class ScheduledTask:
    """已调度的任务"""
    task_id: str
    name: str
    func: Callable
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    cron_expression: Optional[str] = None
    interval_seconds: Optional[float] = None
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    last_result: Any = None
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    max_consecutive_failures: int = 3
    _consecutive_failures: int = 0
    
    def __lt__(self, other):
        """比较优先级用于优先级队列"""
        if isinstance(other, ScheduledTask):
            return self.priority.value > other.priority.value  # 高的优先级先执行
        return NotImplemented
    
    def __eq__(self, other):
        if isinstance(other, ScheduledTask):
            return self.task_id == other.task_id
        return NotImplemented
    
    def __hash__(self):
        return hash(self.task_id)


@dataclass
class TaskExecution:
    """任务执行记录"""
    task_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class TaskScheduler:
    """任务调度器类"""
    
    def __init__(self, timezone: str = "UTC"):
        """
        初始化任务调度器
        
        Args:
            timezone: 时区名称
        """
        self.tasks: Dict[str, ScheduledTask] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.execution_history: deque = deque(maxlen=1000)
        self.state = SchedulerState.STOPPED
        self.timezone = timezone
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._completed_tasks: Set[str] = set()
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
    def add_task(
        self,
        func: Callable,
        name: str,
        task_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[float] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加任务到调度器
        
        Args:
            func: 要执行的函数
            name: 任务名称
            task_id: 任务ID（可选，自动生成）
            priority: 任务优先级
            dependencies: 依赖的任务ID列表
            cron_expression: cron表达式（用于定时任务）
            interval_seconds: 执行间隔秒数（用于周期性任务）
            enabled: 是否启用
            metadata: 附加元数据
            
        Returns:
            任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            priority=priority,
            dependencies=dependencies or [],
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            enabled=enabled,
            metadata=metadata or {}
        )
        
        # 计算下次执行时间
        if cron_expression:
            task.next_run_time = self._get_next_cron_time(cron_expression)
        elif interval_seconds:
            task.next_run_time = datetime.now()
        
        # 添加到任务字典
        self.tasks[task_id] = task
        
        # 更新依赖图
        for dep in task.dependencies:
            self._dependency_graph[dep].add(task_id)
        
        logger.info(f"Task added: {name} ({task_id})")
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """
        从调度器移除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功移除
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            
            # 从依赖图中移除
            for deps in self._dependency_graph.values():
                deps.discard(task_id)
            
            self._dependency_graph.pop(task_id, None)
            self._completed_tasks.discard(task_id)
            
            logger.info(f"Task removed: {task_id}")
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = True
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = False
            return True
        return False
    
    def update_priority(self, task_id: str, priority: TaskPriority) -> bool:
        """更新任务优先级"""
        task = self.tasks.get(task_id)
        if task:
            task.priority = priority
            return True
        return False
    
    def _get_next_cron_time(self, cron_expression: str, from_time: Optional[datetime] = None) -> datetime:
        """计算下次cron执行时间"""
        if from_time is None:
            from_time = datetime.now()
        
        if croniter.is_valid(cron_expression):
            cron = croniter(cron_expression, from_time)
            return cron.get_next(datetime)
        
        raise ValueError(f"Invalid cron expression: {cron_expression}")
    
    def _check_dependencies(self, task: ScheduledTask) -> bool:
        """检查任务依赖是否满足"""
        for dep_id in task.dependencies:
            if dep_id not in self._completed_tasks:
                return False
        return True
    
    async def _execute_task(self, task: ScheduledTask) -> TaskExecution:
        """执行单个任务"""
        execution = TaskExecution(
            task_id=task.task_id,
            start_time=datetime.now(),
            status="running"
        )
        
        try:
            # 异步执行
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func()
            else:
                result = task.func()
            
            task.last_result = result
            task.last_error = None
            task._consecutive_failures = 0
            execution.status = "completed"
            execution.result = result
            
            logger.info(f"Task executed successfully: {task.name} ({task.task_id})")
            
        except Exception as e:
            task.last_error = str(e)
            task._consecutive_failures += 1
            execution.status = "failed"
            execution.error = str(e)
            
            # 检查是否超过最大连续失败次数
            if task._consecutive_failures >= task.max_consecutive_failures:
                logger.warning(f"Task exceeded max failures: {task.name} ({task.task_id})")
                task.enabled = False
            
            logger.error(f"Task execution failed: {task.name} ({task.task_id}) - {e}")
        
        finally:
            execution.end_time = datetime.now()
            self.execution_history.append(execution)
            task.last_run_time = execution.end_time
        
        return execution
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        logger.info("Scheduler loop started")
        
        while self.state == SchedulerState.RUNNING:
            now = datetime.now()
            
            # 检查所有启用的任务
            for task_id, task in list(self.tasks.items()):
                if not task.enabled:
                    continue
                
                # 检查依赖
                if not self._check_dependencies(task):
                    continue
                
                # 检查是否应该执行
                should_run = False
                
                if task.cron_expression or task.interval_seconds:
                    if task.next_run_time and now >= task.next_run_time:
                        should_run = True
                elif task_id not in self._completed_tasks:
                    # 一次性任务，没有执行过的
                    should_run = True
                
                if should_run:
                    # 添加到执行队列（考虑优先级）
                    await self.task_queue.put((-task.priority.value, task))
                    
                    # 更新下次执行时间
                    if task.interval_seconds:
                        task.next_run_time = now + timedelta(seconds=task.interval_seconds)
                    elif task.cron_expression:
                        task.next_run_time = self._get_next_cron_time(task.cron_expression)
                    else:
                        # 一次性任务，执行后标记为完成
                        task.next_run_time = None
            
            # 执行队列中的任务
            while not self.task_queue.empty():
                try:
                    priority, task = await asyncio.wait_for(
                        self.task_queue.get(), 
                        timeout=1.0
                    )
                    
                    # 检查任务是否已经在运行
                    if task.task_id in self._running_tasks:
                        continue
                    
                    # 创建执行任务
                    self._running_tasks[task.task_id] = asyncio.create_task(
                        self._execute_task(task)
                    )
                    
                    # 设置回调清理运行任务
                    def cleanup(task_id):
                        def callback(f):
                            self._running_tasks.pop(task_id, None)
                            if task_id not in task.dependencies:
                                # 如果没有其他任务依赖它，添加到已完成
                                self._completed_tasks.add(task_id)
                        return callback
                    
                    self._running_tasks[task.task_id].add_done_callback(
                        cleanup(task.task_id)
                    )
                    
                except asyncio.TimeoutError:
                    break
            
            # 短暂休眠
            await asyncio.sleep(0.1)
        
        logger.info("Scheduler loop stopped")
    
    async def start(self):
        """启动调度器"""
        if self.state == SchedulerState.RUNNING:
            logger.warning("Scheduler is already running")
            return
        
        self.state = SchedulerState.RUNNING
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self):
        """停止调度器"""
        self.state = SchedulerState.STOPPED
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # 等待所有运行中的任务完成
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        logger.info("Scheduler stopped")
    
    async def pause(self):
        """暂停调度器"""
        if self.state == SchedulerState.RUNNING:
            self.state = SchedulerState.PAUSED
            logger.info("Scheduler paused")
    
    async def resume(self):
        """恢复调度器"""
        if self.state == SchedulerState.PAUSED:
            self.state = SchedulerState.RUNNING
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("Scheduler resumed")
    
    def run_now(self, task_id: str) -> bool:
        """
        立即执行任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        task = self.tasks.get(task_id)
        if task:
            # 设置下次执行时间为现在
            task.next_run_time = datetime.now()
            task.enabled = True
            return True
        return False
    
    async def execute_task_chain(self, task_ids: List[str]) -> List[TaskExecution]:
        """
        按顺序执行任务链
        
        Args:
            task_ids: 任务ID列表
            
        Returns:
            执行结果列表
        """
        results = []
        
        for task_id in task_ids:
            task = self.tasks.get(task_id)
            if task:
                execution = await self._execute_task(task)
                results.append(execution)
                
                if execution.status == "failed":
                    logger.warning(f"Task chain stopped due to failure: {task_id}")
                    break
                
                self._completed_tasks.add(task_id)
        
        return results
    
    def get_next_scheduled_time(self, task_id: str) -> Optional[datetime]:
        """获取任务下次执行时间"""
        task = self.tasks.get(task_id)
        return task.next_run_time if task else None
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        total = len(self.tasks)
        enabled = sum(1 for t in self.tasks.values() if t.enabled)
        running = len(self._running_tasks)
        completed = len(self._completed_tasks)
        
        return {
            "total_tasks": total,
            "enabled_tasks": enabled,
            "disabled_tasks": total - enabled,
            "running_tasks": running,
            "completed_tasks": completed,
            "state": self.state.value
        }
    
    def get_execution_history(self, limit: int = 100) -> List[TaskExecution]:
        """获取执行历史"""
        return list(self.execution_history)[-limit:]
    
    def add_callback(self, event: str, callback: Callable):
        """添加事件回调"""
        self._callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """触发事件回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# 便捷函数
def create_task_scheduler(timezone: str = "UTC") -> TaskScheduler:
    """创建任务调度器实例"""
    return TaskScheduler(timezone=timezone)
