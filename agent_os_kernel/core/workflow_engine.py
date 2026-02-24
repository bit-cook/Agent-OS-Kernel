# -*- coding: utf-8 -*-
"""
工作流引擎模块 - Agent-OS-Kernel

提供工作流定义、任务调度、依赖管理和错误处理功能。
支持DAG结构的工作流定义，自动处理任务依赖和执行顺序。
"""

from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(Enum):
    """工作流状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """计算任务执行时长"""
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return None


@dataclass
class TaskConfig:
    """任务配置"""
    task_id: str
    func: Callable
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    condition: Optional[Callable[[Dict[str, TaskResult]], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parallel: bool = False


class Task:
    """任务类"""
    
    def __init__(self, config: TaskConfig):
        self.task_id = config.task_id
        self.func = config.func
        self.dependencies = config.dependencies
        self.retry_count = config.retry_count
        self.retry_delay = config.retry_delay
        self.timeout = config.timeout
        self.condition = config.condition
        self.metadata = config.metadata
        self.parallel = config.parallel
        
        self.status = TaskStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.retry_attempt = 0
        self._result_obj: Optional[TaskResult] = None
    
    @property
    def result_obj(self) -> TaskResult:
        """获取任务结果对象"""
        if self._result_obj is None:
            self._result_obj = TaskResult(
                task_id=self.task_id,
                status=self.status,
                result=self.result,
                error=self.error,
                retry_count=self.retry_attempt,
                metadata=self.metadata
            )
        return self._result_obj


class Workflow:
    """工作流类 - 支持DAG结构"""
    
    def __init__(self, workflow_id: str, name: str = None):
        self.workflow_id = workflow_id
        self.name = name or workflow_id
        self.tasks: Dict[str, Task] = {}
        self.task_graph: Dict[str, Set[str]] = defaultdict(set)  # 任务ID -> 依赖任务ID
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # 任务ID -> 依赖它的任务ID
        
        self.status = WorkflowStatus.CREATED
        self.results: Dict[str, TaskResult] = {}
        self.global_result: Any = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error: Optional[str] = None
        
        self._task_completed: Dict[str, bool] = {}
    
    def add_task(self, task: Task) -> None:
        """添加任务到工作流"""
        if task.task_id in self.tasks:
            raise ValueError(f"任务 {task.task_id} 已存在")
        
        self.tasks[task.task_id] = task
        
        # 更新任务图
        for dep in task.dependencies:
            if dep not in self.tasks:
                raise ValueError(f"依赖任务 {dep} 不存在")
            self.task_graph[task.task_id].add(dep)
            self.reverse_graph[dep].add(task.task_id)
    
    def get_execution_order(self) -> List[str]:
        """获取拓扑排序后的执行顺序 (Kahn算法)"""
        in_degree: Dict[str, int] = {task_id: 0 for task_id in self.tasks}
        
        # 计算入度
        for task_id in self.tasks:
            for dep in self.task_graph.get(task_id, []):
                if dep in in_degree:
                    in_degree[task_id] += 1
        
        # 使用队列进行拓扑排序
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            # 更新依赖当前任务的任务入度
            for dependent in self.reverse_graph.get(current, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        if len(order) != len(self.tasks):
            raise ValueError("工作流存在循环依赖")
        
        return order
    
    def get_ready_tasks(self) -> List[str]:
        """获取当前可执行的任务"""
        ready = []
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                # 检查所有依赖是否完成
                deps = self.task_graph.get(task_id, set())
                if all(self.tasks.get(dep, None) and 
                       self.tasks[dep].status == TaskStatus.COMPLETED 
                       for dep in deps):
                    # 检查条件
                    if task.condition is None:
                        ready.append(task_id)
                    else:
                        if task.condition(self.results):
                            ready.append(task_id)
        return ready
    
    def validate(self) -> bool:
        """验证工作流DAG结构"""
        try:
            order = self.get_execution_order()
            return len(order) == len(self.tasks)
        except ValueError:
            return False
    
    def reset(self) -> None:
        """重置工作流状态"""
        self.status = WorkflowStatus.CREATED
        self.results = {}
        self.global_result = None
        self.start_time = None
        self.end_time = None
        self.error = None
        self._task_completed = {}
        
        for task in self.tasks.values():
            task.status = TaskStatus.PENDING
            task.result = None
            task.error = None
            task.retry_attempt = 0
            task._result_obj = None


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.workflows: Dict[str, Workflow] = {}
        self.running_workflows: Set[str] = set()
        
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    def create_workflow(self, workflow_id: str, name: str = None) -> Workflow:
        """创建工作流"""
        workflow = Workflow(workflow_id, name)
        self.workflows[workflow_id] = workflow
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self.workflows.get(workflow_id)
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        if workflow_id in self.running_workflows:
            return False
        return self.workflows.pop(workflow_id, None) is not None
    
    async def execute_task(self, workflow: Workflow, task_id: str, 
                          context: Dict[str, Any], 
                          task_results: Dict[str, TaskResult]) -> TaskResult:
        """执行单个任务"""
        task = workflow.tasks[task_id]
        task.status = TaskStatus.RUNNING
        
        import time
        start_time = time.time()
        
        try:
            # 准备任务输入
            task_input = {}
            for dep_id in task.dependencies:
                if dep_id in task_results:
                    task_input[dep_id] = task_results[dep_id].result
            
            # 执行任务函数
            async_func = asyncio.iscoroutinefunction(task.func)
            
            if async_func:
                if task.timeout:
                    result = await asyncio.wait_for(
                        task.func(task_input, context),
                        timeout=task.timeout
                    )
                else:
                    result = await task.func(task_input, context)
            else:
                if task.timeout:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(task.func, task_input, context),
                        timeout=task.timeout
                    )
                else:
                    result = await asyncio.to_thread(task.func, task_input, context)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.error = None
            
        except Exception as e:
            task.retry_attempt += 1
            
            if task.retry_attempt <= task.retry_count:
                task.status = TaskStatus.PENDING
                await asyncio.sleep(task.retry_delay)
                # 重新执行
                return await self.execute_task(workflow, task_id, context, task_results)
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"任务 {task_id} 执行失败: {e}")
        
        end_time = time.time()
        
        # 创建结果对象
        task_result = TaskResult(
            task_id=task_id,
            status=task.status,
            result=task.result,
            error=task.error,
            retry_count=task.retry_attempt,
            start_time=start_time,
            end_time=end_time,
            metadata=task.metadata
        )
        
        task._result_obj = task_result
        workflow.results[task_id] = task_result
        
        return task_result
    
    async def run(self, workflow_id: str, context: Dict[str, Any] = None) -> Workflow:
        """运行工作流"""
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        if not workflow.validate():
            raise ValueError("工作流验证失败")
        
        workflow.reset()
        workflow.status = WorkflowStatus.RUNNING
        workflow.start_time = None
        self.running_workflows.add(workflow_id)
        
        import time
        workflow.start_time = time.time()
        context = context or {}
        
        try:
            # 获取执行顺序
            execution_order = workflow.get_execution_order()
            
            # 使用队列管理任务执行
            task_queue = set(execution_order)
            task_results: Dict[str, TaskResult] = {}
            completed = set()
            
            while task_queue:
                # 查找可执行的任务
                ready_tasks = []
                for task_id in task_queue:
                    task = workflow.tasks[task_id]
                    if task.status == TaskStatus.PENDING:
                        deps = workflow.task_graph.get(task_id, set())
                        if all(dep in completed for dep in deps):
                            if task.condition is None:
                                ready_tasks.append(task_id)
                            else:
                                if task.condition(task_results):
                                    ready_tasks.append(task_id)
                
                if not ready_tasks and len(completed) < len(execution_order):
                    # 检查是否有任务可以并行执行
                    parallel_tasks = [
                        t for t in task_queue 
                        if workflow.tasks[t].status == TaskStatus.PENDING 
                        and workflow.tasks[t].parallel
                    ]
                    if parallel_tasks:
                        ready_tasks = parallel_tasks
                
                if not ready_tasks:
                    # 等待任意任务完成
                    await asyncio.sleep(0.1)
                    continue
                
                # 执行准备好的任务
                async with self._semaphore:
                    for task_id in ready_tasks:
                        task_queue.remove(task_id)
                        
                        # 检查是否应该跳过
                        task = workflow.tasks[task_id]
                        if task.condition and not task.condition(task_results):
                            task.status = TaskStatus.SKIPPED
                            workflow.results[task_id] = TaskResult(
                                task_id=task_id,
                                status=TaskStatus.SKIPPED
                            )
                            completed.add(task_id)
                            continue
                        
                        # 执行任务
                        result = await self.execute_task(workflow, task_id, context, task_results)
                        task_results[task_id] = result
                        
                        if result.status == TaskStatus.COMPLETED:
                            completed.add(task_id)
                        else:
                            # 如果有任务失败，检查是否需要取消后续任务
                            if task.error_handling == "fail_all":
                                workflow.status = WorkflowStatus.FAILED
                                workflow.error = f"任务 {task_id} 失败"
                                self.running_workflows.discard(workflow_id)
                                workflow.end_time = time.time()
                                return workflow
            
            # 检查工作流是否成功完成
            failed_tasks = [
                tid for tid, result in workflow.results.items()
                if result.status == TaskStatus.FAILED
            ]
            
            if failed_tasks:
                workflow.status = WorkflowStatus.FAILED
                workflow.error = f"以下任务失败: {failed_tasks}"
            else:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.global_result = {
                    task_id: result.result 
                    for task_id, result in workflow.results.items()
                }
        
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)
            logger.exception("工作流执行失败")
        
        finally:
            self.running_workflows.discard(workflow_id)
            workflow.end_time = time.time()
        
        return workflow
    
    def run_sync(self, workflow_id: str, context: Dict[str, Any] = None) -> Workflow:
        """同步运行工作流"""
        return asyncio.run(self.run(workflow_id, context))
    
    def get_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            return None
        
        completed = sum(1 for r in workflow.results.values() 
                       if r.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED))
        failed = sum(1 for r in workflow.results.values() 
                    if r.status == TaskStatus.FAILED)
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "progress": f"{completed}/{len(workflow.tasks)}",
            "completed": completed,
            "failed": failed,
            "total": len(workflow.tasks)
        }


# 便捷函数
def create_workflow_engine(max_concurrent: int = 10) -> WorkflowEngine:
    """创建工作流引擎实例"""
    return WorkflowEngine(max_concurrent)
