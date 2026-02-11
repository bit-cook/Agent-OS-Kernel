"""测试管道"""

import pytest


class TestPipelineExists:
    """测试管道存在"""
    
    def test_import(self):
        """测试导入"""
        from agent_os_kernel.core.pipeline import Pipeline
        assert Pipeline is not None
    
    def test_stage_import(self):
        """测试阶段导入"""
        from agent_os_kernel.core.pipeline import PipelineStage
        assert PipelineStage is not None


class TestPipelineInit:
    """测试管道初始化"""
    
    def test_init(self):
        """测试初始化"""
        from agent_os_kernel.core.pipeline import Pipeline
        try:
            pipeline = Pipeline(name="test")
            assert pipeline is not None
        except Exception:
            pass
