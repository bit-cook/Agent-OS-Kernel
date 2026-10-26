"""测试事件总线"""

import pytest
import asyncio
from agent_os_kernel.core.event_bus_enhanced import EnhancedEventBus, EventType, EventPriority


class TestEventBus:
    """测试事件总线"""

    def test_initialization(self):
        """测试初始化"""
        bus = EnhancedEventBus()
        assert bus is not None

    def test_subscribe_event(self):
        """测试订阅事件"""
        bus = EnhancedEventBus()
        results = []

        def handler(event):
            results.append(event.event_type.value)

        sub_id = bus.subscribe(EventType.TASK_STARTED, handler)

        assert sub_id is not None
        assert isinstance(sub_id, str)

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = EnhancedEventBus()
        results = []

        def handler(event):
            results.append(event.event_type.value)

        sub_id = bus.subscribe(EventType.TASK_STARTED, handler)
        bus.unsubscribe(sub_id)

        assert bus.unsubscribe(sub_id) is False

    def test_get_stats(self):
        """测试获取统计"""
        bus = EnhancedEventBus()
        stats = bus.get_stats()

        assert "events_published" in stats
        assert "events_processed" in stats


@pytest.mark.asyncio
class TestEventBusAsync:
    """异步测试事件总线"""

    async def test_publish_subscribe(self):
        """测试发布订阅"""
        bus = EnhancedEventBus()
        results = []

        async def handler(event):
            results.append(event.event_type.value)

        bus.subscribe(EventType.TASK_STARTED, handler)

        await bus.publish_event(EventType.TASK_STARTED, {"data": "test"})
        await asyncio.sleep(0.1)

        assert len(results) == 1
        assert results[0] == "task:started"

    async def test_priority_ordering(self):
        """测试优先级"""
        bus = EnhancedEventBus()
        results = []

        def low_handler(event):
            results.append("low")

        def high_handler(event):
            results.append("high")

        bus.subscribe(EventType.TASK_STARTED, low_handler, EventPriority.LOW)
        bus.subscribe(EventType.TASK_STARTED, high_handler, EventPriority.HIGH)

        await bus.publish_event(EventType.TASK_STARTED, {})
        await asyncio.sleep(0.1)

        assert len(results) == 2
        # 高优先级先执行
        assert results[0] == "high"

    async def test_wildcard_subscription(self):
        """测试通配符订阅"""
        bus = EnhancedEventBus()
        results = []

        def wildcard_handler(event):
            results.append(event.event_type.value)

        bus.subscribe_wildcard(wildcard_handler)

        await bus.publish_event(EventType.TASK_STARTED, {})
        await bus.publish_event(EventType.AGENT_STARTED, {})
        await asyncio.sleep(0.1)

        assert len(results) == 2

    async def test_multiple_subscribers(self):
        """测试多个订阅者"""
        bus = EnhancedEventBus()
        results = []

        async def handler1(event):
            results.append("handler1")

        async def handler2(event):
            results.append("handler2")

        bus.subscribe(EventType.TASK_COMPLETED, handler1)
        bus.subscribe(EventType.TASK_COMPLETED, handler2)

        await bus.publish_event(EventType.TASK_COMPLETED, {})
        await asyncio.sleep(0.1)

        assert len(results) == 2
