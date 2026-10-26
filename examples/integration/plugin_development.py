"""
插件开发示例

展示如何为 Agent OS Kernel 开发插件：
1. 插件基础结构（继承 PluginBase）
2. 事件注册与处理（register_event_handler / on_event）
3. 工具扩展（自定义 Tool 并注册到 ToolRegistry）
4. 生命周期管理（注册、初始化、启用、禁用、卸载）

注意：早期版本的 Hooks / register_hook / trigger_hook API 已重构为
基于 PluginEventType 的事件系统，本示例按当前 API 编写。
"""

from agent_os_kernel.core.plugin_system import (
    PluginManager,
    PluginBase,
    PluginInfo,
    PluginState,
    PluginEventType,
    create_plugin_manager,
)
from agent_os_kernel.tools.base import Tool, ToolParameter, ToolResult, ToolErrorCode
from agent_os_kernel.tools.registry import ToolRegistry


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


# 示例 1: 简单插件（注册事件处理器）
def create_simple_plugin():
    """创建一个简单插件（带事件处理）"""

    def on_state_change(event):
        print(f"[Hook] 状态变更事件: plugin={event.plugin_id}, data={event.data}")
        return {"result": "success"}

    # 创建插件管理器
    manager = PluginManager()

    # 注册事件处理器（替代旧版的 register_hook）
    manager.register_event_handler(PluginEventType.STATE_CHANGED, on_state_change)
    manager.register_event_handler(PluginEventType.ENABLED, on_state_change)

    return manager


# 示例 2: 自定义工具插件
class WordCountTool(Tool):
    """自定义业务工具：统计文本词数"""

    def name(self) -> str:
        return "word_count"

    def description(self) -> str:
        return "Count the number of words in a text"

    def parameters(self):
        return [
            ToolParameter(
                name="text",
                type="string",
                description="The text to analyze",
                required=True,
            )
        ]

    def execute(self, text: str = "", **kwargs):
        count = len(text.split())
        return ToolResult.success(data={"text": text, "words": count})


class CustomToolsPlugin(DemoPluginBase):
    """自定义工具插件 - 演示工具扩展"""

    def __init__(self):
        super().__init__(
            plugin_id="custom_tools",
            name="custom_tools",
            version="1.0.0",
        )
        self.tool_registry = None

    def initialize(self) -> bool:
        """初始化插件：注册自定义工具"""
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(WordCountTool())
        tools = [t["name"] for t in self.tool_registry.list_tools()]
        print(f"  [custom_tools] 已注册工具: {tools}")
        return True

    def shutdown(self) -> bool:
        self.tool_registry = None
        return True

    def on_event(self, event) -> None:
        """接收插件生命周期事件"""
        print(f"  [custom_tools] 收到事件: {event.event_type.value} ({event.data})")


# 示例 3: 业务逻辑插件
class BusinessLogicPlugin(DemoPluginBase):
    """业务逻辑插件示例"""

    def __init__(self):
        super().__init__(
            plugin_id="business_logic",
            name="business_logic",
            version="1.0.0",
        )

    def initialize(self) -> bool:
        # 在管理器上注册事件处理器
        self.plugin_manager.register_event_handler(
            PluginEventType.STATE_CHANGED,
            self._on_task_state_changed,
        )
        self.plugin_manager.register_event_handler(
            PluginEventType.ERROR,
            self._on_error,
        )
        print("  [business_logic] 事件处理器已注册")
        return True

    def shutdown(self) -> bool:
        return True

    def _on_task_state_changed(self, event):
        agent_name = event.data.get("agent_name", "unknown")
        result = event.data.get("result", {})
        print(f"  [business_logic] Agent {agent_name} 状态变更: {result}")
        return result

    def _on_error(self, event):
        agent_name = event.data.get("agent_name", "unknown")
        error = event.data.get("error", "unknown error")
        print(f"  [business_logic] Agent {agent_name} 错误: {error}")
        return {"error": str(error)}


