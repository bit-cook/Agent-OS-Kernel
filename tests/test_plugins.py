"""测试插件"""



class TestPluginManager:
    """测试插件管理器"""
    
    def test_initialization(self):
        """测试初始化"""
        from agent_os_kernel.core.plugin_system import PluginManager
        pm = PluginManager()
        assert pm is not None
    
    def test_get_stats(self):
        """测试获取统计"""
        from agent_os_kernel.core.plugin_system import PluginManager
        pm = PluginManager()
        stats = pm.get_stats()
        assert stats is not None


class TestBasePlugin:
    """测试基类插件"""
    
    def test_exists(self):
        """测试存在"""
        from agent_os_kernel.core.plugin_system import BasePlugin
        assert BasePlugin is not None
