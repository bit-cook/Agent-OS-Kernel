# -*- coding: utf-8 -*-
"""
State Management - 状态管理

支持：
1. Agent 状态追踪
2. 状态持久化
3. 状态恢复
4. 状态转换历史
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import json
import copy

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent 状态"""
    CREATED = "created"        # 创建
    PENDING = "pending"        # 等待
    RUNNING = "running"        # 运行
    WAITING = "waiting"        # 等待输入
    THINKING = "thinking"      # 思考中
    ACTING = "acting"         # 执行中
    COMPLETED = "completed"    # 完成
    FAILED = "failed"         # 失败
    STOPPED = "stopped"       # 停止
    SUSPENDED = "suspended"   # 暂停


@dataclass
class StateTransition:
    """状态转换"""
    from_state: AgentState
    to_state: AgentState
    timestamp: datetime
    reason: str
    data: Dict = field(default_factory=dict)


@dataclass
class AgentStateRecord:
    """Agent 状态记录"""
    agent_id: str
    current_state: AgentState
    created_at: datetime
    updated_at: datetime
    transitions: List[StateTransition] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()
        self.updated_at = self.created_at


class StateManager:
    """
    状态管理器
    
    功能：
    1. 状态追踪
    2. 状态转换
    3. 状态持久化
    4. 状态恢复
    """
    
    def __init__(self, storage=None):
        self._states: Dict[str, AgentStateRecord] = {}
        self._storage = storage
        self._lock = asyncio.Lock()
    
    async def create_agent(
        self,
        agent_id: str,
        initial_state: AgentState = AgentState.CREATED,
        metadata: Dict = None
    ) -> AgentStateRecord:
        """创建 Agent 状态"""
        async with self._lock:
            record = AgentStateRecord(
                agent_id=agent_id,
                current_state=initial_state,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata=metadata or {}
            )
            self._states[agent_id] = record
            
            if self._storage:
                await self._save_state(record)
            
            logger.info(f"Agent state created: {agent_id} -> {initial_state.value}")
            return record
    
    async def transition(
        self,
        agent_id: str,
        to_state: AgentState,
        reason: str = "",
        data: Dict = None
    ) -> bool:
        """状态转换"""
        async with self._lock:
            if agent_id not in self._states:
                logger.warning(f"Agent not found: {agent_id}")
                return False
            
            record = self._states[agent_id]
            from_state = record.current_state
            
            # 创建转换记录
            transition = StateTransition(
                from_state=from_state,
                to_state=to_state,
                timestamp=datetime.now(),
                reason=reason,
                data=data or {}
            )
            
            record.transitions.append(transition)
            record.current_state = to_state
            record.updated_at = datetime.now()
            
            if self._storage:
                await self._save_state(record)
            
            logger.info(
                f"State transition: {agent_id} "
                f"{from_state.value} -> {to_state.value}"
            )
            
            return True
    
    async def get_state(self, agent_id: str) -> Optional[AgentStateRecord]:
        """获取状态"""
        return self._states.get(agent_id)
    
    async def get_all_states(self) -> List[AgentStateRecord]:
        """获取所有状态"""
        return list(self._states.values())
    
    async def get_states_by_state(
        self,
        state: AgentState
    ) -> List[AgentStateRecord]:
        """按状态筛选"""
        return [
            r for r in self._states.values()
            if r.current_state == state
        ]
    
    async def get_transitions(
        self,
        agent_id: str,
        limit: int = 100
    ) -> List[StateTransition]:
        """获取转换历史"""
        record = self._states.get(agent_id)
        if record:
            return record.transitions[-limit:]
        return []
    
    async def checkpoint(self, agent_id: str) -> Dict:
        """创建检查点"""
        record = self._states.get(agent_id)
        if record:
            return {
                "agent_id": record.agent_id,
                "state": record.current_state.value,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
                "transitions": [
                    {
                        "from": t.from_state.value,
                        "to": t.to_state.value,
                        "time": t.timestamp.isoformat(),
                        "reason": t.reason
                    }
                    for t in record.transitions
                ],
                "metadata": record.metadata
            }
        return None
    
    async def restore(self, checkpoint: Dict) -> bool:
        """从检查点恢复"""
        try:
            record = AgentStateRecord(
                agent_id=checkpoint["agent_id"],
                current_state=AgentState(checkpoint["state"]),
                created_at=datetime.fromisoformat(checkpoint["created_at"]),
                updated_at=datetime.fromisoformat(checkpoint["updated_at"]),
                metadata=checkpoint.get("metadata", {})
            )
            
            record.transitions = [
                StateTransition(
                    from_state=AgentState(t["from"]),
                    to_state=AgentState(t["to"]),
                    timestamp=datetime.fromisoformat(t["time"]),
                    reason=t["reason"]
                )
                for t in checkpoint.get("transitions", [])
            ]
            
            self._states[record.agent_id] = record
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    async def _save_state(self, record: AgentStateRecord):
        """保存状态到存储"""
        if self._storage:
            checkpoint = await self.checkpoint(record.agent_id)
            await self._storage.save_agent_state(record.agent_id, checkpoint)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        states = {}
        for state in AgentState:
            states[state.value] = len([
                r for r in self._states.values()
                if r.current_state == state
            ])
        
        return {
            "total_agents": len(self._states),
            "by_state": states,
            "total_transitions": sum(
                len(r.transitions)
                for r in self._states.values()
            )
        }


# 便捷函数
def create_state_manager(storage=None) -> StateManager:
    """创建状态管理器"""
    return StateManager(storage)
