# -*- coding: utf-8 -*-
"""
Tests for Service Mesh Module - Agent-OS-Kernel 服务网格模块测试
"""

import pytest
import time
import threading
from agent_os_kernel.core.service_mesh import (
    CircuitState,
    LoadBalancingStrategy,
    ServiceInstance,
    ServiceInfo,
    CircuitBreaker,
    CircuitBreakerOpen,
    ServiceRegistry,
    LoadBalancer,
    ServiceClient,
    ServiceNotFound,
    NoHealthyInstance,
    ServiceMesh,
    create_service_mesh,
    create_service_registry,
    create_load_balancer,
    create_circuit_breaker,
)


class TestServiceInstance:
    """服务实例测试"""
    
    def test_service_instance_creation(self):
        """测试服务实例创建"""
        instance = ServiceInstance(
            service_id="test-service-1",
            service_name="test-service",
            host="localhost",
            port=8080,
        )
        
        assert instance.service_id == "test-service-1"
        assert instance.service_name == "test-service"
        assert instance.host == "localhost"
        assert instance.port == 8080
        assert instance.address == "localhost:8080"
        assert instance.is_healthy is True
    
    def test_service_instance_with_metadata(self):
        """测试带元数据的服务实例"""
        instance = ServiceInstance(
            service_id="test-service-2",
            service_name="test-service",
            host="192.168.1.1",
            port=8080,
            metadata={"version": "1.0.0", "region": "us-east"},
            weight=200,
        )
        
        assert instance.metadata["version"] == "1.0.0"
        assert instance.weight == 200
        assert instance.is_healthy is True
    
    def test_service_instance_health_status(self):
        """测试服务实例健康状态"""
        instance = ServiceInstance(
            service_id="test-service-3",
            service_name="test-service",
            host="localhost",
            port=8080,
        )
        
        assert instance.is_healthy is True
        instance.status = "unhealthy"
        assert instance.is_healthy is False


class TestCircuitBreaker:
    """熔断器测试"""
    
    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        cb = CircuitBreaker(name="test", failure_threshold=5)
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_records_success(self):
        """测试熔断器记录成功"""
        cb = CircuitBreaker(name="test", failure_threshold=5)
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_opens_after_failures(self):
        """测试熔断器达到阈值后打开"""
        cb = CircuitBreaker(name="test", failure_threshold=3)
        
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """测试熔断器超时后进入半开状态"""
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout_seconds=0.1)
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        time.sleep(0.2)
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_closes_on_success(self):
        """测试熔断器半开状态下成功后关闭"""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1,
        )
        
        cb.record_failure()
        time.sleep(0.2)
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_allows_request_when_closed(self):
        """测试熔断器关闭时允许请求"""
        cb = CircuitBreaker(name="test")
        assert cb.allow_request() is True
    
    def test_circuit_breaker_blocks_request_when_open(self):
        """测试熔断器打开时拒绝请求"""
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.allow_request() is False
    
    def test_circuit_breaker_call_with_fallback(self):
        """测试熔断器调用带降级"""
        cb = CircuitBreaker(name="test", failure_threshold=1)
        
        def success_func():
            return "success"
        
        def fallback_func():
            return "fallback"
        
        # 关闭状态
        result = cb.call_with_circuit(success_func, fallback=fallback_func)
        assert result == "success"
        
        # 打开状态，应该调用降级
        cb.record_failure()
        result = cb.call_with_circuit(success_func, fallback=fallback_func)
        assert result == "fallback"
    
    def test_circuit_breaker_call_raises_when_open(self):
        """测试熔断器打开时抛出异常"""
        cb = CircuitBreaker(name="test", failure_threshold=1)
        
        def success_func():
            return "success"
        
        cb.record_failure()
        
        with pytest.raises(CircuitBreakerOpen):
            cb.call_with_circuit(success_func)
    
    def test_circuit_breaker_get_stats(self):
        """测试熔断器获取统计"""
        cb = CircuitBreaker(name="test", failure_threshold=5, success_threshold=3)
        cb.record_failure()
        cb.record_success()
        
        stats = cb.get_stats()
        assert stats["name"] == "test"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["failure_threshold"] == 5


