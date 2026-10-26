"""
Distributed Scheduler - 分布式调度器

跨节点任务调度、负载均衡、故障转移
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
from enum import Enum
import asyncio
import random
import logging


class SchedulerState(Enum):
    """调度器状态"""
    IDLE = "idle"
    SCHEDULING = "scheduling"
    BALANCING = "balancing"


@dataclass
class NodeInfo:
    """节点信息"""
    node_id: str
    hostname: str
    port: int
    cpu_count: int
    memory_mb: int
    gpu_count: int
    status: str = "online"
    load: float = 0.0


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    name: str
    priority: int
    cpu_needed: float
    memory_mb: int
    gpu_needed: int
    node_id: Optional[str] = None
    status: str = "pending"


class DistributedScheduler:
    """分布式调度器"""
    
    def __init__(self, scheduler_id: str):
        self.scheduler_id = scheduler_id
        self.state = SchedulerState.IDLE
        self._nodes: Dict[str, NodeInfo] = {}
        self._tasks: Dict[str, TaskInfo] = {}
        self._task_queue: asyncio.PriorityQueue = None
        self._callbacks: List[Callable] = []
        self._failover_enabled = True
        
        self._task_queue = asyncio.PriorityQueue()
    
    def register_node(self, node: NodeInfo):
        """注册节点"""
        self._nodes[node.node_id] = node
    
    def unregister_node(self, node_id: str):
        """注销节点"""
        if node_id in self._nodes:
            del self._nodes[node_id]
    
    async def submit_task(self, task: TaskInfo):
        """提交任务"""
        self._tasks[task.task_id] = task
        await self._task_queue.put((-task.priority, task.task_id))
    
    async def schedule(self):
        """调度任务"""
        self.state = SchedulerState.SCHEDULING
        
        while not self._task_queue.empty():
            _, task_id = await self._task_queue.get()
            
            if task_id not in self._tasks:
                continue
            
            task = self._tasks[task_id]
            
            # 选择最佳节点
            best_node = self._select_best_node(task)
            
            if best_node:
                task.node_id = best_node
                task.status = "scheduled"
                
                # 执行调度回调
                for callback in self._callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(task, best_node)
                        else:
                            callback(task, best_node)
                    except Exception as _suppressed:
                        logging.getLogger(__name__).debug(
                            "suppressed exception: %s", _suppressed
                        )
            else:
                task.status = "pending"
                await self._task_queue.put((-task.priority, task_id))
        
        self.state = SchedulerState.IDLE
    
    def _select_best_node(self, task: TaskInfo) -> Optional[str]:
        """选择最佳节点"""
        candidates = []
        
        for node_id, node in self._nodes.items():
            if node.status != "online":
                continue
            
            # 检查资源
            if node.cpu_count >= task.cpu_needed:
                if node.memory_mb >= task.memory_mb:
                    if node.gpu_count >= task.gpu_needed:
                        # 计算负载得分
                        load_score = 1.0 - node.load
                        candidates.append((node_id, load_score))
        
        if not candidates:
            return None
        
        # 选择负载最低的节点
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    async def rebalance(self):
        """负载均衡"""
        self.state = SchedulerState.BALANCING
        
        # 计算平均负载
        if not self._nodes:
            self.state = SchedulerState.IDLE
            return
        
        avg_load = sum(n.load for n in self._nodes.values()) / len(self._nodes)
        
        # 迁移高负载节点的任务到低负载节点
        for node_id, node in self._nodes.items():
            if node.load > avg_load * 1.5:
                # 尝试迁移任务
                for task_id, task in list(self._tasks.items()):
                    if task.node_id == node_id:
                        # 找低负载节点
                        for target_id, target in self._nodes.items():
                            if target_id != node_id and target.load < avg_load * 0.7:
                                task.node_id = target_id
                                break
        
        self.state = SchedulerState.IDLE
    
    async def failover(self, node_id: str):
        """故障转移"""
        if not self._failover_enabled:
            return
        
        # 重新调度故障节点的任务
        for task_id, task in self._tasks.items():
            if task.node_id == node_id:
                task.status = "pending"
                task.node_id = None
                await self._task_queue.put((-task.priority, task_id))
        
        # 从节点列表移除
        self.unregister_node(node_id)
    
    def add_callback(self, callback: Callable):
        """添加回调"""
        self._callbacks.append(callback)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "scheduler_id": self.scheduler_id,
            "state": self.state.value,
            "nodes": len(self._nodes),
            "pending_tasks": self._task_queue.qsize(),
            "active_tasks": len([t for t in self._tasks.values() if t.status == "scheduled"]),
            "failover_enabled": self._failover_enabled
        }
