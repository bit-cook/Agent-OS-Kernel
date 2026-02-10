# -*- coding: utf-8 -*-
"""Cache System - 缓存系统

支持多级缓存、TTL、缓存失效、分布式缓存。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    MEMORY = "memory"
    DISK = "disk"
    DISTRIBUTED = "distributed"


class EvictionPolicy(Enum):
    """淘汰策略"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    FIFO = "fifo"  # 先进先出
    TTL = "ttl"  # 基于过期时间


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    level: CacheLevel = CacheLevel.MEMORY
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds is None:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds
    
    def touch(self):
        """访问"""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1


class CacheSystem:
    """缓存系统"""
    
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: float = 3600.0,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        enable_disk_cache: bool = False,
        disk_cache_dir: str = "/tmp/agent_os_cache"
    ):
        """
        初始化缓存系统
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认 TTL
            eviction_policy: 淘汰策略
            enable_disk_cache: 启用磁盘缓存
            disk_cache_dir: 磁盘缓存目录
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.eviction_policy = eviction_policy
        self.enable_disk_cache = enable_disk_cache
        
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._disk_cache_dir = disk_cache_dir
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "evictions": 0
        }
        
        logger.info(f"CacheSystem initialized: max_size={max_size}")
    
    def _generate_key(self, key: Any) -> str:
        """生成缓存键"""
        if isinstance(key, str):
            return key
        return hashlib.md5(json.dumps(key).encode()).hexdigest()
    
    async def get(self, key: Any, default: Any = None) -> Any:
        """
        获取缓存
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            缓存值
        """
        cache_key = self._generate_key(key)
        
        async with self._lock:
            if cache_key not in self._memory_cache:
                self._stats["misses"] += 1
                return default
            
            entry = self._memory_cache[cache_key]
            
            if entry.is_expired():
                del self._memory_cache[cache_key]
                self._stats["misses"] += 1
                return default
            
            entry.touch()
            self._stats["hits"] += 1
            
            return entry.value
    
    async def set(
        self,
        key: Any,
        value: Any,
        ttl_seconds: float = None,
        level: CacheLevel = CacheLevel.MEMORY
    ):
        """
        设置缓存
        
        Args:
            key: 键
            value: 值
            ttl_seconds: TTL
            level: 缓存级别
        """
        cache_key = self._generate_key(key)
        ttl = ttl_seconds or self.default_ttl
        
        entry = CacheEntry(
            key=cache_key,
            value=value,
            ttl_seconds=ttl if ttl > 0 else None,
            level=level
        )
        
        async with self._lock:
            # 检查是否需要淘汰
            if cache_key not in self._memory_cache and len(self._memory_cache) >= self.max_size:
                await self._evict()
            
            self._memory_cache[cache_key] = entry
            self._stats["writes"] += 1
        
        logger.debug(f"Cache set: {cache_key}")
    
    async def delete(self, key: Any) -> bool:
        """删除缓存"""
        cache_key = self._generate_key(key)
        
        async with self._lock:
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
                return True
        return False
    
    async def clear(self, level: CacheLevel = CacheLevel.MEMORY):
        """清空缓存"""
        async with self._lock:
            if level == CacheLevel.MEMORY:
                self._memory_cache.clear()
        
        logger.info(f"Cache cleared: {level.value}")
    
    async def _evict(self):
        """淘汰条目"""
        if not self._memory_cache:
            return
        
        if self.eviction_policy == EvictionPolicy.LRU:
            # LRU: 淘汰最近最少使用的
            oldest = min(
                self._memory_cache.values(),
                key=lambda e: e.accessed_at
            )
            del self._memory_cache[oldest.key]
        
        elif self.eviction_policy == EvictionPolicy.LFU:
            # LFU: 淘汰访问次数最少的
            least_used = min(
                self._memory_cache.values(),
                key=lambda e: e.access_count
            )
            del self._memory_cache[least_used.key]
        
        elif self.eviction_policy == EvictionPolicy.FIFO:
            # FIFO: 淘汰最早的
            oldest = min(
                self._memory_cache.values(),
                key=lambda e: e.created_at
            )
            del self._memory_cache[oldest.key]
        
        elif self.eviction_policy == EvictionPolicy.TTL:
            # TTL: 淘汰过期的
            now = datetime.utcnow()
            expired = [
                e for e in self._memory_cache.values()
                if e.ttl_seconds and (now - e.created_at).total_seconds() > e.ttl_seconds
            ]
            if expired:
                for entry in expired:
                    del self._memory_cache[entry.key]
            else:
                # 没有过期的，删除最早的
                oldest = min(
                    self._memory_cache.values(),
                    key=lambda e: e.created_at
                )
                del self._memory_cache[oldest.key]
        
        self._stats["evictions"] += 1
    
    async def exists(self, key: Any) -> bool:
        """检查键是否存在"""
        cache_key = self._generate_key(key)
        
        async with self._lock:
            if cache_key not in self._memory_cache:
                return False
            
            entry = self._memory_cache[cache_key]
            return not entry.is_expired()
    
    async def get_or_set(
        self,
        key: Any,
        factory: Callable,
        ttl_seconds: float = None
    ) -> Any:
        """获取或设置"""
        value = await self.get(key)
        
        if value is None:
            if asyncio.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()
            
            await self.set(key, value, ttl_seconds)
        
        return value
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "writes": self._stats["writes"],
            "evictions": self._stats["evictions"],
            "hit_rate": f"{hit_rate:.2f}%",
            "memory_usage": len(self._memory_cache),
            "max_size": self.max_size
        }


# 全局缓存
_cache_system: Optional[CacheSystem] = None


def get_cache_system() -> CacheSystem:
    """获取全局缓存系统"""
    global _cache_system
    if _cache_system is None:
        _cache_system = CacheSystem()
    return _cache_system
