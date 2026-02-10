# -*- coding: utf-8 -*-
"""Agent Pool - Agent 对象池管理

用于复用 Agent 实例，提高性能。
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

from .agent_definition import AgentDefinition
from .task_manager import TaskManager, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class PooledAgent:
    """池化 Agent"""
    agent_id: str
    definition: AgentDefinition
    status: str = "idle"
    last_used: datetime = field(default_factory=datetime.utcnow)
    task_count: int = 0
    error_count: int = 0
    
    def is_idle(self) -> bool:
        return self.status == "idle"
    
    def mark_busy(self):
        self.status = "busy"
        self.last_used = datetime.utcnow()
    
    def mark_idle(self):
        self.status = "idle"
    
    def record_task(self):
        self.task_count += 1
        self.last_used = datetime.utcnow()
    
    def record_error(self):
        self.error_count += 1


class AgentPool:
    """Agent 对象池"""
    
    def __init__(
        self,
        max_size: int = 10,
        min_idle: int = 2,
        max_idle_time: int = 3600,
        cleanup_interval: int = 300
    ):
        """
        初始化 Agent 池
        
        Args:
            max_size: 池最大容量
            min_idle: 最小空闲 Agent 数
            max_idle_time: 最大空闲时间（秒）
            cleanup_interval: 清理间隔（秒）
        """
        self.max_size = max_size
        self.min_idle = min_idle
        self.max_idle_time = max_idle_time
        self.cleanup_interval = cleanup_interval
        
        self._agents: Dict[str, PooledAgent] = {}
        self._idle_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"AgentPool initialized: max_size={max_size}, min_idle={min_idle}")
    
    async def initialize(self):
        """初始化池，创建最小空闲数量的 Agent"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # 创建最小空闲 Agent
        for _ in range(self.min_idle):
            agent = await self._create_agent()
            await self._idle_queue.put(agent)
        
        logger.info(f"AgentPool initialized with {self.min_idle} idle agents")
    
    async def shutdown(self):
        """关闭池"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有 Agent
        async with self._lock:
            for agent in self._agents.values():
                await self._shutdown_agent(agent)
        
        self._agents.clear()
        logger.info("AgentPool shutdown complete")
    
    async def acquire(
        self,
        definition: AgentDefinition,
        timeout: float = 30.0
    ) -> PooledAgent:
        """
        获取一个 Agent
        
        Args:
            definition: Agent 定义
            timeout: 超时时间
            
        Returns:
            PooledAgent 实例
        """
        deadline = asyncio.get_event_loop().time() + timeout
        
        while True:
            # 尝试从空闲队列获取
            try:
                agent = await asyncio.wait_for(
                    self._idle_queue.get(),
                    timeout=max(0, deadline - asyncio.get_event_loop().time())
                )
                
                # 检查 Agent 是否仍然有效
                if agent.agent_id in self._agents:
                    agent.mark_busy()
                    return agent
                    
            except asyncio.TimeoutError:
                pass
            
            # 尝试创建新 Agent
            async with self._lock:
                if len(self._agents) < self.max_size:
                    agent = await self._create_agent(definition)
                    agent.mark_busy()
                    return agent
            
            # 队列已满，等待
            if asyncio.get_event_loop().time() >= deadline:
                raise TimeoutError("Failed to acquire agent within timeout")
    
    async def release(self, agent: PooledAgent):
        """
        释放 Agent 回池中
        
        Args:
            agent: 要释放的 PooledAgent
        """
        if agent.error_count > 5:
            # 错误太多，移除而不是放回池
            async with self._lock:
                self._agents.pop(agent.agent_id, None)
            logger.warning(f"Agent {agent.agent_id} removed due to too many errors")
            return
        
        # 检查是否超过最大空闲时间
        idle_time = (datetime.utcnow() - agent.last_used).total_seconds()
        
        async with self._lock:
            if agent.agent_id in self._agents:
                if idle_time > self.max_idle_time:
                    # 移除超时的 Agent
                    self._agents.pop(agent.agent_id, None)
                    await self._shutdown_agent(agent)
                    logger.info(f"Agent {agent.agent_id} removed due to idle timeout")
                else:
                    # 放回空闲队列
                    agent.mark_idle()
                    await self._idle_queue.put(agent)
                    logger.debug(f"Agent {agent.agent_id} returned to pool")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        idle_count = 0
        busy_count = 0
        
        for agent in self._agents.values():
            if agent.is_idle():
                idle_count += 1
            else:
                busy_count += 1
        
        return {
            "total_agents": len(self._agents),
            "idle_agents": idle_count,
            "busy_agents": busy_count,
            "queue_size": self._idle_queue.qsize(),
            "max_size": self.max_size,
            "utilization": busy_count / max(1, len(self._agents))
        }
    
    async def _create_agent(self, definition: Optional[AgentDefinition] = None) -> PooledAgent:
        """创建新 Agent"""
        agent_id = str(uuid.uuid4())
        
        pooled = PooledAgent(
            agent_id=agent_id,
            definition=definition or AgentDefinition(
                name=f"PooledAgent-{agent_id[:8]}",
                role="general",
                goal="执行任务",
                backstory="池化 Agent 实例"
            )
        )
        
        async with self._lock:
            self._agents[agent_id] = pooled
        
        logger.debug(f"Created new agent in pool: {agent_id}")
        return pooled
    
    async def _shutdown_agent(self, agent: PooledAgent):
        """关闭 Agent"""
        logger.debug(f"Shutting down agent: {agent.agent_id}")
        # 这里可以添加实际的清理逻辑
    
    async def _cleanup_loop(self):
        """清理过期 Agent"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                now = datetime.utcnow()
                to_remove = []
                
                async with self._lock:
                    for agent in self._agents.values():
                        if agent.is_idle():
                            idle_time = (now - agent.last_used).total_seconds()
                            if idle_time > self.max_idle_time:
                                to_remove.append(agent.agent_id)
                
                for agent_id in to_remove:
                    async with self._lock:
                        agent = self._agents.pop(agent_id, None)
                    if agent:
                        await self._shutdown_agent(agent)
                        logger.info(f"Cleaned up idle agent: {agent_id}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")


