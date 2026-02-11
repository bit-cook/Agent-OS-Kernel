"""测试任务管理器"""

import pytest


class TestTaskManagerExists:
    """测试任务管理器存在"""
    
    def test_import(self):
        from agent_os_kernel.core.task_manager import TaskManager
        assert TaskManager is not None
    
    def test_status_import(self):
        from agent_os_kernel.core.task_manager import ExecutionStatus
        assert ExecutionStatus is not None
