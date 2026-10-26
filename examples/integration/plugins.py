"""
Plugin Demo
展示插件系统的使用方式

按当前插件 API 编写：
- 插件继承 PluginBase，实现 initialize()/shutdown()
- 通过 PluginManager 注册、初始化、启用、禁用、卸载
- 事件替代旧版钩子：register_event_handler + publish_event
"""

import asyncio
from agent_os_kernel.core.plugin_system import (
    PluginManager,
    PluginBase,
    PluginState,
    PluginEventType,
    create_plugin_manager,
)


class DemoPluginBase(PluginBase):
    """演示用插件基类

    PluginManager.get_stats() 会读取插件的 is_loaded / is_enabled 属性，
    这里基于 PluginState 提供这两个派生属性。
    """

    @property
    def is_loaded(self) -> bool:
        return self.state not in (PluginState.UNLOADED, PluginState.UNLOADING)

    @property
    def is_enabled(self) -> bool:
        return self.state == PluginState.ENABLED


class MetricsPlugin(DemoPluginBase):
    """指标插件"""

    def __init__(self):
        super().__init__(
            plugin_id="metrics-plugin",
            name="metrics-plugin",
            version="1.0.0",
        )

    def initialize(self) -> bool:
        print("  ✓ Metrics plugin initialized")
        return True

    def shutdown(self) -> bool:
        return True

    def enable(self) -> bool:
        print("  ✓ Metrics plugin enabled")
        self.state = PluginState.ENABLED
        return True


class LoggingPlugin(DemoPluginBase):
    """日志插件 - 监听 Agent 创建事件"""

    def __init__(self):
        super().__init__(
            plugin_id="logging-plugin",
            name="logging-plugin",
            version="1.0.0",
        )

    def initialize(self) -> bool:
        # 注册事件处理器（替代旧版 register_hook）
        self.plugin_manager.register_event_handler(
            PluginEventType.STATE_CHANGED,
            self._on_agent_created,
        )
        print("  ✓ Logging plugin initialized")
        return True

    def shutdown(self) -> bool:
        return True

    def _on_agent_created(self, event):
        if event.data.get("kind") == "agent_created":
            print(f"  [LOG] Agent created: {event.data.get('agent_id')}")


class MonitoringPlugin(DemoPluginBase):
    """监控插件"""

    def __init__(self):
        super().__init__(
            plugin_id="monitoring-plugin",
            name="monitoring-plugin",
            version="1.0.0",
        )

    def initialize(self) -> bool:
        print("  ✓ Monitoring plugin initialized")
        return True

    def shutdown(self) -> bool:
        return True

    def enable(self) -> bool:
        print("  ✓ Monitoring plugin enabled")
        self.state = PluginState.ENABLED
        return True


async def main():
    print("=" * 60)
    print("🔌 Plugin System Demo")
    print("=" * 60)
    
    # 创建插件管理器
    manager = create_plugin_manager()
    
    # 加载插件（注册到管理器）
    print("\n1. Loading plugins...")
    
    manager.register_plugin(MetricsPlugin())
    manager.register_plugin(LoggingPlugin())
    manager.register_plugin(MonitoringPlugin())
    
    # 初始化插件
    print("\n2. Initializing plugins...")
    for plugin_id in manager.list_plugin_ids():
        manager.initialize_plugin(plugin_id)
    
    # 启用插件
    print("\n3. Enabling plugins...")
    
    manager.enable_plugin("metrics-plugin")
    manager.enable_plugin("logging-plugin")
    manager.enable_plugin("monitoring-plugin")
    
    # 触发事件（替代旧版 trigger_hook）
    print("\n4. Triggering events...")
    
    manager.publish_event(
        "demo",
        PluginEventType.STATE_CHANGED,
        {"kind": "agent_created", "agent_id": "test-agent-1"},
    )
    manager.publish_event(
        "demo",
        PluginEventType.STATE_CHANGED,
        {"kind": "agent_created", "agent_id": "test-agent-2"},
    )
    
    # 列出插件
    print("\n5. Listing plugins...")
    
    for info in manager.list_plugins():
        print(f"  - {info.name} v{info.version} ({info.state.value})")
    
    # 统计
    print("\n6. Statistics...")
    
    stats = manager.get_stats()
    print(f"  {stats}")
    
    # 禁用插件
    print("\n7. Disabling plugin...")
    
    manager.disable_plugin("monitoring-plugin")
    
    # 卸载插件
    print("\n8. Unloading plugin...")
    
    manager.unregister_plugin("monitoring-plugin")
    
    # 关闭管理器
    manager.shutdown()
    
    print("\n" + "=" * 60)
    print("✅ Plugin Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
