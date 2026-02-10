# -*- coding: utf-8 -*-
"""测试工作池"""

import pytest
import asyncio
from agent_os_kernel.core.worker import WorkerPool, WorkerStatus


class TestWorkerPool:
    """WorkerPool 测试类"""
    
    @pytest.fixture
    def pool(self):
        """创建工作池"""
        return WorkerPool(name="test", max_workers=3)
    
    def test_add_worker(self, pool):
        """测试添加工作节点"""
        worker = pool.add_worker("worker-1", "TestWorker")
        
        assert worker.worker_id == "worker-1"
        assert worker.name == "TestWorker"
        assert worker.status == WorkerStatus.IDLE
        
        assert len(pool._workers) == 1
    
    def test_remove_worker(self, pool):
        """测试移除工作节点"""
        pool.add_worker("worker-1", "TestWorker")
        
        result = pool.remove_worker("worker-1")
        assert result is True
        assert len(pool._workers) == 0
        
        result = pool.remove_worker("nonexistent")
        assert result is False
    
    def test_list_workers(self, pool):
        """测试列出工作节点"""
        pool.add_worker("w1", "Worker1")
        pool.add_worker("w2", "Worker2")
        
        workers = pool.list_workers()
        assert len(workers) == 2
    
    def test_get_available_workers(self, pool):
        """测试获取可用工作节点"""
        w1 = pool.add_worker("w1", "Worker1")
        w2 = pool.add_worker("w2", "Worker2")
        
        available = pool.get_available_workers()
        assert len(available) == 2
        
        w1.status = WorkerStatus.BUSY
        
        available = pool.get_available_workers()
        assert len(available) == 1
    
    def test_get_stats(self, pool):
        """测试统计"""
        pool.add_worker("w1", "Worker1")
        pool.add_worker("w2", "Worker2")
        
        stats = pool.get_stats()
        
        assert stats["name"] == "test"
        assert stats["total_workers"] == 2
        assert stats["available_workers"] == 2
        assert stats["strategy"] == "least_busy"
