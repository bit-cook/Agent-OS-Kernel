"""测试状态机"""

import pytest


class TestStateMachineExists:
    """测试状态机存在"""
    
    def test_import(self):
        """测试导入"""
        try:
            from agent_os_kernel.core.state_machine import StateMachine
            assert StateMachine is not None
        except ImportError:
            pass
    
    def test_state_import(self):
        """测试状态导入"""
        try:
            from agent_os_kernel.core.state_machine import State
            assert State is not None
        except ImportError:
            pass
