# -*- coding: utf-8 -*-
"""Workflow Agent - 工作流 Agent

支持复杂的多步骤工作流执行。
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    name: str
    description: str
    task: str
    agent_type: str = "assistant"  # assistant, researcher, coder, etc.
    depends_on: List[str] = field(default_factory=list)
    parallel_with: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300


@dataclass
class WorkflowConfig:
    """工作流配置"""
    name: str
    description: str = ""
    max_concurrent_steps: int = 3
    timeout_seconds: int = 3600
    retry_failed_steps: bool = True
    continue_on_failure: bool = False


class WorkflowAgent:
    """
    工作流 Agent
    
    支持：
    1. 线性工作流
    2. 并行工作流
    3. 条件分支
    4. 循环
    """
    
    def __init__(self, config: WorkflowConfig, llm = None):
        self.config = config
        self.llm = llm
        
        self.steps: Dict[str, WorkflowStep] = {}
        self.status: WorkflowStatus = WorkflowStatus.PENDING
        self._results: List[Dict] = []
        
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
    
    def add_step(
        self,
        step_id: str,
        name: str,
        task: str,
        agent_type: str = "assistant",
        depends_on: List[str] = None,
        parallel_with: List[str] = None
    ) -> str:
        """添加步骤"""
        step = WorkflowStep(
            step_id=step_id,
            name=name,
            description="",
            task=task,
            agent_type=agent_type,
            depends_on=depends_on or [],
            parallel_with=parallel_with or []
        )
        
        self.steps[step_id] = step
        return step_id
    
    def add_linear_workflow(self, steps: List[Dict]) -> List[str]:
        """添加线性工作流"""
        step_ids = []
        
        for i, step_def in enumerate(steps):
            step_id = f"step_{i}"
            
            depends_on = []
            if i > 0:
                depends_on = [f"step_{i-1}"]
            
            self.add_step(
                step_id=step_id,
                name=step_def.get("name", f"Step {i+1}"),
                task=step_def.get("task", ""),
                agent_type=step_def.get("agent", "assistant"),
                depends_on=depends_on
            )
            
            step_ids.append(step_id)
        
        return step_ids
    
    def add_parallel_workflow(
        self,
        name: str,
        tasks: List[Dict],
        max_concurrent: int = None
    ) -> List[str]:
        """添加并行工作流"""
        step_ids = []
        
        for i, task_def in enumerate(tasks):
            step_id = f"{name}_step_{i}"
            
            self.add_step(
                step_id=step_id,
                name=task_def.get("name", f"Task {i+1}"),
                task=task_def.get("task", ""),
                agent_type=task_def.get("agent", "assistant"),
                parallel_with=[f"{name}_step_{j}" for j in range(len(tasks)) if j != i]
            )
            
            step_ids.append(step_id)
        
        return step_ids
    
    def add_conditional_workflow(
        self,
        condition_step_id: str,
        if_steps: List[Dict],
        else_steps: List[Dict]
    ):
        """添加条件工作流"""
        # 添加条件步骤
        self.add_step(
            step_id=condition_step_id,
            name="条件判断",
            task="判断是否满足条件",
            agent_type="assistant"
        )
        
        # 添加 IF 分支
        for i, step_def in enumerate(if_steps):
            self.add_step(
                step_id=f"if_{i}",
                name=step_def.get("name", f"If Step {i+1}"),
                task=step_def.get("task", ""),
                agent_type=step_def.get("agent", "assistant"),
                depends_on=[condition_step_id]
            )
        
        # 添加 ELSE 分支
        for i, step_def in enumerate(else_steps):
            self.add_step(
                step_id=f"else_{i}",
                name=step_def.get("name", f"Else Step {i+1}"),
                task=step_def.get("task", ""),
                agent_type=step_def.get("agent", "assistant"),
                depends_on=[condition_step_id]
            )
    
    async def run(self) -> Dict[str, Any]:
        """执行工作流"""
        self.status = WorkflowStatus.RUNNING
        self._start_time = datetime.now()
        
        ready_steps = []
        running_tasks = []
        completed_steps = set()
        
        # 找到所有没有依赖的步骤
        for step_id, step in self.steps.items():
            if not step.depends_on:
                ready_steps.append(step_id)
        
        logger.info(f"Starting workflow: {self.config.name}")
        logger.info(f"Initial ready steps: {ready_steps}")
        
        try:
            while len(completed_steps) < len(self.steps):
                # 启动新任务
                while len(running_tasks) < self.config.max_concurrent_steps and ready_steps:
                    step_id = ready_steps.pop(0)
                    step = self.steps[step_id]
                    
                    # 检查依赖是否都完成
                    if not all(d in completed_steps for d in step.depends_on):
                        ready_steps.append(step_id)
                        continue
                    
                    # 启动任务
                    task = asyncio.create_task(
                        self._execute_step(step)
                    )
                    running_tasks.append((step_id, task))
                
                # 等待完成
                if running_tasks:
                    done, running_tasks = await asyncio.wait(
                        [t for _, t in running_tasks],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for step_id, task in done:
                        result = task.result()
                        step = self.steps[step_id]
                        
                        if result["success"]:
                            step.status = StepStatus.COMPLETED
                            completed_steps.add(step_id)
                            
                            # 检查是否有并行步骤可以启动
                            for pid, pstep in self.steps.items():
                                if pstep.status == StepStatus.PENDING:
                                    deps_done = all(
                                        d in completed_steps
                                        for d in pstep.depends_on
                                    )
                                    
                                    if deps_done:
                                        ready_steps.append(pid)
                        else:
                            if self.config.continue_on_failure:
                                step.status = StepStatus.FAILED
                                completed_steps.add(step_id)
                            else:
                                step.status = StepStatus.FAILED
                                return {
                                    "success": False,
                                    "failed_step": step_id,
                                    "error": result.get("error")
                                }
            
            self.status = WorkflowStatus.COMPLETED
            
        except Exception as e:
            self.status = WorkflowStatus.FAILED
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            self._end_time = datetime.now()
        
        return self._generate_result()
    
    async def _execute_step(self, step: WorkflowStep) -> Dict[str, Any]:
        """执行单个步骤"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        
        try:
            logger.info(f"Executing step: {step.name}")
            
            # 模拟步骤执行
            await asyncio.sleep(0.5)
            
            # 生成结果
            result = {
                "success": True,
                "step_id": step.step_id,
                "name": step.name,
                "result": f"步骤 {step.name} 执行完成",
                "duration": (datetime.now() - step.started_at).total_seconds()
            }
            
            step.result = result
            step.completed_at = datetime.now()
            step.status = StepStatus.COMPLETED
            
            return result
            
        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            
            return {
                "success": False,
                "step_id": step.step_id,
                "error": str(e)
            }
    
    def _generate_result(self) -> Dict[str, Any]:
        """生成结果"""
        completed = sum(1 for s in self.steps.values() if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in self.steps.values() if s.status == StepStatus.FAILED)
        
        duration = None
        if self._start_time and self._end_time:
            duration = (self._end_time - self._start_time).total_seconds()
        
        return {
            "success": failed == 0,
            "workflow": self.config.name,
            "total_steps": len(self.steps),
            "completed": completed,
            "failed": failed,
            "duration_seconds": duration,
            "results": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "status": s.status.value,
                    "result": s.result
                }
                for s in self.steps.values()
            ]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "name": self.config.name,
            "status": self.status.value,
            "total_steps": len(self.steps),
            "completed_steps": sum(
                1 for s in self.steps.values()
                if s.status == StepStatus.COMPLETED
            ),
            "failed_steps": sum(
                1 for s in self.steps.values()
                if s.status == StepStatus.FAILED
            ),
            "progress": f"{sum(1 for s in self.steps.values() if s.status in [StepStatus.COMPLETED, StepStatus.RUNNING])}/{len(self.steps)}"
        }
    
    def visualize(self) -> str:
        """可视化工作流"""
        lines = [f"Workflow: {self.config.name}\n"]
        
        for step_id, step in self.steps.items():
            status_icon = {
                StepStatus.PENDING: "⏳",
                StepStatus.RUNNING: "🔄",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️"
            }[step.status]
            
            deps = f" (depends: {', '.join(step.depends_on)})" if step.depends_on else ""
            
            lines.append(f"{status_icon} {step_id}: {step.name}{deps}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "config": {
                "name": self.config.name,
                "description": self.config.description,
                "max_concurrent_steps": self.config.max_concurrent_steps,
                "timeout_seconds": self.config.timeout_seconds
            },
            "steps": {
                sid: {
                    "step_id": s.step_id,
                    "name": s.name,
                    "agent_type": s.agent_type,
                    "depends_on": s.depends_on,
                    "status": s.status.value
                }
                for sid, s in self.steps.items()
            }
        }


# 便捷函数
def create_linear_workflow(
    name: str,
    steps: List[Dict],
    max_concurrent: int = 1
) -> WorkflowAgent:
    """创建线性工作流"""
    config = WorkflowConfig(
        name=name,
        max_concurrent_steps=max_concurrent
    )
    
    agent = WorkflowAgent(config)
    agent.add_linear_workflow(steps)
    
    return agent


def create_parallel_workflow(
    name: str,
    tasks: List[Dict],
    max_concurrent: int = 3
) -> WorkflowAgent:
    """创建并行工作流"""
    config = WorkflowConfig(
        name=name,
        max_concurrent_steps=max_concurrent
    )
    
    agent = WorkflowAgent(config)
    agent.add_parallel_workflow(name, tasks, max_concurrent)
    
    return agent
