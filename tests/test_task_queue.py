"""测试任务队列"""

import pytest


class TestTaskQueueExists:
    """测试任务队列存在"""
    
    def test_import(self):
        from agent_os_kernel.core.task_queue import TaskQueue
        assert TaskQueue is not None
    
    def test_status_import(self):
        from agent_os_kernel.core.task_queue import TaskStatus
        assert TaskStatus is not None
    
    def test_priority_import(self):
        from agent_os_kernel.core.task_queue import TaskPriority
        assert TaskPriority is not None
