# -*- coding: utf-8 -*-
"""Workflow Engine - 工作流引擎

基于有向无环图 (DAG) 的工作流编排引擎。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(Enum):
    """工作流状态"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowNode:
    """工作流节点"""
    node_id: str
    name: str
    task: Callable
    dependencies: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def can_execute(self, completed_nodes: set) -> bool:
        """检查是否可以执行"""
        return all(dep in completed_nodes for dep in self.dependencies)


@dataclass
class Workflow:
    """工作流定义"""
    workflow_id: str
    name: str
    description: str = ""
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    entry_point: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    context: Dict = field(default_factory=dict)
    
    def add_node(self, node: WorkflowNode):
        """添加节点"""
        self.nodes[node.node_id] = node
        if node.dependencies:
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    self.nodes[dep_id] = WorkflowNode(
                        node_id=dep_id,
                        name=f"Node-{dep_id}",
                        task=lambda x: x
                    )
    
    def get_executable_nodes(self, completed: set) -> List[WorkflowNode]:
        """获取可执行的节点"""
        return [
            node for node in self.nodes.values()
            if node.status == NodeStatus.PENDING and node.can_execute(completed)
        ]


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(
        self,
        max_concurrent: int = 10,
        retry_delay: float = 1.0
    ):
        """
        初始化工作流引擎
        
        Args:
            max_concurrent: 最大并发数
            retry_delay: 重试延迟（秒）
        """
        self.max_concurrent = max_concurrent
        self.retry_delay = retry_delay
        
        self._workflows: Dict[str, Workflow] = {}
        self._running: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        
        logger.info(f"WorkflowEngine initialized: max_concurrent={max_concurrent}")
    
    async def create_workflow(
        self,
        name: str,
        description: str = ""
    ) -> Workflow:
        """创建工作流"""
        workflow = Workflow(
            workflow_id=str(uuid.uuid4()),
            name=name,
            description=description
        )
        
        async with self._lock:
            self._workflows[workflow.workflow_id] = workflow
        
        logger.info(f"Created workflow: {workflow.workflow_id}")
        return workflow
    
    async def add_task(
        self,
        workflow: Workflow,
        task_id: str,
        task: Callable,
        dependencies: List[str] = None,
        max_retries: int = 3
    ):
        """添加任务节点"""
        node = WorkflowNode(
            node_id=task_id,
            name=task_id,
            task=task,
            dependencies=dependencies or [],
            max_retries=max_retries
        )
        
        workflow.add_node(node)
        logger.debug(f"Added task: {task_id}")
    
    async def execute(
        self,
        workflow: Workflow,
        context: Dict = None
    ) -> Dict:
        """
        执行工作流
        
        Args:
            workflow: 工作流定义
            context: 初始上下文
            
        Returns:
            执行结果
        """
        workflow.context.update(context or {})
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)
        
        completed = set()
        failed = set()
        pending = {
            node_id: node
            for node_id, node in workflow.nodes.items()
            if not node.dependencies
        }
        
        active_tasks = []
        
        logger.info(f"Starting workflow: {workflow.name}")
        
        while pending or active_tasks:
            # 启动新任务
            while pending and len(active_tasks) < self.max_concurrent:
                node_id, node = pending.popitem()
                node.status = NodeStatus.RUNNING
                node.started_at = datetime.now(timezone.utc)
                
                task = asyncio.create_task(
                    self._execute_node(workflow, node, completed, failed)
                )
                active_tasks.append((node_id, task))
            
            # 等待完成
            if active_tasks:
                done, active_tasks = await asyncio.wait(
                    [t for _, t in active_tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for node_id, task in done:
                    try:
                        result = task.result()
                        workflow.nodes[node_id].result = result
                        workflow.nodes[node_id].status = NodeStatus.COMPLETED
                        workflow.nodes[node_id].finished_at = datetime.now(timezone.utc)
                        completed.add(node_id)
                        
                        # 检查依赖此节点的新任务
                        for nid, n in workflow.nodes.items():
                            if n.status == NodeStatus.PENDING and nid not in pending:
                                if n.can_execute(completed):
                                    pending[nid] = n
                    
                    except Exception as e:
                        workflow.nodes[node_id].error = str(e)
                        workflow.nodes[node_id].status = NodeStatus.FAILED
                        failed.add(node_id)
                        logger.error(f"Task {node_id} failed: {e}")
        
        workflow.status = (
            WorkflowStatus.COMPLETED if not failed
            else WorkflowStatus.FAILED
        )
        workflow.finished_at = datetime.now(timezone.utc)
        
        logger.info(f"Workflow {workflow.name} completed: {workflow.status}")
        
        return {
            "status": workflow.status,
            "completed": list(completed),
            "failed": list(failed),
            "duration": (workflow.finished_at - workflow.started_at).total_seconds()
        }
    
    async def _execute_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        completed: set,
        failed: set
    ) -> Any:
        """执行单个节点"""
        try:
            # 收集依赖结果
            deps_results = {}
            for dep_id in node.dependencies:
                deps_results[dep_id] = workflow.nodes[dep_id].result
            
            # 执行任务
            if asyncio.iscoroutinefunction(node.task):
                result = await node.task(deps_results, workflow.context)
            else:
                result = node.task(deps_results, workflow.context)
            
            return result
            
        except Exception as e:
            if node.retry_count < node.max_retries:
                node.retry_count += 1
                await asyncio.sleep(self.retry_delay * node.retry_count)
                return await self._execute_node(workflow, node, completed, failed)
            raise
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict]:
        """列出所有工作流"""
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "status": w.status.value,
                "created_at": w.created_at.isoformat(),
                "started_at": w.started_at.isoformat() if w.started_at else None
            }
            for w in self._workflows.values()
        ]


# 注册到 __init__.py
