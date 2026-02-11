"""测试插件管理器"""

import pytest
from agent_os_kernel.core.plugin_system import (
    PluginManager, PluginState, PluginInfo, BasePlugin
)


class TestPluginManager:
    """测试插件管理器"""
    
    def test_initialization(self):
        """测试初始化"""
        pm = PluginManager()
        assert pm is not None
    
    def test_get_stats(self):
        """测试获取统计"""
        pm = PluginManager()
        stats = pm.get_stats()
        
        assert "total_plugins" in stats
        assert "loaded" in stats
        assert "enabled" in stats
    
    def test_list_plugins(self):
        """测试列出插件"""
        pm = PluginManager()
        plugins = pm.list_plugins()
        
        assert isinstance(plugins, list)
    
    def test_list_loaded(self):
        """测试列出已加载插件"""
        pm = PluginManager()
        loaded = pm.list_loaded()
        
        assert isinstance(loaded, list)


class TestPluginInfo:
    """测试插件信息"""
    
    def test_create_plugin_info(self):
        """测试创建插件信息"""
        info = PluginInfo(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author"
        )
        
        assert info.name == "test-plugin"
        assert info.version == "1.0.0"
        assert info.state == PluginState.UNLOADED


class TestPluginState:
    """测试插件状态"""
    
    def test_state_values(self):
        """测试状态值"""
        assert PluginState.UNLOADED.value == "unloaded"
        assert PluginState.LOADED.value == "loaded"
        assert PluginState.ENABLED.value == "enabled"
        assert PluginState.DISABLED.value == "disabled"
        assert PluginState.ERROR.value == "error"


class TestBasePlugin:
    """测试基类插件"""
    
    def test_base_plugin_raises(self):
        """测试基类方法"""
        
        class TestPlugin(BasePlugin):
            @property
            def name(self):
                return "test"
            
            @property
            def version(self):
                return "1.0.0"
            
            @property
            def description(self):
                return "A test"
        
        plugin = TestPlugin()
        
        # 这些方法应该有默认实现
        assert plugin.name == "test"
        assert plugin.version == "1.0.0"
        
        # lifecycle 方法应该有默认实现（不抛出异常）
        plugin.initialize(None)
        plugin.enable()
        plugin.disable()
        plugin.cleanup()
