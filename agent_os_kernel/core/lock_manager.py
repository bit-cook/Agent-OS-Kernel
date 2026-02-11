# -*- coding: utf-8 -*-
"""Lock Manager - 锁管理器

支持分布式锁、读写锁、信号量、限时锁。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone, timezone, timedelta, timedelta
from enum import Enum
from uuid import uuid4
import time

logger = logging.getLogger(__name__)


class LockType(Enum):
    """锁类型"""
    MUTEX = "mutex"  # 互斥锁
    READ_WRITE = "rw"  # 读写锁
    SEMAPHORE = "semaphore"  # 信号量
    TIMEOUT = "timeout"  # 限时锁


class LockStatus(Enum):
    """锁状态"""
    UNLOCKED = "unlocked"
    LOCKED = "locked"
    WAITING = "waiting"
    EXPIRED = "expired"


@dataclass
class Lock:
    """锁"""
    lock_id: str
    name: str
    lock_type: LockType
    owner_id: str
    status: LockStatus = LockStatus.UNLOCKED
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    timeout_seconds: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """检查是否有效"""
        if self.expires_at is None:
            return self.status == LockStatus.LOCKED
        return datetime.now(timezone.utc) < self.expires_at and self.status == LockStatus.LOCKED


class LockManager:
    """锁管理器"""
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        max_concurrent: int = 100
    ):
        """
        初始化锁管理器
        
        Args:
            default_timeout: 默认超时
            max_concurrent: 最大并发锁数
        """
        self.default_timeout = default_timeout
        self.max_concurrent = max_concurrent
        
        self._locks: Dict[str, Lock] = {}
        self._waiting: Dict[str, asyncio.Queue] = {}
        self._read_locks: Dict[str, int] = {}  # 读写锁的读计数
        self._lock = asyncio.Lock()
        self._stats = {
            "acquired": 0,
            "released": 0,
            "timeouts": 0,
            "deadlocks": 0
        }
        
        logger.info("LockManager initialized")
    
    async def acquire(
        self,
        name: str,
        owner_id: str,
        lock_type: LockType = LockType.MUTEX,
        timeout_seconds: float = None,
        blocking: bool = True
    ) -> Optional[Lock]:
        """
        获取锁
        
        Args:
            name: 锁名称
            owner_id: 所有者 ID
            lock_type: 锁类型
            timeout_seconds: 超时时间
            blocking: 是否阻塞
            
        Returns:
            锁对象或 None
        """
        lock_id = f"{name}_{owner_id}"
        timeout = timeout_seconds or self.default_timeout
        
        async with self._lock:
            if name in self._locks:
                existing_lock = self._locks[name]
                
                if lock_type == LockType.READ_WRITE and existing_lock.lock_type == LockType.READ_WRITE:
                    # 读锁：可以多个同时获取
                    if owner_id in self._read_locks:
                        self._read_locks[owner_id] += 1
                        self._stats["acquired"] += 1
                        return self._locks[name]
                    elif len(self._read_locks) < self.max_concurrent:
                        self._read_locks[owner_id] = 1
                        self._stats["acquired"] += 1
                        return self._locks[name]
                
                # 等待或超时
                if not blocking:
                    return None
                
                if name not in self._waiting:
                    self._waiting[name] = asyncio.Queue()
                
                wait_task = asyncio.create_task(self._waiting[name].get())
            
            # 创建新锁
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout) if timeout > 0 else None
            
            lock = Lock(
                lock_id=lock_id,
                name=name,
                lock_type=lock_type,
                owner_id=owner_id,
                status=LockStatus.LOCKED,
                expires_at=expires_at,
                timeout_seconds=timeout
            )
            
            self._locks[name] = lock
            
            if lock_type == LockType.READ_WRITE:
                self._read_locks[owner_id] = self._read_locks.get(owner_id, 0) + 1
            
            self._stats["acquired"] += 1
            
            logger.debug(f"Lock acquired: {name} by {owner_id}")
            
            return lock
    
    async def release(self, name: str, owner_id: str) -> bool:
        """
        释放锁
        
        Args:
            name: 锁名称
            owner_id: 所有者 ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            if name not in self._locks:
                return False
            
            lock = self._locks[name]
            
            if lock.owner_id != owner_id:
                logger.warning(f"Lock release denied: {name} by {owner_id}")
                return False
            
            # 读锁处理
            if lock.lock_type == LockType.READ_WRITE:
                self._read_locks[owner_id] -= 1
                if self._read_locks[owner_id] <= 0:
                    del self._read_locks[owner_id]
            
            del self._locks[name]
            self._stats["released"] += 1
            
            # 通知等待者
            if name in self._waiting:
                await self._waiting[name].put(True)
            
            logger.debug(f"Lock released: {name} by {owner_id}")
            
            return True
    
    async def release_all(self, owner_id: str):
        """释放所有属于 owner 的锁"""
        async with self._lock:
            released = []
            
            for name in list(self._locks.keys()):
                if self._locks[name].owner_id == owner_id:
                    await self.release(name, owner_id)
                    released.append(name)
            
            return released
    
    async def acquire_timeout(
        self,
        name: str,
        owner_id: str,
        timeout_seconds: float = 5.0
    ) -> Optional[Lock]:
        """获取限时锁"""
        return await self.acquire(
            name,
            owner_id,
            LockType.TIMEOUT,
            timeout_seconds,
            blocking=True
        )
    
    async def acquire_semaphore(
        self,
        name: str,
        owner_id: str,
        max_concurrent: int = None
    ) -> bool:
        """获取信号量"""
        async with self._lock:
            current = self._read_locks.get(name, 0)
            limit = max_concurrent or self.max_concurrent
            
            if current >= limit:
                return False
            
            self._read_locks[name] = current + 1
            
            lock = Lock(
                lock_id=f"{name}_{owner_id}",
                name=name,
                lock_type=LockType.SEMAPHORE,
                owner_id=owner_id
            )
            self._locks[name] = lock
            
            return True
    
    def is_locked(self, name: str) -> bool:
        """检查是否已锁定"""
        return name in self._locks and self._locks[name].is_valid()
    
    def get_lock_info(self, name: str) -> Optional[Dict]:
        """获取锁信息"""
        if name not in self._locks:
            return None
        
        lock = self._locks[name]
        return {
            "name": lock.name,
            "owner": lock.owner_id,
            "type": lock.lock_type.value,
            "status": lock.status.value,
            "created": lock.created_at.isoformat(),
            "expires": lock.expires_at.isoformat() if lock.expires_at else None
        }
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "acquired": self._stats["acquired"],
            "released": self._stats["released"],
            "timeouts": self._stats["timeouts"],
            "active_locks": len(self._locks)
        }


# 上下文管理器锁
class async_lock:
    """异步锁上下文管理器"""
    
    def __init__(self, lock_manager: LockManager, name: str, **kwargs):
        self.lock_manager = lock_manager
        self.name = name
        self.kwargs = kwargs
        self.lock: Optional[Lock] = None
    
    async def __aenter__(self) -> Lock:
        self.lock = await self.lock_manager.acquire(self.name, "context", **self.kwargs)
        return self.lock
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.lock:
            await self.lock_manager.release(self.name, self.lock.owner_id)