# 示例 4: 数据分析插件
class AnalyticsPlugin(DemoPluginBase):
    """数据分析插件 - 通过事件统计系统行为"""

    def __init__(self):
        super().__init__(
            plugin_id="analytics",
            name="analytics",
            version="1.0.0",
        )
        self.stats = {
            "agents_created": 0,
            "state_changes": 0,
            "errors": 0,
        }

    def initialize(self) -> bool:
        self.plugin_manager.register_event_handler(
            PluginEventType.STATE_CHANGED, self._track_state_change
        )
        self.plugin_manager.register_event_handler(
            PluginEventType.ERROR, self._track_error
        )
        return True

    def shutdown(self) -> bool:
        return True

    def _track_state_change(self, event):
        self.stats["state_changes"] += 1
        if event.data.get("kind") == "agent_created":
            self.stats["agents_created"] += 1
        print(f"  [analytics] Agent created: {event.data.get('agent_name')}")

    def _track_error(self, event):
        self.stats["errors"] += 1

    def get_stats(self) -> dict:
        return self.stats.copy()


# 示例 5: 完整插件模板
PLUGIN_TEMPLATE = '''
# my_plugin.py - 插件模板
# 复制此文件并修改为你的插件

from agent_os_kernel.core.plugin_system import (
    PluginManager,
    PluginBase,
    PluginState,
    PluginEventType,
)


class MyPlugin(PluginBase):
    """我的插件"""

    def __init__(self):
        super().__init__(
            plugin_id="my_plugin",
            name="my_plugin",
            version="1.0.0",
        )

    def initialize(self) -> bool:
        """初始化插件 - 注册后调用"""
        # 注册事件处理器（替代旧版的 register_hook）
        self.plugin_manager.register_event_handler(
            PluginEventType.STATE_CHANGED,
            self._on_state_changed,
            priority=100  # 优先级，数字越大越先执行
        )
        return True

    def shutdown(self) -> bool:
        """关闭插件 - 卸载前调用"""
        return True

    def _on_state_changed(self, event):
        """状态变更事件处理"""
        print(f"Agent state changed: {event.data}")
        return event.data


def create_plugin() -> MyPlugin:
    """插件入口函数"""
    return MyPlugin()
'''


def demo_plugin_system():
    """演示插件系统"""
    print("=" * 60)
    print("插件系统演示")
    print("=" * 60)
    
    # 创建插件管理器
    manager = create_plugin_manager()
    
    # 注册业务逻辑插件
    business = BusinessLogicPlugin()
    manager.register_plugin(business)
    
    # 注册数据分析插件
    analytics = AnalyticsPlugin()
    manager.register_plugin(analytics)
    
    # 注册自定义工具插件
    custom_tools = CustomToolsPlugin()
    manager.register_plugin(custom_tools)
    
    # 初始化插件（调用各插件的 initialize()）
    print("\n0. 初始化插件:")
    for plugin_id in manager.list_plugin_ids():
        manager.initialize_plugin(plugin_id)
    
    # 启用插件
    print("\n1. 启用插件:")
    for plugin_id in manager.list_plugin_ids():
        manager.enable_plugin(plugin_id)
    
    # 触发事件（替代旧版的 trigger_hook）
    print("\n2. 触发状态变更事件:")
    manager.publish_event(
        "demo",
        PluginEventType.STATE_CHANGED,
        {"kind": "agent_created", "agent_name": "TestAgent", "result": {"status": "ok"}},
    )
    
    print("\n3. 触发错误事件:")
    manager.publish_event(
        "demo",
        PluginEventType.ERROR,
        {"agent_name": "TestAgent", "error": Exception("Test error")},
    )
    
    print("\n4. 统计信息:")
    print(f"Stats: {analytics.get_stats()}")
    
    print("\n5. 列出所有插件:")
    plugins = manager.list_plugins()
    for plugin in plugins:
        print(f"  - {plugin.name} v{plugin.version} ({plugin.state.value})")
    
    print("\n6. 管理器统计:")
    print(f"  {manager.get_stats()}")
    
    print("\n7. 禁用并卸载 analytics 插件:")
    manager.disable_plugin("analytics")
    manager.unregister_plugin("analytics")
    
    print("\n8. 插件模板:")
    print(PLUGIN_TEMPLATE[:500] + "...")
    
    # 关闭管理器
    manager.shutdown()


if __name__ == "__main__":
    demo_plugin_system()
