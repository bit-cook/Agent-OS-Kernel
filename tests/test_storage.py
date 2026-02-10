"""测试存储管理器"""

import pytest
import tempfile
import os
from agent_os_kernel.core.storage import StorageManager, StorageBackend


class TestStorageManager:
    """测试 StorageManager"""
    
    def test_memory_backend_initialization(self):
        """测试内存存储后端初始化"""
        manager = StorageManager(backend=StorageBackend.MEMORY)
        
        assert manager.backend == StorageBackend.MEMORY
        assert manager.data == {}
    
    def test_file_backend_initialization(self):
        """测试文件存储后端初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(
                backend=StorageBackend.FILE,
                base_path=tmpdir
            )
            
            assert manager.backend == StorageBackend.FILE
            assert manager.base_path == tmpdir
    
    def test_save_and_retrieve(self):
        """测试保存和检索"""
        manager = StorageManager()
        
        # 保存数据
        manager.save("key1", {"data": "value1"})
        
        # 检索
        result = manager.retrieve("key1")
        assert result == {"data": "value1"}
    
    def test_retrieve_nonexistent(self):
        """测试检索不存在的键"""
        manager = StorageManager()
        
        result = manager.retrieve("nonexistent")
        assert result is None
    
    def test_delete(self):
        """测试删除"""
        manager = StorageManager()
        
        manager.save("key1", {"data": "value1"})
        assert manager.retrieve("key1") is not None
        
        manager.delete("key1")
        assert manager.retrieve("key1") is None
    
    def test_list_keys(self):
        """测试列出所有键"""
        manager = StorageManager()
        
        manager.save("key1", {"data": "value1"})
        manager.save("key2", {"data": "value2"})
        manager.save("key3", {"data": "value3"})
        
        keys = manager.list_keys()
        
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys
    
    def test_exists(self):
        """测试键是否存在"""
        manager = StorageManager()
        
        manager.save("exists", {"data": "value"})
        
        assert manager.exists("exists") is True
        assert manager.exists("not_exists") is False
    
    def test_clear(self):
        """测试清空存储"""
        manager = StorageManager()
        
        manager.save("key1", {"data": "value1"})
        manager.save("key2", {"data": "value2"})
        
        manager.clear()
        
        assert len(manager.list_keys()) == 0
    
    def test_bulk_save(self):
        """测试批量保存"""
        manager = StorageManager()
        
        data = {
            "k1": {"v": 1},
            "k2": {"v": 2},
            "k3": {"v": 3}
        }
        
        manager.bulk_save(data)
        
        assert manager.retrieve("k1") == {"v": 1}
        assert manager.retrieve("k2") == {"v": 2}
        assert manager.retrieve("k3") == {"v": 3}


class TestStorageBackend:
    """测试存储后端"""
    
    def test_postgresql_backend_requires_connection(self):
        """测试 PostgreSQL 后端需要连接"""
        # This would require a real PostgreSQL connection
        # For unit testing, we skip or mock
        pass
    
    def test_backend_type_enum(self):
        """测试后端类型枚举"""
        assert StorageBackend.MEMORY.value == "memory"
        assert StorageBackend.FILE.value == "file"
        assert StorageBackend.POSTGRESQL.value == "postgresql"
EXAMPLESEOF
echo "✅ 存储测试创建完成"
