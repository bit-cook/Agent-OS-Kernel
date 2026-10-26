# -*- coding: utf-8 -*-
"""Agent Migration - Agent 热迁移

支持 Agent 在不同节点间无缝迁移。
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pickle

logger = logging.getLogger(__name__)


@dataclass
class MigrationCheckpoint:
    """迁移检查点"""
    checkpoint_id: str
    agent_state: Dict[str, Any]
    context: List[Dict]
    memory: Dict[str, Any]
    tools_state: Dict[str, Any]
    created_at: datetime
    version: str = "1.0"


class AgentMigration:
    """
    Agent 热迁移管理器
    
    功能：
    1. 创建迁移检查点
    2. 恢复 Agent 状态
    3. 零停机迁移
    """
    
    def __init__(self, storage_dir: str = "./migrations"):
        self.storage_dir = storage_dir
        self._active_migrations: Dict[str, str] = {}  # task_id -> status
        self._checkpoints: Dict[str, MigrationCheckpoint] = {}
        
        import os
        os.makedirs(storage_dir, exist_ok=True)
    
    async def create_checkpoint(
        self,
        agent_id: str,
        state: Dict[str, Any],
        context: List[Dict],
        memory: Dict[str, Any],
        tools_state: Dict[str, Any]
    ) -> str:
        """创建检查点"""
        checkpoint_id = f"checkpoint_{agent_id}_{int(datetime.now().timestamp())}"
        
        checkpoint = MigrationCheckpoint(
            checkpoint_id=checkpoint_id,
            agent_state=state,
            context=context,
            memory=memory,
            tools_state=tools_state,
            created_at=datetime.now()
        )
        
        # 持久化
        self._checkpoints[checkpoint_id] = checkpoint
        await self._persist_checkpoint(checkpoint)
        
        logger.info(f"Checkpoint created: {checkpoint_id}")
        
        return checkpoint_id
    
    async def _persist_checkpoint(self, checkpoint: MigrationCheckpoint):
        """持久化检查点"""
        
        path = f"{self.storage_dir}/{checkpoint.checkpoint_id}.chk"
        
        try:
            with open(path, 'wb') as f:
                pickle.dump(checkpoint, f)
        except Exception as e:
            logger.error(f"Failed to persist checkpoint: {e}")
    
    async def restore_from_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """从检查点恢复"""
        if checkpoint_id in self._checkpoints:
            checkpoint = self._checkpoints[checkpoint_id]
        else:
            checkpoint = await self._load_checkpoint(checkpoint_id)
        
        if not checkpoint:
            return None
        
        logger.info(f"Restoring from checkpoint: {checkpoint_id}")
        
        return {
            "agent_state": checkpoint.agent_state,
            "context": checkpoint.context,
            "memory": checkpoint.memory,
            "tools_state": checkpoint.tools_state
        }
    
    async def _load_checkpoint(self, checkpoint_id: str) -> Optional[MigrationCheckpoint]:
        """加载检查点"""
        import os
        
        path = f"{self.storage_dir}/{checkpoint_id}.chk"
        
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    async def migrate(
        self,
        agent_id: str,
        source_node: str,
        target_node: str,
        checkpoint_id: str = None
    ) -> Dict[str, Any]:
        """
        执行迁移
        
        流程：
        1. 创建/获取检查点
        2. 暂停源 Agent
        3. 传输状态
        4. 恢复目标 Agent
        5. 验证并切换
        """
        migration_id = f"mig_{agent_id}_{int(datetime.now().timestamp())}"
        
        self._active_migrations[migration_id] = "in_progress"
        
        try:
            # 1. 创建检查点 (如果未提供)
            if not checkpoint_id:
                checkpoint_id = await self.create_checkpoint(
                    agent_id=agent_id,
                    state={"status": "paused"},
                    context=[],
                    memory={},
                    tools_state={}
                )
            
            # 2. 模拟状态传输
            logger.info(f"Migrating {agent_id} from {source_node} to {target_node}")
            
            # 3. 传输延迟 (模拟)
            await asyncio.sleep(0.5)
            
            # 4. 目标节点恢复
            restored = await self.restore_from_checkpoint(checkpoint_id)
            
            if not restored:
                raise Exception("Restore failed")
            
            self._active_migrations[migration_id] = "completed"
            
            return {
                "migration_id": migration_id,
                "success": True,
                "agent_id": agent_id,
                "source_node": source_node,
                "target_node": target_node,
                "checkpoint_id": checkpoint_id,
                "duration_seconds": 0.5
            }
            
        except Exception as e:
            self._active_migrations[migration_id] = "failed"
            
            return {
                "migration_id": migration_id,
                "success": False,
                "error": str(e)
            }
    
    async def get_migration_status(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """获取迁移状态"""
        status = self._active_migrations.get(migration_id)
        
        if not status:
            return None
        
        return {
            "migration_id": migration_id,
            "status": status
        }
    
    async def list_checkpoints(self, agent_id: str = None) -> List[Dict[str, Any]]:
        """列出检查点"""
        result = []
        
        for cp_id, checkpoint in self._checkpoints.items():
            if agent_id and agent_id not in cp_id:
                continue
            
            result.append({
                "checkpoint_id": cp_id,
                "created_at": checkpoint.created_at.isoformat(),
                "version": checkpoint.version
            })
        
        return result
    
    async def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """清理旧检查点"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = [
            cp_id for cp_id, checkpoint in self._checkpoints.items()
            if checkpoint.created_at < cutoff
        ]
        
        for cp_id in to_remove:
            del self._checkpoints[cp_id]
            logger.info(f"Cleaned up checkpoint: {cp_id}")
        
        return len(to_remove)


# 便捷函数
def create_migration_manager(storage_dir: str = "./migrations") -> AgentMigration:
    """创建迁移管理器"""
    return AgentMigration(storage_dir)
