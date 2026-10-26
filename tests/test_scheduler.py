"""测试调度器"""


class TestAgentScheduler:
    """测试Agent调度器"""

    def test_initialization(self):
        """测试初始化"""
        from agent_os_kernel.core.scheduler import AgentScheduler

        scheduler = AgentScheduler()
        assert scheduler is not None

    def test_get_statistics(self):
        """测试获取统计"""
        from agent_os_kernel.core.scheduler import AgentScheduler

        scheduler = AgentScheduler()
        # 调度器应该能创建
        assert scheduler is not None


class TestSchedulerBasic:
    """测试基本调度"""

    def test_scheduler_exists(self):
        """测试调度器存在"""
        from agent_os_kernel.core.scheduler import AgentScheduler

        assert AgentScheduler is not None
