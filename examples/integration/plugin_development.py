"""
插件开发示例

展示如何为 Agent OS Kernel 开发插件：
1. 插件基础结构
2. 钩子注册
3. 工具扩展
4. 事件处理
"""

from agent_os_kernel.core.plugin_system import PluginManager, Hooks, PluginInfo
from agent_os_kernel.core.types import ToolDefinition, ToolParameter, ToolCategory


# 示例 1: 简单插件
def create_simple_plugin():
    """创建一个简单插件"""
    
    def my_hook_callback(*args, **kwargs):
        print(f"Hook called with args: {args}, kwargs: {kwargs}")
        return {"result": "success"}
    
    # 创建插件管理器
    manager = PluginManager()
    
    # 注册钩子
    manager.register_hook(Hooks.BEFORE_AGENT_SPAWN, my_hook_callback)
    manager.register_hook(Hooks.AFTER_AGENT_RUN, my_hook_callback)
    
    return manager


# 示例 2: 自定义工具插件
class CustomToolsPlugin:
    """自定义工具插件"""
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        return PluginInfo(
            name="custom_tools",
            version="1.0.0",
            author="Developer",
            description="提供自定义业务工具",
            entry_point="plugins.custom_tools",
            dependencies=[],
            hooks=["before_tool_call", "after_tool_call"]
        )
    
    @staticmethod
    def register_hooks(manager: PluginManager):
        """注册插件钩子"""
        manager.register_hook(
            "before_tool_call",
            CustomToolsPlugin._before_tool_call,
            priority=100
        )
        manager.register_hook(
            "after_tool_call",
            CustomToolsPlugin._after_tool_call,
            priority=100
        )
    
    @staticmethod
    def _before_tool_call(tool_name: str, **kwargs):
        print(f"Before calling tool: {tool_name}")
        # 可以在这里添加日志、验证等逻辑
        return {"tool": tool_name, "allowed": True}
    
    @staticmethod
    def _after_tool_call(tool_name: str, result: dict, **kwargs):
        print(f"After calling tool: {tool_name}, result: {result}")
        # 可以在这里添加后置处理、统计等逻辑
        return result


# 示例 3: 业务逻辑插件
class BusinessLogicPlugin:
    """业务逻辑插件示例"""
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        return PluginInfo(
            name="business_logic",
            version="1.0.0",
            author="Developer",
            description="业务逻辑扩展",
            entry_point="plugins.business",
            hooks=["on_agent_complete", "on_error"]
        )
    
    @staticmethod
    def register_hooks(manager: PluginManager):
        manager.register_hook("on_agent_complete", BusinessLogicPlugin._on_complete)
        manager.register_hook("on_error", BusinessLogicPlugin._on_error)
    
    @staticmethod
    def _on_complete(agent_name: str, result: dict):
        print(f"Agent {agent_name} completed with result: {result}")
        # 可以发送通知、更新数据库等
        return result
    
    @staticmethod
    def _on_error(agent_name: str, error: Exception):
        print(f"Agent {agent_name} error: {error}")
        # 可以发送告警、记录错误等
        return {"error": str(error)}


# 示例 4: 数据分析插件
class AnalyticsPlugin:
    """数据分析插件"""
    
    def __init__(self):
        self.stats = {
            'agents_created': 0,
            'tools_called': 0,
            'errors': 0
        }
    
    def get_plugin_info(self) -> PluginInfo:
        return PluginInfo(
            name="analytics",
            version="1.0.0",
            author="Developer",
            description="性能分析和统计",
            entry_point="plugins.analytics",
            hooks=["after_agent_spawn", "after_tool_call", "on_error"]
        )
    
    def register_hooks(self, manager: PluginManager):
        manager.register_hook("after_agent_spawn", self._track_agent)
        manager.register_hook("after_tool_call", self._track_tool)
        manager.register_hook("on_error", self._track_error)
    
    def _track_agent(self, agent_name: str, **kwargs):
        self.stats['agents_created'] += 1
        print(f"Agent created: {agent_name}")
    
    def _track_tool(self, tool_name: str, **kwargs):
        self.stats['tools_called'] += 1
    
    def _track_error(self, error: Exception, **kwargs):
        self.stats['errors'] += 1
    
    def get_stats(self) -> dict:
        return self.stats.copy()


# 示例 5: 完整插件模板
PLUGIN_TEMPLATE = '''
# my_plugin.py - 插件模板
# 复制此文件并修改为你的插件

from agent_os_kernel.core.plugin_system import PluginManager, Hooks, PluginInfo
from agent_os_kernel.core.types import ToolDefinition, ToolParameter, ToolCategory


class MyPlugin:
    """我的插件"""
    
    @staticmethod
    def get_plugin_info() -> PluginInfo:
        """返回插件信息"""
        return PluginInfo(
            name="my_plugin",
            version="1.0.0",
            author="Your Name",
            description="插件描述",
            entry_point="plugins.my_plugin",
            dependencies=[],
            hooks=[
                "before_agent_spawn",
                "after_agent_run",
                "on_error"
            ]
        )
    
    @staticmethod
    def register_hooks(manager: PluginManager):
        """注册钩子"""
        # 在这里注册你的钩子
        manager.register_hook(
            Hooks.BEFORE_AGENT_SPAWN,
            MyPlugin._before_spawn,
            priority=100  # 优先级，数字越大越先执行
        )
        
        manager.register_hook(
            Hooks.AFTER_AGENT_RUN,
            MyPlugin._after_run,
            priority=100
        )
        
        manager.register_hook(
            Hooks.ON_ERROR,
            MyPlugin._on_error,
            priority=100
        )
    
    @staticmethod
    def _before_spawn(agent_name: str, **kwargs):
        """Agent 创建前的钩子"""
        print(f"Agent {agent_name} is about to spawn")
        # 可以返回修改后的参数
        return kwargs
    
    @staticmethod
    def _after_run(agent_name: str, result: dict, **kwargs):
        """Agent 运行后的钩子"""
        print(f"Agent {agent_name} completed with result: {result}")
        return result
    
    @staticmethod
    def _on_error(agent_name: str, error: Exception, **kwargs):
        """错误处理钩子"""
        print(f"Agent {agent_name} error: {error}")
        # 可以返回恢复策略
        return {"action": "retry", "error": str(error)}


def get_plugin_info():
    """插件入口函数"""
    return MyPlugin.get_plugin_info()


def register_hooks(manager: PluginManager):
    """钩子注册函数"""
    MyPlugin.register_hooks(manager)
'''


def demo_plugin_system():
    """演示插件系统"""
    print("=" * 60)
    print("插件系统演示")
    print("=" * 60)
    
    # 创建插件管理器
    manager = PluginManager()
    
    # 注册业务逻辑插件
    BusinessLogicPlugin.register_hooks(manager)
    
    # 注册数据分析插件
    analytics = AnalyticsPlugin()
    analytics.register_hooks(manager)
    
    # 触发钩子
    print("\n1. 触发 Agent 完成钩子:")
    manager.trigger_hook("on_agent_complete", "TestAgent", result={"status": "ok"})
    
    print("\n2. 触发错误钩子:")
    manager.trigger_hook("on_error", "TestAgent", error=Exception("Test error"))
    
    print("\n3. 统计信息:")
    print(f"Stats: {analytics.get_stats()}")
    
    print("\n4. 列出所有插件:")
    plugins = manager.list_plugins()
    for plugin in plugins:
        print(f"  - {plugin.name} v{plugin.version}")
    
    print("\n5. 插件模板:")
    print(PLUGIN_TEMPLATE[:500] + "...")


if __name__ == "__main__":
    demo_plugin_system()
