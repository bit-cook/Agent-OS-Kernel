"""测试增强存储管理器"""

import pytest
from agent_os_kernel.core.storage import StorageManager, StorageBackend


class TestStorageManager:
    """测试存储管理器"""
    
    def test_initialization(self):
        """测试初始化"""
        storage = StorageManager()
        assert storage is not None
    
    def test_save_retrieve(self):
        """测试保存和获取"""
        storage = StorageManager()
        
        storage.save("test/key1", {"data": "value1"})
        storage.save("test/key2", {"data": "value2"})
        
        result1 = storage.retrieve("test/key1")
        result2 = storage.retrieve("test/key2")
        
        assert result1["data"] == "value1"
        assert result2["data"] == "value2"
    
    def test_exists(self):
        """测试存在性检查"""
        storage = StorageManager()
        
        storage.save("exists/key", {"test": True})
        
        assert storage.exists("exists/key") is True
        assert storage.exists("not/exists/key") is False
    
    def test_delete(self):
        """测试删除"""
        storage = StorageManager()
        
        storage.save("delete/key", {"data": "test"})
        assert storage.exists("delete/key") is True
        
        storage.delete("delete/key")
        assert storage.exists("delete/key") is False
    
    def test_clear(self):
        """测试清空"""
        storage = StorageManager()
        
        storage.save("key1", {"data": 1})
        storage.save("key2", {"data": 2})
        
        storage.clear()
        
        assert storage.exists("key1") is False
        assert storage.exists("key2") is False
    
    def test_get_stats(self):
        """测试获取统计"""
        storage = StorageManager()
        storage.save("stats/key", {"data": "test"})
        
        stats = storage.get_stats()
        
        assert isinstance(stats, dict)
        assert "data" in stats


class TestStorageBackend:
    """测试存储后端"""
    
    def test_backend_types(self):
        """测试后端类型"""
        assert StorageBackend.MEMORY.value == "memory"
        assert StorageBackend.FILE.value == "file"
        assert StorageBackend.POSTGRESQL.value == "postgresql"
        assert StorageBackend.VECTOR.value == "vector"
