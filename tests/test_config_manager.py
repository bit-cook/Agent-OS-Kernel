# -*- coding: utf-8 -*-
"""测试配置管理器"""

import pytest
import asyncio
import tempfile
import os
from agent_os_kernel.core.config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager 测试类"""
    
    @pytest.fixture
    def config_dir(self):
        """创建临时配置目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, config_dir):
        """创建配置管理器"""
        return ConfigManager(config_dir=config_dir)
    
    async def test_load_yaml(self, config_dir, manager):
        """测试加载 YAML 配置"""
        # 创建测试文件
        config_path = os.path.join(config_dir, "test.yaml")
        with open(config_path, 'w') as f:
            import yaml
            yaml.dump({"key": "value", "nested": {"a": 1}}, f)
        
        await manager.load("test")
        
        value = await manager.get("test", "key")
        assert value == "value"
        
        nested = await manager.get("test", "nested")
        assert nested == {"a": 1}
    
    async def test_get_default(self, manager):
        """测试默认值"""
        result = await manager.get("nonexistent", "key", default="default")
        assert result == "default"
    
    async def test_set_value(self, manager):
        """测试设置值"""
        await manager.set("test", "new_key", "new_value")
        result = await manager.get("test", "new_key")
        assert result == "new_value"
    
    def test_list_configs(self, manager):
        """测试列出配置"""
        manager._configs["config1"] = None
        manager._configs["config2"] = None
        
        configs = manager.list_configs()
        assert "config1" in configs
        assert "config2" in configs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
