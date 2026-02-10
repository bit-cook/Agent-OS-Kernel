# -*- coding: utf-8 -*-
"""Task Manager - 任务管理

参考 LangGraph 和 CrewAI 的 Task 设计
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
from uuid import uuid4
import asyncio
import logging

from .agent_definition import TaskDefinition, AgentDefinition
from .exceptions import TaskError, TaskTimeoutError

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task 状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"  # 等待依赖


@dataclass
class TaskExecution:
    """Task 执行记录"""
    
    task_id: str
    definition: TaskDefinition
    status: TaskStatus
    result: Optional[str] = None
    error: Optional[str] = None
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 迭代信息
    iterations: int = 0
    max_iterations: int = 10
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "definition": self.definition.to_dict(),
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "iterations": self.iterations,
            "max_iterations": self.max_iterations,
            "metadata": self.metadata,
        }


class TaskManager:
    """Task 管理器
    
    功能:
    - Task 创建和管理
    - 依赖解析
    - 执行状态追踪
    - 超时和重试
    """
    
    def __init__(self, max_workers: int = 10):
        """初始化 Task 管理器
        
        Args:
            max_workers: 最大并行执行数
        """
        self.max_workers = max_workers
        self._tasks: Dict[str, TaskExecution] = {}
        self._task_queue: List[str] = []
        self._callbacks: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        
        logger.info(f"TaskManager initialized with max_workers={max_workers}")
    
    def create_task(
        self,
        description: str,
        expected_output: str,
        agent_name: str,
        task_id: Optional[str] = None,
        priority: int = 50,
        timeout: float = 300.0,
        max_iterations: int = 10,
        depends_on: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """创建 Task
        
        Args:
            description: 任务描述
            expected_output: 预期输出
            agent_name: 执行的 Agent 名称
            task_id: Task ID (可选)
            priority: 优先级 (0-100)
            timeout: 超时时间 (秒)
            max_iterations: 最大迭代次数
            depends_on: 依赖的 Task ID 列表
            
        Returns:
            task_id: 创建的 Task ID
        """
        task_id = task_id or str(uuid4())[:8]
        
        definition = TaskDefinition(
            description=description,
            expected_output=expected_output,
            agent_name=agent_name,
            priority=priority,
            timeout=timeout,
            depends_on=depends_on or [],
        )
        
        execution = TaskExecution(
            task_id=task_id,
            definition=definition,
            status=TaskStatus.PENDING,
            max_iterations=max_iterations,
            metadata=kwargs,
        )
        
        self._tasks[task_id] = execution
        self._task_queue.append(task_id)
        
        # 按优先级排序
        self._task_queue.sort(key=lambda tid: self._tasks[tid].definition.priority)
        
        logger.info(f"Task created: {task_id} - {description[:50]}...")
        
        return task_id
    
    async def execute_task(
        self,
        task_id: str,
        agent_executor: Callable,
        context: Optional[Dict] = None
    ) -> Dict:
        """执行 Task
        
        Args:
            task_id: Task ID
            agent_executor: Agent 执行函数
            context: 上下文
            
        Returns:
            执行结果
        """
        async with self._lock:
            if task_id not in self._tasks:
                raise TaskError(f"Task not found: {task_id}")
            
            execution = self._tasks[task_id]
            
            # 检查依赖
            for dep_id in execution.definition.depends_on:
                if dep_id not in self._tasks:
                    raise TaskError(f"Dependency not found: {dep_id}")
                if self._tasks[dep_id].status != TaskStatus.COMPLETED:
                    execution.status = TaskStatus.BLOCKED
                    return {"status": "blocked", "reason": f"Waiting for {dep_id}"}
            
            # 开始执行
            execution.status = TaskStatus.IN_PROGRESS
            execution.started_at = datetime.utcnow()
            execution.iterations += 1
            
            logger.info(f"Task started: {task_id}")
            
            try:
                # 检查超时
                if execution.started_at:
                    elapsed = (datetime.utcnow() - execution.started_at).total_seconds()
                    if elapsed > execution.definition.timeout:
                        raise TaskTimeoutError(
                            f"Task timeout: {execution.definition.timeout}s"
                        )
                
                # 执行
                result = await agent_executor(
                    task=execution.definition,
                    context=context or {}
                )
                
                # 验证输出
                if execution.definition.validation_criteria:
                    if not self._validate_output(
                        result, 
                        execution.definition.validation_criteria
                    ):
                        if execution.iterations >= execution.max_iterations:
                            raise TaskError(
                                f"Max iterations reached, validation failed"
                            )
                        # 重试
                        return await self.execute_task(
                            task_id, 
                            agent_executor, 
                            context
                        )
                
                execution.status = TaskStatus.COMPLETED
                execution.result = result
                execution.completed_at = datetime.utcnow()
                
                logger.info(f"Task completed: {task_id}")
                
                return {
                    "status": "completed",
                    "task_id": task_id,
                    "result": result,
                    "duration": (execution.completed_at - execution.started_at).total_seconds()
                }
                
            except Exception as e:
                execution.status = TaskStatus.FAILED
                execution.error = str(e)
                execution.completed_at = datetime.utcnow()
                
                logger.error(f"Task failed: {task_id} - {e}")
                
                raise TaskError(f"Task execution failed: {e}")
    
    def _validate_output(
        self, 
        result: str, 
        criteria: str
    ) -> bool:
        """验证输出"""
        # 简单实现: 检查关键词
        keywords = criteria.lower().split(",")
        result_lower = result.lower()
        
        for keyword in keywords:
            if keyword.strip() and keyword.strip() not in result_lower:
                return False
        
        return True
    
    def get_task(self, task_id: str) -> Optional[TaskExecution]:
        """获取 Task"""
        return self._tasks.get(task_id)
    
    def list_tasks(
        self, 
        status: Optional[TaskStatus] = None,
        agent_name: Optional[str] = None
    ) -> List[TaskExecution]:
        """列出 Task"""
        result = list(self._tasks.values())
        
        if status:
            result = [t for t in result if t.status == status]
        
        if agent_name:
            result = [
                t for t in result 
                if t.definition.agent_name == agent_name
            ]
        
        return result
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = len(self._tasks)
        completed = len([t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED])
        failed = len([t for t in self._tasks.values() if t.status == TaskStatus.FAILED])
        
        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "in_progress": len([t for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS]),
            "pending": len([t for t in self._tasks.values() if t.status == TaskStatus.PENDING]),
            "blocked": len([t for t in self._tasks.values() if t.status == TaskStatus.BLOCKED]),
            "success_rate": completed / total if total > 0 else 0,
        }
    
    def reset(self):
        """重置所有 Task"""
        self._tasks.clear()
        self._task_queue.clear()
        logger.info("TaskManager reset")
