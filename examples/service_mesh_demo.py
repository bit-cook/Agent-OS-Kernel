# -*- coding: utf-8 -*-
"""
Service Mesh Demo - Agent-OS-Kernel 服务网格示例

演示服务网格的核心功能：
1. 服务发现
2. 负载均衡
3. 熔断器
4. 服务间通信
"""

import time
import random
from agent_os_kernel.core.service_mesh import (
    CircuitState,
    LoadBalancingStrategy,
    ServiceInstance,
    ServiceRegistry,
    LoadBalancer,
    CircuitBreaker,
    CircuitBreakerOpen,
    ServiceMesh,
    create_service_mesh,
    create_service_registry,
    create_load_balancer,
    create_circuit_breaker,
)


def demo_service_discovery():
    """演示服务发现功能"""
    print("=" * 60)
    print("演示 1: 服务发现")
    print("=" * 60)
    
    # 创建服务注册中心
    registry = create_service_registry()
    
    # 注册多个服务实例
    print("\n注册服务实例...")
    
    # 用户服务实例
    user_instances = []
    for i in range(3):
        instance = ServiceInstance(
            service_id=f"user-service-{i+1}",
            service_name="user-service",
            host=f"192.168.1.{10+i}",
            port=8080,
            metadata={"region": f"region-{i}"},
            weight=100 - i * 20,
        )
        registry.register(instance)
        user_instances.append(instance)
        print(f"  注册: {instance.service_id} @ {instance.address}")
    
    # 订单服务实例
    order_instance = ServiceInstance(
        service_id="order-service-1",
        service_name="order-service",
        host="192.168.1.20",
        port=8081,
        metadata={"region": "region-0"},
    )
    registry.register(order_instance)
    print(f"  注册: {order_instance.service_id} @ {order_instance.address}")
    
    # 发现服务
    print("\n发现服务...")
    
    user_services = registry.discover("user-service")
    print(f"\nuser-service 发现 {len(user_services)} 个实例:")
    for instance in user_services:
        print(f"  - {instance.service_id}: {instance.address} (权重: {instance.weight})")
    
    order_services = registry.discover("order-service")
    print(f"\norder-service 发现 {len(order_services)} 个实例:")
    for instance in order_services:
        print(f"  - {instance.service_id}: {instance.address}")
    
    # 获取所有服务
    all_services = registry.get_all_services()
    print(f"\n所有已注册服务: {all_services}")
    
    # 获取统计信息
    stats = registry.get_stats()
    print(f"\n注册中心统计:")
    print(f"  - 总服务数: {stats['total_services']}")
    print(f"  - 总实例数: {stats['total_instances']}")
    
    print("\n✅ 服务发现演示完成")
    return registry


def demo_load_balancing():
    """演示负载均衡功能"""
    print("\n" + "=" * 60)
    print("演示 2: 负载均衡")
    print("=" * 60)
    
    # 创建负载均衡器
    strategies = [
        (LoadBalancingStrategy.ROUND_ROBIN, "轮询"),
        (LoadBalancingStrategy.RANDOM, "随机"),
        (LoadBalancingStrategy.WEIGHTED, "加权"),
        (LoadBalancingStrategy.LEAST_CONNECTIONS, "最少连接"),
        (LoadBalancingStrategy.CONSISTENT_HASH, "一致性哈希"),
    ]
    
    # 创建测试实例
    instances = [
        ServiceInstance(
            service_id=f"service-{i}",
            service_name="test-service",
            host=f"192.168.1.{i}",
            port=8080,
            connection_count=random.randint(0, 20),
        )
        for i in range(5)
    ]
    
    for strategy, name in strategies:
        print(f"\n负载均衡策略: {name}")
        lb = LoadBalancer(strategy)
        
        if strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            # 一致性哈希测试
            print("  使用相同 key 多次选择:")
            for i in range(3):
                selected = lb.select(instances, key="user:123")
                print(f"    第{i+1}次: {selected.service_id}")
        else:
            # 其他策略测试
            print("  选择 10 次:")
            selected_counts = {inst.service_id: 0 for inst in instances}
            for _ in range(10):
                selected = lb.select(instances)
                if selected:
                    selected_counts[selected.service_id] += 1
            
            for inst_id, count in selected_counts.items():
                print(f"    {inst_id}: {count} 次")
    
    print("\n✅ 负载均衡演示完成")


def demo_circuit_breaker():
    """演示熔断器功能"""
    print("\n" + "=" * 60)
    print("演示 3: 熔断器")
    print("=" * 60)
    
    # 创建熔断器
    cb = create_circuit_breaker(
        name="payment-service",
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=1.0,
    )
    
    print(f"\n熔断器配置:")
    print(f"  - 名称: {cb.name}")
    print(f"  - 失败阈值: {cb.failure_threshold}")
    print(f"  - 成功阈值: {cb.success_threshold}")
    print(f"  - 超时时间: {cb.timeout_seconds}秒")
    print(f"  - 初始状态: {cb.state.value}")
    
    # 模拟服务调用
    def unreliable_service():
        """不可靠的服务"""
        if random.random() < 0.7:  # 70% 失败率
            raise Exception("Service error")
        return "success"
    
    def fallback():
        """降级服务"""
        return "fallback response"
    
    print("\n模拟服务调用 (70% 失败率):")
    for i in range(10):
        time.sleep(0.2)
        
        try:
            if cb.state == CircuitState.OPEN:
                print(f"  调用 {i+1}: 熔断器打开 - 使用降级")
                result = cb.call_with_circuit(unreliable_service, fallback=fallback)
            else:
                result = cb.call_with_circuit(unreliable_service, fallback=fallback)
                print(f"  调用 {i+1}: {result}")
        except CircuitBreakerOpen:
            print(f"  调用 {i+1}: 熔断器打开，异常")
        
        stats = cb.get_stats()
        print(f"    状态: {stats['state']}, 失败数: {stats['failure_count']}")
    
    print(f"\n最终状态: {cb.state.value}")
    print("\n✅ 熔断器演示完成")
    
    return cb


