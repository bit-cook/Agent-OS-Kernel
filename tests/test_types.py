# -*- coding: utf-8 -*-
"""测试类型定义"""

import pytest
from agent_os_kernel.core.types import AgentState, ResourceQuota


class TestTypes:
    """类型测试类"""
    
    def test_agent_state(self):
        """测试 Agent 状态"""
        assert AgentState.IDLE.value == "idle"
        assert AgentState.RUNNING.value == "running"
        assert AgentState.BLOCKED.value == "blocked"
        assert AgentState.TERMINATED.value == "terminated"
    
    def test_resource_quota(self):
        """测试资源配额"""
        quota = ResourceQuota(
            max_memory=1024,
            max_cpu=50.0,
            max_tokens=10000
        )
        
        assert quota.max_memory == 1024
        assert quota.max_cpu == 50.0
        assert quota.max_tokens == 10000
    
    def test_resource_quota_defaults(self):
        """测试默认资源配额"""
        quota = ResourceQuota()
        
        assert quota.max_memory == 4096
        assert quota.max_cpu == 100.0
        assert quota.max_tokens == 128000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
