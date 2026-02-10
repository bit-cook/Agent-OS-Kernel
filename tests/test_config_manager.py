# -*- coding: utf-8 -*-
"""测试配置管理器"""

import pytest
import asyncio
import tempfile
import os
from agent_os_kernel.core.config_manager import ConfigManager, TaskQueue


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


class TestTaskQueue:
    """TaskQueue 测试类"""
    
    @pytest.fixture
    def queue(self):
        """创建任务队列"""
        return TaskQueue(max_concurrent=2, max_size=100)
    
    async def test_submit_task(self, queue):
        """测试提交任务"""
        results = []
        
        async def task(x):
            results.append(x)
            return x * 2
        
        task_id = await queue.submit("test_task", task, 5)
        
        assert task_id is not None
        await asyncio.sleep(0.2)
        
        assert len(results) == 1
        assert results[0] == 5
    
    async def test_priority(self, queue):
        """测试优先级"""
        order = []
        
        async def task(name, delay=0):
            await asyncio.sleep(delay)
            return name
        
        # 提交低优先级
        await queue.submit(
            "low", task, "low", 
            priority=TaskPriority.LOW
        )
        # 提交高优先级
        await queue.submit(
            "high", task, "high",
            priority=TaskPriority.HIGH
        )
        
        await asyncio.sleep(0.3)
        
        assert queue._stats["submitted"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
