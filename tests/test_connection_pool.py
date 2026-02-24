# -*- coding: utf-8 -*-
"""
Connection Pool Tests - 测试连接池功能
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from agent_os_kernel.core.connection_pool import (
    ConnectionPool,
    Connection,
    ConnectionBackend,
    ConnectionConfig,
    ConnectionState,
    ConnectionInfo,
    ConnectionAcquireError,
    ConnectionTimeoutError,
    ConnectionHealthError,
    create_connection_pool,
)


class MockConnectionBackend(ConnectionBackend):
    """模拟连接后端用于测试"""
    
    def __init__(self, healthy: bool = True, connection_count: int = 5):
        self.healthy = healthy
        self.connection_count = connection_count
        self.created_connections = 0
        self.closed_connections = 0
        self.health_check_count = 0
        self.validate_count = 0
    
    async def create_connection(self) -> MagicMock:
        """创建模拟连接"""
        self.created_connections += 1
        mock_conn = MagicMock()
        mock_conn.id = f"mock_conn_{self.created_connections}"
        return mock_conn
    
    async def close_connection(self, connection: MagicMock) -> None:
        """关闭模拟连接"""
        self.closed_connections += 1
    
    async def health_check(self, connection: MagicMock) -> bool:
        """模拟健康检查"""
        self.health_check_count += 1
        return self.healthy
    
    async def validate_connection(self, connection: MagicMock) -> bool:
        """模拟连接验证"""
        self.validate_count += 1
        return self.healthy


@pytest.fixture
def mock_backend():
    """创建模拟后端"""
    return MockConnectionBackend()


@pytest.fixture
def connection_pool(mock_backend):
    """创建连接池"""
    config = ConnectionConfig(
        max_connections=5,
        min_idle_connections=2,
        acquire_timeout=5.0,
        idle_timeout=60.0
    )
    pool = ConnectionPool(mock_backend, config)
    return pool


class TestConnectionPoolBasic:
    """测试连接池基础功能"""
    
    @pytest.mark.asyncio
    async def test_connection_acquire(self, connection_pool, mock_backend):
        """测试连接获取"""
        await connection_pool.initialize()
        
        # 获取连接
        conn = await connection_pool.acquire()
        
        assert conn is not None
        assert conn.connection_id in connection_pool._active_connections
        assert conn.state == ConnectionState.ACTIVE
        assert mock_backend.created_connections >= 1
        
        await connection_pool.release(conn)
    
    @pytest.mark.asyncio
    async def test_connection_release(self, connection_pool, mock_backend):
        """测试连接释放"""
        await connection_pool.initialize()
        
        # 获取并释放连接
        conn = await connection_pool.acquire()
        connection_id = conn.connection_id
        await connection_pool.release(conn)
        
        # 连接应该回到池中
        assert connection_id not in connection_pool._active_connections
        assert conn.state == ConnectionState.IDLE
    
    @pytest.mark.asyncio
    async def test_connection_reuse(self, connection_pool, mock_backend):
        """测试连接复用"""
        await connection_pool.initialize()
        
        # 获取连接
        conn1 = await connection_pool.acquire()
        await connection_pool.release(conn1)
        
        # 复用同一个连接
        conn2 = await connection_pool.acquire()
        
        # 应该是同一个连接对象
        assert conn1.connection_id == conn2.connection_id
        
        await connection_pool.release(conn2)
    
    @pytest.mark.asyncio
    async def test_multiple_connection_acquire(self, connection_pool, mock_backend):
        """测试获取多个连接"""
        await connection_pool.initialize()
        
        connections = []
        for _ in range(3):
            conn = await connection_pool.acquire()
            connections.append(conn)
        
        # 应该能获取多个连接
        assert len(connections) == 3
        assert len(connection_pool._active_connections) == 3
        
        # 释放所有连接
        for conn in connections:
            await connection_pool.release(conn)
        
        assert len(connection_pool._active_connections) == 0


class TestConnectionPoolHealthCheck:
    """测试连接健康检查"""
    
    @pytest.mark.asyncio
    async def test_connection_health_check(self, connection_pool, mock_backend):
        """测试连接健康检查"""
        await connection_pool.initialize()
        
        conn = await connection_pool.acquire()
        
        # 进行健康检查
        is_healthy = await conn.check_health()
        
        assert is_healthy is True
        assert mock_backend.health_check_count >= 1
        
        await connection_pool.release(conn)
    
    @pytest.mark.asyncio
    async def test_health_check_all_connections(self, connection_pool, mock_backend):
        """测试对所有连接进行健康检查"""
        await connection_pool.initialize()
        
        # 获取多个连接
        connections = []
        for _ in range(2):
            conn = await connection_pool.acquire()
            connections.append(conn)
        
        # 释放一些回池中
        for conn in connections[:1]:
            await connection_pool.release(conn)
        
        # 健康检查所有
        results = await connection_pool.health_check_all()
        
        assert len(results) >= 2
        for is_healthy in results.values():
            assert is_healthy is True
        
        # 清理
        for conn in connections:
            await connection_pool.release(conn)
    
    @pytest.mark.asyncio
    async def test_unhealthy_connection_removal(self, connection_pool, mock_backend):
        """测试移除不健康的连接"""
        # 设置后端为不健康
        mock_backend.healthy = False
        
        await connection_pool.initialize()
        
        conn = await connection_pool.acquire()
        await connection_pool.release(conn)
        
        # 移除不健康连接
        removed_count = await connection_pool.remove_unhealthy()
        
        assert removed_count >= 1


class TestConnectionPoolTimeout:
    """测试连接超时功能"""
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, connection_pool, mock_backend):
        """测试获取连接超时"""
        # 设置很小的获取超时
        connection_pool.config.acquire_timeout = 0.1
        
        # 设置max_connections为0来强制超时
        connection_pool.config.max_connections = 0
        
        # 应该抛出超时异常
        with pytest.raises(ConnectionTimeoutError):
            await connection_pool.acquire(timeout=0.05)
    
    @pytest.mark.asyncio
    async def test_connection_idle_timeout(self, connection_pool, mock_backend):
        """测试连接空闲超时"""
        # 设置很短的空闲超时
        connection_pool.config.idle_timeout = 0.1
        
        await connection_pool.initialize()
        
        conn = await connection_pool.acquire()
        await connection_pool.release(conn)
        
        # 等待超时
        time.sleep(0.15)
        
        # 获取连接（应该创建新的，因为旧的已超时）
        conn2 = await connection_pool.acquire()
        
        # 应该是新的连接
        assert conn2.connection_id != conn.connection_id
        
        await connection_pool.release(conn2)
    
    @pytest.mark.asyncio
    async def test_acquire_with_custom_timeout(self, connection_pool, mock_backend):
        """测试使用自定义超时获取连接"""
        await connection_pool.initialize()
        
        # 使用自定义超时
        conn = await connection_pool.acquire(timeout=5.0)
        
        assert conn is not None
        assert conn.state == ConnectionState.ACTIVE
        
        await connection_pool.release(conn)


class TestConnectionPoolStats:
    """测试连接池统计功能"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, connection_pool, mock_backend):
        """测试获取统计信息"""
        await connection_pool.initialize()
        
        stats = connection_pool.get_stats()
        
        assert "total_connections" in stats
        assert "idle_connections" in stats
        assert "active_connections" in stats
        assert "max_connections" in stats
        assert stats["max_connections"] == 5
        assert stats["min_idle_connections"] == 2
    
    @pytest.mark.asyncio
    async def test_stats_after_acquire(self, connection_pool, mock_backend):
        """测试获取连接后的统计"""
        await connection_pool.initialize()
        
        stats_before = connection_pool.get_stats()
        
        conn = await connection_pool.acquire()
        
        stats_during = connection_pool.get_stats()
        
        await connection_pool.release(conn)
        
        stats_after = connection_pool.get_stats()
        
        # 获取连接后活跃数应该增加
        assert stats_during["active_connections"] > stats_before["active_connections"]
        assert stats_during["idle_connections"] < stats_before["idle_connections"]


