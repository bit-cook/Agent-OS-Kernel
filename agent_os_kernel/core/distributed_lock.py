# -*- coding: utf-8 -*-
"""
Distributed Lock Module - 提供分布式锁功能

支持:
- 互斥锁 (Mutex Lock)
- 读写锁 (Read-Write Lock)
- 超时机制
- 锁续期 (Lock Renewal)
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from contextlib import contextmanager


class LockType(Enum):
    """锁类型"""
    MUTEX = "mutex"
    READ = "read"
    WRITE = "write"


class LockState(Enum):
    """锁状态"""
    FREE = "free"
    LOCKED = "locked"
    EXPIRED = "expired"


@dataclass
class LockOwner:
    """锁持有者信息"""
    owner_id: str
    lock_type: LockType
    acquire_time: float
    expire_time: float
    renewals: int = 0
    
    def is_expired(self, current_time: float) -> bool:
        """检查是否已过期"""
        return current_time >= self.expire_time


class LockAcquireError(Exception):
    """获取锁失败异常"""
    pass


class LockRenewalError(Exception):
    """锁续期失败异常"""
    pass


class LockTimeoutError(LockAcquireError):
    """锁获取超时异常"""
    pass


class DistributedLockBackend(ABC):
    """分布式锁后端抽象基类"""
    
    @abstractmethod
    async def acquire(self, lock_name: str, owner_id: str, 
                      lock_type: LockType, timeout: float, 
                      expire_time: float) -> bool:
        """获取锁"""
        pass
    
    @abstractmethod
    async def release(self, lock_name: str, owner_id: str) -> bool:
        """释放锁"""
        pass
    
    @abstractmethod
    async def renew(self, lock_name: str, owner_id: str, 
                    new_expire_time: float) -> bool:
        """续期锁"""
        pass
    
    @abstractmethod
    async def is_locked(self, lock_name: str) -> bool:
        """检查锁是否被持有"""
        pass
    
    @abstractmethod
    async def get_owner(self, lock_name: str) -> Optional[LockOwner]:
        """获取锁的持有者信息"""
        pass


class InMemoryLockBackend(DistributedLockBackend):
    """内存锁后端实现"""
    
    def __init__(self):
        self._locks: Dict[str, LockOwner] = {}
        self._lock_types: Dict[str, LockType] = {}
    
    async def acquire(self, lock_name: str, owner_id: str,
                      lock_type: LockType, timeout: float,
                      expire_time: float) -> bool:
        current_time = time.time()
        
        if lock_name in self._locks:
            existing_owner = self._locks[lock_name]
            if not existing_owner.is_expired(current_time):
                return False
        
        lock_owner = LockOwner(
            owner_id=owner_id,
            lock_type=lock_type,
            acquire_time=current_time,
            expire_time=expire_time
        )
        self._locks[lock_name] = lock_owner
        self._lock_types[lock_name] = lock_type
        return True
    
    async def release(self, lock_name: str, owner_id: str) -> bool:
        if lock_name not in self._locks:
            return False
        
        owner = self._locks[lock_name]
        if owner.owner_id != owner_id:
            return False
        
        del self._locks[lock_name]
        del self._lock_types[lock_name]
        return True
    
    async def renew(self, lock_name: str, owner_id: str,
                    new_expire_time: float) -> bool:
        if lock_name not in self._locks:
            return False
        
        owner = self._locks[lock_name]
        if owner.owner_id != owner_id:
            return False
        
        owner.expire_time = new_expire_time
        owner.renewals += 1
        return True
    
    async def is_locked(self, lock_name: str) -> bool:
        if lock_name not in self._locks:
            return False
        owner = self._locks[lock_name]
        return not owner.is_expired(time.time())
    
    async def get_owner(self, lock_name: str) -> Optional[LockOwner]:
        return self._locks.get(lock_name)
    
    def cleanup_expired(self):
        """清理过期的锁"""
        current_time = time.time()
        expired = [
            name for name, owner in self._locks.items()
            if owner.is_expired(current_time)
        ]
        for name in expired:
            del self._locks[name]
            del self._lock_types[name]


class ReadWriteLockBackend(InMemoryLockBackend):
    """读写锁后端实现"""
    
    def __init__(self):
        super().__init__()
        self._read_locks: Dict[str, Set[str]] = {}
        self._write_lock: Optional[str] = None
    
    async def acquire(self, lock_name: str, owner_id: str,
                      lock_type: LockType, timeout: float,
                      expire_time: float) -> bool:
        current_time = time.time()
        
        if lock_type == LockType.WRITE:
            # 写锁需要独占
            if self._write_lock and self._write_lock != lock_name:
                existing_owner = self._locks.get(self._write_lock)
                if existing_owner and not existing_owner.is_expired(current_time):
                    return False
            
            # 检查是否有读锁
            if lock_name in self._read_locks and self._read_locks[lock_name]:
                return False
            
            # 检查是否有其他写锁
            if self._locks.get(lock_name):
                existing_owner = self._locks[lock_name]
                if (existing_owner.lock_type == LockType.WRITE and 
                    not existing_owner.is_expired(current_time)):
                    return False
            
        elif lock_type == LockType.READ:
            # 读锁可以并发，但如果有写锁则需要等待
            if self._write_lock and self._write_lock == lock_name:
                existing_owner = self._locks.get(lock_name)
                if existing_owner and not existing_owner.is_expired(current_time):
                    return False
            
            # 检查是否有写锁
            if self._locks.get(lock_name):
                existing_owner = self._locks[lock_name]
                if (existing_owner.lock_type == LockType.WRITE and 
                    not existing_owner.is_expired(current_time)):
                    return False
        
        # 获取锁
        lock_owner = LockOwner(
            owner_id=owner_id,
            lock_type=lock_type,
            acquire_time=current_time,
            expire_time=expire_time
        )
        self._locks[lock_name] = lock_owner
        self._lock_types[lock_name] = lock_type
        
        if lock_type == LockType.WRITE:
            self._write_lock = lock_name
        else:
            if lock_name not in self._read_locks:
                self._read_locks[lock_name] = set()
            self._read_locks[lock_name].add(owner_id)
        
        return True
    
    async def release(self, lock_name: str, owner_id: str) -> bool:
        if lock_name not in self._locks:
            return False
        
        owner = self._locks[lock_name]
        if owner.owner_id != owner_id:
            return False
        
        lock_type = owner.lock_type
        
        del self._locks[lock_name]
        del self._lock_types[lock_name]
        
        if lock_type == LockType.WRITE:
            self._write_lock = None
        elif lock_type == LockType.READ and lock_name in self._read_locks:
            self._read_locks[lock_name].discard(owner_id)
            if not self._read_locks[lock_name]:
                del self._read_locks[lock_name]
        
        return True


class DistributedLock:
    """分布式锁"""
    
    def __init__(self, backend: Optional[DistributedLockBackend] = None):
        self._backend = backend or InMemoryLockBackend()
        self._default_timeout = 30.0  # 默认超时时间
        self._default_expire = 60.0   # 默认过期时间
        self._renewal_interval = 0.7  # 续期间隔（相对于过期时间的比例）
    
    @property
    def backend(self) -> DistributedLockBackend:
        return self._backend
    
    def set_defaults(self, timeout: float, expire: float, 
                     renewal_interval: float = 0.7):
        """设置默认值"""
        self._default_timeout = timeout
        self._default_expire = expire
        self._renewal_interval = renewal_interval
    
    async def acquire_mutex(self, lock_name: str, owner_id: Optional[str] = None,
                            timeout: Optional[float] = None,
                            expire: Optional[float] = None) -> str:
        """获取互斥锁
        
        Args:
            lock_name: 锁名称
            owner_id: 持有者ID（可选，默认自动生成）
            timeout: 获取锁的超时时间
            expire: 锁的过期时间
        
        Returns:
            持有者ID
        
        Raises:
            LockTimeoutError: 获取锁超时
        """
        owner_id = owner_id or str(uuid.uuid4())
        timeout = timeout or self._default_timeout
        expire = expire or self._default_expire
        
        expire_time = time.time() + expire
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            acquired = await self._backend.acquire(
                lock_name, owner_id, LockType.MUTEX, timeout, expire_time
            )
            if acquired:
                return owner_id
            await asyncio.sleep(0.01)
        
        raise LockTimeoutError(f"Failed to acquire mutex lock '{lock_name}' within {timeout}s")
    
    async def acquire_read_lock(self, lock_name: str, owner_id: Optional[str] = None,
                                 timeout: Optional[float] = None,
                                 expire: Optional[float] = None) -> str:
        """获取读锁
        
        Args:
            lock_name: 锁名称
            owner_id: 持有者ID（可选，默认自动生成）
            timeout: 获取锁的超时时间
            expire: 锁的过期时间
        
        Returns:
            持有者ID
        
        Raises:
            LockTimeoutError: 获取锁超时
        """
        owner_id = owner_id or str(uuid.uuid4())
        timeout = timeout or self._default_timeout
        expire = expire or self._default_expire
        
        expire_time = time.time() + expire
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            acquired = await self._backend.acquire(
                lock_name, owner_id, LockType.READ, timeout, expire_time
            )
            if acquired:
                return owner_id
            await asyncio.sleep(0.01)
        
        raise LockTimeoutError(f"Failed to acquire read lock '{lock_name}' within {timeout}s")
    
    async def acquire_write_lock(self, lock_name: str, owner_id: Optional[str] = None,
                                  timeout: Optional[float] = None,
                                  expire: Optional[float] = None) -> str:
        """获取写锁
        
        Args:
            lock_name: 锁名称
            owner_id: 持有者ID（可选，默认自动生成）
            timeout: 获取锁的超时时间
            expire: 锁的过期时间
        
        Returns:
            持有者ID
        
        Raises:
            LockTimeoutError: 获取锁超时
        """
        owner_id = owner_id or str(uuid.uuid4())
        timeout = timeout or self._default_timeout
        expire = expire or self._default_expire
        
        expire_time = time.time() + expire
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            acquired = await self._backend.acquire(
                lock_name, owner_id, LockType.WRITE, timeout, expire_time
            )
            if acquired:
                return owner_id
            await asyncio.sleep(0.01)
        
        raise LockTimeoutError(f"Failed to acquire write lock '{lock_name}' within {timeout}s")
    
    async def release(self, lock_name: str, owner_id: str) -> bool:
        """释放锁"""
        return await self._backend.release(lock_name, owner_id)
    
    async def renew(self, lock_name: str, owner_id: str,
                    expire: Optional[float] = None) -> bool:
        """续期锁
        
        Args:
            lock_name: 锁名称
            owner_id: 持有者ID
            expire: 新的过期时间（从当前时间算起）
        
        Returns:
            是否续期成功
        """
        expire = expire or self._default_expire
        new_expire_time = time.time() + expire
        return await self._backend.renew(lock_name, owner_id, new_expire_time)
    
    async def renew_periodically(self, lock_name: str, owner_id: str,
                                  expire: Optional[float] = None,
                                  interval: Optional[float] = None,
                                  callback: Optional[Callable] = None) -> asyncio.Task:
        """定期续期锁
        
        Args:
            lock_name: 锁名称
            owner_id: 持有者ID
            expire: 过期时间
            interval: 续期间隔
            callback: 续期回调函数
        
        Returns:
            asyncio.Task 对象，可用于取消续期
        """
        expire = expire or self._default_expire
        interval = interval or (expire * self._renewal_interval)
        
        async def renewal_loop():
            try:
                while True:
                    await asyncio.sleep(interval)
                    success = await self.renew(lock_name, owner_id, expire)
                    if callback:
                        callback(success, lock_name, owner_id)
                    if not success:
                        break
            except asyncio.CancelledError:
                pass
        
        return asyncio.create_task(renewal_loop())
    
    async def is_locked(self, lock_name: str) -> bool:
        """检查锁是否被持有"""
        return await self._backend.is_locked(lock_name)
    
    async def get_lock_info(self, lock_name: str) -> Optional[Dict[str, Any]]:
        """获取锁信息"""
        owner = await self._backend.get_owner(lock_name)
        if not owner:
            return None
        
        return {
            "lock_name": lock_name,
            "owner_id": owner.owner_id,
            "lock_type": owner.lock_type.value,
            "acquire_time": owner.acquire_time,
            "expire_time": owner.expire_time,
            "renewals": owner.renewals,
            "is_expired": owner.is_expired(time.time())
        }
    
    @contextmanager
    async def mutex_lock(self, lock_name: str, owner_id: Optional[str] = None,
                         timeout: Optional[float] = None,
                         expire: Optional[float] = None):
        """互斥锁上下文管理器"""
        owner_id = await self.acquire_mutex(lock_name, owner_id, timeout, expire)
        try:
            yield owner_id
        finally:
            await self.release(lock_name, owner_id)
    
    @contextmanager
    async def read_lock(self, lock_name: str, owner_id: Optional[str] = None,
                        timeout: Optional[float] = None,
                        expire: Optional[float] = None):
        """读锁上下文管理器"""
        owner_id = await self.acquire_read_lock(lock_name, owner_id, timeout, expire)
        try:
            yield owner_id
        finally:
            await self.release(lock_name, owner_id)
    
    @contextmanager
    async def write_lock(self, lock_name: str, owner_id: Optional[str] = None,
                         timeout: Optional[float] = None,
                         expire: Optional[float] = None):
        """写锁上下文管理器"""
        owner_id = await self.acquire_write_lock(lock_name, owner_id, timeout, expire)
        try:
            yield owner_id
        finally:
            await self.release(lock_name, owner_id)


class ReadWriteLock:
    """读写锁封装"""
    
    def __init__(self, backend: Optional[ReadWriteLockBackend] = None):
        self._backend = backend or ReadWriteLockBackend()
        self._default_timeout = 30.0
        self._default_expire = 60.0
    
    @property
    def backend(self) -> ReadWriteLockBackend:
        return self._backend
    
    async def acquire_read(self, lock_name: str, owner_id: Optional[str] = None,
                           timeout: Optional[float] = None,
                           expire: Optional[float] = None) -> str:
        """获取读锁"""
        owner_id = owner_id or str(uuid.uuid4())
        timeout = timeout or self._default_timeout
        expire = expire or self._default_expire
        expire_time = time.time() + expire
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            acquired = await self._backend.acquire(
                lock_name, owner_id, LockType.READ, timeout, expire_time
            )
            if acquired:
                return owner_id
            await asyncio.sleep(0.01)
        
        raise LockTimeoutError(f"Failed to acquire read lock '{lock_name}' within {timeout}s")
    
    async def acquire_write(self, lock_name: str, owner_id: Optional[str] = None,
                            timeout: Optional[float] = None,
                            expire: Optional[float] = None) -> str:
        """获取写锁"""
        owner_id = owner_id or str(uuid.uuid4())
        timeout = timeout or self._default_timeout
        expire = expire or self._default_expire
        expire_time = time.time() + expire
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            acquired = await self._backend.acquire(
                lock_name, owner_id, LockType.WRITE, timeout, expire_time
            )
            if acquired:
                return owner_id
            await asyncio.sleep(0.01)
        
        raise LockTimeoutError(f"Failed to acquire write lock '{lock_name}' within {timeout}s")
    
    async def release_read(self, lock_name: str, owner_id: str) -> bool:
        """释放读锁"""
        return await self._backend.release(lock_name, owner_id)
    
    async def release_write(self, lock_name: str, owner_id: str) -> bool:
        """释放写锁"""
        return await self._backend.release(lock_name, owner_id)
    
    async def renew(self, lock_name: str, owner_id: str,
                    expire: Optional[float] = None) -> bool:
        """续期锁"""
        expire = expire or self._default_expire
        new_expire_time = time.time() + expire
        return await self._backend.renew(lock_name, owner_id, new_expire_time)
    
    @contextmanager
    async def read(self, lock_name: str, owner_id: Optional[str] = None,
                   timeout: Optional[float] = None,
                   expire: Optional[float] = None):
        """读锁上下文管理器"""
        owner_id = await self.acquire_read(lock_name, owner_id, timeout, expire)
        try:
            yield owner_id
        finally:
            await self.release_read(lock_name, owner_id)
    
    @contextmanager
    async def write(self, lock_name: str, owner_id: Optional[str] = None,
                    timeout: Optional[float] = None,
                    expire: Optional[float] = None):
        """写锁上下文管理器"""
        owner_id = await self.acquire_write(lock_name, owner_id, timeout, expire)
        try:
            yield owner_id
        finally:
            await self.release_write(lock_name, owner_id)


def create_distributed_lock(backend: Optional[DistributedLockBackend] = None) -> DistributedLock:
    """创建分布式锁实例"""
    return DistributedLock(backend)


def create_read_write_lock(backend: Optional[ReadWriteLockBackend] = None) -> ReadWriteLock:
    """创建读写锁实例"""
    return ReadWriteLock(backend)
