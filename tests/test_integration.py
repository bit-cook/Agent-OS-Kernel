"""集成测试"""


class TestIntegration:
    """测试集成"""

    def test_kernel_import(self):
        """测试内核导入"""
        from agent_os_kernel import AgentOSKernel

        assert AgentOSKernel is not None

    def test_core_imports(self):
        """测试核心导入"""
        from agent_os_kernel.core import ContextManager, EventBus, StorageManager

        assert ContextManager is not None
        assert EventBus is not None
        assert StorageManager is not None

    def test_llm_imports(self):
        """测试LLM导入"""
        from agent_os_kernel.llm import LLMProviderFactory, MockProvider

        assert LLMProviderFactory is not None
        assert MockProvider is not None