def demo_service_communication():
    """演示服务间通信"""
    print("\n" + "=" * 60)
    print("演示 4: 服务间通信")
    print("=" * 60)
    
    # 创建服务网格
    mesh = create_service_mesh()
    
    # 注册服务
    print("\n注册服务...")
    
    user_service = mesh.register_service(
        service_name="user-service",
        host="192.168.1.10",
        port=8080,
        metadata={"version": "1.0.0"},
    )
    print(f"  注册 user-service: {user_service.service_id}")
    
    order_service = mesh.register_service(
        service_name="order-service",
        host="192.168.1.11",
        port=8080,
        metadata={"version": "1.0.0"},
    )
    print(f"  注册 order-service: {order_service.service_id}")
    
    # 创建熔断器
    mesh.create_circuit_breaker(
        name="user-service",
        failure_threshold=5,
        success_threshold=3,
    )
    
    # 设置负载均衡策略
    mesh.set_load_balancing_strategy(LoadBalancingStrategy.WEIGHTED)
    
    # 模拟服务调用
    print("\n服务调用演示:")
    
    # 调用 user-service
    print("\n  调用 user-service:")
    result = mesh.call_service(
        "user-service",
        method="GET",
        path="/api/users/123",
        data={"include": "orders"},
    )
    print(f"    状态码: {result['status_code']}")
    print(f"    实例: {result['instance']}")
    print(f"    URL: {result['url']}")
    print(f"    响应: {result['message']}")
    
    # 调用 order-service
    print("\n  调用 order-service:")
    result = mesh.call_service(
        "order-service",
        method="POST",
        path="/api/orders",
        data={"user_id": 123, "items": [{"id": 1, "qty": 2}]},
    )
    print(f"    状态码: {result['status_code']}")
    print(f"    实例: {result['instance']}")
    print(f"    URL: {result['url']}")
    
    # 获取网格统计
    stats = mesh.get_mesh_stats()
    print(f"\n服务网格统计:")
    print(f"  - 服务数: {stats['registry']['total_services']}")
    print(f"  - 实例数: {stats['registry']['total_instances']}")
    
    print("\n✅ 服务间通信演示完成")


def demo_full_workflow():
    """完整工作流演示"""
    print("\n" + "=" * 60)
    print("完整工作流演示")
    print("=" * 60)
    
    # 创建服务网格
    mesh = create_service_mesh()
    
    print("\n步骤 1: 注册多个服务实例")
    
    # 注册支付服务的多个实例
    for i in range(3):
        instance = mesh.register_service(
            service_name="payment-service",
            host=f"192.168.1.{100+i}",
            port=8080,
            weight=100 - i * 20,
        )
        print(f"  注册支付服务实例: {instance.service_id}")
    
    print("\n步骤 2: 配置熔断器")
    cb = mesh.create_circuit_breaker(
        name="payment-service",
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=2.0,
    )
    print(f"  熔断器状态: {cb.state.value}")
    
    print("\n步骤 3: 设置负载均衡策略")
    mesh.set_load_balancing_strategy(LoadBalancingStrategy.ROUND_ROBIN)
    print(f"  负载均衡策略: 轮询")
    
    print("\n步骤 4: 模拟服务调用 (模拟不稳定服务)")
    
    def simulate_unstable_service():
        """模拟不稳定服务"""
        if random.random() < 0.4:
            raise Exception("Temporary failure")
        return {"status": "ok", "message": "Payment processed"}
    
    print("\n  发起 15 次请求:")
    success_count = 0
    fallback_count = 0
    circuit_open_count = 0
    
    for i in range(15):
        time.sleep(0.3)
        
        try:
            if cb.state == CircuitState.OPEN:
                circuit_open_count += 1
                print(f"    请求 {i+1}: 熔断器打开")
                continue
            
            result = mesh.call_service("payment-service")
            success_count += 1
            print(f"    请求 {i+1}: 成功")
            
        except Exception as e:
            fallback_count += 1
            print(f"    请求 {i+1}: 失败 - {str(e)}")
        
        # 模拟状态变化
        if i % 5 == 0 and i > 0:
            print(f"      [检查点] 熔断器状态: {cb.state.value}")
    
    print(f"\n步骤 5: 统计结果")
    print(f"  - 成功请求: {success_count}")
    print(f"  - 失败请求: {fallback_count}")
    print(f"  - 熔断器打开次数: {circuit_open_count}")
    print(f"  - 最终熔断器状态: {cb.state.value}")
    
    print("\n✅ 完整工作流演示完成")


def main():
    """主函数"""
    print("=" * 60)
    print("Agent-OS-Kernel 服务网格演示")
    print("=" * 60)
    
    # 演示服务发现
    registry = demo_service_discovery()
    
    # 演示负载均衡
    demo_load_balancing()
    
    # 演示熔断器
    cb = demo_circuit_breaker()
    
    # 演示服务间通信
    demo_service_communication()
    
    # 完整工作流
    demo_full_workflow()
    
    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
