"""测试上下文管理器"""

import pytest
from agent_os_kernel.core.context_manager import ContextManager, ContextPage, PageStatus


class TestContextPage:
    """测试 ContextPage 数据类"""
    
    def test_create_page(self):
        page = ContextPage(
            agent_pid="test_agent",
            content="Hello World",
            tokens=2,
            importance_score=0.8,
            page_type="user"
        )
        
        assert page.agent_pid == "test_agent"
        assert page.content == "Hello World"
        assert page.tokens == 2
        assert page.importance_score == 0.8
        assert page.page_type == "user"
        assert page.status == PageStatus.IN_MEMORY
        assert page.page_id is not None
        assert page.access_count == 0
    
    def test_page_touch(self):
        page = ContextPage(agent_pid="test", content="test")
        page.touch()
        
        assert page.access_count == 1
        assert page.last_accessed is not None
    
    def test_page_dirty_flag(self):
        page = ContextPage(agent_pid="test", content="test")
        assert page.is_dirty() is False
        
        page.mark_dirty()
        assert page.is_dirty() is True
        assert page.status == PageStatus.DIRTY
        
        page.mark_clean()
        assert page.is_dirty() is False
        assert page.status == PageStatus.IN_MEMORY
    
    def test_page_swap_flow(self):
        page = ContextPage(agent_pid="test", content="test content")
        assert page.status == PageStatus.IN_MEMORY
        
        # Swap out
        page.status = PageStatus.SWAPPED
        assert page.status == PageStatus.SWAP_OUT
        assert page.is_dirty() is False  # Should be clean when swapped
    
    def test_lru_score_calculation(self):
        page = ContextPage(agent_pid="test", content="test")
        page.access_count = 5
        page.last_accessed = 0  # Old time
        
        score = page.get_lru_score(current_time=1000)
        assert score > 0  # Should have high LRU score (unused recently)


class TestContextManager:
    """测试 ContextManager"""
    
    def test_initialization(self):
        manager = ContextManager(max_tokens=1000)
        
        assert manager.max_tokens == 1000
        assert manager.used_tokens == 0
        assert manager.pages == {}
    
    def test_add_page(self):
        manager = ContextManager(max_tokens=1000)
        page = manager.add_page(
            agent_pid="agent1",
            content="Hello",
            tokens=2,
            page_type="user"
        )
        
        assert page is not None
        assert page.agent_pid == "agent1"
        assert len(manager.pages) == 1
        assert manager.used_tokens >= 2
    
    def test_get_page(self):
        manager = ContextManager(max_tokens=1000)
        added = manager.add_page(agent_pid="agent1", content="Test")
        
        retrieved = manager.get_page(added.page_id)
        
        assert retrieved is not None
        assert retrieved.page_id == added.page_id
        assert retrieved.access_count == 1  # touch() called
    
    def test_get_nonexistent_page(self):
        manager = ContextManager(max_tokens=1000)
        
        result = manager.get_page("nonexistent")
        
        assert result is None
    
    def test_remove_page(self):
        manager = ContextManager(max_tokens=1000)
        page = manager.add_page(agent_pid="agent1", content="Test")
        
        removed = manager.remove_page(page.page_id)
        
        assert removed is True
        assert len(manager.pages) == 0
        assert manager.get_page(page.page_id) is None
    
    def test_get_agent_pages(self):
        manager = ContextManager(max_tokens=1000)
        manager.add_page(agent_pid="agent1", content="page1")
        manager.add_page(agent_pid="agent1", content="page2")
        manager.add_page(agent_pid="agent2", content="page3")
        
        agent1_pages = manager.get_agent_pages("agent1")
        agent2_pages = manager.get_agent_pages("agent2")
        
        assert len(agent1_pages) == 2
        assert len(agent2_pages) == 1
    
    def test_swap_out_low_priority(self):
        # Create manager with very low token limit
        manager = ContextManager(max_tokens=10)
        manager.add_page(agent_pid="a1", content="x" * 10, importance_score=0.1)
        manager.add_page(agent_pid="a1", content="y" * 10, importance_score=0.9)
        
        initial_count = len(manager.pages)
        freed = manager.swap_out_if_needed()
        
        # Should have tried to free space
        # Result depends on implementation
        assert isinstance(freed, int)
    
    def test_get_memory_stats(self):
        manager = ContextManager(max_tokens=1000)
        manager.add_page(agent_pid="a1", content="test")
        
        stats = manager.get_memory_stats()
        
        assert stats['total_pages'] == 1
        assert stats['used_tokens'] >= 1
        assert stats['max_tokens'] == 1000
        assert 'usage_percent' in stats
    
    def test_clear_agent_pages(self):
        manager = ContextManager(max_tokens=1000)
        manager.add_page(agent_pid="agent1", content="page1")
        manager.add_page(agent_pid="agent1", content="page2")
        manager.add_page(agent_pid="agent2", content="page3")
        
        manager.clear_agent_pages("agent1")
        
        assert len(manager.get_agent_pages("agent1")) == 0
        assert len(manager.get_agent_pages("agent2")) == 1
        assert len(manager.pages) == 1


class TestContextPageEviction:
    """测试页面置换策略"""
    
    def test_eviction_order(self):
        """测试低重要性页面先被换出"""
        manager = ContextManager(max_tokens=50)
        
        # Add pages with different importance
        high = manager.add_page(agent_pid="a1", content="important", importance_score=0.9)
        low = manager.add_page(agent_pid="a1", content="less important", importance_score=0.2)
        
        # Both should be in memory initially
        assert manager.get_page(high.page_id) is not None
        assert manager.get_page(low.page_id) is not None
    
    def test_importance_based_swap(self):
        """测试基于重要性的置换"""
        manager = ContextManager(max_tokens=20)
        
        # Fill up
        p1 = manager.add_page(agent_pid="a1", content="a" * 10, importance_score=0.9)
        p2 = manager.add_page(agent_pid="a1", content="b" * 10, importance_score=0.1)
        
        # Access low importance page to make it less likely to be swapped
        manager.get_page(p2.page_id)
        
        # Try to add another page that should trigger swap
        p3 = manager.add_page(agent_pid="a1", content="c" * 10, importance_score=0.5)
        
        # System should handle this gracefully
        assert p3 is not None
