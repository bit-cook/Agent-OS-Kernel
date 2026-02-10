"""测试插件系统"""

import pytest
from agent_os_kernel.core.plugin_system import PluginManager, Plugin, Hooks, PluginInfo


class TestPluginManager:
    """测试 PluginManager"""
    
    def test_initialization(self):
        manager = PluginManager()
        
        assert manager._plugins == {}
        assert manager._hooks == {}
        assert manager._enabled is True
    
    def test_register_hook(self):
        manager = PluginManager()
        
        def my_callback(*args, **kwargs):
            return "called"
        
        manager.register_hook("test_hook", my_callback)
        
        assert "test_hook" in manager._hooks
        assert len(manager._hooks["test_hook"]) == 1
    
    def test_register_multiple_hooks(self):
        manager = PluginManager()
        
        def callback1(*args, **kwargs):
            return "first"
        def callback2(*args, **kwargs):
            return "second"
        
        manager.register_hook("test", callback1, priority=10)
        manager.register_hook("test", callback2, priority=5)
        
        # 应该按优先级排序
        assert manager._hooks["test"][0]['priority'] == 10
    
    def test_trigger_hook(self):
        manager = PluginManager()
        
        results = []
        def callback(data):
            results.append(data)
            return data * 2
        
        manager.register_hook("test", callback)
        result = manager.trigger_hook("test", 5)
        
        assert result == [10]
        assert results == [5]
    
    def test_trigger_hook_no_callbacks(self):
        manager = PluginManager()
        
        result = manager.trigger_hook("empty_hook")
        
        assert result == []
    
    def test_unregister_hook(self):
        manager = PluginManager()
        
        def callback(*args, **kwargs):
            return "called"
        
        manager.register_hook("test", callback)
        manager.unregister_hook("test", callback)
        
        assert len(manager._hooks["test"]) == 0
    
    def test_get_plugin(self):
        manager = PluginManager()
        
        # 手动添加插件
        info = PluginInfo(
            name="test",
            version="1.0",
            author="test",
            description="test",
            entry_point="test"
        )
        plugin = Plugin(info=info, module=None)
        manager._plugins["test"] = plugin
        
        retrieved = manager.get_plugin("test")
        
        assert retrieved is not None
        assert retrieved.info.name == "test"
    
    def test_get_nonexistent_plugin(self):
        manager = PluginManager()
        
        result = manager.get_plugin("nonexistent")
        
        assert result is None
    
    def test_list_plugins(self):
        manager = PluginManager()
        
        # 添加插件
        info1 = PluginInfo(name="p1", version="1.0", author="a", description="d", entry_point="e")
        info2 = PluginInfo(name="p2", version="1.0", author="a", description="d", entry_point="e")
        manager._plugins["p1"] = Plugin(info=info1, module=None)
        manager._plugins["p2"] = Plugin(info=info2, module=None)
        
        plugins = manager.list_plugins()
        
        assert len(plugins) == 2
    
    def test_enable_disable_plugin(self):
        manager = PluginManager()
        
        info = PluginInfo(name="test", version="1.0", author="a", description="d", entry_point="e")
        plugin = Plugin(info=info, module=None, enabled=False)
        manager._plugins["test"] = plugin
        
        manager.enable_plugin("test")
        assert plugin.enabled is True
        
        manager.disable_plugin("test")
        assert plugin.enabled is False
    
    def test_get_plugin_info_dict(self):
        manager = PluginManager()
        
        info = PluginInfo(name="test", version="1.0", author="a", description="d", entry_point="e", hooks=["h1"])
        manager._plugins["test"] = Plugin(info=info, module=None, enabled=True)
        
        result = manager.get_plugin_info_dict()
        
        assert "test" in result
        assert result["test"]["enabled"] is True
        assert result["test"]["hooks"] == ["h1"]


class TestHooks:
    """测试 Hooks 常量"""
    
    def test_all_hooks_defined(self):
        assert Hooks.BEFORE_AGENT_SPAWN == "before_agent_spawn"
        assert Hooks.AFTER_AGENT_SPAWN == "after_agent_spawn"
        assert Hooks.BEFORE_AGENT_RUN == "before_agent_run"
        assert Hooks.AFTER_AGENT_RUN == "after_agent_run"
        assert Hooks.BEFORE_TOOL_CALL == "before_tool_call"
        assert Hooks.AFTER_TOOL_CALL == "after_tool_call"
        assert Hooks.ON_ERROR == "on_error"
        assert Hooks.ON_SHUTDOWN == "on_shutdown"
        assert Hooks.ON_CHECKPOINT == "on_checkpoint"
        assert Hooks.ON_RESTORE == "on_restore"


class TestPlugin:
    """测试 Plugin 数据类"""
    
    def test_create_plugin(self):
        info = PluginInfo(
            name="test",
            version="1.0",
            author="author",
            description="desc",
            entry_point="entry"
        )
        
        plugin = Plugin(info=info, module=None)
        
        assert plugin.info.name == "test"
        assert plugin.enabled is True
        assert plugin.hooks == {}
    
    def test_plugin_with_custom_values(self):
        info = PluginInfo(name="test", version="2.0", author="a", description="d", entry_point="e")
        
        plugin = Plugin(
            info=info,
            module=None,
            enabled=False,
            hooks={"test": lambda: None}
        )
        
        assert plugin.enabled is False
        assert len(plugin.hooks) == 1
