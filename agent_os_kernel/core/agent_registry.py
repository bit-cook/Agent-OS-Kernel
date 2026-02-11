# -*- coding: utf-8 -*-
"""Agent Registry - Agent 注册中心"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
import uuid

logger = logging.getLogger(__name__)


@dataclass
class AgentMetadata:
    agent_id: str
    name: str
    role: str
    version: str = "1.0.0"
    status: str = "active"
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)


class AgentRegistry:
    def __init__(self, heartbeat_timeout: int = 60, cleanup_interval: int = 300):
        self.heartbeat_timeout = heartbeat_timeout
        self.cleanup_interval = cleanup_interval
        self._agents: Dict[str, AgentMetadata] = {}
        self._index_by_name: Dict[str, str] = {}
        self._index_by_role: Dict[str, List[str]] = {}
        self._index_by_tag: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        self._running = False
    
    async def initialize(self):
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def shutdown(self):
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
    
    async def register(self, agent_id: str, name: str, role: str, owner: str = None, 
                      tags: List[str] = None, capabilities: List[str] = None) -> AgentMetadata:
        meta = AgentMetadata(agent_id=agent_id, name=name, role=role, owner=owner,
                            tags=tags or [], capabilities=capabilities or [])
        async with self._lock:
            self._agents[agent_id] = meta
            self._index_by_name[name] = agent_id
            self._index_by_role.setdefault(role, []).append(agent_id)
            for tag in meta.tags:
                self._index_by_tag.setdefault(tag, []).append(agent_id)
        return meta
    
    async def unregister(self, agent_id: str) -> bool:
        async with self._lock:
            if agent_id not in self._agents:
                return False
            agent = self._agents.pop(agent_id)
            self._index_by_name.pop(agent.name, None)
            if agent.role in self._index_by_role:
                self._index_by_role[agent.role].remove(agent_id)
        return True
    
    async def heartbeat(self, agent_id: str) -> bool:
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].heartbeat = datetime.now(timezone.utc)
                return True
        return False
    
    async def get(self, agent_id: str) -> Optional[AgentMetadata]:
        async with self._lock:
            return self._agents.get(agent_id)
    
    async def list_all(self) -> List[AgentMetadata]:
        async with self._lock:
            return list(self._agents.values())
    
    async def list_active(self) -> List[AgentMetadata]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.heartbeat_timeout)
        async with self._lock:
            return [a for a in self._agents.values() if a.heartbeat > cutoff]
    
    def get_stats(self) -> Dict:
        return {
            "total_agents": len(self._agents),
            "active_agents": len([a for a in self._agents.values() 
                                 if a.heartbeat > datetime.now(timezone.utc) - timedelta(seconds=self.heartbeat_timeout)])
        }
    
    async def _cleanup_loop(self):
        while self._running:
            await asyncio.sleep(self.cleanup_interval)
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(seconds=self.heartbeat_timeout * 3)
            async with self._lock:
                to_remove = [aid for aid, a in self._agents.items() if a.heartbeat < cutoff]
            for aid in to_remove:
                await self.unregister(aid)


# 全局注册中心
_registry = None

def get_agent_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
