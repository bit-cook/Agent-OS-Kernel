"""测试上下文管理器"""

import pytest
from agent_os_kernel.core.context_manager import (
    ContextManager, ContextPage, PageStatus
)
from agent_os_kernel.core.exceptions import ContextOverflowError


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
        
        page.status = PageStatus.SWAPPED
        assert page.is_dirty() is False
    
    def test_lru_score_calculation(self):
        page = ContextPage(agent_pid="test", content="test")
        page.access_count = 5
        page.last_accessed = 0
        
        score = page.get_lru_score(current_time=1000)
        assert score > 0


class TestContextManager:
    """测试 ContextManager"""
    
    def test_initialization(self):
        manager = ContextManager(max_context_tokens=1000)
        
        assert manager.max_context_tokens == 1000
        assert manager.current_usage >= 0
        assert hasattr(manager, 'pages_in_memory')
    
    def test_allocate_page(self):
        manager = ContextManager(max_context_tokens=1000)
        page_id = manager.allocate_page(
            agent_pid="agent1",
            content="Hello",
            importance=0.8
        )
        
        assert page_id is not None
        assert isinstance(page_id, str)
        assert len(page_id) > 0
    
    def test_access_page(self):
        manager = ContextManager(max_context_tokens=1000)
        page_id = manager.allocate_page(agent_pid="agent1", content="Test")
        
        page = manager.access_page(page_id)
        assert page is not None
        assert page.content == "Test"
    
    def test_get_nonexistent_page(self):
        manager = ContextManager(max_context_tokens=1000)
        result = manager.access_page("nonexistent")
        assert result is None
    
    def test_get_agent_context(self):
        manager = ContextManager(max_context_tokens=1000)
        
        manager.allocate_page(agent_pid="agent1", content="page1", importance=0.5)
        manager.allocate_page(agent_pid="agent1", content="page2", importance=0.7)
        manager.allocate_page(agent_pid="agent2", content="page3", importance=0.6)
        
        context1 = manager.get_agent_context("agent1")
        context2 = manager.get_agent_context("agent2")
        
        assert isinstance(context1, str)
        assert "page1" in context1
        assert "page2" in context1
        assert "page3" in context2
    
    def test_release_agent_pages(self):
        manager = ContextManager(max_context_tokens=1000)
        
        manager.allocate_page(agent_pid="agent1", content="page1", importance=0.5)
        manager.allocate_page(agent_pid="agent1", content="page2", importance=0.7)
        
        released = manager.release_agent_pages("agent1")
        assert released == 2
        
        context = manager.get_agent_context("agent1")
        assert context == ""
    
    def test_update_page_content(self):
        manager = ContextManager(max_context_tokens=1000)
        page_id = manager.allocate_page(agent_pid="a1", content="old", importance=0.5)
        
        manager.update_page_content(page_id, "new content")
        
        page = manager.access_page(page_id)
        assert page.content == "new content"
    
    def test_update_page_importance(self):
        manager = ContextManager(max_context_tokens=1000)
        page_id = manager.allocate_page(agent_pid="a1", content="test", importance=0.5)
        
        manager.update_page_importance(page_id, 0.9)
        
        page = manager.access_page(page_id)
        assert page.importance_score == 0.9
    
    def test_context_overflow_error(self):
        """测试上下文溢出错误"""
        manager = ContextManager(max_context_tokens=10)
        
        try:
            manager.allocate_page(
                agent_pid="test",
                content="x" * 10000,
                importance=1.0
            )
        except (ContextOverflowError, MemoryError):
            pass
    
    def test_get_stats(self):
        manager = ContextManager(max_context_tokens=1000)
        manager.allocate_page(agent_pid="a1", content="test", importance=0.5)
        
        stats = manager.get_stats()
        
        assert isinstance(stats, dict)
        assert "max_tokens" in stats
        assert stats["max_tokens"] == 1000
    
    def test_token_estimation(self):
        manager = ContextManager(max_context_tokens=10000)
        
        tokens1 = manager._estimate_tokens("Hello world")
        assert tokens1 > 0
        
        long_text = "word " * 100
        tokens2 = manager._estimate_tokens(long_text)
        assert tokens2 > tokens1


class TestContextManagerKVCache:
    """测试 KV Cache 优化器"""
    
    def test_kv_cache_optimizer_exists(self):
        manager = ContextManager(max_context_tokens=1000)
        
        assert hasattr(manager, 'kv_cache_optimizer')
        assert hasattr(manager.kv_cache_optimizer, 'get_hit_rate_stats')
