"""测试 Agent Pool"""

import pytest
from agent_os_kernel.core.agent_pool import AgentPool


class TestAgentPool:
    """测试 Agent 池"""
    
    def test_initialization(self):
        """测试初始化"""
        pool = AgentPool(max_size=5)
        assert pool.max_size == 5
        assert pool.idle_timeout == 300.0
    
    def test_get_stats(self):
        """测试获取统计"""
        pool = AgentPool(max_size=5)
        stats = pool.get_stats()
        
        assert "total_agents" in stats
        assert "idle_agents" in stats
        assert "busy_agents" in stats
        assert "max_size" in stats
        assert stats["max_size"] == 5
    
    def test_get_active_agents(self):
        """测试获取活跃Agent"""
        pool = AgentPool(max_size=5)
        agents = pool.get_active_agents()
        
        assert isinstance(agents, list)
