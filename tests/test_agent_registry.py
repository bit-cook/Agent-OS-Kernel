"""测试Agent注册表"""

import pytest


class TestAgentRegistryExists:
    """测试Agent注册表存在"""
    
    def test_import(self):
        from agent_os_kernel.core.agent_registry import AgentRegistry
        assert AgentRegistry is not None
