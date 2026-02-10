# -*- coding: utf-8 -*-
import logging
"""Enhanced Storage Manager - 增强存储管理器

完整实现五种存储角色。
"""

import asyncio
import json
import pickle
import hashlib
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import OrderedDict
import threading

logger = logging.getLogger(__name__)


class StorageRole(Enum):
    """存储角色"""
    EPISODIC = "episodic"  # 记忆存储
    STATE = "state"  # 状态持久化
    VECTOR = "vector"  # 向量索引
    AUDIT = "audit"  # 审计日志
    CHECKPOINT = "checkpoint"  # 检查点存储


@dataclass
class StorageStats:
    """存储统计"""
    role: str = ""
    total_keys: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0
    last_access: Optional[datetime] = None


class EnhancedStorageManager:
    """增强存储管理器"""
    
    def __init__(
        self,
        max_memory_size: int = 10000,
        enable_compression: bool = True,
        cleanup_interval: int = 300  # 5分钟
    ):
        """
        初始化增强存储管理器
        
        Args:
            max_memory_size: 最大内存条目数
            enable_compression: 启用压缩
            cleanup_interval: 清理间隔（秒）
        """
        self.max_memory_size = max_memory_size
        self.enable_compression = enable_compression
        self.cleanup_interval = cleanup_interval
        
        # 五种角色的存储
        self._storages: Dict[StorageRole, Dict[str, Any]] = {
            role: {} for role in StorageRole
        }
        
        # 元数据
        self._metadata: Dict[str, Dict] = {}
        
        # 访问统计
        self._access_log: OrderedDict = OrderedDict()
        
        # 锁
        self._lock = asyncio.Lock()
        
        # 清理任务
        self._cleanup_task = None
        self._running = False
        
        # 统计
        self._stats: Dict[str, StorageStats] = {
            role.value: StorageStats(role=role.value)
            for role in StorageRole
        }
        
        logger.info("EnhancedStorageManager initialized")
    
    async def start(self):
        """启动存储管理器"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("EnhancedStorageManager started")
    
    async def stop(self):
        """停止存储管理器"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("EnhancedStorageManager stopped")
    
    # ==================== 基础 CRUD 操作 ====================
    
    async def save(
        self,
        key: str,
        value: Any,
        role: StorageRole = StorageRole.STATE,
        ttl_seconds: Optional[int] = None,
        metadata: Dict = None
    ) -> bool:
        """
        保存数据
        
        Args:
            key: 键
            value: 值
            role: 存储角色
            ttl_seconds: 存活时间
            metadata: 元数据
            
        Returns:
            是否成功
        """
        async with self._lock:
            try:
                # 序列化
                if self.enable_compression:
                    data = pickle.dumps(value)
                else:
                    data = pickle.dumps(value)
                
                size = len(data)
                
                # 存储
                self._storages[role][key] = value
                
                # 元数据
                self._metadata[key] = {
                    'role': role.value,
                    'size': size,
                    'created': time.time(),
                    'modified': time.time(),
                    'ttl': ttl_seconds,
                    'metadata': metadata or {}
                }
                
                # 更新统计
                self._stats[role.value].total_keys = len(self._storages[role])
                self._stats[role.value].total_size_bytes += size
                
                # LRU 淘汰
                if len(self._storages[role]) > self.max_memory_size:
                    oldest_key = next(iter(self._storages[role]))
                    del self._storages[role][oldest_key]
                    del self._metadata[oldest_key]
                
                return True
                
            except Exception as e:
                logger.error(f"Save failed: {e}")
                return False
    
    async def retrieve(
        self,
        key: str,
        role: StorageRole = None,
        default: Any = None
    ) -> Any:
        """
        检索数据
        
        Args:
            key: 键
            role: 存储角色
            default: 默认值
            
        Returns:
            值
        """
        async with self._lock:
            try:
                # 确定搜索的角色
                roles_to_search = (
                    [role] if role else list(StorageRole)
                )
                
                for r in roles_to_search:
                    if key in self._storages[r]:
                        # 检查 TTL
                        meta = self._metadata.get(key, {})
                        if meta.get('ttl'):
                            age = time.time() - meta.get('created', 0)
                            if age > meta['ttl']:
                                del self._storages[r][key]
                                del self._metadata[key]
                                continue
                        
                        # 更新访问时间
                        meta['accessed'] = time.time()
                        
                        # 更新统计
                        self._stats[r.value].last_access = datetime.utcnow()
                        
                        return self._storages[r][key]
                
                return default
                
            except Exception as e:
                logger.error(f"Retrieve failed: {e}")
                return default
    
    async def delete(self, key: str, role: StorageRole = None) -> bool:
        """
        删除数据
        
        Args:
            key: 键
            role: 存储角色
            
        Returns:
            是否成功
        """
        async with self._lock:
            try:
                roles_to_search = (
                    [role] if role else list(StorageRole)
                )
                
                deleted = False
                for r in roles_to_search:
                    if key in self._storages[r]:
                        del self._storages[r][key]
                        if key in self._metadata:
                            del self._metadata[key]
                        deleted = True
                
                return deleted
                
            except Exception as e:
                logger.error(f"Delete failed: {e}")
                return False
    
    async def exists(self, key: str, role: StorageRole = None) -> bool:
        """检查键是否存在"""
        async with self._lock:
            roles_to_search = (
                [role] if role else list(StorageRole)
            )
            return any(key in self._storages[r] for r in roles_to_search)
    
    # ==================== 五种角色专用方法 ====================
    
    # 1. 记忆存储 (Episodic Memory)
    async def save_episode(self, episode_id: str, episode_data: Dict) -> bool:
        """保存记忆片段"""
        episode_data['_timestamp'] = time.time()
        return await self.save(
            key=f"episode:{episode_id}",
            value=episode_data,
            role=StorageRole.EPISODIC
        )
    
    async def get_episodes(self, limit: int = 10) -> List[Dict]:
        """获取最近的记忆片段"""
        async with self._lock:
            episodes = [
                (k, v) for k, v in self._storages[StorageRole.EPISODIC].items()
                if k.startswith("episode:")
            ]
            episodes.sort(key=lambda x: x[1].get('_timestamp', 0), reverse=True)
            return [v for k, v in episodes[:limit]]
    
    # 2. 状态持久化 (State)
    async def save_state(self, agent_id: str, state: Dict) -> bool:
        """保存 Agent 状态"""
        return await self.save(
            key=f"state:{agent_id}",
            value=state,
            role=StorageRole.STATE
        )
    
    async def load_state(self, agent_id: str) -> Optional[Dict]:
        """加载 Agent 状态"""
        return await self.retrieve(
            key=f"state:{agent_id}",
            role=StorageRole.STATE
        )
    
    # 3. 向量索引 (Vector)
    async def save_vector(self, vector_id: str, vector: List[float], metadata: Dict = None) -> bool:
        """保存向量"""
        return await self.save(
            key=f"vector:{vector_id}",
            value={
                'vector': vector,
                'metadata': metadata or {}
            },
            role=StorageRole.VECTOR
        )
    
    async def search_vectors(self, query: List[float], limit: int = 5) -> List[Dict]:
        """搜索向量（简单实现）"""
        async with self._lock:
            results = []
            for k, v in self._storages[StorageRole.VECTOR].items():
                if k.startswith("vector:"):
                    # 简单余弦相似度
                    similarity = self._cosine_similarity(query, v['vector'])
                    results.append({
                        'id': k.replace("vector:", ""),
                        'similarity': similarity,
                        'metadata': v.get('metadata', {})
                    })
            
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:limit]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        import math
        if len(a) != len(b):
            return 0.0
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    # 4. 审计日志 (Audit)
    async def log_audit(self, action: str, details: Dict) -> bool:
        """记录审计日志"""
        return await self.save(
            key=f"audit:{int(time.time())}:{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}",
            value={
                'action': action,
                'details': details,
                'timestamp': time.time()
            },
            role=StorageRole.AUDIT
        )
    
    async def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        async with self._lock:
            logs = [
                v for k, v in self._storages[StorageRole.AUDIT].items()
                if k.startswith("audit:")
            ]
            logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            return logs[:limit]
    
    # 5. 检查点存储 (Checkpoint)
    async def save_checkpoint(self, checkpoint_id: str, data: Dict) -> bool:
        """保存检查点"""
        return await self.save(
            key=f"checkpoint:{checkpoint_id}",
            value={
                'data': data,
                'timestamp': time.time()
            },
            role=StorageRole.CHECKPOINT
        )
    
    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        """加载检查点"""
        return await self.retrieve(
            key=f"checkpoint:{checkpoint_id}",
            role=StorageRole.CHECKPOINT
        )
    
    async def list_checkpoints(self) -> List[str]:
        """列出所有检查点"""
        async with self._lock:
            return [
                k.replace("checkpoint:", "")
                for k in self._storages[StorageRole.CHECKPOINT].keys()
            ]
    
    # ==================== 工具方法 ====================
    
    async def list_keys(self, role: StorageRole = None, prefix: str = "") -> List[str]:
        """列出键"""
        async with self._lock:
            if role:
                return [k for k in self._storages[role].keys() if k.startswith(prefix)]
            return [
                k for role in StorageRole
                for k in self._storages[role].keys()
                if k.startswith(prefix)
            ]
    
    async def clear(self, role: StorageRole = None):
        """清空存储"""
        async with self._lock:
            if role:
                self._storages[role].clear()
            else:
                for role in StorageRole:
                    self._storages[role].clear()
            self._metadata.clear()
    
    async def get_stats(self) -> Dict[str, StorageStats]:
        """获取统计"""
        return self._stats
    
    async def _cleanup_loop(self):
        """清理过期条目"""
        while self._running:
            await asyncio.sleep(self.cleanup_interval)
            
            async with self._lock:
                now = time.time()
                
                for role in StorageRole:
                    expired_keys = []
                    
                    for key, meta in self._metadata.items():
                        if meta.get('role') == role.value:
                            ttl = meta.get('ttl')
                            if ttl and (now - meta.get('created', 0)) > ttl:
                                expired_keys.append(key)
                    
                    for key in expired_keys:
                        if key in self._storages[role]:
                            del self._storages[role][key]
                        if key in self._metadata:
                            del self._metadata[key]
                
                logger.debug("Storage cleanup completed")
