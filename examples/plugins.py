"""
Plugin Demo

展示插件系统的使用方式
"""

from agent_os_kernel.core.plugin_system import (
    PluginManager,
    BasePlugin,
    PluginState
)


class MetricsPlugin(BasePlugin):
    """指标插件"""
    
    @property
    def name(self) -> str:
        return "metrics-plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Collect and report metrics"
    
    def initialize(self, manager: PluginManager):
        print("  ✓ Metrics plugin initialized")
    
    def enable(self):
        print("  ✓ Metrics plugin enabled")


class LoggingPlugin(BasePlugin):
    """日志插件"""
    
    @property
    def name(self) -> str:
        return "logging-plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Logging plugin"
    
    async def on_agent_created(self, agent_id: str):
        print(f"  [LOG] Agent created: {agent_id}")
    
    def initialize(self, manager: PluginManager):
        manager.register_hook(self.name, "agent_created", self.on_agent_created)
        print("  ✓ Logging plugin initialized")


class MonitoringPlugin(BasePlugin):
    """监控插件"""
    
    @property
    def name(self) -> str:
        return "monitoring-plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "System monitoring"
    
    def enable(self):
        print("  ✓ Monitoring plugin enabled")


async def main():
    print("=" * 60)
    print("🔌 Plugin System Demo")
    print("=" * 60)
    
    # 创建插件管理器
    manager = create_plugin_manager()
    
    # 加载插件
    print("\n1. Loading plugins...")
    
    await manager.load_plugin(MetricsPlugin)
    await manager.load_plugin(LoggingPlugin)
    await manager.load_plugin(MonitoringPlugin)
    
    # 启用插件
    print("\n2. Enabling plugins...")
    
    await manager.enable_plugin("metrics-plugin")
    await manager.enable_plugin("logging-plugin")
    await manager.enable_plugin("monitoring-plugin")
    
    # 触发钩子
    print("\n3. Triggering hooks...")
    
    await manager.trigger_hook("agent_created", "test-agent-1")
    await manager.trigger_hook("agent_created", "test-agent-2")
    
    # 列出插件
    print("\n4. Listing plugins...")
    
    for info in manager.list_plugins():
        print(f"  - {info.name} v{info.version} ({info.state.value})")
    
    # 统计
    print("\n5. Statistics...")
    
    stats = manager.get_stats()
    print(f"  {stats}")
    
    # 禁用插件
    print("\n6. Disabling plugin...")
    
    await manager.disable_plugin("monitoring-plugin")
    
    # 卸载插件
    print("\n7. Unloading plugin...")
    
    await manager.unload_plugin("monitoring-plugin")
    
    print("\n" + "=" * 60)
    print("✅ Plugin Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


def create_plugin_manager():
    """创建插件管理器"""
    return PluginManager()
