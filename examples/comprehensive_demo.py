#!/usr/bin/env python3
"""综合示例 - Agent OS Kernel 核心组件演示"""

import asyncio
from agent_os_kernel.core.context_manager import ContextManager
from agent_os_kernel.core.storage import StorageManager
from agent_os_kernel.core.event_bus_enhanced import EnhancedEventBus, EventType
from agent_os_kernel.core.checkpointer import Checkpointer
from agent_os_kernel.core.circuit_breaker import CircuitBreaker, CircuitConfig


async def main():
    print("="*60)
    print("Agent OS Kernel - 综合示例")
    print("="*60)
    
    # 1. ContextManager
    print("\n[1] ContextManager - 虚拟内存式上下文管理")
    
    ctx = ContextManager(max_context_tokens=100000)
    page_id = ctx.allocate_page(
        agent_pid="agent-001",
        content="你是一个智能助手。",
        importance=0.9
    )
    context = ctx.get_agent_context("agent-001")
    print(f"   ✓ 上下文已分配，长度: {len(context)}")
    
    # 2. StorageManager
    print("\n[2] StorageManager - 五重角色存储")
    
    storage = StorageManager()
    storage.save("session/data", {"user": "Alice"})
    data = storage.retrieve("session/data")
    print(f"   ✓ 数据已存储: {data}")
    
    # 3. EventBus
    print("\n[3] EventBus - 事件总线")
    
    bus = EnhancedEventBus()
    
    results = []
    
    async def on_task(event):
        results.append(event.event_type.value)
    
    bus.subscribe(EventType.TASK_STARTED, on_task)
    await bus.publish_event(EventType.TASK_STARTED, {"task": "demo"})
    await asyncio.sleep(0.1)
    print(f"   ✓ 事件已发布，收到: {len(results)} 个响应")
    
    # 4. Checkpointer
    print("\n[4] Checkpointer - 状态保存/恢复")
    
    cp = Checkpointer()
    cp_id = await cp.create("demo-state", {"step": 1, "data": "test"})
    state = await cp.restore(cp_id)
    print(f"   ✓ 检查点已创建/恢复: {state}")
    
    # 5. CircuitBreaker
    print("\n[5] CircuitBreaker - 熔断保护")
    
    config = CircuitConfig(name="demo", failure_threshold=5, timeout_seconds=60)
    cb = CircuitBreaker(config=config)
    print(f"   ✓ 熔断器已创建，状态: {cb.state.value}")
    
    # 6. 统计
    print("\n[6] 组件就绪")
    print("   ✓ 所有核心组件运行正常")
    
    print("\n" + "="*60)
    print("Agent OS Kernel 核心组件演示完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
