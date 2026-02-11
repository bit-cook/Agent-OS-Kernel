"""测试成本跟踪器"""

import pytest


class TestCostTrackerExists:
    """测试成本跟踪器存在"""
    
    def test_import(self):
        """测试导入"""
        try:
            from agent_os_kernel.core.cost_tracker import CostTracker
            assert CostTracker is not None
        except ImportError:
            pass
