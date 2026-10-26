"""测试存储"""

from agent_os_kernel.core.storage import StorageManager


class TestStorageManager:
    """测试存储管理器"""

    def test_initialization(self):
        """测试初始化"""
        storage = StorageManager()
        assert storage is not None

    def test_save_retrieve(self):
        """测试保存和获取"""
        storage = StorageManager()
        storage.save("key1", {"data": "value1"})
        result = storage.retrieve("key1")
        assert result["data"] == "value1"

    def test_exists(self):
        """测试存在性"""
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
