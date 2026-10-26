# -*- coding: utf-8 -*-

"""熔断器演示"""

import asyncio
import random

from agent_os_kernel.core.circuit_breaker import (
    CircuitBreaker,
    CircuitConfig,
    CircuitError,
    CircuitState,
)


async def main():
    print("="*60)
    print("Circuit Breaker Demo")
    print("="*60)

    # 创建熔断器
    config = CircuitConfig(
        failure_threshold=3,
        timeout_seconds=2,
        success_threshold=2
    )
    breaker = CircuitBreaker("api", config)

    async def unreliable_api():
        """模拟不稳定的 API"""
        if random.random() < 0.7:  # 70% 失败率
            raise ConnectionError("API 暂时不可用")
        return {"status": "ok", "data": "success"}

    async def fallback():
        """降级服务"""
        return {"status": "fallback", "message": "使用缓存数据"}

    print("\n🔄 测试不稳定的 API...")

    # 测试调用
    for i in range(10):
        await asyncio.sleep(0.3)

        state = breaker.state.value
        print(f"  请求 {i+1}: 熔断器状态 = {state}")

        try:
            result = await breaker.call_async(unreliable_api)
            print(f"    ✅ 结果: {result}")
        except CircuitError as e:
            # 熔断器打开：走降级逻辑
            print(f"    ⛔ 熔断中，执行降级: {await fallback()}")
        except Exception as e:
            # 业务异常：同样走降级逻辑
            print(f"    ❌ 错误: {e}，执行降级: {await fallback()}")

        # 显示统计
        info = breaker.get_info()
        metrics = info["metrics"]
        print(f"    📊 统计: 连续失败 {metrics['consecutive_failures']} 次, "
              f"总请求 {metrics['total_requests']} 次, "
              f"拒绝 {metrics['rejected_requests']} 次")

    # 最终状态
    info = breaker.get_info()
    print(f"\n📊 最终状态: {info['state']}")
    print(f"   失败次数: {info['failure_count']}/{info['failure_threshold']}")
    print(f"   状态切换次数: {info['metrics']['state_transitions']}")

    # 重置熔断器
    breaker.reset()
    print(f"\n♻️ 重置后状态: {breaker.state.value}")

    print("\n✅ 演示完成")


if __name__ == "__main__":
    random.seed(42)  # 固定随机种子，保证演示可复现
    asyncio.run(main())
