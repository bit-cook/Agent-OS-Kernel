"""测试检查点管理器"""

import pytest
import asyncio
from agent_os_kernel.core.checkpointer import Checkpointer


class TestCheckpointer:
    """测试检查点"""
    
    def test_initialization(self):
        """测试初始化"""
        cp = Checkpointer(max_checkpoints=50)
        assert cp.max_checkpoints == 50
    
    def test_get_stats(self):
        """测试获取统计"""
        cp = Checkpointer()
        stats = cp.get_stats()
        
        assert "total_checkpoints" in stats
        assert "max_checkpoints" in stats


@pytest.mark.asyncio
class TestCheckpointerAsync:
    """异步测试检查点"""
    
    async def test_create_checkpoint(self):
        """测试创建检查点"""
        cp = Checkpointer()
        cp_id = await cp.create("test-checkpoint", {"data": "value"})
        
        assert cp_id is not None
        assert isinstance(cp_id, str)
    
    async def test_restore_checkpoint(self):
        """测试恢复检查点"""
        cp = Checkpointer()
        cp_id = await cp.create("test", {"key": "value"})
        
        state = await cp.restore(cp_id)
        
        assert state is not None
        assert state["key"] == "value"
    
    async def test_list_checkpoints(self):
        """测试列出检查点"""
        cp = Checkpointer()
        await cp.create("test1", {"data": 1})
        await cp.create("test2", {"data": 2})
        
        checkpoints = await cp.list_checkpoints()
        
        assert isinstance(checkpoints, list)
        assert len(checkpoints) >= 2
    
    async def test_delete_checkpoint(self):
        """测试删除检查点"""
        cp = Checkpointer()
        cp_id = await cp.create("to-delete", {"data": "test"})
        
        result = await cp.delete(cp_id)
        
        assert result is True
        
        restored = await cp.restore(cp_id)
        assert restored is None
    
    async def test_checkpoint_with_tag(self):
        """测试带标签的检查点"""
        cp = Checkpointer()
        cp_id = await cp.create("tagged", {"data": "test"}, tag="my-tag")
        
        checkpoint = await cp.get_by_tag("my-tag")
        
        assert checkpoint is not None
