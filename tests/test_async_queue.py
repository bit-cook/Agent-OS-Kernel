"""测试异步队列"""

import pytest


class TestAsyncQueueExists:
    """测试异步队列存在"""
    
    def test_queue_import(self):
        from agent_os_kernel.core.async_queue import AsyncQueue
        assert AsyncQueue is not None
    
    def test_message_import(self):
        from agent_os_kernel.core.async_queue import Message
        assert Message is not None
    
    def test_status_import(self):
        from agent_os_kernel.core.async_queue import MessageStatus
        assert MessageStatus is not None
