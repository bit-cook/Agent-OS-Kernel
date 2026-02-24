# -*- coding: utf-8 -*-
"""
Proxy Manager Module - 提供代理管理功能

支持:
- 代理配置管理
- 代理池管理
- 代理健康检查
- 代理负载均衡
- 代理故障转移
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar
from collections import deque
import threading


class ProxyType(Enum):
    """代理类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyState(Enum):
    """代理状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHECKING = "checking"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass
class ProxyConfig:
    """代理配置"""
    host: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0
    weight: int = 1  # 用于负载均衡
    priority: int = 0  # 用于优先级排序


@dataclass
class ProxyInfo:
    """代理信息"""
    proxy_id: str
    config: ProxyConfig
    created_time: float
    last_check_time: float
    last_success_time: float
    success_count: int = 0
    failure_count: int = 0
    response_time: float = 0.0
    state: ProxyState = ProxyState.INACTIVE
    error_message: Optional[str] = None
    
    def is_healthy(self, current_time: float, 
                   check_interval: float = 300.0) -> bool:
        """检查代理是否健康"""
        return (self.state == ProxyState.ACTIVE and
                current_time - self.last_check_time < check_interval and
                self.failure_count < 3)


class ProxyCreateError(Exception):
    """创建代理失败异常"""
    pass


class ProxyCheckError(Exception):
    """代理检查失败异常"""
    pass


class ProxyNotFoundError(Exception):
    """代理未找到异常"""
    pass


class ProxyUnavailableError(Exception):
    """代理不可用异常"""
    pass


T = TypeVar('T', bound='ProxyBackend')


class ProxyBackend(ABC):
    """代理后端抽象基类"""
    
    @abstractmethod
    async def create_proxy(self, config: ProxyConfig) -> Any:
        """创建代理连接"""
        pass
    
    @abstractmethod
    async def close_proxy(self, proxy: Any) -> None:
        """关闭代理连接"""
        pass
    
    @abstractmethod
    async def health_check(self, proxy: Any, config: ProxyConfig) -> bool:
        """执行健康检查"""
        pass
    
    @abstractmethod
    async def test_connection(self, config: ProxyConfig) -> float:
        """测试代理连接并返回响应时间"""
        pass


class ProxyManager:
    """代理管理器"""
    
    def __init__(self, backend: Optional[ProxyBackend] = None,
                 check_interval: float = 300.0,
                 max_concurrent_checks: int = 5):
        """
        初始化代理管理器
        
        Args:
            backend: 代理后端实现
            check_interval: 健康检查间隔（秒）
            max_concurrent_checks: 最大并发检查数
        """
        self._backend = backend
        self._check_interval = check_interval
        self._max_concurrent_checks = max_concurrent_checks
        
        self._proxies: Dict[str, ProxyInfo] = {}
        self._proxy_semaphore = asyncio.Semaphore(max_concurrent_checks)
        self._lock = threading.Lock()
        
        self._initialised = False
        self._check_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """初始化代理管理器"""
        if self._initialised:
            return
        
        self._initialised = True
        self._check_task = asyncio.create_task(self._periodic_check())
    
    async def shutdown(self) -> None:
        """关闭代理管理器"""
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有代理
        for proxy_id in list(self._proxies.keys()):
            await self.remove_proxy(proxy_id)
        
        self._initialised = False
    
    async def add_proxy(self, config: ProxyConfig) -> str:
        """
        添加代理
        
        Args:
            config: 代理配置
            
        Returns:
            代理ID
        """
        proxy_id = str(uuid.uuid4())
        
        proxy_info = ProxyInfo(
            proxy_id=proxy_id,
            config=config,
            created_time=time.time(),
            last_check_time=0,
            last_success_time=0
        )
        
        with self._lock:
            self._proxies[proxy_id] = proxy_info
        
        # 执行初始健康检查
        try:
            await self._check_proxy(proxy_id)
        except ProxyCheckError:
            pass
        
        return proxy_id
    
    async def remove_proxy(self, proxy_id: str) -> None:
        """
        移除代理
        
        Args:
            proxy_id: 代理ID
            
        Raises:
            ProxyNotFoundError: 代理不存在
        """
        with self._lock:
            if proxy_id not in self._proxies:
                raise ProxyNotFoundError(f"Proxy {proxy_id} not found")
            
            proxy_info = self._proxies.pop(proxy_id)
        
        # 如果有后端，关闭代理连接
        if self._backend and hasattr(proxy_info, '_proxy'):
            try:
                await self._backend.close_proxy(proxy_info._proxy)
            except Exception:
                pass
    
    async def get_proxy(self, proxy_id: str) -> ProxyInfo:
        """
        获取代理信息
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            代理信息
            
        Raises:
            ProxyNotFoundError: 代理不存在
        """
        with self._lock:
            if proxy_id not in self._proxies:
                raise ProxyNotFoundError(f"Proxy {proxy_id} not found")
            return self._proxies[proxy_id]
    
    async def list_proxies(self, state: Optional[ProxyState] = None) -> List[ProxyInfo]:
        """
        列出所有代理
        
        Args:
            state: 可选的状态过滤
            
        Returns:
            代理信息列表
        """
        with self._lock:
            proxies = list(self._proxies.values())
        
        if state:
            proxies = [p for p in proxies if p.state == state]
        
        return proxies
    
    async def enable_proxy(self, proxy_id: str) -> None:
        """
        启用代理
        
        Args:
            proxy_id: 代理ID
        """
        async with self._proxy_semaphore:
            with self._lock:
                if proxy_id not in self._proxies:
                    raise ProxyNotFoundError(f"Proxy {proxy_id} not found")
                self._proxies[proxy_id].state = ProxyState.ACTIVE
    
    async def disable_proxy(self, proxy_id: str) -> None:
        """
        禁用代理
        
        Args:
            proxy_id: 代理ID
        """
        async with self._proxy_semaphore:
            with self._lock:
                if proxy_id not in self._proxies:
                    raise ProxyNotFoundError(f"Proxy {proxy_id} not found")
                self._proxies[proxy_id].state = ProxyState.INACTIVE
    
    async def check_proxy(self, proxy_id: str) -> bool:
        """
        检查代理健康状态
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            是否健康
            
        Raises:
            ProxyCheckError: 检查失败
        """
        return await self._check_proxy(proxy_id)
    
    async def _check_proxy(self, proxy_id: str) -> bool:
        """内部代理检查方法"""
        async with self._proxy_semaphore:
            with self._lock:
                if proxy_id not in self._proxies:
                    raise ProxyNotFoundError(f"Proxy {proxy_id} not found")
                
                proxy_info = self._proxies[proxy_id]
                proxy_info.state = ProxyState.CHECKING
            
            try:
                if self._backend:
                    # 使用后端进行健康检查
                    proxy_conn = await self._backend.create_proxy(proxy_info.config)
                    is_healthy = await self._backend.health_check(
                        proxy_conn, proxy_info.config
                    )
                    
                    with self._lock:
                        proxy_info.last_check_time = time.time()
                        proxy_info._proxy = proxy_conn
                        
                        if is_healthy:
                            proxy_info.state = ProxyState.ACTIVE
                            proxy_info.success_count += 1
                            proxy_info.error_message = None
                        else:
                            proxy_info.state = ProxyState.ERROR
                            proxy_info.failure_count += 1
                            proxy_info.error_message = "Health check failed"
                    
                    return is_healthy
                else:
                    # 使用默认检查方法
                    response_time = await self._default_health_check(
                        proxy_info.config
                    )
                    
                    with self._lock:
                        proxy_info.last_check_time = time.time()
                        proxy_info.response_time = response_time
                        
                        if response_time > 0:
                            proxy_info.state = ProxyState.ACTIVE
                            proxy_info.success_count += 1
                            proxy_info.last_success_time = time.time()
                            proxy_info.error_message = None
                        else:
                            proxy_info.state = ProxyState.ERROR
                            proxy_info.failure_count += 1
                            proxy_info.error_message = "Connection failed"
                    
                    return proxy_info.state == ProxyState.ACTIVE
                    
            except Exception as e:
                with self._lock:
                    proxy_info.last_check_time = time.time()
                    proxy_info.state = ProxyState.ERROR
                    proxy_info.failure_count += 1
                    proxy_info.error_message = str(e)
                
                raise ProxyCheckError(f"Proxy check failed: {e}")
    
    async def _default_health_check(self, config: ProxyConfig) -> float:
        """默认健康检查方法"""
        try:
            start_time = time.time()
            
            # 简单的连接测试
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(config.timeout)
            
            try:
                sock.connect((config.host, config.port))
                elapsed = time.time() - start_time
                return elapsed
            finally:
                sock.close()
                
        except Exception:
            return 0.0
    
    async def get_healthy_proxy(self) -> ProxyInfo:
        """
        获取一个健康的代理（用于负载均衡）
        
        Returns:
            健康的代理信息
            
        Raises:
            ProxyUnavailableError: 没有可用的代理
        """
        proxies = await self.list_proxies(state=ProxyState.ACTIVE)
        
        if not proxies:
            raise ProxyUnavailableError("No healthy proxy available")
        
        # 基于权重选择代理
        total_weight = sum(p.config.weight for p in proxies)
        random_value = (total_weight * hash(str(time.time())) % total_weight 
                       if total_weight > 0 else 0)
        
        current_weight = 0
        for proxy in proxies:
            current_weight += proxy.config.weight
            if current_weight > random_value:
                return proxy
        
        return proxies[0]
    
    async def get_proxy_by_priority(self) -> ProxyInfo:
        """
        获取一个代理（基于优先级）
        
        Returns:
            代理信息
            
        Raises:
            ProxyUnavailableError: 没有可用的代理
        """
        proxies = await self.list_proxies(state=ProxyState.ACTIVE)
        
        if not proxies:
            raise ProxyUnavailableError("No proxy available")
        
        # 按优先级排序（优先级高的在前）
        proxies.sort(key=lambda p: (-p.config.priority, p.response_time))
        
        return proxies[0]
    
    async def check_all_proxies(self) -> Dict[str, bool]:
        """检查所有代理的健康状态"""
        results = {}
        
        for proxy_id in list(self._proxies.keys()):
            try:
                results[proxy_id] = await self._check_proxy(proxy_id)
            except Exception as e:
                results[proxy_id] = False
        
        return results
    
    async def _periodic_check(self) -> None:
        """定期健康检查任务"""
        while True:
            try:
                await asyncio.sleep(self._check_interval)
                
                for proxy_id in list(self._proxies.keys()):
                    proxy_info = self._proxies.get(proxy_id)
                    if proxy_info and proxy_info.state == ProxyState.ACTIVE:
                        try:
                            await self._check_proxy(proxy_id)
                        except Exception:
                            pass
                            
            except asyncio.CancelledError:
                break
            except Exception:
                pass
    
    @property
    def proxy_count(self) -> int:
        """获取代理数量"""
        with self._lock:
            return len(self._proxies)
    
    @property
    def active_proxy_count(self) -> int:
        """获取活跃代理数量"""
        with self._lock:
            return sum(1 for p in self._proxies.values() 
                      if p.state == ProxyState.ACTIVE)


async def create_proxy_manager(backend: Optional[ProxyBackend] = None,
                               check_interval: float = 300.0,
                               max_concurrent_checks: int = 5) -> ProxyManager:
    """
    创建代理管理器
    
    Args:
        backend: 代理后端实现
        check_interval: 健康检查间隔
        max_concurrent_checks: 最大并发检查数
        
    Returns:
        代理管理器实例
    """
    manager = ProxyManager(backend, check_interval, max_concurrent_checks)
    await manager.initialize()
    return manager
