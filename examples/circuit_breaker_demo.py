#!/usr/bin/env python3
"""CircuitBreaker 使用示例"""

from agent_os_kernel.core.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitConfig
)


def main():
    print("="*50)
    print("CircuitBreaker 示例")
    print("="*50)
    
    # 1. 创建熔断器
    print("\n1. 创建熔断器")
    
    config = CircuitConfig(
        name="api-service",
        failure_threshold=3,
        timeout_seconds=60
    )
    
    cb = CircuitBreaker(config=config)
    print(f"   名称: {cb.name}")
    print(f"   初始状态: {cb.state.value}")
    
    # 2. 获取指标
    print("\n2. 获取指标")
    
    metrics = cb.get_metrics()
    print(f"   总调用: {metrics.total_calls}")
    print(f"   失败调用: {metrics.failed_calls}")
    print(f"   失败率: {metrics.failure_rate:.2%}")
    
    # 3. 重置
    print("\n3. 重置熔断器")
    
    cb.reset()
    print(f"   重置后状态: {cb.state.value}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    main()
