# -*- coding: utf-8 -*-
"""
Thread Pool Test Module - 线程池测试模块

包含5个测试用例:
1. 测试线程池基本提交和执行
2. 测试任务优先级
3. 测试线程池指标统计
4. 测试线程池关闭
5. 测试并发任务执行
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from agent_os_kernel.core.thread_pool import (
    Task,
    TaskPriority,
    ThreadPool,
    ThreadPoolConfig,
    ThreadPoolMetrics,
    ThreadPoolState,
)


class TestTaskPriority:
    """测试任务优先级"""
    
    def test_priority_ordering(self):
        """测试优先级顺序"""
        # 创建不同优先级的任务
        low_task = Task(
            task_id="1",
            func=lambda: None,
            args=(),
            kwargs={},
            priority=TaskPriority.LOW,
            submitted_time=time.time()
        )
        normal_task = Task(
            task_id="2",
            func=lambda: None,
            args=(),
            kwargs={},
            priority=TaskPriority.NORMAL,
            submitted_time=time.time()
        )
        high_task = Task(
            task_id="3",
            func=lambda: None,
            args=(),
            kwargs={},
            priority=TaskPriority.HIGH,
            submitted_time=time.time()
        )
        critical_task = Task(
            task_id="4",
            func=lambda: None,
            args=(),
            kwargs={},
            priority=TaskPriority.CRITICAL,
            submitted_time=time.time()
        )
        
        # 高优先级任务应该排在前面 (使用 > 比较)
        assert critical_task > normal_task
        assert high_task > low_task
        assert normal_task > low_task
    
    def test_priority_values(self):
        """测试优先级值"""
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.CRITICAL.value == 3


class TestThreadPoolConfig:
    """测试线程池配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ThreadPoolConfig()
        assert config.min_workers == 2
        assert config.max_workers == 10
        assert config.max_queue_size == 100
        assert config.thread_prefix == "worker"
        assert config.daemon is True
        assert config.idle_timeout == 60.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = ThreadPoolConfig(
            min_workers=4,
            max_workers=20,
            max_queue_size=500,
            thread_prefix="myworker",
            daemon=False,
            idle_timeout=120.0
        )
        assert config.min_workers == 4
        assert config.max_workers == 20
        assert config.max_queue_size == 500
        assert config.thread_prefix == "myworker"
        assert config.daemon is False
        assert config.idle_timeout == 120.0


class TestThreadPoolMetrics:
    """测试线程池指标"""
    
    def test_default_metrics(self):
        """测试默认指标"""
        metrics = ThreadPoolMetrics()
        assert metrics.submitted_tasks == 0
        assert metrics.completed_tasks == 0
        assert metrics.failed_tasks == 0
        assert metrics.active_workers == 0
        assert metrics.queued_tasks == 0
        assert metrics.total_execution_time == 0.0
        assert metrics.average_execution_time == 0.0
        assert metrics.peak_queued_tasks == 0
    
    def test_to_dict(self):
        """测试转换为字典"""
        metrics = ThreadPoolMetrics(
            submitted_tasks=10,
            completed_tasks=8,
            failed_tasks=2,
            active_workers=2,
            queued_tasks=3,
            total_execution_time=5.5,
            average_execution_time=0.6875,
            peak_queued_tasks=5
        )
        result = metrics.to_dict()
        assert isinstance(result, dict)
        assert result["submitted_tasks"] == 10
        assert result["completed_tasks"] == 8
        assert result["failed_tasks"] == 2
        assert result["peak_queued_tasks"] == 5


