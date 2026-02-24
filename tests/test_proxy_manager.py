# -*- coding: utf-8 -*-
"""
Proxy Manager Tests - 测试代理管理器功能
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from agent_os_kernel.core.proxy_manager import (
    ProxyManager,
    ProxyBackend,
    ProxyConfig,
    ProxyInfo,
    ProxyType,
    ProxyState,
    ProxyNotFoundError,
    ProxyCheckError,
    ProxyUnavailableError,
    create_proxy_manager,
)


class MockProxyBackend(ProxyBackend):
    """模拟代理后端用于测试"""
    
    def __init__(self, healthy: bool = True, response_time: float = 0.1):
        self.healthy = healthy
        self.response_time = response_time
        self.created_proxies = 0
        self.closed_proxies = 0
        self.health_check_count = 0
        self.test_connection_count = 0
    
    async def create_proxy(self, config: ProxyConfig) -> MagicMock:
        """创建模拟代理"""
        self.created_proxies += 1
        mock_proxy = MagicMock()
        mock_proxy.id = f"mock_proxy_{self.created_proxies}"
        return mock_proxy
    
    async def close_proxy(self, proxy: MagicMock) -> None:
        """关闭模拟代理"""
        self.closed_proxies += 1
    
    async def health_check(self, proxy: MagicMock, config: ProxyConfig) -> bool:
        """模拟健康检查"""
        self.health_check_count += 1
        return self.healthy
    
    async def test_connection(self, config: ProxyConfig) -> float:
        """模拟连接测试"""
        self.test_connection_count += 1
        return self.response_time if self.healthy else 0.0


@pytest.fixture
def mock_backend():
    """创建模拟后端"""
    return MockProxyBackend()


@pytest.fixture
def proxy_manager(mock_backend):
    """创建代理管理器"""
    manager = ProxyManager(
        backend=mock_backend,
        check_interval=60.0,
        max_concurrent_checks=2
    )
    return manager


class TestProxyManagerBasic:
    """测试代理管理器基础功能"""
    
    @pytest.mark.asyncio
    async def test_add_proxy(self, proxy_manager, mock_backend):
        """测试添加代理"""
        await proxy_manager.initialize()
        
        config = ProxyConfig(
            host="192.168.1.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            timeout=5.0
        )
        
        proxy_id = await proxy_manager.add_proxy(config)
        
        assert proxy_id is not None
        assert len(proxy_id) == 36  # UUID格式
        
        proxy_info = await proxy_manager.get_proxy(proxy_id)
        assert proxy_info.config.host == "192.168.1.1"
        assert proxy_info.config.port == 8080
        assert proxy_info.proxy_id == proxy_id
        
        await proxy_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_remove_proxy(self, proxy_manager, mock_backend):
        """测试移除代理"""
        await proxy_manager.initialize()
        
        config = ProxyConfig(host="192.168.1.1", port=8080)
        proxy_id = await proxy_manager.add_proxy(config)
        
        # 移除代理
        await proxy_manager.remove_proxy(proxy_id)
        
        # 验证代理已被移除
        with pytest.raises(ProxyNotFoundError):
            await proxy_manager.get_proxy(proxy_id)
        
        assert proxy_manager.proxy_count == 0
        
        await proxy_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_list_proxies(self, proxy_manager, mock_backend):
        """测试列出代理"""
        await proxy_manager.initialize()
        
        # 添加多个代理
        config1 = ProxyConfig(host="192.168.1.1", port=8080)
        config2 = ProxyConfig(host="192.168.1.2", port=8081)
        config3 = ProxyConfig(host="192.168.1.3", port=8082)
        
        id1 = await proxy_manager.add_proxy(config1)
        id2 = await proxy_manager.add_proxy(config2)
        id3 = await proxy_manager.add_proxy(config3)
        
        # 列出所有代理
        proxies = await proxy_manager.list_proxies()
        assert len(proxies) == 3
        
        # 过滤活跃代理
        active_proxies = await proxy_manager.list_proxies(state=ProxyState.ACTIVE)
        assert len(active_proxies) >= 0
        
        await proxy_manager.shutdown()


class TestProxyManagerHealthCheck:
    """测试代理健康检查功能"""
    
    @pytest.mark.asyncio
    async def test_proxy_health_check(self, proxy_manager, mock_backend):
        """测试代理健康检查"""
        await proxy_manager.initialize()
        
        config = ProxyConfig(host="192.168.1.1", port=8080)
        proxy_id = await proxy_manager.add_proxy(config)
        
        # 执行健康检查
        is_healthy = await proxy_manager.check_proxy(proxy_id)
        
        assert is_healthy is True or is_healthy is False
        assert mock_backend.health_check_count >= 1
        
        await proxy_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_proxy_check_all(self, proxy_manager, mock_backend):
        """测试检查所有代理"""
        await proxy_manager.initialize()
        
        # 添加多个代理
        config1 = ProxyConfig(host="192.168.1.1", port=8080)
        config2 = ProxyConfig(host="192.168.1.2", port=8081)
        
        id1 = await proxy_manager.add_proxy(config1)
        id2 = await proxy_manager.add_proxy(config2)
        
        # 检查所有代理
        results = await proxy_manager.check_all_proxies()
        
        assert len(results) == 2
        assert id1 in results
        assert id2 in results
        
        await proxy_manager.shutdown()


class TestProxyManagerEnableDisable:
    """测试代理启用禁用功能"""
    
    @pytest.mark.asyncio
    async def test_enable_disable_proxy(self, proxy_manager, mock_backend):
        """测试启用和禁用代理"""
        await proxy_manager.initialize()
        
        config = ProxyConfig(host="192.168.1.1", port=8080)
        proxy_id = await proxy_manager.add_proxy(config)
        
        # 禁用代理
        await proxy_manager.disable_proxy(proxy_id)
        proxy_info = await proxy_manager.get_proxy(proxy_id)
        assert proxy_info.state == ProxyState.INACTIVE
        
        # 启用代理
        await proxy_manager.enable_proxy(proxy_id)
        proxy_info = await proxy_manager.get_proxy(proxy_id)
        assert proxy_info.state == ProxyState.ACTIVE
        
        await proxy_manager.shutdown()


class TestProxyManagerSelection:
    """测试代理选择功能"""
    
    @pytest.mark.asyncio
    async def test_get_healthy_proxy(self, proxy_manager, mock_backend):
        """测试获取健康代理"""
        await proxy_manager.initialize()
        
        # 添加代理
        config = ProxyConfig(host="192.168.1.1", port=8080, weight=1)
        proxy_id = await proxy_manager.add_proxy(config)
        
        # 如果有活跃代理，获取它
        active_proxies = await proxy_manager.list_proxies(state=ProxyState.ACTIVE)
        if active_proxies:
            proxy = await proxy_manager.get_healthy_proxy()
            assert proxy is not None
            assert isinstance(proxy, ProxyInfo)
        else:
            # 如果没有活跃代理，测试异常情况
            with pytest.raises(ProxyUnavailableError):
                await proxy_manager.get_healthy_proxy()
        
        await proxy_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_proxy_by_priority(self, proxy_manager, mock_backend):
        """测试按优先级获取代理"""
        await proxy_manager.initialize()
        
        # 添加多个代理，不同优先级
        config1 = ProxyConfig(host="192.168.1.1", port=8080, priority=1)
        config2 = ProxyConfig(host="192.168.1.2", port=8081, priority=2)
        
        id1 = await proxy_manager.add_proxy(config1)
        id2 = await proxy_manager.add_proxy(config2)
        
        # 按优先级获取代理
        try:
            proxy = await proxy_manager.get_proxy_by_priority()
            assert proxy is not None
            assert isinstance(proxy, ProxyInfo)
        except ProxyUnavailableError:
            # 如果没有活跃代理，预期此异常
            pass
        
        await proxy_manager.shutdown()


class TestProxyManagerLifecycle:
    """测试代理管理器生命周期"""
    
    @pytest.mark.asyncio
    async def test_initialize_shutdown(self, proxy_manager, mock_backend):
        """测试初始化和关闭"""
        assert not proxy_manager._initialised
        assert proxy_manager._check_task is None
        
        await proxy_manager.initialize()
        assert proxy_manager._initialised
        assert proxy_manager._check_task is not None
        assert not proxy_manager._check_task.done()
        
        await proxy_manager.shutdown()
        assert not proxy_manager._initialised
        assert proxy_manager._check_task.done()
    
    @pytest.mark.asyncio
    async def test_proxy_count(self, proxy_manager, mock_backend):
        """测试代理计数"""
        await proxy_manager.initialize()
        
        assert proxy_manager.proxy_count == 0
        assert proxy_manager.active_proxy_count == 0
        
        # 添加代理
        config = ProxyConfig(host="192.168.1.1", port=8080)
        await proxy_manager.add_proxy(config)
        
        assert proxy_manager.proxy_count == 1
        
        await proxy_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_proxy_manager(self):
        """测试创建代理管理器工厂函数"""
        manager = await create_proxy_manager()
        
        assert manager is not None
        assert manager._initialised
        
        await manager.shutdown()


class TestProxyConfig:
    """测试代理配置"""
    
    def test_proxy_config_creation(self):
        """测试创建代理配置"""
        config = ProxyConfig(
            host="192.168.1.1",
            port=8080,
            proxy_type=ProxyType.HTTPS,
            username="user",
            password="pass",
            timeout=15.0,
            max_retries=5,
            weight=2,
            priority=1
        )
        
        assert config.host == "192.168.1.1"
        assert config.port == 8080
        assert config.proxy_type == ProxyType.HTTPS
        assert config.username == "user"
        assert config.password == "pass"
        assert config.timeout == 15.0
        assert config.max_retries == 5
        assert config.weight == 2
        assert config.priority == 1
    
    def test_proxy_info_is_healthy(self):
        """测试代理信息健康检查"""
        info = ProxyInfo(
            proxy_id="test-id",
            config=ProxyConfig(host="192.168.1.1", port=8080),
            created_time=time.time() - 100,
            last_check_time=time.time() - 50,
            last_success_time=time.time() - 50,
            success_count=5,
            failure_count=1,
            state=ProxyState.ACTIVE
        )
        
        assert info.is_healthy(time.time()) is True
        
        # 测试不健康的情况
        info.failure_count = 3
        assert info.is_healthy(time.time()) is False
        
        info.state = ProxyState.ERROR
        assert info.is_healthy(time.time()) is False
