"""测试内核"""


class TestKernel:
    """测试内核"""

    def test_initialization(self):
        """测试初始化"""
        from agent_os_kernel import AgentOSKernel

        kernel = AgentOSKernel()
        assert kernel is not None

    def test_get_stats(self):
        """测试获取统计"""
        from agent_os_kernel import AgentOSKernel

        kernel = AgentOSKernel()
        stats = kernel.get_stats()
        assert stats is not None


class TestKernelStats:
    """测试内核统计"""

    def test_stats_exists(self):
        """测试统计存在"""
        from agent_os_kernel import KernelStats

        assert KernelStats is not None
