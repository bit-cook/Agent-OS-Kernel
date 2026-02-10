# -*- coding: utf-8 -*-
"""测试插件系统"""

import pytest
import asyncio
from agent_os_kernel.core.plugin_system import PluginManager, PluginState, PluginInfo


class TestPluginManager:
    """PluginManager 测试类"""
    
    @pytest.fixture
    def manager(self):
        """创建插件管理器"""
        return PluginManager()
    
    def test_register_plugin(self, manager):
        """测试注册插件"""
        def my_plugin():
            return {"name": "test"}
        
        plugin_info = manager.register_plugin("test_plugin", my_plugin)
        
        assert plugin_info.name == "test_plugin"
        assert PluginState.REGISTERED in manager.list_plugins()
    
    def test_load_plugin(self, manager):
        """测试加载插件"""
        def my_plugin():
            return {"name": "loaded"}
        
        manager.register_plugin("loaded_plugin", my_plugin)
        manager.load_plugin("loaded_plugin")
        
        assert PluginState.LOADED in manager.list_plugins()
    
    def test_unload_plugin(self, manager):
        """测试卸载插件"""
        def my_plugin():
            return {"name": "unload"}
        
        manager.register_plugin("unload_plugin", my_plugin)
        manager.load_plugin("unload_plugin")
        manager.unload_plugin("unload_plugin")
        
        assert PluginState.REGISTERED in manager.list_plugins()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