class TestServiceDiscovery:
    """服务发现测试"""
    
    def test_service_registration(self):
        """测试服务注册"""
        registry = create_service_registry()
        instance = ServiceInstance(
            service_id="test-1",
            service_name="user-service",
            host="localhost",
            port=8080,
        )
        
        result = registry.register(instance)
        assert result is True
        
        instances = registry.discover("user-service")
        assert len(instances) == 1
        assert instances[0].service_id == "test-1"
    
    def test_service_deregistration(self):
        """测试服务注销"""
        registry = create_service_registry()
        instance = ServiceInstance(
            service_id="test-1",
            service_name="user-service",
            host="localhost",
            port=8080,
        )
        
        registry.register(instance)
        result = registry.deregister("test-1")
        assert result is True
        
        instances = registry.discover("user-service")
        assert len(instances) == 0
    
    def test_multiple_instances_registration(self):
        """测试多个实例注册"""
        registry = create_service_registry()
        
        for i in range(3):
            instance = ServiceInstance(
                service_id=f"test-{i}",
                service_name="user-service",
                host=f"192.168.1.{i}",
                port=8080,
            )
            registry.register(instance)
        
        instances = registry.discover("user-service")
        assert len(instances) == 3
    
    def test_service_discovery_filters_unhealthy(self):
        """测试服务发现过滤不健康实例"""
        registry = create_service_registry()
        
        healthy = ServiceInstance(
            service_id="healthy-1",
            service_name="test-service",
            host="localhost",
            port=8080,
            status="healthy",
        )
        
        unhealthy = ServiceInstance(
            service_id="unhealthy-1",
            service_name="test-service",
            host="localhost",
            port=8081,
            status="unhealthy",
        )
        
        registry.register(healthy)
        registry.register(unhealthy)
        
        instances = registry.discover("test-service")
        assert len(instances) == 1
        assert instances[0].service_id == "healthy-1"
    
    def test_update_heartbeat(self):
        """测试更新心跳"""
        registry = create_service_registry()
        instance = ServiceInstance(
            service_id="test-1",
            service_name="test-service",
            host="localhost",
            port=8080,
        )
        
        registry.register(instance)
        old_heartbeat = instance.last_heartbeat
        time.sleep(0.1)
        
        result = registry.update_heartbeat("test-1")
        assert result is True
        assert instance.last_heartbeat > old_heartbeat
    
    def test_update_status(self):
        """测试更新状态"""
        registry = create_service_registry()
        instance = ServiceInstance(
            service_id="test-1",
            service_name="test-service",
            host="localhost",
            port=8080,
        )
        
        registry.register(instance)
        result = registry.update_status("test-1", "unhealthy")
        assert result is True
        assert instance.status == "unhealthy"
    
    def test_get_all_services(self):
        """测试获取所有服务"""
        registry = create_service_registry()
        
        registry.register(ServiceInstance(
            service_id="test-1",
            service_name="user-service",
            host="localhost",
            port=8080,
        ))
        registry.register(ServiceInstance(
            service_id="test-2",
            service_name="order-service",
            host="localhost",
            port=8081,
        ))
        
        services = registry.get_all_services()
        assert "user-service" in services
        assert "order-service" in services
        assert len(services) == 2
    
    def test_service_not_found(self):
        """测试服务未找到"""
        registry = create_service_registry()
        instances = registry.discover("non-existent")
        assert len(instances) == 0
    
    def test_registry_stats(self):
        """测试注册中心统计"""
        registry = create_service_registry()
        
        registry.register(ServiceInstance(
            service_id="test-1",
            service_name="test-service",
            host="localhost",
            port=8080,
        ))
        
        stats = registry.get_stats()
        assert stats["total_services"] == 1
        assert stats["total_instances"] == 1


class TestLoadBalancing:
    """负载均衡测试"""
    
    def test_round_robin_selection(self):
        """测试轮询选择"""
        lb = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
        
        instances = [
            ServiceInstance(
                service_id=f"test-{i}",
                service_name="test-service",
                host=f"192.168.1.{i}",
                port=8080,
            )
            for i in range(3)
        ]
        
        selected = [lb.select(instances) for _ in range(4)]
        ids = [i.service_id for i in selected]
        assert ids == ["test-0", "test-1", "test-2", "test-0"]
    
    def test_random_selection(self):
        """测试随机选择"""
        lb = LoadBalancer(LoadBalancingStrategy.RANDOM)
        
        instances = [
            ServiceInstance(
                service_id=f"test-{i}",
                service_name="test-service",
                host=f"192.168.1.{i}",
                port=8080,
            )
            for i in range(3)
        ]
        
        # 多次选择确保随机性
        selected = set()
        for _ in range(100):
            instance = lb.select(instances)
            if instance:
                selected.add(instance.service_id)
        
        assert len(selected) > 1  # 至少有两个不同的实例被选中
    
    def test_weighted_selection(self):
        """测试加权选择"""
        lb = LoadBalancer(LoadBalancingStrategy.WEIGHTED)
        
        instances = [
            ServiceInstance(
                service_id="high-weight",
                service_name="test-service",
                host="localhost",
                port=8080,
                weight=100,
            ),
            ServiceInstance(
                service_id="low-weight",
                service_name="test-service",
                host="localhost",
                port=8081,
                weight=1,
            ),
        ]
        
        # 多次选择，高权重应该更频繁
        high_weight_count = 0
        for _ in range(100):
            instance = lb.select(instances)
            if instance.service_id == "high-weight":
                high_weight_count += 1
        
        assert high_weight_count > 80  # 高权重应该被选中超过80%
    
    def test_least_connections_selection(self):
        """测试最少连接选择"""
        lb = LoadBalancer(LoadBalancingStrategy.LEAST_CONNECTIONS)
        
        instances = [
            ServiceInstance(
                service_id="test-0",
                service_name="test-service",
                host="localhost",
                port=8080,
                connection_count=10,
            ),
            ServiceInstance(
                service_id="test-1",
                service_name="test-service",
                host="localhost",
                port=8081,
                connection_count=2,
            ),
        ]
        
        selected = lb.select(instances)
        assert selected.service_id == "test-1"
    
    def test_consistent_hash_selection(self):
        """测试一致性哈希选择"""
        lb = LoadBalancer(LoadBalancingStrategy.CONSISTENT_HASH)
        
        instances = [
            ServiceInstance(
                service_id="test-0",
                service_name="test-service",
                host="localhost",
                port=8080,
            ),
            ServiceInstance(
                service_id="test-1",
                service_name="test-service",
                host="localhost",
                port=8081,
            ),
        ]
        
        # 相同 key 应该选择相同实例
        selected1 = lb.select(instances, key="user:123")
        selected2 = lb.select(instances, key="user:123")
        assert selected1.service_id == selected2.service_id
    
    def test_select_returns_none_for_empty_instances(self):
        """测试空实例列表返回 None"""
        lb = LoadBalancer()
        selected = lb.select([])
        assert selected is None
    
    def test_select_returns_none_for_all_unhealthy(self):
        """测试所有不健康时返回 None"""
        lb = LoadBalancer()
        
        instances = [
            ServiceInstance(
                service_id="test-0",
                service_name="test-service",
                host="localhost",
                port=8080,
                status="unhealthy",
            ),
        ]
        
        selected = lb.select(instances)
        assert selected is None


