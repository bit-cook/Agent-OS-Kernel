"""测试批处理器"""



class TestBatchProcessorExists:
    """测试批处理器存在"""
    
    def test_import(self):
        """测试导入"""
        from agent_os_kernel.core.batch_processor import BatchProcessor
        assert BatchProcessor is not None
    
    def test_type_import(self):
        """测试类型导入"""
        from agent_os_kernel.core.batch_processor import AggregationType
        assert AggregationType is not None
