# -*- coding: utf-8 -*-
"""
Connection Pool Module - 提供连接池功能

支持:
- 连接管理
- 连接复用
- 连接健康检查
- 连接超时
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar
from contextlib import contextmanager
from collections import deque
import threading


class ConnectionState(Enum):
    """连接状态"""
    IDLE = "idle"
    ACTIVE = "active"
    CHECKING = "checking"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class ConnectionConfig:
    """连接配置"""
    max_connections: int = 10
    min_idle_connections: int = 2
    connection_timeout: float = 30.0
    acquire_timeout: float = 10.0
    idle_timeout: float = 300.0
    health_check_interval: float = 60.0
    max_retries: int = 3
    retry_delay: float = 0.1


@dataclass
class ConnectionInfo:
    """连接信息"""
    connection_id: str
    created_time: float
    last_used_time: float
    last_health_check: float
    use_count: int = 0
    error_count: int = 0
    
    def is_healthy(self, current_time: float, 
                   health_check_interval: float) -> bool:
        """检查连接是否健康"""
        return (current_time - self.last_health_check < health_check_interval and
                self.error_count == 0)


class ConnectionCreateError(Exception):
    """创建连接失败异常"""
    pass


class ConnectionAcquireError(Exception):
    """获取连接失败异常"""
    pass


class ConnectionTimeoutError(ConnectionAcquireError):
    """连接获取超时异常"""
    pass


class ConnectionHealthError(Exception):
    """连接健康检查失败异常"""
    pass


T = TypeVar('T', bound='Connection')


class ConnectionBackend(ABC):
    """连接后端抽象基类"""
    
    @abstractmethod
    async def create_connection(self) -> Any:
        """创建新连接"""
        pass
    
    @abstractmethod
    async def close_connection(self, connection: Any) -> None:
        """关闭连接"""
        pass
    
    @abstractmethod
    async def health_check(self, connection: Any) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    async def validate_connection(self, connection: Any) -> bool:
        """验证连接是否有效"""
        pass


class Connection(ABC):
    """连接基类"""
    
    def __init__(self, connection_id: str, backend: ConnectionBackend,
                 config: ConnectionConfig):
        self.connection_id = connection_id
        self.backend = backend
        self.config = config
        self.state = ConnectionState.IDLE
        self.info = ConnectionInfo(
            connection_id=connection_id,
            created_time=time.time(),
            last_used_time=time.time(),
            last_health_check=time.time()
        )
        self._connection = None
        self._lock = threading.Lock()
    
    async def get_connection(self) -> Any:
        """获取实际连接对象"""
        if self._connection is None:
            self._connection = await self.backend.create_connection()
        return self._connection
    
    async def close(self) -> None:
        """关闭连接"""
        with self._lock:
            if self._connection is not None:
                await self.backend.close_connection(self._connection)
                self._connection = None
                self.state = ConnectionState.CLOSED
    
    async def check_health(self) -> bool:
        """检查连接健康状态"""
        self.state = ConnectionState.CHECKING
        try:
            connection = await self.get_connection()
            is_healthy = await self.backend.health_check(connection)
            self.info.last_health_check = time.time()
            if is_healthy:
                self.state = ConnectionState.IDLE
            else:
                self.state = ConnectionState.ERROR
                self.info.error_count += 1
            return is_healthy
        except Exception as e:
            self.state = ConnectionState.ERROR
            self.info.error_count += 1
            return False
    
    async def validate(self) -> bool:
        """验证连接是否有效"""
        try:
            connection = await self.get_connection()
            return await self.backend.validate_connection(connection)
        except Exception:
            return False
    
    def mark_used(self) -> None:
        """标记连接已被使用"""
        self.info.last_used_time = time.time()
        self.info.use_count += 1
        self.state = ConnectionState.ACTIVE
    
    def release(self) -> None:
        """释放连接回到池中"""
        self.info.last_used_time = time.time()
        self.state = ConnectionState.IDLE


class ConnectionPool:
    """
    连接池管理器
    
    提供连接的管理、复用、健康检查和超时处理
    """
    
    def __init__(self, backend: ConnectionBackend, 
                 config: Optional[ConnectionConfig] = None):
        self.backend = backend
        self.config = config or ConnectionConfig()
        self._connections: deque = deque()
        self._active_connections: Dict[str, Connection] = {}
        self._lock = threading.Lock()
        self._acquire_lock = asyncio.Lock()
        self._closed = False
        self._health_check_task = None
        
    def _create_connection(self) -> Connection:
        """创建新连接"""
        connection_id = str(uuid.uuid4())
        return Connection(connection_id, self.backend, self.config)
    
    async def initialize(self) -> None:
        """初始化连接池，创建最小连接数"""
        for _ in range(self.config.min_idle_connections):
            conn = self._create_connection()
            self._connections.append(conn)
    
    async def acquire(self, timeout: Optional[float] = None) -> Connection:
        """
        从池中获取连接
        
        Args:
            timeout: 获取超时时间，默认使用配置中的 acquire_timeout
            
        Returns:
            Connection: 可用的连接对象
            
        Raises:
            ConnectionTimeoutError: 获取连接超时
            ConnectionAcquireError: 获取连接失败
        """
        timeout = timeout or self.config.acquire_timeout
        start_time = time.time()
        
        # 尝试从池中获取可用连接
        while time.time() - start_time < timeout:
            with self._lock:
                # 查找可用的健康连接
                while self._connections:
                    conn = self._connections.popleft()
                    current_time = time.time()
                    
                    # 检查连接是否过期
                    if (current_time - conn.info.created_time > self.config.idle_timeout or
                        current_time - conn.info.last_used_time > self.config.idle_timeout):
                        # 连接已过期，关闭并继续查找
                        asyncio.create_task(conn.close())
                        continue
                    
                    # 标记连接为活跃
                    conn.mark_used()
                    self._active_connections[conn.connection_id] = conn
                    return conn
            
            # 池中没有可用连接，尝试创建新连接
            if len(self._active_connections) < self.config.max_connections:
                try:
                    conn = self._create_connection()
                    await conn.get_connection()  # 确保连接可以创建
                    conn.mark_used()
                    with self._lock:
                        self._active_connections[conn.connection_id] = conn
                    return conn
                except Exception as e:
                    raise ConnectionAcquireError(f"Failed to create connection: {e}")
            
            # 连接数已达上限，等待
            await asyncio.sleep(0.01)
        
        raise ConnectionTimeoutError(
            f"Failed to acquire connection within {timeout} seconds"
        )
    
    async def release(self, connection: Connection) -> None:
        """
        将连接释放回池中
        
        Args:
            connection: 要释放的连接对象
        """
        if self._closed:
            await connection.close()
            return
        
        with self._lock:
            if connection.connection_id in self._active_connections:
                del self._active_connections[connection.connection_id]
            
            # 检查连接是否仍然健康
            current_time = time.time()
            if (current_time - connection.info.created_time > self.config.idle_timeout or
                connection.info.error_count >= self.config.max_retries):
                # 连接不健康，关闭
                await connection.close()
                return
            
            # 检查是否需要关闭多余的空闲连接
            idle_count = len([c for c in self._connections 
                             if c.state == ConnectionState.IDLE])
            
            if idle_count < self.config.min_idle_connections:
                connection.release()
                self._connections.append(connection)
            else:
                await connection.close()
    
    @contextmanager
    def connection(self, timeout: Optional[float] = None):
        """
        上下文管理器方式获取连接
        
        Usage:
            async with pool.connection() as conn:
                # 使用连接
                pass
        """
        conn = None
        try:
            loop = asyncio.get_event_loop()
            conn = loop.run_until_complete(self.acquire(timeout))
            yield conn
        finally:
            if conn is not None:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.release(conn))
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        对所有连接进行健康检查
        
        Returns:
            Dict[str, bool]: 连接ID到健康状态的映射
        """
        results = {}
        
        with self._lock:
            all_connections = list(self._connections) + list(
                self._active_connections.values()
            )
        
        for conn in all_connections:
            try:
                is_healthy = await conn.check_health()
                results[conn.connection_id] = is_healthy
            except Exception:
                results[conn.connection_id] = False
        
        return results
    
    async def remove_unhealthy(self) -> int:
        """
        移除所有不健康的连接
        
        Returns:
            int: 移除的连接数量
        """
        removed_count = 0
        current_time = time.time()
        
        with self._lock:
            # 检查并移除不健康的空闲连接
            new_connections = deque()
            while self._connections:
                conn = self._connections.popleft()
                
                if conn.info.is_healthy(current_time, self.config.health_check_interval):
                    new_connections.append(conn)
                else:
                    asyncio.create_task(conn.close())
                    removed_count += 1
            
            self._connections = new_connections
        
        # 检查活跃连接
        with self._lock:
            unhealthy_active = []
            for conn in self._active_connections.values():
                if not conn.info.is_healthy(current_time, self.config.health_check_interval):
                    unhealthy_active.append(conn.connection_id)
            
            for conn_id in unhealthy_active:
                conn = self._active_connections.pop(conn_id)
                asyncio.create_task(conn.close())
                removed_count += 1
        
        return removed_count
    
    async def replenish_idle(self) -> int:
        """
        补充空闲连接至最小数量
        
        Returns:
            int: 补充的连接数量
        """
        current_time = time.time()
        idle_count = 0
        
        with self._lock:
            for conn in self._connections:
                if conn.state == ConnectionState.IDLE:
                    if conn.info.is_healthy(current_time, self.config.health_check_interval):
                        idle_count += 1
                    else:
                        self._connections.remove(conn)
                        asyncio.create_task(conn.close())
        
        while idle_count < self.config.min_idle_connections:
            try:
                conn = self._create_connection()
                await conn.get_connection()
                conn.release()
                with self._lock:
                    self._connections.append(conn)
                idle_count += 1
                replenished_count += 1
            except Exception:
                break
        
        return replenished_count
    
    async def close_all(self) -> None:
        """
        关闭所有连接并清理资源
        """
        self._closed = True
        
        # 取消健康检查任务
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # 关闭所有活跃连接
        with self._lock:
            active_connections = list(self._active_connections.values())
            self._active_connections.clear()
            self._connections.clear()
        
        for conn in active_connections:
            await conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接池统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        current_time = time.time()
        
        with self._lock:
            idle_count = len([c for c in self._connections 
                             if c.state == ConnectionState.IDLE])
            active_count = len(self._active_connections)
            total_count = idle_count + active_count
            
            healthy_count = sum(
                1 for c in list(self._connections) + list(self._active_connections.values())
                if c.info.is_healthy(current_time, self.config.health_check_interval)
            )
        
        return {
            "total_connections": total_count,
            "idle_connections": idle_count,
            "active_connections": active_count,
            "healthy_connections": healthy_count,
            "max_connections": self.config.max_connections,
            "min_idle_connections": self.config.min_idle_connections,
            "connection_timeout": self.config.connection_timeout,
            "acquire_timeout": self.config.acquire_timeout,
            "idle_timeout": self.config.idle_timeout,
        }


def create_connection_pool(backend: ConnectionBackend,
                           max_connections: int = 10,
                           min_idle_connections: int = 2,
                           connection_timeout: float = 30.0,
                           acquire_timeout: float = 10.0,
                           idle_timeout: float = 300.0,
                           health_check_interval: float = 60.0) -> ConnectionPool:
    """
    创建连接池的便捷函数
    
    Args:
        backend: 连接后端实现
        max_connections: 最大连接数
        min_idle_connections: 最小空闲连接数
        connection_timeout: 连接超时时间
        acquire_timeout: 获取连接超时时间
        idle_timeout: 空闲超时时间
        health_check_interval: 健康检查间隔
        
    Returns:
        ConnectionPool: 配置好的连接池实例
    """
    config = ConnectionConfig(
        max_connections=max_connections,
        min_idle_connections=min_idle_connections,
        connection_timeout=connection_timeout,
        acquire_timeout=acquire_timeout,
        idle_timeout=idle_timeout,
        health_check_interval=health_check_interval
    )
    
    return ConnectionPool(backend, config)
