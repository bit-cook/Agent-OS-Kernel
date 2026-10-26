"""测试类型定义"""



class TestAgentState:
    """测试Agent状态"""
    
    def test_agent_state_exists(self):
        """测试AgentState存在"""
        from agent_os_kernel.core.types import AgentState
        assert AgentState is not None
    
    def test_agent_state_has_values(self):
        """测试AgentState有值"""
        from agent_os_kernel.core.types import AgentState
        # 检查主要状态
        assert hasattr(AgentState, 'IDLE') or hasattr(AgentState, 'RUNNING')


class TestResourceQuota:
    """测试资源配额"""
    
    def test_resource_quota_exists(self):
        """测试ResourceQuota存在"""
        from agent_os_kernel.core.types import ResourceQuota
        assert ResourceQuota is not None
    
    def test_quota_init(self):
        """测试配额初始化"""
        from agent_os_kernel.core.types import ResourceQuota
        quota = ResourceQuota()
        assert quota is not None
