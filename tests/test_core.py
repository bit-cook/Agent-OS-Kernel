"""
Core Module Tests
"""

import sys
sys.path.insert(0, '.')

import asyncio
from datetime import datetime


async def test_events():
    """测试事件系统"""
    print("\n" + "=" * 50)
    print("Testing Events System")
    print("=" * 50)
    
    from agent_os_kernel.core.events import (
        EventBus, Event, EventType
    )
    
    # 创建事件总线
    bus = EventBus()
    print("✓ EventBus created")
    
    # 创建事件
    event = Event.create(
        event_type=EventType.AGENT_CREATED,
        source="test",
        data={"agent_id": "test-agent"}
    )
    print(f"✓ Event created: {event.event_type.value}")
    
    # 测试通过
    print("✓ Events test passed")
    return True


async def test_state():
    """测试状态管理"""
    print("\n" + "=" * 50)
    print("Testing State Management")
    print("=" * 50)
    
    from agent_os_kernel.core.state import (
        StateManager, AgentState
    )
    
    # 创建状态管理器
    state_manager = StateManager()
    print("✓ StateManager created")
    
    # 创建 Agent 状态
    record = await state_manager.create_agent(
        agent_id="test-agent",
        initial_state=AgentState.CREATED
    )
    print(f"✓ Agent state created: {record.current_state.value}")
    
    # 状态转换
    result = await state_manager.transition(
        agent_id="test-agent",
        to_state=AgentState.RUNNING,
        reason="Starting"
    )
    print(f"✓ State transition: {result}")
    
    # 获取状态
    state = await state_manager.get_state("test-agent")
    print(f"✓ Got state: {state.current_state.value}")
    
    print("✓ State test passed")
    return True


async def test_metrics():
    """测试指标系统"""
    print("\n" + "=" * 50)
    print("Testing Metrics")
    print("=" * 50)
    
    from agent_os_kernel.core.metrics import (
        MetricsCollector, MetricType
    )
    
    # 创建收集器
    collector = MetricsCollector()
    print("✓ MetricsCollector created")
    
    # 测试计数器
    collector.counter("test_counter", 1)
    print("✓ Counter incremented")
    
    # 测试仪表盘
    collector.gauge("test_gauge", 100)
    print("✓ Gauge set")
    
    # 测试直方图
    collector.histogram("test_histogram", 0.5)
    print("✓ Histogram recorded")
    
    # 获取统计
    stats = collector.get_stats()
    print(f"✓ Stats: {stats['total_metrics']} metrics")
    
    print("✓ Metrics test passed")
    return True


async def test_plugins():
    """测试插件系统"""
    print("\n" + "=" * 50)
    print("Testing Plugin System")
    print("=" * 50)
    
    from agent_os_kernel.core.plugin_system import (
        PluginManager, BasePlugin, PluginState
    )
    
    # 创建插件管理器
    manager = PluginManager()
    print("✓ PluginManager created")
    
    # 检查状态
    stats = manager.get_stats()
    print(f"✓ Stats: {stats['total_plugins']} plugins")
    
    print("✓ Plugins test passed")
    return True


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("Agent OS Kernel - Core Module Tests")
    print("=" * 60)
    
    tests = [
        ("Events", test_events),
        ("State", test_state),
        ("Metrics", test_metrics),
        ("Plugins", test_plugins),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = await test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
