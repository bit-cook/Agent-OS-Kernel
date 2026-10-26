"""测试工具"""


class TestToolResult:
    """测试工具结果"""

    def test_creation(self):
        """测试创建"""
        from agent_os_kernel.tools.base import ToolResult

        result = ToolResult(success=True)
        assert result.success is True

    def test_with_data(self):
        """测试带数据"""
        from agent_os_kernel.tools.base import ToolResult

        result = ToolResult(success=True, data="test")
        assert result.data == "test"


class TestToolRegistry:
    """测试工具注册表"""

    def test_exists(self):
        """测试注册表存在"""
        from agent_os_kernel.tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert registry is not None

    def test_get_stats(self):
        """测试获取统计"""
        from agent_os_kernel.tools.registry import ToolRegistry

        registry = ToolRegistry()
        stats = registry.get_stats()
        assert stats is not None
