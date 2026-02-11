#!/usr/bin/env python3
"""EventBus 使用示例"""

import asyncio
from agent_os_kernel.core.event_bus_enhanced import (
    EnhancedEventBus, EventType, EventPriority
)


async def main():
    print("="*50)
    print("EventBus 示例")
    print("="*50)
    
    bus = EnhancedEventBus()
    
    results = []
    
    async def on_task_started(event):
        print(f"   任务开始: {event.payload}")
        results.append(event.event_type.value)
    
    bus.subscribe(EventType.TASK_STARTED, on_task_started)
    
    await bus.publish_event(EventType.TASK_STARTED, {"task_id": "task-001"})
    await asyncio.sleep(0.1)
    
    print(f"   收到事件: {len(results)}")
    print("="*50)
    print("完成!")


if __name__ == "__main__":
    asyncio.run(main())