class TestThreadPool:
    """测试线程池核心功能"""
    
    def test_submit_and_execute(self):
        """测试基本任务提交和执行"""
        result = []
        
        def task_func(x, y):
            result.append(x + y)
            return x + y
        
        with ThreadPool() as pool:
            task_id = pool.submit(task_func, 2, 3)
            assert task_id is not None
            assert len(task_id) > 0
            
            # 等待任务执行
            time.sleep(0.3)
        
        assert result == [5]
    
    def test_multiple_tasks(self):
        """测试多个任务提交"""
        results = []
        
        def increment(n):
            results.append(n)
            return n + 1
        
        with ThreadPool() as pool:
            for i in range(5):
                pool.submit(increment, i)
            time.sleep(0.5)
        
        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}
    
    def test_task_priority(self):
        """测试任务优先级"""
        execution_order = []
        
        def task(name):
            execution_order.append(name)
            return name
        
        with ThreadPool() as pool:
            # 提交不同优先级的任务
            pool.submit(task, "low1", priority=TaskPriority.LOW)
            pool.submit(task, "high1", priority=TaskPriority.HIGH)
            pool.submit(task, "normal1", priority=TaskPriority.NORMAL)
            time.sleep(0.3)
        
        # 高优先级任务应该先执行
        assert execution_order.index("high1") < execution_order.index("normal1")
        assert execution_order.index("normal1") < execution_order.index("low1")
    
    def test_metrics_collection(self):
        """测试指标收集"""
        def simple_task():
            time.sleep(0.1)
        
        with ThreadPool() as pool:
            for _ in range(3):
                pool.submit(simple_task)
            time.sleep(0.5)
            
            metrics = pool.get_metrics()
            
            assert metrics["submitted_tasks"] >= 3
            assert metrics["completed_tasks"] >= 3
    
    def test_graceful_shutdown(self):
        """测试优雅关闭"""
        execution_count = 0
        
        def long_task():
            nonlocal execution_count
            time.sleep(0.3)
            execution_count += 1
        
        pool = ThreadPool()
        
        # 提交多个任务
        for _ in range(3):
            pool.submit(long_task)
        
        # 立即关闭，应该等待任务完成
        pool.shutdown(wait=True, timeout=5.0)
        
        assert pool.get_state() == ThreadPoolState.TERMINATED
        assert execution_count == 3
    
    def test_concurrent_task_execution(self):
        """测试并发任务执行"""
        lock = threading.Lock()
        counter = 0
        
        def increment():
            nonlocal counter
            with lock:
                counter += 1
            time.sleep(0.2)
        
        with ThreadPool() as pool:
            # 提交多个任务
            for _ in range(5):
                pool.submit(increment)
            time.sleep(1.0)
        
        assert counter == 5
    
    def test_shutdown_with_running_tasks(self):
        """测试关闭时正在运行的任务"""
        results = []
        
        def delayed_task(delay):
            time.sleep(delay)
            results.append("done")
        
        pool = ThreadPool()
        pool.submit(delayed_task, 0.5)
        pool.submit(delayed_task, 0.3)
        
        # 快速关闭
        pool.shutdown(wait=False)
        
        assert pool.get_state() in (
            ThreadPoolState.SHUTTING_DOWN,
            ThreadPoolState.TERMINATED
        )
    
    def test_get_metrics(self):
        """测试获取指标"""
        def task():
            return 42
        
        with ThreadPool() as pool:
            pool.submit(task)
            time.sleep(0.2)
            
            metrics = pool.get_metrics()
            
            assert isinstance(metrics, dict)
            assert "submitted_tasks" in metrics
            assert "completed_tasks" in metrics
            assert "active_workers" in metrics
    
    def test_worker_count(self):
        """测试工作线程数量"""
        with ThreadPool() as pool:
            initial_workers = pool.get_worker_count()
            
            # 添加任务触发线程扩展
            for _ in range(5):
                pool.submit(lambda: None)
            time.sleep(0.3)
            
            workers_after = pool.get_worker_count()
            
            assert initial_workers >= 1
            assert workers_after >= initial_workers
    
    def test_get_state(self):
        """测试获取状态"""
        pool = ThreadPool()
        assert pool.get_state() == ThreadPoolState.RUNNING
        
        pool.shutdown(wait=False)
        assert pool.get_state() == ThreadPoolState.TERMINATED


class TestThreadPoolEdgeCases:
    """测试边界情况"""
    
    def test_exception_handling(self):
        """测试任务异常处理"""
        def failing_task():
            raise ValueError("Test error")
        
        with ThreadPool() as pool:
            pool.submit(failing_task)
            time.sleep(0.3)
            
            metrics = pool.get_metrics()
            # 异常任务应该被计入失败
            assert metrics["failed_tasks"] >= 1
    
    def test_task_with_args_kwargs(self):
        """测试带参数的任务"""
        def task_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        with ThreadPool() as pool:
            task_id = pool.submit(task_with_args, 1, 2, c=3)
            time.sleep(0.2)
            
            assert task_id is not None
    
    def test_context_manager(self):
        """测试上下文管理器"""
        def simple_task():
            return "completed"
        
        with ThreadPool() as pool:
            pool.submit(simple_task)
            state = pool.get_state()
            assert state == ThreadPoolState.RUNNING
        
        # 退出后应该已关闭
        state_after = pool.get_state()
        assert state_after == ThreadPoolState.TERMINATED
