# -*- coding: utf-8 -*-
"""Distributed Scheduler - 分布式调度器

支持跨节点的 Agent 调度和负载均衡。
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class SchedulerStrategy(Enum):
    """调度策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    DATA_LOCALITY = "data_locality"
    COST_OPTIMIZED = "cost_optimized"


@dataclass
class NodeStatus:
    """节点状态"""
    node_id: str
    hostname: str
    port: int
    load: float = 0.0
    agents_count: int = 0
    available: bool = True
    last_heartbeat: datetime = field(default_factory=datetime.now)
    capabilities: List[str] = field(default_factory=list)
    resources: Dict[str, float] = field(default_factory=dict)


@dataclass
class DistributedTask:
    """分布式任务"""
    task_id: str
    agent_config: Dict[str, Any]
    priority: int = 0
    scheduling_strategy: SchedulerStrategy = SchedulerStrategy.LEAST_LOADED
    preferred_nodes: List[str] = field(default_factory=list)
    data_requirements: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class DistributedScheduler:
    """
    分布式调度器
    
    功能：
    1. 节点注册和发现
    2. 任务分发
    3. 负载均衡
    4. 故障转移
    """
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 8001):
        self.node_id = node_id
        self.host = host
        self.port = port
        
        self._nodes: Dict[str, NodeStatus] = {}
        self._tasks: Dict[str, DistributedTask] = {}
        self._running: bool = False
        self._heartbeat_interval: int = 5  # 秒
        self._lock = asyncio.Lock()
        
        # 策略
        self._default_strategy = SchedulerStrategy.LEAST_LOADED
    
    async def start(self):
        """启动调度器"""
        self._running = True
        logger.info(f"Distributed scheduler started: {self.node_id}@{self.host}:{self.port}")
        
        # 启动心跳监控
        asyncio.create_task(self._heartbeat_loop())
    
    async def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("Distributed scheduler stopped")
    
    async def register_node(
        self,
        node_id: str,
        hostname: str,
        port: int,
        capabilities: List[str] = None,
        resources: Dict[str, float] = None
    ) -> bool:
        """注册节点"""
        async with self._lock:
            if node_id in self._nodes:
                logger.warning(f"Node already registered: {node_id}")
                return False
            
            node = NodeStatus(
                node_id=node_id,
                hostname=hostname,
                port=port,
                capabilities=capabilities or [],
                resources=resources or {}
            )
            
            self._nodes[node_id] = node
            logger.info(f"Node registered: {node_id}")
            
            return True
    
    async def unregister_node(self, node_id: str) -> bool:
        """注销节点"""
        async with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                logger.info(f"Node unregistered: {node_id}")
                return True
            return False
    
    async def submit_task(
        self,
        task_id: str,
        agent_config: Dict[str, Any],
        priority: int = 0,
        preferred_nodes: List[str] = None,
        data_requirements: Dict[str, str] = None
    ) -> str:
        """提交任务"""
        task = DistributedTask(
            task_id=task_id,
            agent_config=agent_config,
            priority=priority,
            preferred_nodes=preferred_nodes or [],
            data_requirements=data_requirements or {}
        )
        
        async with self._lock:
            self._tasks[task_id] = task
        
        logger.info(f"Task submitted: {task_id}")
        
        # 异步调度
        asyncio.create_task(self._schedule_task(task))
        
        return task_id
    
    async def _schedule_task(self, task: DistributedTask):
        """调度任务"""
        # 选择最佳节点
        best_node = await self._select_node(task)
        
        if best_node:
            await self._dispatch_task(best_node, task)
        else:
            logger.warning(f"No suitable node for task: {task.task_id}")
    
    async def _select_node(self, task: DistributedTask) -> Optional[NodeStatus]:
        """选择最佳节点"""
        available = [n for n in self._nodes.values() if n.available]
        
        if not available:
            return None
        
        strategy = task.scheduling_strategy or self._default_strategy
        
        if strategy == SchedulerStrategy.LEAST_LOADED:
            return min(available, key=lambda n: n.load)
        
        elif strategy == SchedulerStrategy.ROUND_ROBIN:
            return available[0]
        
        elif strategy == SchedulerStrategy.DATA_LOCALITY:
            # 优先选择有数据的节点
            for node in sorted(available, key=lambda n: n.load):
                if any(cap in task.data_requirements.values() for cap in node.capabilities):
                    return node
            return available[0]
        
        elif strategy == SchedulerStrategy.COST_OPTIMIZED:
            # 选择资源最便宜的节点
            return min(available, key=lambda n: n.resources.get("cost_per_hour", float('inf')))
        
        return available[0]
    
    async def _dispatch_task(self, node: NodeStatus, task: DistributedTask):
        """分发任务到节点"""
        logger.info(f"Dispatching task {task.task_id} to node {node.node_id}")
        
        # 模拟任务分发
        async with self._lock:
            if task.task_id in self._tasks:
                del self._tasks[task.task_id]
            
            node.agents_count += 1
            node.load = min(1.0, node.agents_count / 10)  # 简单负载计算
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """获取集群状态"""
        async with self._lock:
            nodes = [
                {
                    "node_id": n.node_id,
                    "hostname": n.hostname,
                    "port": n.port,
                    "load": n.load,
                    "agents_count": n.agents_count,
                    "available": n.available,
                    "capabilities": n.capabilities
                }
                for n in self._nodes.values()
            ]
            
            total_agents = sum(n.agents_count for n in self._nodes.values())
            avg_load = sum(n.load for n in self._nodes.values()) / max(1, len(self._nodes))
        
        return {
            "scheduler_id": self.node_id,
            "total_nodes": len(self._nodes),
            "total_agents": total_agents,
            "avg_load": avg_load,
            "pending_tasks": len(self._tasks),
            "nodes": nodes
        }
    
    async def _heartbeat_loop(self):
        """心跳监控循环"""
        while self._running:
            try:
                async with self._lock:
                    now = datetime.now()
                    
                    # 检查节点心跳
                    expired = []
                    for node_id, node in self._nodes.items():
                        if (now - node.last_heartbeat) > timedelta(seconds=self._heartbeat_interval * 3):
                            expired.append(node_id)
                    
                    for node_id in expired:
                        await self.unregister_node(node_id)
                        logger.warning(f"Node heartbeat expired: {node_id}")
                
                await asyncio.sleep(self._heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(1)
    
    async def receive_heartbeat(self, node_id: str, load: float, agents_count: int):
        """接收心跳"""
        async with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].load = load
                self._nodes[node_id].agents_count = agents_count
                self._nodes[node_id].last_heartbeat = datetime.now()


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, scheduler: DistributedScheduler):
        self.scheduler = scheduler
    
    async def get_best_node(self, requirements: Dict[str, Any] = None) -> Optional[NodeStatus]:
        """获取最佳节点"""
        available = [n for n in self.scheduler._nodes.values() if n.available]
        
        if not available:
            return None
        
        # 考虑资源需求
        if requirements:
            for node in sorted(available, key=lambda n: n.load):
                if all(
                    node.resources.get(k, 0) >= v
                    for k, v in requirements.items()
                ):
                    return node
        
        # 返回负载最低的
        return min(available, key=lambda n: n.load)
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        results = {}
        
        for node_id in self.scheduler._nodes:
            results[node_id] = True  # 简化
        
        return results


# 便捷函数
def create_distributed_scheduler(
    node_id: str,
    host: str = "localhost",
    port: int = 8001
) -> DistributedScheduler:
    """创建分布式调度器"""
    return DistributedScheduler(node_id, host, port)
