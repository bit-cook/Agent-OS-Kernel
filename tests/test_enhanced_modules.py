"""测试增强模块"""


class TestEnhancedEventBus:
    """测试增强事件总线"""

    def test_initialization(self):
        """测试初始化"""
        from agent_os_kernel.core.event_bus_enhanced import EnhancedEventBus

        bus = EnhancedEventBus()
        assert bus is not None

    def test_get_stats(self):
        """测试获取统计"""
        from agent_os_kernel.core.event_bus_enhanced import EnhancedEventBus

        bus = EnhancedEventBus()
        stats = bus.get_stats()
        assert stats is not None


class TestEnhancedMemory:
    """测试增强内存"""

    def test_memory_exists(self):
        """测试内存存在"""
        from agent_os_kernel.core.enhanced_memory import EnhancedMemory

        assert EnhancedMemory is not None

    def test_memory_types(self):
        """测试内存类型"""
        from agent_os_kernel.core.enhanced_memory import MemoryType, ShortTermMemory, LongTermMemory

        assert MemoryType is not None
        assert ShortTermMemory is not None
        assert LongTermMemory is not None


class TestBaseLLMProvider:
    """测试基础LLM Provider"""

    def test_provider_exists(self):
        """测试Provider存在"""
        from agent_os_kernel.llm.base_provider import BaseLLMProvider

        assert BaseLLMProvider is not None

    def test_metrics_exists(self):
        """测试指标存在"""
        from agent_os_kernel.llm.base_provider import ProviderMetrics

        assert ProviderMetrics is not None
