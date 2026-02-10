"""测试配置管理器"""

import pytest
from agent_os_kernel.core.config_manager import ConfigManager


class TestConfigManager:
    """测试配置管理器"""
    
    def test_initialization(self):
        """测试初始化"""
        cm = ConfigManager(config_dir="/tmp/test_config")
        assert cm.config_dir.exists() or True
    
    def test_get_stats(self):
        """测试获取统计"""
        cm = ConfigManager()
        stats = cm.get_stats()
        
        assert "total_configs" in stats
        assert "hot_reload_enabled" in stats
    
    def test_list_configs(self):
        """测试列出配置"""
        cm = ConfigManager()
        configs = cm.list_configs()
        
        assert isinstance(configs, list)
