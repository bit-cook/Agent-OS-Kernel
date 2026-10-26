#!/usr/bin/env python3
"""
综合示例 - 展示Agent-OS-Kernel所有核心功能

此示例演示如何组合使用多个核心模块构建完整的Agent系统。
"""

import asyncio
from agent_os_kernel.core.rate_limiter import RateLimiter, RateLimitConfig
from datetime import datetime

# 导入核心组件
from agent_os_kernel.core import (
    # 缓存
    CacheSystem,
    # 消息队列
    PriorityMessageQueue, MessageBroker,
    # 熔断器
    CircuitBreaker, CircuitConfig,
    # 限流器
    # 重试机制
    RetryMechanism, RetryCondition,
    # 工作流
    WorkflowEngine, Workflow,
    # 分布式锁
    DistributedLock,
    # 事件总线
    EventBus,
    # 状态机
    StateMachine,
    # 插件系统
    PluginManager,
)


class AgentSystem:
    """完整的Agent系统示例"""
    
    def __init__(self):
        self.cache = CacheSystem()
        self.message_broker = MessageBroker()
        self.circuit_breaker = CircuitBreaker("api_calls")
        self.rate_limiter = RateLimiter(RateLimitConfig())
        self.workflow_engine = WorkflowEngine()
        self.event_bus = EventBus()
        self.plugin_manager = PluginManager()
        
    async def process_task(self, task_data: dict) -> dict:
        """处理任务的完整流程"""
        
        # 1. 检查缓存
        cache_key = f"task:{task_data['id']}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            print(f"✅ 缓存命中: {cache_key}")
            return cached_result
        
        # 2. 限流检查
        if not await self.rate_limiter.acquire():
            return {"error": "Rate limit exceeded"}
        
        # 3. 使用熔断器调用外部API
        try:
            result = await self.circuit_breaker.call(
                self._call_external_api,
                task_data
            )
        except Exception as e:
            return {"error": f"API call failed: {e}"}
        
        # 4. 缓存结果
        self.cache.set(cache_key, result, ttl=300)
        
        # 5. 发送事件
        self.event_bus.publish("task.completed", {
            "task_id": task_data['id'],
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    async def _call_external_api(self, data: dict) -> dict:
        """模拟外部API调用"""
        await asyncio.sleep(0.1)
        return {"status": "success", "data": data}


async def main():
    """主函数"""
    print("=" * 60)
    print("Agent-OS-Kernel 综合示例")
    print("=" * 60)
    
    system = AgentSystem()
    
    # 模拟处理多个任务
    tasks = [
        {"id": f"task_{i}", "payload": f"data_{i}"}
        for i in range(5)
    ]
    
    for task in tasks:
        result = await system.process_task(task)
        print(f"📦 任务 {task['id']}: {result.get('status', 'error')}")
    
    print("\n" + "=" * 60)
    print("所有任务处理完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
