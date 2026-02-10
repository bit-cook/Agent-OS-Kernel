# -*- coding: utf-8 -*-

from abc import abstractmethod
"""测试 Agent Pool"""

import pytest
import asyncio
from agent_os_kernel.core.agent_pool import AgentPool, PooledAgent
from agent_os_kernel.core.agent_definition import AgentDefinition


class TestAgentPool:
    """AgentPool 测试类"""
    
    @pytest.fixture
    def pool(self):
        """创建测试池"""
        return AgentPool(
            max_size=5,
            min_idle=1,
            max_idle_time=60,
            cleanup_interval=10
        )
    
    @pytest.fixture
    def definition(self):
        """创建测试定义"""
        return AgentDefinition(
            name="TestAgent",
            role="tester",
            goal="运行测试"
        )
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, pool):
        """测试池初始化"""
        await pool.initialize()
        
        stats = pool.get_stats()
        
        assert stats["total_agents"] >= 1
        assert stats["idle_agents"] >= 1
        assert pool._cleanup_task is not None
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_acquire_agent(self, pool, definition):
        """测试获取 Agent"""
        await pool.initialize()
        
        agent = await pool.acquire(definition, timeout=5.0)
        
        assert agent is not None
        assert agent.status == "busy"
        assert agent.definition.name == "TestAgent"
        
        stats = pool.get_stats()
        assert stats["busy_agents"] >= 1
        
        await pool.release(agent)
        
        stats = pool.get_stats()
        assert stats["idle_agents"] >= 1
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_release_agent(self, pool, definition):
        """测试释放 Agent"""
        await pool.initialize()
        
        agent = await pool.acquire(definition)
        agent.record_task()
        
        await pool.release(agent)
        
        stats = pool.get_stats()
        assert agent.is_idle()
        assert stats["idle_agents"] >= 1
    
    @pytest.mark.asyncio
    async def test_multiple_acquire_release(self, pool, definition):
        """测试多次获取和释放"""
        await pool.initialize()
        
        agents = []
        for i in range(3):
            agent = await pool.acquire(definition)
            agents.append(agent)
        
        stats = pool.get_stats()
        assert stats["busy_agents"] == 3
        
        for agent in agents:
            await pool.release(agent)
        
        stats = pool.get_stats()
        assert stats["idle_agents"] >= 3
        
        await pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_pool_stats(self, pool, definition):
        """测试池统计"""
        await pool.initialize()
        
        stats = pool.get_stats()
        
        assert "total_agents" in stats
        assert "idle_agents" in stats
        assert "busy_agents" in stats
        assert "queue_size" in stats
        assert "max_size" in stats
        assert "utilization" in stats
        
        await pool.shutdown()


class TestPooledAgent:
    """PooledAgent 测试类"""
    
    def test_is_idle(self):
        """测试空闲状态"""
        agent = PooledAgent(
            agent_id="test-001",
            definition=AgentDefinition(name="Test", role="test", goal="test")
        )
        
        assert agent.is_idle()
        agent.mark_busy()
        assert not agent.is_idle()
        agent.mark_idle()
        assert agent.is_idle()
    
    def test_record_task(self):
        """测试任务记录"""
        agent = PooledAgent(
            agent_id="test-001",
            definition=AgentDefinition(name="Test", role="test", goal="test")
        )
        
        initial = agent.task_count
        agent.record_task()
        assert agent.task_count == initial + 1
    
    def test_record_error(self):
        """测试错误记录"""
        agent = PooledAgent(
            agent_id="test-001",
            definition=AgentDefinition(name="Test", role="test", goal="test")
        )
        
        for _ in range(3):
            agent.record_error()
        
        assert agent.error_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
