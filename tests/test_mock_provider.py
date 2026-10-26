"""测试Mock Provider"""


class TestMockProvider:
    """测试Mock Provider"""

    def test_initialization(self):
        """测试初始化"""
        from agent_os_kernel.llm.mock_provider import MockProvider

        assert MockProvider is not None

    def test_provider_exists(self):
        """测试Provider存在"""
        from agent_os_kernel.llm.mock_provider import MockProvider

        provider = MockProvider()
        assert provider is not None


class TestMockErrorProvider:
    """测试Mock错误Provider"""

    def test_exists(self):
        """测试存在"""
        from agent_os_kernel.llm.mock_provider import MockErrorProvider

        assert MockErrorProvider is not None
