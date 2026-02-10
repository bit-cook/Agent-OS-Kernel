# -*- coding: utf-8 -*-
"""测试增强模块"""

import pytest
import asyncio
import sys
sys.path.insert(0, '.')


class TestEnhancedStorage:
    """增强存储测试类"""
    
    @pytest.fixture
    def storage(self):
        """创建存储管理器"""
        from agent_os_kernel.core.storage_enhanced import EnhancedStorageManager, StorageRole
        return EnhancedStorageManager()
    
    @pytest.mark.asyncio
    async def test_save_retrieve(self, storage):
        """测试保存和检索"""
        result = await storage.save("test_key", {"data": "test_value"})
        assert result is True
        
        value = await storage.retrieve("test_key")
        assert value == {"data": "test_value"}
    
    @pytest.mark.asyncio
    async def test_storage_roles(self, storage):
        """测试五种存储角色"""
        # 记忆存储
        await storage.save_episode("ep1", {"event": "test"})
        episodes = await storage.get_episodes()
        assert len(episodes) >= 1
        
        # 状态存储
        await storage.save_state("agent1", {"status": "running"})
        state = await storage.load_state("agent1")
        assert state["status"] == "running"
        
        # 向量存储
        await storage.save_vector("vec1", [0.1, 0.2, 0.3])
        vectors = await storage.search_vectors([0.1, 0.2, 0.3])
        assert len(vectors) >= 1
        
        # 检查点存储
        await storage.save_checkpoint("cp1", {"step": 1})
        cp = await storage.load_checkpoint("cp1")
        assert cp is not None
    
    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """测试删除"""
        await storage.save("key1", "value1")
        assert await storage.exists("key1") is True
        
        result = await storage.delete("key1")
        assert result is True
        assert await storage.exists("key1") is False
    
    @pytest.mark.asyncio
    async def test_get_stats(self, storage):
        """测试获取统计"""
        await storage.save("key", "value")
        stats = await storage.get_stats()
        
        assert "state" in stats


class TestEnhancedEventBus:
    """增强事件总线测试类"""
    
    @pytest.fixture
    def event_bus(self):
        """创建事件总线"""
        from agent_os_kernel.core.event_bus_enhanced import EnhancedEventBus, EventType
        return EnhancedEventBus()
    
    @pytest.mark.asyncio
    async def test_publish_subscribe(self, event_bus):
        """测试发布订阅"""
        results = []
        
        async def handler(event):
            results.append(event.event_type.value)
        
        event_bus.subscribe(EventType.TASK_STARTED, handler)
        
        await event_bus.publish_event(EventType.TASK_STARTED)
        await asyncio.sleep(0.1)
        
        assert EventType.TASK_STARTED.value in results
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """测试取消订阅"""
        results = []
        
        async def handler(event):
            results.append(event.event_type.value)
        
        sub_id = event_bus.subscribe(EventType.TASK_COMPLETED, handler)
        
        await event_bus.publish_event(EventType.TASK_COMPLETED)
        await asyncio.sleep(0.1)
        
        assert len(results) == 1
        
        # 取消订阅
        event_bus.unsubscribe(sub_id)
        
        results.clear()
        
        await event_bus.publish_event(EventType.TASK_COMPLETED)
        await asyncio.sleep(0.1)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus):
        """测试通配符订阅"""
        results = []
        
        async def handler(event):
            results.append(event.event_type.value)
        
        event_bus.subscribe_all(handler)
        
        await event_bus.publish_event(EventType.AGENT_STARTED)
        await event_bus.publish_event(EventType.TASK_STARTED)
        await asyncio.sleep(0.1)
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, event_bus):
        """测试获取指标"""
        metrics = event_bus.get_metrics()
        
        assert "events_published" in metrics
        assert "events_processed" in metrics


class TestBaseProvider:
    """基础 Provider 测试类"""
    
    @pytest.mark.asyncio
    async def test_base_provider(self):
        """测试基础 Provider"""
        from agent_os_kernel.llm.base_provider import BaseLLMProvider, ProviderMetrics
        
        # 创建 mock provider
        class MockProvider(BaseLLMProvider):
            @property
            def provider_name(self):
                return "mock"
            
            async def chat(self, messages, **kwargs):
                return {"content": "test"}
            
            async def stream_chat(self, messages, **kwargs):
                yield "test"
        
        provider = MockProvider({"model": "test"})
        
        # 测试指标
        metrics = provider.get_metrics()
        assert "total_requests" in metrics
        
        # 测试 token 计数
        tokens = await provider.count_tokens("hello world")
        assert tokens > 0
        
        # 测试模型信息
        info = await provider.get_model_info()
        assert info["provider"] == "mock"
        
        # 测试健康检查
        health = await provider.health_check()
        assert "healthy" in health
    
    @pytest.mark.asyncio
    async def test_embeddings_default(self):
        """测试默认 embeddings 实现"""
        from agent_os_kernel.llm.base_provider import BaseLLMProvider
        
        class MockProvider(BaseLLMProvider):
            @property
            def provider_name(self):
                return "mock"
            
            async def chat(self, messages, **kwargs):
                return {"content": "test"}
            
            async def stream_chat(self, messages, **kwargs):
                yield "test"
        
        provider = MockProvider({})
        
        # 默认 embeddings 应该返回随机向量
        embeddings = await provider.embeddings(["hello", "world"])
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1536


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
