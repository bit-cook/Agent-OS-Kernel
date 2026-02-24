# -*- coding: utf-8 -*-
"""
Pool Manager Module - 提供通用资源池管理功能

支持:
- 资源池创建和管理
- 资源分配和回收
- 池大小动态调整
- 资源生命周期管理
- 池状态监控
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Generic
from contextlib import contextmanager
from collections import deque
import threading


class PoolState(Enum):
    """池状态"""
    INITIALIZING = "initializing"
    READY = "ready"
    GROWING = "growing"
    SHRINKING = "shrinking"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class ResourceState(Enum):
    """资源状态"""
    AVAILABLE = "available"
    IN_USE = "in_use"
    RESERVED = "reserved"
    RECLAIMING = "reclaiming"
    DISCARDED = "discarded"


@dataclass
class PoolConfig:
    """池配置"""
    min_size: int = 5
    max_size: int = 100
    initial_size: int = 5
    acquire_timeout: float = 30.0
    idle_timeout: float = 300.0
    shrink_interval: float = 60.0
    health_check_interval: float = 30.0
    max_idle_time: float = 600.0
    validate_on_acquire: bool = True
    validate_on_release: bool = True
    preallocate: bool = True


@dataclass
class ResourceInfo:
    """资源信息"""
    resource_id: str
    created_time: float
    last_used_time: float
    last_health_check: float
    use_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PoolError(Exception):
    """池操作基础异常"""
    pass


class PoolAcquireError(PoolError):
    """获取资源失败"""
    pass


class PoolTimeoutError(PoolAcquireError):
    """池操作超时"""
    pass


class PoolExhaustedError(PoolAcquireError):
    """池资源耗尽"""
    pass


class PoolClosedError(PoolError):
    """池已关闭"""
    pass


class ResourceCreateError(PoolError):
    """创建资源失败"""
    pass


class ResourceValidateError(PoolError):
    """资源验证失败"""
    pass


T = TypeVar('T')
R = TypeVar('R')


class PoolResource(Generic[T]):
    """池资源包装器"""
    
    def __init__(self, resource_id: str, resource: T, 
                 config: PoolConfig):
        self.resource_id = resource_id
        self.resource = resource
        self.config = config
        self.state = ResourceState.AVAILABLE
        self.info = ResourceInfo(
            resource_id=resource_id,
            created_time=time.time(),
            last_used_time=time.time(),
            last_health_check=time.time()
        )
        self._lock = threading.Lock()
    
    def mark_used(self) -> None:
        """标记资源为使用中"""
        self.info.last_used_time = time.time()
        self.info.use_count += 1
        self.state = ResourceState.IN_USE
    
    def release(self) -> None:
        """释放资源"""
        self.info.last_used_time = time.time()
        self.state = ResourceState.AVAILABLE
    
    def mark_discarded(self) -> None:
        """标记资源为丢弃"""
        self.state = ResourceState.DISCARDED
    
    def is_expired(self, current_time: float) -> bool:
        """检查资源是否过期"""
        return (current_time - self.info.created_time > self.config.max_idle_time or
                current_time - self.info.last_used_time > self.config.idle_timeout)
    
    def is_healthy(self, current_time: float) -> bool:
        """检查资源是否健康"""
        return (self.state != ResourceState.DISCARDED and
                self.info.error_count < 3 and
                current_time - self.info.last_health_check < self.config.health_check_interval)


class PoolBackend(ABC, Generic[T]):
    """池后端抽象基类"""
    
    @abstractmethod
    async def create(self) -> T:
        """创建新资源"""
        pass
    
    @abstractmethod
    async def destroy(self, resource: T) -> None:
        """销毁资源"""
        pass
    
    @abstractmethod
    async def validate(self, resource: T) -> bool:
        """验证资源有效性"""
        pass
    
    @abstractmethod
    async def reset(self, resource: T) -> None:
        """重置资源状态"""
        pass


class PoolManager(Generic[T]):
    """
    通用资源池管理器
    
    提供资源的管理、分配、回收和生命周期控制
    """
    
    def __init__(self, backend: PoolBackend[T], 
                 config: Optional[PoolConfig] = None):
        self.backend = backend
        self.config = config or PoolConfig()
        self._available: deque = deque()
        self._in_use: Dict[str, PoolResource[T]] = {}
        self._all_resources: Dict[str, PoolResource[T]] = {}
        self._lock = threading.Lock()
        self._state = PoolState.INITIALIZING
        self._closed = False
        self._shrink_task = None
        
    def _generate_id(self) -> str:
        """生成资源ID"""
        return str(uuid.uuid4())
    
    def _create_resource(self) -> PoolResource[T]:
        """创建新资源"""
        resource_id = self._generate_id()
        return PoolResource(resource_id, None, self.config)
    
    async def initialize(self) -> None:
        """初始化资源池"""
        self._state = PoolState.INITIALIZING
        
        # 预分配资源
        if self.config.preallocate:
            for _ in range(self.config.initial_size):
                try:
                    resource = await self.backend.create()
                    pr = self._create_resource()
                    pr.resource = resource
                    self._available.append(pr)
                    self._all_resources[pr.resource_id] = pr
                except Exception as e:
                    # 初始化失败不影响启动
                    pass
        
        self._state = PoolState.READY
    
    async def acquire(self, timeout: Optional[float] = None) -> PoolResource[T]:
        """
        从池中获取资源
        
        Args:
            timeout: 获取超时时间
            
        Returns:
            PoolResource: 可用的资源包装器
            
        Raises:
            PoolTimeoutError: 获取超时
            PoolExhaustedError: 池资源耗尽
            PoolClosedError: 池已关闭
        """
        if self._closed:
            raise PoolClosedError("Pool is closed")
        
        timeout = timeout or self.config.acquire_timeout
        start_time = time.time()
        resource_id = None
        
        while time.time() - start_time < timeout:
            # 尝试从可用队列获取
            with self._lock:
                while self._available:
                    pr = self._available.popleft()
                    current_time = time.time()
                    
                    # 检查资源是否过期
                    if pr.is_expired(current_time):
                        asyncio.create_task(self._discard_resource(pr))
                        continue
                    
                    # 标记为使用中
                    pr.mark_used()
                    self._in_use[pr.resource_id] = pr
                    resource_id = pr.resource_id
                    break
            
            if resource_id:
                break
            
            # 尝试创建新资源
            with self._lock:
                if len(self._all_resources) < self.config.max_size:
                    try:
                        resource = await self.backend.create()
                        pr = self._create_resource()
                        pr.resource = resource
                        pr.mark_used()
                        self._in_use[pr.resource_id] = pr
                        self._all_resources[pr.resource_id] = pr
                        resource_id = pr.resource_id
                        break
                    except Exception:
                        raise ResourceCreateError("Failed to create resource")
            
            # 等待后重试
            await asyncio.sleep(0.01)
        
        if not resource_id:
            raise PoolTimeoutError(
                f"Failed to acquire resource within {timeout} seconds"
            )
        
        pr = self._in_use[resource_id]
        
        # 验证资源
        if self.config.validate_on_acquire:
            try:
                if not await self.backend.validate(pr.resource):
                    await self.release(pr, validate=False)
                    raise ResourceValidateError("Resource validation failed")
            except Exception:
                await self.release(pr, validate=False)
                raise
        
        return pr
    
    async def release(self, pr: PoolResource[T], 
                      validate: Optional[bool] = None) -> None:
        """
        释放资源回池中
        
        Args:
            pr: 要释放的资源
            validate: 是否验证资源，默认使用配置
        """
        if self._closed:
            await self._destroy_resource(pr)
            return
        
        validate = validate if validate is not None else self.config.validate_on_release
        
        # 验证资源
        if validate:
            try:
                if not await self.backend.validate(pr.resource):
                    await self._discard_resource(pr)
                    return
            except Exception:
                await self._discard_resource(pr)
                return
        
        # 检查是否应该丢弃
        current_time = time.time()
        if pr.info.error_count >= 3 or pr.is_expired(current_time):
            await self._discard_resource(pr)
            return
        
        # 重置资源
        try:
            await self.backend.reset(pr.resource)
        except Exception:
            await self._discard_resource(pr)
            return
        
        # 放回池中
        pr.release()
        with self._lock:
            if pr.resource_id in self._in_use:
                del self._in_use[pr.resource_id]
            self._available.append(pr)
    
    async def _discard_resource(self, pr: PoolResource[T]) -> None:
        """丢弃资源"""
        pr.mark_discarded()
        with self._lock:
            if pr.resource_id in self._in_use:
                del self._in_use[pr.resource_id]
            if pr.resource_id in self._all_resources:
                del self._all_resources[pr.resource_id]
        
        try:
            if pr.resource is not None:
                await self.backend.destroy(pr.resource)
        except Exception:
            pass
    
    async def _destroy_resource(self, pr: PoolResource[T]) -> None:
        """销毁资源"""
        try:
            if pr.resource is not None:
                await self.backend.destroy(pr.resource)
        except Exception:
            pass
    
    async def shrink(self) -> int:
        """
        收缩池大小，移除多余的空闲资源
        
        Returns:
            int: 移除的资源数量
        """
        if self._state == PoolState.CLOSED:
            return 0
        
        self._state = PoolState.SHRINKING
        removed_count = 0
        current_time = time.time()
        
        # 计算目标空闲数
        target_idle = min(
            max(self.config.min_size, len(self._in_use)),
            self.config.max_size
        )
        
        with self._lock:
            new_available = deque()
            
            while self._available and len(new_available) < target_idle:
                pr = self._available.popleft()
                
                # 检查资源是否健康
                if pr.is_healthy(current_time):
                    new_available.append(pr)
                else:
                    asyncio.create_task(self._discard_resource(pr))
                    removed_count += 1
            
            self._available = new_available
        
        self._state = PoolState.READY
        return removed_count
    
    async def grow(self, count: int) -> int:
        """
        增长池大小，添加新资源
        
        Args:
            count: 要添加的资源数量
            
        Returns:
            int: 实际添加的资源数量
        """
        if self._state == PoolState.CLOSED:
            return 0
        
        self._state = PoolState.GROWING
        added_count = 0
        current_size = 0
        
        with self._lock:
            current_size = len(self._all_resources)
        
        for i in range(min(count, self.config.max_size - current_size)):
            try:
                resource = await self.backend.create()
                pr = self._create_resource()
                pr.resource = resource
                
                with self._lock:
                    self._available.append(pr)
                    self._all_resources[pr.resource_id] = pr
                
                added_count += 1
            except Exception:
                break
        
        self._state = PoolState.READY
        return added_count
    
    async def health_check(self) -> Dict[str, bool]:
        """
        对所有资源进行健康检查
        
        Returns:
            Dict[str, bool]: 资源ID到健康状态的映射
        """
        results = {}
        current_time = time.time()
        
        with self._lock:
            all_resources = list(self._all_resources.values())
        
        for pr in all_resources:
            try:
                if pr.state == ResourceState.DISCARDED:
                    results[pr.resource_id] = False
                    continue
                
                is_healthy = await self.backend.validate(pr.resource)
                pr.info.last_health_check = current_time
                
                if not is_healthy:
                    pr.info.error_count += 1
                
                results[pr.resource_id] = is_healthy
            except Exception:
                pr.info.error_count += 1
                results[pr.resource_id] = False
        
        return results
    
    async def cleanup_unhealthy(self) -> int:
        """
        清理所有不健康的资源
        
        Returns:
            int: 清理的资源数量
        """
        removed_count = 0
        current_time = time.time()
        
        with self._lock:
            unhealthy_ids = [
                pr.resource_id for pr in self._all_resources.values()
                if not pr.is_healthy(current_time)
            ]
        
        for resource_id in unhealthy_ids:
            with self._lock:
                pr = self._all_resources.pop(resource_id, None)
                if pr and pr.resource_id in self._in_use:
                    del self._in_use[pr.resource_id]
            
            if pr:
                await self._discard_resource(pr)
                removed_count += 1
        
        return removed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取池统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        current_time = time.time()
        
        with self._lock:
            total = len(self._all_resources)
            available = len(self._available)
            in_use = len(self._in_use)
            
            healthy_count = sum(
                1 for pr in self._all_resources.values()
                if pr.is_healthy(current_time)
            )
            
            total_use_count = sum(
                pr.info.use_count for pr in self._all_resources.values()
            )
        
        return {
            "state": self._state.value,
            "total_resources": total,
            "available_resources": available,
            "in_use_resources": in_use,
            "healthy_resources": healthy_count,
            "min_size": self.config.min_size,
            "max_size": self.config.max_size,
            "total_use_count": total_use_count,
            "utilization_rate": in_use / total if total > 0 else 0,
            "is_closed": self._closed,
        }
    
    async def close(self) -> None:
        """
        关闭池，释放所有资源
        """
        if self._closed:
            return
        
        self._closed = True
        self._state = PoolState.CLOSING
        
        # 取消收缩任务
        if self._shrink_task:
            self._shrink_task.cancel()
        
        # 销毁所有资源
        with self._lock:
            all_resources = list(self._all_resources.values())
            self._all_resources.clear()
            self._available.clear()
            self._in_use.clear()
        
        for pr in all_resources:
            await self._destroy_resource(pr)
        
        self._state = PoolState.CLOSED
    
    @contextmanager
    def resource(self, timeout: Optional[float] = None):
        """
        上下文管理器方式获取资源
        
        Usage:
            async with pool.resource() as pr:
                # 使用资源
                resource = pr.resource
                pass
        """
        pr = None
        try:
            loop = asyncio.get_event_loop()
            pr = loop.run_until_complete(self.acquire(timeout))
            yield pr
        finally:
            if pr is not None:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.release(pr))


def create_pool(backend: PoolBackend,
                min_size: int = 5,
                max_size: int = 100,
                initial_size: int = 5,
                acquire_timeout: float = 30.0,
                idle_timeout: float = 300.0,
                validate_on_acquire: bool = True,
                validate_on_release: bool = True) -> PoolManager:
    """
    创建资源池的便捷函数
    
    Args:
        backend: 池后端实现
        min_size: 最小池大小
        max_size: 最大池大小
        initial_size: 初始池大小
        acquire_timeout: 获取超时时间
        idle_timeout: 空闲超时时间
        validate_on_acquire: 获取时验证
        validate_on_release: 释放时验证
        
    Returns:
        PoolManager: 配置好的池管理器实例
    """
    config = PoolConfig(
        min_size=min_size,
        max_size=max_size,
        initial_size=initial_size,
        acquire_timeout=acquire_timeout,
        idle_timeout=idle_timeout,
        validate_on_acquire=validate_on_acquire,
        validate_on_release=validate_on_release
    )
    
    return PoolManager(backend, config)
