"""测试Worker"""



class TestWorkerPoolExists:
    """测试Worker池存在"""
    
    def test_import(self):
        from agent_os_kernel.core.worker import WorkerPool
        assert WorkerPool is not None
    
    def test_status_import(self):
        from agent_os_kernel.core.worker import WorkerStatus
        assert WorkerStatus is not None