class TestConnectionPoolClose:
    """测试连接池关闭功能"""
    
    @pytest.mark.asyncio
    async def test_close_all_connections(self, connection_pool, mock_backend):
        """测试关闭所有连接"""
        await connection_pool.initialize()
        
        # 获取一些连接
        connections = []
        for _ in range(2):
            conn = await connection_pool.acquire()
            connections.append(conn)
        
        # 关闭所有
        await connection_pool.close_all()
        
        # 所有连接应该被关闭
        assert len(connection_pool._active_connections) == 0
        assert len(connection_pool._connections) == 0
        assert mock_backend.closed_connections >= 2
    
    @pytest.mark.asyncio
    async def test_release_after_close(self, connection_pool, mock_backend):
        """测试关闭后释放连接"""
        await connection_pool.initialize()
        
        conn = await connection_pool.acquire()
        
        # 关闭连接池
        await connection_pool.close_all()
        
        # 释放连接（应该被关闭而不是放回池中）
        await connection_pool.release(conn)
        
        assert conn.state == ConnectionState.CLOSED


class TestCreateConnectionPool:
    """测试创建连接池函数"""
    
    def test_create_connection_pool_defaults(self):
        """测试默认参数创建连接池"""
        backend = MockConnectionBackend()
        pool = create_connection_pool(backend)
        
        assert pool is not None
        assert pool.config.max_connections == 10
        assert pool.config.min_idle_connections == 2
        assert pool.config.acquire_timeout == 10.0
    
    def test_create_connection_pool_custom(self):
        """测试自定义参数创建连接池"""
        backend = MockConnectionBackend()
        pool = create_connection_pool(
            backend,
            max_connections=20,
            min_idle_connections=5,
            acquire_timeout=30.0
        )
        
        assert pool.config.max_connections == 20
        assert pool.config.min_idle_connections == 5
        assert pool.config.acquire_timeout == 30.0


class TestConnectionInfo:
    """测试连接信息"""
    
    def test_connection_info_healthy(self):
        """测试健康连接"""
        info = ConnectionInfo(
            connection_id="test_id",
            created_time=time.time(),
            last_used_time=time.time(),
            last_health_check=time.time()
        )
        
        current_time = time.time()
        is_healthy = info.is_healthy(current_time, 60.0)
        
        assert is_healthy is True
    
    def test_connection_info_error(self):
        """测试错误连接"""
        info = ConnectionInfo(
            connection_id="test_id",
            created_time=time.time(),
            last_used_time=time.time(),
            last_health_check=time.time(),
            error_count=1
        )
        
        current_time = time.time()
        is_healthy = info.is_healthy(current_time, 60.0)
        
        assert is_healthy is False


class TestConnectionPoolReplenish:
    """测试连接池补充功能"""
    
    @pytest.mark.asyncio
    async def test_replenish_idle_connections(self, connection_pool, mock_backend):
        """测试补充空闲连接"""
        await connection_pool.initialize()
        
        # 获取所有空闲连接
        initial_idle = len(connection_pool._connections)
        
        # 设置最小空闲数为5
        connection_pool.config.min_idle_connections = 5
        
        # 补充
        replenished = await connection_pool.replenish_idle()
        
        # 应该补充了连接
        assert replenished > 0 or len(connection_pool._connections) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
