# -*- coding: utf-8 -*-
"""Checkpointer - 状态持久化与时间旅行

参考 LangGraph Checkpointer 设计
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TypeVar, Generic
from datetime import datetime
from uuid import uuid4
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)


T = TypeVar('T')


@dataclass
class Checkpoint:
    """检查点"""
    
    id: str  # 检查点 ID
    state: Dict[str, Any]  # 状态数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # 版本信息
    version: int = 1
    
    # 父检查点 (用于时间旅行)
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "state": self.state,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "parent_id": self.parent_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Checkpoint':
        return cls(
            id=data["id"],
            state=data["state"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            version=data.get("version", 1),
            parent_id=data.get("parent_id"),
        )


@dataclass
class CheckpointMetadata:
    """检查点元数据"""
    
    checkpoint_id: str
    thread_id: str  # 线程 ID
    step: int  # 步骤号
    
    # 执行信息
    source: str = "manual"  # manual, auto, error_recovery
    
    # 注释
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "thread_id": self.thread_id,
            "step": self.step,
            "source": self.source,
            "notes": self.notes,
        }


class CheckpointStorage(Generic[T]):
    """检查点存储基类"""
    
    def save(self, checkpoint: Checkpoint) -> bool:
        """保存检查点"""
        raise NotImplementedError
    
    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        raise NotImplementedError
    
    def list(
        self, 
        thread_id: str, 
        limit: int = 10,
        before: Optional[datetime] = None
    ) -> List[Checkpoint]:
        """列出检查点"""
        raise NotImplementedError
    
    def delete(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        raise NotImplementedError


class MemoryCheckpointStorage(CheckpointStorage[Dict]):
    """内存检查点存储
    
    适用于开发测试，不适用于生产
    """
    
    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._thread_checkpoints: Dict[str, List[str]] = {}  # thread_id -> [checkpoint_ids]
        self._lock = Lock()
        
        logger.info("MemoryCheckpointStorage initialized")
    
    def save(self, checkpoint: Checkpoint) -> bool:
        """保存检查点"""
        with self._lock:
            checkpoint.version = len(self._checkpoints) + 1
            self._checkpoints[checkpoint.id] = checkpoint
            
            # 记录到线程
            thread_id = checkpoint.metadata.get("thread_id", "default")
            if thread_id not in self._thread_checkpoints:
                self._thread_checkpoints[thread_id] = []
            self._thread_checkpoints[thread_id].append(checkpoint.id)
            
            logger.debug(f"Checkpoint saved: {checkpoint.id}")
            return True
    
    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        with self._lock:
            return self._checkpoints.get(checkpoint_id)
    
    def list(
        self, 
        thread_id: str = "default",
        limit: int = 10,
        before: Optional[datetime] = None
    ) -> List[Checkpoint]:
        """列出检查点"""
        with self._lock:
            checkpoint_ids = self._thread_checkpoints.get(thread_id, [])
            checkpoints = [
                self._checkpoints[cid] 
                for cid in checkpoint_ids 
                if cid in self._checkpoints
            ]
            
            # 按时间排序
            checkpoints.sort(key=lambda c: c.created_at, reverse=True)
            
            # 过滤 before
            if before:
                checkpoints = [c for c in checkpoints if c.created_at < before]
            
            return checkpoints[:limit]
    
    def delete(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        with self._lock:
            if checkpoint_id in self._checkpoints:
                del self._checkpoints[checkpoint_id]
                
                # 从线程记录中移除
                for thread_ids in self._thread_checkpoints.values():
                    if checkpoint_id in thread_ids:
                        thread_ids.remove(checkpoint_id)
                
                return True
            return False


class SQLiteCheckpointStorage(CheckpointStorage[Dict]):
    """SQLite 检查点存储
    
    适用于单机部署
    """
    
    def __init__(self, db_path: str = "./checkpoints.db"):
        import sqlite3
        
        self.db_path = db_path
        self._lock = Lock()
        
        # 初始化数据库
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    state TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    version INTEGER,
                    parent_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thread_checkpoints (
                    thread_id TEXT,
                    checkpoint_id TEXT,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """)
        
        logger.info(f"SQLiteCheckpointStorage initialized: {db_path}")
    
    def _get_conn(self):
        import sqlite3
        return sqlite3.connect(self.db_path)
    
    def save(self, checkpoint: Checkpoint) -> bool:
        """保存检查点"""
        with self._lock:
            import sqlite3
            
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO checkpoints 
                    (id, state, metadata, created_at, version, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint.id,
                    json.dumps(checkpoint.state),
                    json.dumps(checkpoint.metadata),
                    checkpoint.created_at.isoformat(),
                    checkpoint.version,
                    checkpoint.parent_id,
                ))
                
                # 记录到线程
                thread_id = checkpoint.metadata.get("thread_id", "default")
                conn.execute("""
                    INSERT OR IGNORE INTO thread_checkpoints 
                    (thread_id, checkpoint_id) VALUES (?, ?)
                """, (thread_id, checkpoint.id))
                
                return True
    
    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        with self._lock:
            import sqlite3
            
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM checkpoints WHERE id = ?",
                    (checkpoint_id,)
                ).fetchone()
                
                if row:
                    return Checkpoint(
                        id=row[0],
                        state=json.loads(row[1]),
                        metadata=json.loads(row[2]),
                        created_at=datetime.fromisoformat(row[3]),
                        version=row[4],
                        parent_id=row[5],
                    )
                return None
    
    def list(
        self, 
        thread_id: str = "default",
        limit: int = 10,
        before: Optional[datetime] = None
    ) -> List[Checkpoint]:
        """列出检查点"""
        import sqlite3
        
        with self._get_conn() as conn:
            query = """
                SELECT c.* FROM checkpoints c
                JOIN thread_checkpoints t ON c.id = t.checkpoint_id
                WHERE t.thread_id = ?
            """
            params = [thread_id]
            
            if before:
                query += " AND c.created_at < ?"
                params.append(before.isoformat())
            
            query += " ORDER BY c.created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [
                Checkpoint(
                    id=row[0],
                    state=json.loads(row[1]),
                    metadata=json.loads(row[2]),
                    created_at=datetime.fromisoformat(row[3]),
                    version=row[4],
                    parent_id=row[5],
                )
                for row in rows
            ]
    
    def delete(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        import sqlite3
        
        with self._lock:
            with self._get_conn() as conn:
                # 先从线程表中删除
                conn.execute(
                    "DELETE FROM thread_checkpoints WHERE checkpoint_id = ?",
                    (checkpoint_id,)
                )
                # 再从检查点表中删除
                result = conn.execute(
                    "DELETE FROM checkpoints WHERE id = ?",
                    (checkpoint_id,)
                )
                return result.rowcount > 0


class Checkpointer:
    """检查点管理器
    
    功能:
    - 创建和管理检查点
    - 状态持久化
    - 时间旅行 (恢复到之前的状态)
    """
    
    def __init__(
        self, 
        storage: Optional[CheckpointStorage] = None,
        max_checkpoints: int = 100
    ):
        """初始化 Checkpointer
        
        Args:
            storage: 检查点存储 (默认使用内存存储)
            max_checkpoints: 每个线程最大检查点数
        """
        self.storage = storage or MemoryCheckpointStorage()
        self.max_checkpoints = max_checkpoints
        self._current_state: Dict[str, Any] = {}
        
        logger.info(f"Checkpointer initialized with {type(self.storage).__name__}")
    
    def save(
        self,
        state: Dict[str, Any],
        thread_id: str = "default",
        notes: Optional[str] = None,
        source: str = "auto"
    ) -> Checkpoint:
        """保存检查点
        
        Args:
            state: 要保存的状态
            thread_id: 线程 ID
            notes: 注释
            source: 来源 (manual, auto, error_recovery)
            
        Returns:
            Checkpoint: 创建的检查点
        """
        checkpoint_id = str(uuid4())[:8]
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            state=state.copy(),
            metadata={
                "thread_id": thread_id,
                "source": source,
                "notes": notes,
            },
            created_at=datetime.utcnow(),
        )
        
        self.storage.save(checkpoint)
        
        # 清理旧检查点
        self._cleanup_old_checkpoints(thread_id)
        
        logger.info(f"Checkpoint saved: {checkpoint_id} (thread={thread_id})")
        
        return checkpoint
    
    def load(self, checkpoint_id: str) -> Optional[Dict]:
        """加载检查点
        
        Args:
            checkpoint_id: 检查点 ID
            
        Returns:
            状态数据，或 None
        """
        checkpoint = self.storage.load(checkpoint_id)
        
        if checkpoint:
            logger.info(f"Checkpoint loaded: {checkpoint_id}")
            return checkpoint.state.copy()
        
        logger.warning(f"Checkpoint not found: {checkpoint_id}")
        return None
    
    def get_latest(
        self, 
        thread_id: str = "default"
    ) -> Optional[Checkpoint]:
        """获取最新的检查点"""
        checkpoints = self.storage.list(thread_id, limit=1)
        
        return checkpoints[0] if checkpoints else None
    
    def history(
        self, 
        thread_id: str = "default",
        limit: int = 10
    ) -> List[Checkpoint]:
        """获取检查点历史"""
        return self.storage.list(thread_id, limit=limit)
    
    def restore(
        self, 
        checkpoint_id: str,
        thread_id: Optional[str] = None
    ) -> Dict:
        """恢复到指定检查点
        
        Args:
            checkpoint_id: 检查点 ID
            thread_id: 线程 ID
            
        Returns:
            恢复的状态
        """
        checkpoint = self.storage.load(checkpoint_id)
        
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        # 创建新检查点记录恢复操作
        new_checkpoint = self.save(
            state=checkpoint.state,
            thread_id=thread_id or checkpoint.metadata.get("thread_id", "default"),
            notes=f"Restored from {checkpoint_id}",
            source="manual"
        )
        
        # 设置父检查点
        new_checkpoint.parent_id = checkpoint_id
        
        logger.info(f"Restored to checkpoint: {checkpoint_id}")
        
        return checkpoint.state.copy()
    
    def update_state(
        self,
        updates: Dict[str, Any],
        thread_id: str = "default"
    ) -> Checkpoint:
        """更新当前状态
        
        Args:
            updates: 更新内容
            thread_id: 线程 ID
            
        Returns:
            Checkpoint: 新检查点
        """
        # 获取最新状态
        latest = self.get_latest(thread_id)
        current = latest.state.copy() if latest else {}
        
        # 应用更新
        current.update(updates)
        
        # 保存
        return self.save(
            state=current,
            thread_id=thread_id,
            source="auto"
        )
    
    def _cleanup_old_checkpoints(self, thread_id: str):
        """清理旧的检查点"""
        checkpoints = self.storage.list(thread_id, limit=self.max_checkpoints + 10)
        
        if len(checkpoints) > self.max_checkpoints:
            # 删除最旧的
            to_delete = checkpoints[self.max_checkpoints:]
            
            for cp in to_delete:
                self.storage.delete(cp.id)
            
            logger.debug(
                f"Cleaned up {len(to_delete)} old checkpoints for thread {thread_id}"
            )
    
    def clear_thread(self, thread_id: str):
        """清除线程的所有检查点"""
        checkpoints = self.storage.list(thread_id, limit=1000)
        
        for cp in checkpoints:
            self.storage.delete(cp.id)
        
        logger.info(f"Cleared all checkpoints for thread: {thread_id}")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "storage_type": type(self.storage).__name__,
            "max_checkpoints": self.max_checkpoints,
        }
