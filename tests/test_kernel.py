"""
from abc import abstractmethod
Tests for Kernel Module
"""

import pytest
from agent_os_kernel import AgentOSKernel


class TestKernel:
    """Test kernel functionality"""
    
    def test_create_kernel(self):
        """Test kernel creation"""
        kernel = AgentOSKernel()
        assert kernel is not None
    
    def test_kernel_version(self):
        """Test kernel version"""
        kernel = AgentOSKernel()
        stats = kernel.get_stats()
        assert "version" in stats
    
    def test_spawn_agent(self):
        """Test agent spawning"""
        kernel = AgentOSKernel()
        pid = kernel.spawn_agent(
            name="TestAgent",
            task="Test task",
            priority=50
        )
        assert pid is not None
    
    def test_list_agents(self):
        """Test listing agents"""
        kernel = AgentOSKernel()
        
        kernel.spawn_agent(name="Agent1", task="Task 1")
        kernel.spawn_agent(name="Agent2", task="Task 2")
        
        agents = kernel.list_agents()
        assert len(agents) >= 2


class TestContextManager:
    """Test context management"""
    
    def test_create_manager(self):
        """Test context manager creation"""
        from agent_os_kernel import ContextManager
        cm = ContextManager()
        assert cm is not None
    
    def test_allocate_page(self):
        """Test page allocation"""
        from agent_os_kernel import ContextManager
        
        cm = ContextManager(max_context_tokens=128000)
        page_id = cm.allocate_page(
            agent_pid="test-agent",
            content="Test content",
            importance=0.8
        )
        assert page_id is not None


class TestStorageManager:
    """Test storage management"""
    
    def test_storage_from_postgresql(self):
        """Test PostgreSQL storage creation"""
        from agent_os_kernel import StorageManager
        
        # In-memory test
        storage = StorageManager.from_memory()
        assert storage is not None
    
    def test_vector_search(self):
        """Test vector search functionality"""
        from agent_os_kernel import StorageManager
        
        storage = StorageManager.from_memory(enable_vector=True)
        results = storage.semantic_search(
            query="test query",
            limit=5
        )
        assert isinstance(results, list)


class TestLLMProviders:
    """Test LLM providers"""
    
    def test_factory_creation(self):
        """Test factory creation"""
        from agent_os_kernel.llm import LLMProviderFactory
        
        factory = LLMProviderFactory()
        assert factory is not None
    
    def test_provider_config(self):
        """Test provider configuration"""
        from agent_os_kernel.llm import LLMConfig
        
        config = LLMConfig(
            provider="deepseek",
            model="deepseek-chat"
        )
        assert config.provider == "deepseek"
        assert config.model == "deepseek-chat"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
