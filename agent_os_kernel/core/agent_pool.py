# -*- coding: utf-8 -*-
"""Agent Pool - Agent 对象池

管理 Agent 实例的复用，提高性能。
"""

import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from .agent_definition import AgentDefinition

logger = logging.getLogger(__name__)


@dataclass
class PooledAgent:
    """池化 Agent"""
    agent_id: str
    definition: AgentDefinition
    is_busy: bool = False
    last_used: datetime = field(default_factory=datetime.utcnow)
    use_count: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def mark_busy(self):
        """标记为忙碌"""
        self.is_busy = True
        self.last_used = datetime.now(timezone.utc)
    
    def mark_idle(self):
        """标记为空闲"""
        self.is_busy = False
    
    def increment_use(self):
        """增加使用计数"""
        self.use_count += 1
        self.last_used = datetime.now(timezone.utc)


class AgentPool:
    """Agent 对象池"""
    
    def __init__(
        self,
        max_size: int = 10,
        idle_timeout: float = 300.0,
        cleanup_interval: float = 60.0
    ):
        """
        初始化 Agent 池
        
        Args:
            max_size: 最大池大小
            idle_timeout: 空闲超时时间（秒）
            cleanup_interval: 清理间隔（秒）
        """
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self.cleanup_interval = cleanup_interval
        
        self._agents: Dict[str, PooledAgent] = {}
        self._idle_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"AgentPool initialized: max_size={max_size}")
    
    async def initialize(self):
        """初始化池"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("AgentPool started")
    
    async def shutdown(self):
        """关闭池"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
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
        """获取 Agent"""
        deadline = asyncio.get_event_loop().time() + timeout
        
        while True:
            try:
                agent = await asyncio.wait_for(
                    self._idle_queue.get(),
                    timeout=max(0, deadline - asyncio.get_event_loop().time())
                )
                
                if agent.agent_id in self._agents:
                    agent.mark_busy()
                    return agent
                    
            except asyncio.TimeoutError:
                pass
            
            async with self._lock:
                if len(self._agents) < self.max_size:
                    agent = await self._create_agent(definition)
                    agent.mark_busy()
                    return agent
                
                if asyncio.get_event_loop().time() >= deadline:
                    raise TimeoutError("Failed to acquire agent within timeout")
    
    async def release(self, agent: PooledAgent):
        """释放 Agent"""
        async with self._lock:
            if agent.agent_id in self._agents:
                agent.mark_idle()
                await self._idle_queue.put(agent)
    
    async def remove(self, agent_id: str):
        """移除 Agent"""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
    
    async def _create_agent(self, definition: AgentDefinition) -> PooledAgent:
        """创建 Agent"""
        agent = PooledAgent(
            agent_id=str(uuid4()),
            definition=definition
        )
        
        self._agents[agent.agent_id] = agent
        await self._idle_queue.put(agent)
        
        logger.debug(f"Created agent: {agent.agent_id}")
        
        return agent
    
    async def _shutdown_agent(self, agent: PooledAgent):
        """关闭 Agent"""
        logger.debug(f"Shutdown agent: {agent.agent_id}")
    
    async def _cleanup_loop(self):
        """清理过期 Agent"""
        while self._running:
            await asyncio.sleep(self.cleanup_interval)
            
            async with self._lock:
                now = datetime.now(timezone.utc)
                expired = []
                
                for agent_id, agent in self._agents.items():
                    if not agent.is_busy:
                        idle_time = (now - agent.last_used).total_seconds()
                        if idle_time > self.idle_timeout:
                            expired.append(agent_id)
                
                for agent_id in expired:
                    del self._agents[agent_id]
                    logger.debug(f"Cleaned up expired agent: {agent_id}")
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_agents": len(self._agents),
            "idle_agents": self._idle_queue.qsize(),
            "busy_agents": len(self._agents) - self._idle_queue.qsize(),
            "max_size": self.max_size
        }
    
    def get_active_agents(self) -> list:
        """获取活跃 Agent"""
        return list(self._agents.values())
