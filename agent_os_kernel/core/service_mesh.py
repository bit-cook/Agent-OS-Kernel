# -*- coding: utf-8 -*-
"""
Service Mesh Module - Agent-OS-Kernel 服务网格模块

提供服务发现、负载均衡、熔断器和服务间通信功能。
"""

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 关闭状态，正常运行
    OPEN = "open"           # 打开状态，快速失败
    HALF_OPEN = "half_open" # 半开状态，尝试恢复


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"         # 轮询
    RANDOM = "random"                   # 随机
    WEIGHTED = "weighted"               # 加权
    LEAST_CONNECTIONS = "least_connections"  # 最少连接
    CONSISTENT_HASH = "consistent_hash" # 一致性哈希


@dataclass
class ServiceInstance:
    """服务实例"""
    service_id: str
    service_name: str
    host: str
    port: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    weight: int = 100
    health_check_url: Optional[str] = None
    status: str = "healthy"
    connection_count: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    version: str
    instances: List[ServiceInstance] = field(default_factory=list)
    description: str = ""
    tags: List[str] = field(default_factory=list)


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout_seconds: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
        
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
            return self._state
    
    def record_success(self):
        """记录成功调用"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit breaker {self.name} closed")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self):
        """记录失败调用"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.half_open_max_calls:
                    self._state = CircuitState.OPEN
                    self._last_failure_time = time.time()
                    logger.warning(f"Circuit breaker {self.name} opened due to failure")
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_failure_time = time.time()
                    logger.warning(f"Circuit breaker {self.name} opened")
    
    def allow_request(self) -> bool:
        """是否允许请求"""
        return self.state != CircuitState.OPEN
    
    def call_with_circuit(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """带熔断的调用"""
        if not self.allow_request():
            if fallback:
                return fallback(*args, **kwargs)
            raise CircuitBreakerOpen(f"Circuit breaker {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            if fallback and self.state == CircuitState.OPEN:
                return fallback(*args, **kwargs)
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_threshold": self.failure_threshold,
                "success_threshold": self.success_threshold,
                "timeout_seconds": self.timeout_seconds,
            }


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""
    pass


class ServiceRegistry:
    """服务注册中心 - 服务发现"""
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._instances: Dict[str, ServiceInstance] = {}
        self._lock = threading.RLock()
        self._event_callbacks: List[Callable] = []
        
    def register(self, instance: ServiceInstance) -> bool:
        """注册服务实例"""
        with self._lock:
            if instance.service_id in self._instances:
                logger.warning(f"Service {instance.service_id} already registered")
                return False
            
            self._instances[instance.service_id] = instance
            
            if instance.service_name not in self._services:
                self._services[instance.service_name] = ServiceInfo(
                    name=instance.service_name,
                    version="1.0.0",
                )
            self._services[instance.service_name].instances.append(instance)
            
            self._notify_event("register", instance)
            logger.info(f"Registered service: {instance.service_id} at {instance.address}")
            return True
    
    def deregister(self, service_id: str) -> bool:
        """注销服务实例"""
        with self._lock:
            if service_id not in self._instances:
                return False
            
            instance = self._instances.pop(service_id)
            if instance.service_name in self._services:
                service = self._services[instance.service_name]
                service.instances = [
                    i for i in service.instances if i.service_id != service_id
                ]
            
            self._notify_event("deregister", instance)
            logger.info(f"Deregistered service: {service_id}")
            return True
    
    def discover(self, service_name: str) -> List[ServiceInstance]:
        """发现服务实例"""
        with self._lock:
            if service_name not in self._services:
                return []
            return [
                i for i in self._services[service_name].instances 
                if i.is_healthy
            ]
    
    def get_service_info(self, service_name: str) -> Optional[ServiceInfo]:
        """获取服务信息"""
        with self._lock:
            return self._services.get(service_name)
    
    def get_all_services(self) -> List[str]:
        """获取所有服务名称"""
        with self._lock:
            return list(self._services.keys())
    
    def update_heartbeat(self, service_id: str) -> bool:
        """更新心跳"""
        with self._lock:
            if service_id not in self._instances:
                return False
            self._instances[service_id].last_heartbeat = time.time()
            return True
    
    def update_status(self, service_id: str, status: str) -> bool:
        """更新服务状态"""
        with self._lock:
            if service_id not in self._instances:
                return False
            self._instances[service_id].status = status
            self._notify_event("status_change", self._instances[service_id], status)
            return True
    
    def on_event(self, callback: Callable):
        """注册事件回调"""
        self._event_callbacks.append(callback)
    
    def _notify_event(self, event_type: str, *args):
        """通知事件"""
        for callback in self._event_callbacks:
            try:
                callback(event_type, *args)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_services": len(self._services),
                "total_instances": len(self._instances),
                "services": {
                    name: {
                        "instance_count": len(info.instances),
                        "healthy_count": sum(
                            1 for i in info.instances if i.is_healthy
                        ),
                    }
                    for name, info in self._services.items()
                },
            }


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
    ):
        self.strategy = strategy
        self._round_robin_index: Dict[str, int] = {}
        self._connection_counts: Dict[str, int] = {}
        self._hash_ring: Dict[str, List[Tuple[int, str]]] = {}
        
    def select(
        self,
        instances: List[ServiceInstance],
        key: Optional[str] = None,
    ) -> Optional[ServiceInstance]:
        """选择服务实例"""
        if not instances:
            return None
        
        healthy_instances = [i for i in instances if i.is_healthy]
        if not healthy_instances:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            return self._consistent_hash_select(healthy_instances, key)
        else:
            return healthy_instances[0]
    
    def _round_robin_select(
        self, instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """轮询选择"""
        service_name = instances[0].service_name
        if service_name not in self._round_robin_index:
            self._round_robin_index[service_name] = 0
        index = self._round_robin_index[service_name]
        self._round_robin_index[service_name] = (index + 1) % len(instances)
        return instances[index]
    
    def _random_select(
        self, instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """随机选择"""
        return random.choice(instances)
    
    def _weighted_select(
        self, instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """加权选择"""
        total_weight = sum(i.weight for i in instances)
        if total_weight <= 0:
            return random.choice(instances)
        
        random_value = random.randint(1, total_weight)
        cumulative = 0
        for instance in instances:
            cumulative += instance.weight
            if random_value <= cumulative:
                return instance
        return instances[-1]
    
    def _least_connections_select(
        self, instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """最少连接选择"""
        return min(instances, key=lambda i: i.connection_count)
    
    def _consistent_hash_select(
        self,
        instances: List[ServiceInstance],
        key: Optional[str] = None,
    ) -> ServiceInstance:
        """一致性哈希选择"""
        if not key:
            key = str(uuid.uuid4())
        
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        
        if not instances:
            return None
        
        # 简单的一致性哈希实现
        best_instance = instances[0]
        best_distance = float('inf')
        
        for instance in instances:
            instance_hash = int(
                hashlib.md5(f"{instance.service_id}".encode()).hexdigest(), 16
            )
            distance = (instance_hash - hash_value) % (2 ** 128)
            if distance < best_distance:
                best_distance = distance
                best_instance = instance
        
        return best_instance
    
    def record_connection(self, instance: ServiceInstance):
        """记录连接"""
        instance.connection_count += 1
    
    def release_connection(self, instance: ServiceInstance):
        """释放连接"""
        instance.connection_count = max(0, instance.connection_count - 1)


class ServiceClient:
    """服务客户端 - 服务间通信"""
    
    def __init__(
        self,
        registry: Optional[ServiceRegistry] = None,
        load_balancer: Optional[LoadBalancer] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        default_timeout: float = 30.0,
    ):
        self.registry = registry or ServiceRegistry()
        self.load_balancer = load_balancer or LoadBalancer()
        self.default_timeout = default_timeout
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        
        if circuit_breaker:
            self._circuit_breakers["default"] = circuit_breaker
    
    def call(
        self,
        service_name: str,
        method: str = "GET",
        path: str = "/",
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
        use_circuit_breaker: bool = True,
        fallback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """调用服务"""
        instances = self.registry.discover(service_name)
        if not instances:
            raise ServiceNotFound(f"Service {service_name} not found")
        
        instance = self.load_balancer.select(instances, key=path)
        if not instance:
            raise NoHealthyInstance(f"No healthy instance for {service_name}")
        
        self.load_balancer.record_connection(instance)
        
        try:
            circuit = self._circuit_breakers.get(service_name)
            if circuit and use_circuit_breaker:
                return circuit.call_with_circuit(
                    self._do_request,
                    instance,
                    method,
                    path,
                    data,
                    headers,
                    timeout or self.default_timeout,
                    fallback=fallback,
                )
            else:
                return self._do_request(
                    instance, method, path, data, headers, timeout or self.default_timeout
                )
        finally:
            self.load_balancer.release_connection(instance)
    
    async def async_call(
        self,
        service_name: str,
        method: str = "GET",
        path: str = "/",
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """异步调用服务"""
        instances = self.registry.discover(service_name)
        if not instances:
            raise ServiceNotFound(f"Service {service_name} not found")
        
        instance = self.load_balancer.select(instances, key=path)
        if not instance:
            raise NoHealthyInstance(f"No healthy instance for {service_name}")
        
        return await self._async_do_request(
            instance, method, path, data, headers, timeout or self.default_timeout
        )
    
    def _do_request(
        self,
        instance: ServiceInstance,
        method: str,
        path: str,
        data: Optional[Dict],
        headers: Optional[Dict],
        timeout: float,
    ) -> Dict[str, Any]:
        """执行请求（模拟实现）"""
        # 这里是一个模拟实现，实际场景中会使用 HTTP 客户端
        url = f"http://{instance.address}{path}"
        
        return {
            "status_code": 200,
            "url": url,
            "method": method,
            "data": data,
            "instance": instance.service_id,
            "timestamp": time.time(),
            "message": f"Response from {instance.address}",
        }
    
    async def _async_do_request(
        self,
        instance: ServiceInstance,
        method: str,
        path: str,
        data: Optional[Dict],
        headers: Optional[Dict],
        timeout: float,
    ) -> Dict[str, Any]:
        """异步执行请求（模拟实现）"""
        url = f"http://{instance.address}{path}"
        
        return {
            "status_code": 200,
            "url": url,
            "method": method,
            "data": data,
            "instance": instance.service_id,
            "timestamp": time.time(),
            "message": f"Async response from {instance.address}",
        }
    
    def get_circuit_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        """获取服务的熔断器"""
        return self._circuit_breakers.get(service_name)
    
    def set_circuit_breaker(self, service_name: str, circuit: CircuitBreaker):
        """设置服务的熔断器"""
        self._circuit_breakers[service_name] = circuit
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计"""
        return {
            "registry_stats": self.registry.get_stats(),
            "load_balancer_strategy": self.strategy.value if hasattr(self, 'strategy') else 'default',
            "circuit_breakers": {
                name: cb.get_stats()
                for name, cb in self._circuit_breakers.items()
            },
        }


class ServiceNotFound(Exception):
    """服务未找到异常"""
    pass


class NoHealthyInstance(Exception):
    """无可用健康实例异常"""
    pass


class ServiceMesh:
    """服务网格主类"""
    
    def __init__(self):
        self.registry = ServiceRegistry()
        self.load_balancer = LoadBalancer()
        self.client = ServiceClient(self.registry, self.load_balancer)
        self._running = False
        self._health_check_interval = 30
        
    def register_service(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: Optional[Dict] = None,
        weight: int = 100,
    ) -> ServiceInstance:
        """注册服务"""
        instance = ServiceInstance(
            service_id=f"{service_name}-{uuid.uuid4().hex[:8]}",
            service_name=service_name,
            host=host,
            port=port,
            metadata=metadata or {},
            weight=weight,
        )
        self.registry.register(instance)
        return instance
    
    def discover(self, service_name: str) -> List[ServiceInstance]:
        """发现服务"""
        return self.registry.discover(service_name)
    
    def create_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout_seconds: float = 60.0,
    ) -> CircuitBreaker:
        """创建熔断器"""
        cb = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout_seconds=timeout_seconds,
        )
        self.client.set_circuit_breaker(name, cb)
        return cb
    
    def set_load_balancing_strategy(
        self, strategy: LoadBalancingStrategy
    ) -> None:
        """设置负载均衡策略"""
        self.load_balancer.strategy = strategy
    
    def call_service(
        self,
        service_name: str,
        method: str = "GET",
        path: str = "/",
        data: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """调用服务"""
        return self.client.call(service_name, method, path, data, **kwargs)
    
    def get_mesh_stats(self) -> Dict[str, Any]:
        """获取网格统计"""
        return {
            "registry": self.registry.get_stats(),
            "services": self.client.get_stats(),
        }


# 工厂函数
def create_service_mesh() -> ServiceMesh:
    """创建服务网格实例"""
    return ServiceMesh()


def create_service_registry() -> ServiceRegistry:
    """创建服务注册中心"""
    return ServiceRegistry()


def create_load_balancer(
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
) -> LoadBalancer:
    """创建负载均衡器"""
    return LoadBalancer(strategy)


def create_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout_seconds: float = 60.0,
) -> CircuitBreaker:
    """创建熔断器"""
    return CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout_seconds=timeout_seconds,
    )