class TestServiceCommunication:
    """服务通信测试"""
    
    def test_service_client_call(self):
        """测试服务客户端调用"""
        registry = create_service_registry()
        registry.register(ServiceInstance(
            service_id="test-1",
            service_name="user-service",
            host="localhost",
            port=8080,
        ))
        
        client = ServiceClient(registry=registry)
        result = client.call("user-service")
        
        assert result["status_code"] == 200
        assert result["instance"] == "test-1"
    
    def test_service_client_call_not_found(self):
        """测试服务未找到"""
        registry = create_service_registry()
        client = ServiceClient(registry=registry)
        
        with pytest.raises(ServiceNotFound):
            client.call("non-existent-service")
    
    def test_service_client_with_circuit_breaker(self):
        """测试带熔断器的服务调用"""
        registry = create_service_registry()
        registry.register(ServiceInstance(
            service_id="test-1",
            service_name="test-service",
            host="localhost",
            port=8080,
        ))
        
        circuit = create_circuit_breaker(
            name="test-service",
            failure_threshold=1,
            timeout_seconds=0.1,
        )
        
        client = ServiceClient(registry=registry)
        client.set_circuit_breaker("test-service", circuit)
        
        # 第一次成功调用
        result = client.call("test-service", use_circuit_breaker=True)
        assert result["status_code"] == 200
        
        # 触发熔断
        circuit.record_failure()
        
        # 降级调用
        fallback_called = [False]
        def fallback():
            fallback_called[0] = True
            return {"status_code": 503, "message": "fallback"}
        
        result = client.call(
            "test-service",
            use_circuit_breaker=True,
            fallback=fallback,
        )
        assert result["status_code"] == 503
        assert fallback_called[0] is True
    
    def test_service_client_get_stats(self):
        """测试客户端获取统计"""
        registry = create_service_registry()
        registry.register(ServiceInstance(
            service_id="test-1",
            service_name="test-service",
            host="localhost",
            port=8080,
        ))
        
        client = ServiceClient(registry=registry)
        stats = client.get_stats()
        
        assert "registry_stats" in stats
        assert stats["registry_stats"]["total_services"] == 1


class TestServiceMesh:
    """服务网格测试"""
    
    def test_create_service_mesh(self):
        """测试创建服务网格"""
        mesh = create_service_mesh()
        assert isinstance(mesh, ServiceMesh)
    
    def test_register_service(self):
        """测试注册服务"""
        mesh = create_service_mesh()
        instance = mesh.register_service(
            service_name="user-service",
            host="localhost",
            port=8080,
        )
        
        assert instance.service_name == "user-service"
        instances = mesh.discover("user-service")
        assert len(instances) == 1
    
    def test_create_circuit_breaker(self):
        """测试创建熔断器"""
        mesh = create_service_mesh()
        cb = mesh.create_circuit_breaker(
            name="user-service",
            failure_threshold=5,
        )
        
        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "user-service"
    
    def test_set_load_balancing_strategy(self):
        """测试设置负载均衡策略"""
        mesh = create_service_mesh()
        mesh.set_load_balancing_strategy(LoadBalancingStrategy.WEIGHTED)
        assert mesh.load_balancer.strategy == LoadBalancingStrategy.WEIGHTED
    
    def test_call_service(self):
        """测试调用服务"""
        mesh = create_service_mesh()
        mesh.register_service(
            service_name="test-service",
            host="localhost",
            port=8080,
        )
        
        result = mesh.call_service("test-service")
        assert result["status_code"] == 200
    
    def test_get_mesh_stats(self):
        """测试获取网格统计"""
        mesh = create_service_mesh()
        mesh.register_service(
            service_name="test-service",
            host="localhost",
            port=8080,
        )
        
        stats = mesh.get_mesh_stats()
        assert "registry" in stats
        assert "services" in stats
