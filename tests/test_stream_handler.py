"""测试流处理器"""

import pytest


class TestStreamHandlerExists:
    """测试流处理器存在"""
    
    def test_import(self):
        """测试导入"""
        from agent_os_kernel.core.stream_handler import StreamHandler
        assert StreamHandler is not None
    
    def test_type_import(self):
        """测试类型导入"""
        from agent_os_kernel.core.stream_handler import StreamType
        assert StreamType is not None
