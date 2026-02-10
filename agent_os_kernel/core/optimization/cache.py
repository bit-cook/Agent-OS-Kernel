# -*- coding: utf-8 -*-
"""Tiered Cache - 多层缓存系统

参考 Redis 和内存缓存的最佳实践。

层级结构：
- L1: 内存缓存 (最快)
- L2: 持久化缓存 (Redis)
- L3: 磁盘缓存 (最慢但持久化)
"""

import json
import hashlib
import logging
import pickle
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存层级"""
    MEMORY = "memory"      # 内存缓存
    DISK = "disk"         # 磁盘缓存
    DISTRIBUTED = "redis" # Redis 分布式缓存


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    level: CacheLevel = CacheLevel.MEMORY
    metadata: Dict = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def hit(self):
        """命中缓存"""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CachePolicy:
    """缓存策略"""
    max_memory_mb: int = 100
    max_disk_mb: int = 1000
    default_ttl_seconds: int = 3600  # 1小时
    cleanup_interval_seconds: int = 300  # 5分钟
    eviction_policy: str = "lru"  # lru, lfu, fifo
    compression_enabled: bool = False
    sync_to_disk: bool = True


class MemoryCache:
    """内存缓存"""
    
    def __init__(self, max_size_mb: int = 100):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._max_size = max_size_mb * 1024 * 1024  # 转换为字节
        self._current_size = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                del self._cache[key]
                self._current_size -= self._estimate_size(entry.value)
                return None
            
            entry.hit()
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None,
        metadata: Dict = None
    ) -> bool:
        """设置缓存"""
        with self._lock:
            # 检查是否需要清理空间
            new_size = self._estimate_size(value)
            
            while self._current_size + new_size > self._max_size:
                if not self._evict():
                    return False
            
            # 计算过期时间
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            # 创建条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                level=CacheLevel.MEMORY,
                metadata=metadata or {}
            )
            
            # 删除旧条目
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_size -= self._estimate_size(old_entry.value)
            
            self._cache[key] = entry
            self._current_size += new_size
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._current_size -= self._estimate_size(entry.value)
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._current_size = 0
    
    def stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "size_mb": self._current_size / (1024 * 1024),
                "max_size_mb": self._max_size / (1024 * 1024),
                "items": len(self._cache),
                "hit_rate": self._calculate_hit_rate()
            }
    
    def _evict(self) -> bool:
        """淘汰条目"""
        if not self._cache:
            return False
        
        # LRU 策略
        candidates = list(self._cache.values())
        
        if not candidates:
            return False
        
        # 选择最久未访问的
        oldest = min(candidates, key=lambda x: x.last_accessed or x.created_at)
        
        self._current_size -= self._estimate_size(oldest.value)
        del self._cache[oldest.key]
        
        return True
    
    def _estimate_size(self, value: Any) -> int:
        """估算大小"""
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value))
    
    def _calculate_hit_rate(self) -> float:
        """计算命中率 (简化版)"""
        return 0.0


class DiskCache:
    """磁盘缓存"""
    
    def __init__(self, cache_dir: str = "./cache", max_size_mb: int = 1000):
        self._cache_dir = cache_dir
        self._max_size = max_size_mb * 1024 * 1024
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_path(self, key: str) -> str:
        """获取文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self._cache_dir, f"{key_hash}.cache")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        path = self._get_path(key)
        
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'rb') as f:
                entry = pickle.load(f)
            
            if entry.is_expired():
                os.remove(path)
                return None
            
            entry.hit()
            
            # 更新访问时间
            with open(path, 'wb') as f:
                pickle.dump(entry, f)
            
            return entry.value
        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None,
        metadata: Dict = None
    ) -> bool:
        """设置缓存"""
        path = self._get_path(key)
        
        # 计算过期时间
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            level=CacheLevel.DISK,
            metadata=metadata or {}
        )
        
        try:
            with open(path, 'wb') as f:
                pickle.dump(entry, f)
            return True
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        path = self._get_path(key)
        
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        for file in os.listdir(self._cache_dir):
            if file.endswith('.cache'):
                os.remove(os.path.join(self._cache_dir, file))
    
    def cleanup_expired(self):
        """清理过期缓存"""
        for file in os.listdir(self._cache_dir):
            if not file.endswith('.cache'):
                continue
            
            path = os.path.join(self._cache_dir, file)
            
            try:
                with open(path, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_expired():
                    os.remove(path)
            except:
                os.remove(path)


class TieredCache:
    """
    多层缓存管理器
    
    自动在多个层级之间路由缓存请求。
    """
    
    def __init__(self, policy: CachePolicy = None):
        self.policy = policy or CachePolicy()
        self._memory = MemoryCache(self.policy.max_memory_mb)
        self._disk = DiskCache("./cache", self.policy.max_disk_mb)
        self._redis = None  # 可选 Redis
    
    def get(self, key: str) -> Tuple[Optional[Any], CacheLevel]:
        """获取缓存 (自动多级查询)"""
        # L1: 内存
        value = self._memory.get(key)
        if value is not None:
            return value, CacheLevel.MEMORY
        
        # L2: 磁盘
        value = self._disk.get(key)
        if value is not None:
            # 提升到内存
            self._memory.set(key, value, ttl_seconds=self.policy.default_ttl_seconds)
            return value, CacheLevel.DISK
        
        # L3: Redis (如果配置)
        if self._redis:
            value = self._redis.get(key)
            if value is not None:
                self._memory.set(key, value)
                self._disk.set(key, value)
                return value, CacheLevel.DISTRIBUTED
        
        return None, CacheLevel.MEMORY
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = None,
        levels: List[CacheLevel] = None
    ) -> bool:
        """设置缓存"""
        ttl = ttl_seconds or self.policy.default_ttl_seconds
        
        if levels is None:
            levels = [CacheLevel.MEMORY, CacheLevel.DISK]
        
        success = True
        
        if CacheLevel.MEMORY in levels:
            if not self._memory.set(key, value, ttl):
                success = False
        
        if CacheLevel.DISK in levels:
            if not self._disk.set(key, value, ttl):
                success = False
        
        if CacheLevel.DISTRIBUTED in levels and self._redis:
            self._redis.set(key, value, ttl)
        
        return success
    
    def delete(self, key: str) -> bool:
        """删除缓存 (多级删除)"""
        success = True
        success = self._memory.delete(key) and success
        success = self._disk.delete(key) and success
        if self._redis:
            self._redis.delete(key)
        return success
    
    def clear(self):
        """清空所有缓存"""
        self._memory.clear()
        self._disk.clear()
        if self._redis:
            self._redis.flushdb()
    
    def stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "memory": self._memory.stats(),
            "disk": {
                "enabled": True,
                "size_mb": self._get_disk_usage()
            }
        }
    
    def _get_disk_usage(self) -> float:
        """获取磁盘使用量"""
        total = 0
        for file in os.listdir(self._disk._cache_dir):
            if file.endswith('.cache'):
                total += os.path.getsize(os.path.join(self._disk._cache_dir, file))
        return total / (1024 * 1024)
    
    def enable_redis(self, host: str = "localhost", port: int = 6379):
        """启用 Redis"""
        try:
            import redis
            self._redis = redis.Redis(host=host, port=port, decode_responses=True)
            self._redis.ping()
            logger.info("Redis cache enabled")
        except ImportError:
            logger.warning("Redis not installed")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")


# 便捷函数
def get_cache() -> TieredCache:
    """获取全局缓存实例"""
    return _global_cache


def init_cache(policy: CachePolicy = None) -> TieredCache:
    """初始化全局缓存"""
    global _global_cache
    _global_cache = TieredCache(policy)
    return _global_cache


# 全局实例
_global_cache: Optional[TieredCache] = None
