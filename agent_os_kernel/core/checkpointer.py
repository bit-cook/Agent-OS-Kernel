# -*- coding: utf-8 -*-
"""Checkpointer - 检查点管理器

支持状态保存/恢复/时间旅行。
"""

import asyncio
import logging
import pickle
import hashlib
import time
from datetime import datetime, timezone, timedelta, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class CheckpointStatus(Enum):
    """检查点状态"""
    ACTIVE = "active"
    RESTORED = "restored"
    EXPIRED = "expired"


@dataclass
class Checkpoint:
    """检查点"""
    checkpoint_id: str
    name: str
    state: Dict[str, Any]
    metadata: Dict = field(default_factory=dict)
    status: CheckpointStatus = CheckpointStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    parent_id: Optional[str] = None
    size_bytes: int = 0
    checksum: str = ""
    
    def verify_checksum(self) -> bool:
        """验证校验和"""
        computed = hashlib.md5(pickle.dumps(self.state)).hexdigest()
        return computed == self.checksum


class Checkpointer:
    """检查点管理器"""
    
    def __init__(
        self,
        max_checkpoints: int = 100,
        default_ttl_hours: float = 24.0,
        enable_compression: bool = True
    ):
        self.max_checkpoints = max_checkpoints
        self.default_ttl_hours = default_ttl_hours
        self.enable_compression = enable_compression
        
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._tags: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        
        logger.info(f"Checkpointer initialized: max={max_checkpoints}")
    
    async def create(
        self,
        name: str,
        state: Dict[str, Any],
        tag: str = None,
        ttl_hours: float = None,
        parent_id: str = None,
        metadata: Dict = None
    ) -> str:
        checkpoint_id = str(uuid4())
        
        data = pickle.dumps(state)
        if self.enable_compression:
            import zlib
            data = zlib.compress(data)
        
        checksum = hashlib.md5(pickle.dumps(state)).hexdigest()
        
        expires_at = None
        ttl = ttl_hours or self.default_ttl_hours
        if ttl > 0:
            expires_at = datetime.now() + timedelta(hours=ttl)
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            name=name,
            state=state,
            metadata=metadata or {},
            status=CheckpointStatus.ACTIVE,
            expires_at=expires_at,
            parent_id=parent_id,
            size_bytes=len(data),
            checksum=checksum
        )
        
        async with self._lock:
            self._checkpoints[checkpoint_id] = checkpoint
            if tag:
                self._tags[tag] = checkpoint_id
            if len(self._checkpoints) > self.max_checkpoints:
                await self._cleanup_oldest()
        
        logger.info(f"Checkpoint created: {name} ({checkpoint_id})")
        return checkpoint_id
    
    async def restore(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """恢复检查点"""
        async with self._lock:
            if checkpoint_id not in self._checkpoints:
                return None
            checkpoint = self._checkpoints[checkpoint_id]
        
        if not checkpoint.verify_checksum():
            logger.error(f"Checksum mismatch for checkpoint: {checkpoint_id}")
            return None
        
        checkpoint.status = CheckpointStatus.RESTORED
        logger.info(f"Checkpoint restored: {checkpoint_id}")
        return checkpoint.state
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        async with self._lock:
            return self._checkpoints.get(checkpoint_id)
    
    async def list_checkpoints(self, name: str = None, limit: int = 50) -> List[Checkpoint]:
        async with self._lock:
            checkpoints = list(self._checkpoints.values())
            if name:
                checkpoints = [c for c in checkpoints if c.name == name]
            checkpoints.sort(key=lambda c: c.created_at, reverse=True)
            return checkpoints[:limit]
    
    async def delete(self, checkpoint_id: str) -> bool:
        async with self._lock:
            if checkpoint_id in self._checkpoints:
                del self._checkpoints[checkpoint_id]
                for tag, cid in list(self._tags.items()):
                    if cid == checkpoint_id:
                        del self._tags[tag]
                return True
        return False
    
    async def tag_checkpoint(self, checkpoint_id: str, tag: str) -> bool:
        async with self._lock:
            if checkpoint_id in self._checkpoints:
                self._tags[tag] = checkpoint_id
                return True
        return False
    
    async def get_by_tag(self, tag: str) -> Optional[Checkpoint]:
        async with self._lock:
            cid = self._tags.get(tag)
            return self._checkpoints.get(cid) if cid else None
    
    async def _cleanup_oldest(self):
        if not self._checkpoints:
            return
        oldest = min(self._checkpoints.values(), key=lambda c: c.created_at)
        del self._checkpoints[oldest.checkpoint_id]
        for tag, cid in list(self._tags.items()):
            if cid == oldest.checkpoint_id:
                del self._tags[tag]
    
    def get_stats(self) -> Dict:
        return {
            "total_checkpoints": len(self._checkpoints),
            "tags_count": len(self._tags),
            "max_checkpoints": self.max_checkpoints
        }
