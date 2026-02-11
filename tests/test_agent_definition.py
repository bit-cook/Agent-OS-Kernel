"""测试Agent定义"""

import pytest


class TestAgentDefinitionExists:
    """测试Agent定义存在"""
    
    def test_agent_import(self):
        from agent_os_kernel.core.agent_definition import AgentDefinition
        assert AgentDefinition is not None
    
    def test_task_import(self):
        from agent_os_kernel.core.agent_definition import TaskDefinition
        assert TaskDefinition is not None
    
    def test_crew_import(self):
        from agent_os_kernel.core.agent_definition import CrewDefinition
        assert CrewDefinition is not None
