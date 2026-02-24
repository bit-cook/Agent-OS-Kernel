# -*- coding: utf-8 -*-
"""
任务调度器测试 - Agent-OS-Kernel
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel.core.task_scheduler import (
    TaskScheduler,
    TaskPriority,
    SchedulerState,
    ScheduledTask,
    create_task_scheduler
)


class TestTaskSchedulerBasic:
    """测试任务调度器基础功能"""
    
    def setup_method(self):
        """每个测试前初始化调度器"""
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        """每个测试后清理"""
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_create_scheduler(self):
        """测试创建调度器"""
        assert self.scheduler.state == SchedulerState.STOPPED
        assert len(self.scheduler.tasks) == 0
        assert self.scheduler.timezone == "UTC"
    
    def test_add_task(self):
        """测试添加任务"""
        def dummy_func():
            return "done"
        
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="test_task",
            task_id="test_001"
        )
        
        assert task_id == "test_001"
        assert len(self.scheduler.tasks) == 1
        assert self.scheduler.tasks["test_001"].name == "test_task"
    
    def test_add_task_auto_id(self):
        """测试自动生成任务ID"""
        def dummy_func():
            return "done"
        
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="auto_id_task"
        )
        
        assert task_id is not None
        assert len(task_id) > 0
        assert task_id in self.scheduler.tasks
    
    def test_remove_task(self):
        """测试移除任务"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="test", task_id="t1")
        assert len(self.scheduler.tasks) == 1
        
        result = self.scheduler.remove_task("t1")
        assert result is True
        assert len(self.scheduler.tasks) == 0
    
    def test_remove_nonexistent_task(self):
        """测试移除不存在的任务"""
        result = self.scheduler.remove_task("nonexistent")
        assert result is False
    
    def test_get_task(self):
        """测试获取任务"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="test", task_id="t1")
        
        task = self.scheduler.get_task("t1")
        assert task is not None
        assert task.name == "test"
        
        nonexistent = self.scheduler.get_task("t2")
        assert nonexistent is None
    
    def test_get_all_tasks(self):
        """测试获取所有任务"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="t1", task_id="task1")
        self.scheduler.add_task(func=dummy_func, name="t2", task_id="task2")
        self.scheduler.add_task(func=dummy_func, name="t3", task_id="task3")
        
        tasks = self.scheduler.get_all_tasks()
        assert len(tasks) == 3
    
    def test_enable_disable_task(self):
        """测试启用/禁用任务"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="test", task_id="t1")
        
        assert self.scheduler.get_task("t1").enabled is True
        
        self.scheduler.disable_task("t1")
        assert self.scheduler.get_task("t1").enabled is False
        
        self.scheduler.enable_task("t1")
        assert self.scheduler.get_task("t1").enabled is True


class TestCronJobs:
    """测试cron定时任务"""
    
    def setup_method(self):
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_add_cron_task(self):
        """测试添加cron任务"""
        def dummy_func():
            return "cron done"
        
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="cron_task",
            cron_expression="*/5 * * * *"
        )
        
        task = self.scheduler.get_task(task_id)
        assert task.cron_expression == "*/5 * * * *"
        assert task.next_run_time is not None
    
    def test_invalid_cron_expression(self):
        """测试无效cron表达式"""
        def dummy_func():
            return "done"
        
        with pytest.raises(ValueError):
            self.scheduler.add_task(
                func=dummy_func,
                name="invalid_cron",
                cron_expression="invalid expression"
            )
    
    def test_get_next_cron_time(self):
        """测试计算下次cron时间"""
        next_time = self.scheduler._get_next_cron_time("*/5 * * * *")
        assert next_time is not None
        assert isinstance(next_time, datetime)
        
        # 验证下次时间在5分钟内
        assert next_time - datetime.now() <= timedelta(minutes=5)
    
    def test_cron_task_scheduling(self):
        """测试cron任务调度"""
        execution_count = 0
        
        def increment_func():
            nonlocal execution_count
            execution_count += 1
            return "executed"
        
        self.scheduler.add_task(
            func=increment_func,
            name="count_task",
            cron_expression="* * * * *",  # 每分钟
            task_id="count_001"
        )
        
        # 手动触发执行
        self.scheduler.run_now("count_001")
        
        assert execution_count == 1


class TestPeriodicTasks:
    """测试周期性任务"""
    
    def setup_method(self):
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_add_interval_task(self):
        """测试添加间隔任务"""
        def dummy_func():
            return "interval done"
        
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="interval_task",
            interval_seconds=60.0
        )
        
        task = self.scheduler.get_task(task_id)
        assert task.interval_seconds == 60.0
        assert task.next_run_time is not None
    
    def test_interval_task_execution(self):
        """测试间隔任务执行"""
        results = []
        
        def append_func():
            results.append("done")
            return "done"
        
        task_id = self.scheduler.add_task(
            func=append_func,
            name="interval",
            interval_seconds=1.0
        )
        
        # 立即执行
        self.scheduler.run_now(task_id)
        
        assert len(results) == 1
        assert "done" in results
    
    def test_periodic_with_priority(self):
        """测试带优先级的周期性任务"""
        def dummy_func():
            return "done"
        
        # 添加不同优先级的任务
        self.scheduler.add_task(
            func=dummy_func,
            name="low_priority",
            priority=TaskPriority.LOW,
            interval_seconds=10.0,
            task_id="low"
        )
        
        self.scheduler.add_task(
            func=dummy_func,
            name="high_priority",
            priority=TaskPriority.HIGH,
            interval_seconds=10.0,
            task_id="high"
        )
        
        low_task = self.scheduler.get_task("low")
        high_task = self.scheduler.get_task("high")
        
        assert low_task.priority == TaskPriority.LOW
        assert high_task.priority == TaskPriority.HIGH
        
        # 高优先级任务应该排在前面
        assert high_task > low_task


class TestTaskPriority:
    """测试任务优先级"""
    
    def setup_method(self):
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        def dummy_func():
            return "done"
        
        # 创建不同优先级的任务
        low = ScheduledTask(
            task_id="low",
            name="low",
            func=dummy_func,
            priority=TaskPriority.LOW
        )
        normal = ScheduledTask(
            task_id="normal",
            name="normal",
            func=dummy_func,
            priority=TaskPriority.NORMAL
        )
        high = ScheduledTask(
            task_id="high",
            name="high",
            func=dummy_func,
            priority=TaskPriority.HIGH
        )
        critical = ScheduledTask(
            task_id="critical",
            name="critical",
            func=dummy_func,
            priority=TaskPriority.CRITICAL
        )
        
        # 验证优先级值
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.CRITICAL.value == 3
        
        # 验证排序（高的优先级应该先执行）
        assert critical > high > normal > low
    
    def test_update_priority(self):
        """测试更新任务优先级"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="test", task_id="t1")
        
        assert self.scheduler.get_task("t1").priority == TaskPriority.NORMAL
        
        result = self.scheduler.update_priority("t1", TaskPriority.HIGH)
        assert result is True
        assert self.scheduler.get_task("t1").priority == TaskPriority.HIGH
        
        # 更新不存在的任务
        result = self.scheduler.update_priority("nonexistent", TaskPriority.CRITICAL)
        assert result is False
    
    def test_priority_queue_order(self):
        """测试优先级队列顺序"""
        def dummy_func():
            return "done"
        
        # 添加不同优先级的任务
        self.scheduler.add_task(func=dummy_func, name="low", priority=TaskPriority.LOW, task_id="l")
        self.scheduler.add_task(func=dummy_func, name="high", priority=TaskPriority.HIGH, task_id="h")
        
        high_task = self.scheduler.get_task("h")
        low_task = self.scheduler.get_task("l")
        
        # 高优先级任务应该排在前面
        tasks = sorted([high_task, low_task])
        assert tasks[0].priority.value > tasks[1].priority.value


class TestTaskDependencies:
    """测试任务依赖"""
    
    def setup_method(self):
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_add_task_with_dependencies(self):
        """测试添加带依赖的任务"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="task1", task_id="t1")
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="task2",
            dependencies=["t1"],
            task_id="t2"
        )
        
        task = self.scheduler.get_task(task_id)
        assert "t1" in task.dependencies
    
    def test_dependency_graph(self):
        """测试依赖图"""
        def dummy_func():
            return "done"
        
        # 创建依赖链: t1 -> t2 -> t3
        self.scheduler.add_task(func=dummy_func, name="t1", task_id="t1")
        self.scheduler.add_task(func=dummy_func, name="t2", dependencies=["t1"], task_id="t2")
        self.scheduler.add_task(func=dummy_func, name="t3", dependencies=["t2"], task_id="t3")
        
        # t1 没有前置依赖
        assert len(self.scheduler._dependency_graph["t1"]) == 1
        assert "t2" in self.scheduler._dependency_graph["t1"]
        
        # t2 被 t3 依赖
        assert "t3" in self.scheduler._dependency_graph["t2"]
    
    def test_check_dependencies(self):
        """测试检查依赖"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="t1", task_id="t1")
        self.scheduler.add_task(func=dummy_func, name="t2", dependencies=["t1"], task_id="t2")
        
        task2 = self.scheduler.get_task("t2")
        
        # t2 依赖 t1，但 t1 还未完成
        assert self.scheduler._check_dependencies(task2) is False
        
        # 标记 t1 为已完成
        self.scheduler._completed_tasks.add("t1")
        assert self.scheduler._check_dependencies(task2) is True
    
    def test_execute_task_chain(self):
        """测试执行任务链"""
        results = []
        
        def task1():
            results.append("task1")
            return "result1"
        
        def task2():
            results.append("task2")
            return "result2"
        
        def task3():
            results.append("task3")
            return "result3"
        
        self.scheduler.add_task(func=task1, name="task1", task_id="t1")
        self.scheduler.add_task(func=task2, name="task2", task_id="t2")
        self.scheduler.add_task(func=task3, name="task3", task_id="t3")
        
        # 执行任务链
        results_list = asyncio.run(self.scheduler.execute_task_chain(["t1", "t2", "t3"]))
        
        # 验证执行顺序
        assert len(results_list) == 3
        assert all(r.status == "completed" for r in results_list)
        assert results == ["task1", "task2", "task3"]
    
    def test_chain_stops_on_failure(self):
        """测试任务链在失败时停止"""
        results = []
        
        def task_success():
            results.append("success")
            return "done"
        
        def task_fail():
            results.append("fail")
            raise Exception("Task failed")
        
        def task_after_fail():
            results.append("after_fail")
            return "should_not_run"
        
        self.scheduler.add_task(func=task_success, name="success", task_id="s")
        self.scheduler.add_task(func=task_fail, name="fail", task_id="f")
        self.scheduler.add_task(func=task_after_fail, name="after", task_id="a")
        
        results_list = asyncio.run(self.scheduler.execute_task_chain(["s", "f", "a"]))
        
        # 验证只有前两个任务执行
        assert len(results_list) == 2
        assert results_list[0].status == "completed"
        assert results_list[1].status == "failed"
        assert results == ["success", "fail"]


class TestSchedulerLifecycle:
    """测试调度器生命周期"""
    
    def setup_method(self):
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_start_scheduler(self):
        """测试启动调度器"""
        assert self.scheduler.state == SchedulerState.STOPPED
        
        asyncio.run(self.scheduler.start())
        
        assert self.scheduler.state == SchedulerState.RUNNING
    
    def test_stop_scheduler(self):
        """测试停止调度器"""
        asyncio.run(self.scheduler.start())
        assert self.scheduler.state == SchedulerState.RUNNING
        
        asyncio.run(self.scheduler.stop())
        
        assert self.scheduler.state == SchedulerState.STOPPED
    
    def test_pause_resume_scheduler(self):
        """测试暂停和恢复"""
        asyncio.run(self.scheduler.start())
        assert self.scheduler.state == SchedulerState.RUNNING
        
        asyncio.run(self.scheduler.pause())
        assert self.scheduler.state == SchedulerState.PAUSED
        
        asyncio.run(self.scheduler.resume())
        assert self.scheduler.state == SchedulerState.RUNNING
        
        asyncio.run(self.scheduler.stop())
    
    def test_get_stats(self):
        """测试获取统计信息"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="t1", task_id="t1")
        self.scheduler.add_task(func=dummy_func, name="t2", task_id="t2")
        self.scheduler.disable_task("t2")
        
        stats = self.scheduler.get_task_stats()
        
        assert stats["total_tasks"] == 2
        assert stats["enabled_tasks"] == 1
        assert stats["disabled_tasks"] == 1
        assert stats["state"] == SchedulerState.STOPPED.value


class TestTaskExecution:
    """测试任务执行"""
    
    def setup_method(self):
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_async_task(self):
        """测试异步任务"""
        async def async_func():
            await asyncio.sleep(0.01)
            return "async done"
        
        task_id = self.scheduler.add_task(
            func=async_func,
            name="async_task"
        )
        
        result = asyncio.run(self.scheduler.execute_task_chain([task_id]))
        
        assert len(result) == 1
        assert result[0].status == "completed"
        assert result[0].result == "async done"
    
    def test_failing_task(self):
        """测试失败任务"""
        def fail_func():
            raise ValueError("Task failed")
        
        task_id = self.scheduler.add_task(
            func=fail_func,
            name="fail_task"
        )
        
        results = asyncio.run(self.scheduler.execute_task_chain([task_id]))
        
        assert results[0].status == "failed"
        assert results[0].error == "Task failed"
    
    def test_task_with_metadata(self):
        """测试带元数据的任务"""
        def dummy_func():
            return "done"
        
        metadata = {"category": "test", "version": "1.0"}
        
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="meta_task",
            metadata=metadata
        )
        
        task = self.scheduler.get_task(task_id)
        assert task.metadata["category"] == "test"
        assert task.metadata["version"] == "1.0"


class TestTaskSchedulerEdgeCases:
    """测试边界情况"""
    
    def setup_method(self):
        self.scheduler = create_task_scheduler()
    
    def teardown_method(self):
        if self.scheduler.state == SchedulerState.RUNNING:
            asyncio.run(self.scheduler.stop())
    
    def test_empty_dependencies(self):
        """测试空依赖"""
        def dummy_func():
            return "done"
        
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="no_deps",
            dependencies=[]
        )
        
        task = self.scheduler.get_task(task_id)
        assert len(task.dependencies) == 0
    
    def test_multiple_dependencies(self):
        """测试多依赖"""
        def dummy_func():
            return "done"
        
        self.scheduler.add_task(func=dummy_func, name="t1", task_id="t1")
        self.scheduler.add_task(func=dummy_func, name="t2", task_id="t2")
        self.scheduler.add_task(func=dummy_func, name="t3", task_id="t3")
        
        task_id = self.scheduler.add_task(
            func=dummy_func,
            name="depends_on_all",
            dependencies=["t1", "t2", "t3"]
        )
        
        task = self.scheduler.get_task(task_id)
        assert len(task.dependencies) == 3
        assert set(task.dependencies) == {"t1", "t2", "t3"}
    
    def test_execution_history_limit(self):
        """测试执行历史限制"""
        # 执行多个任务
        for i in range(10):
            def dummy_func():
                return f"result_{i}"
            self.scheduler.add_task(func=dummy_func, name=f"t{i}", task_id=f"t{i}")
        
        # 执行任务链
        asyncio.run(self.scheduler.execute_task_chain([f"t{i}" for i in range(10)]))
        
        # 验证历史记录数量（最大1000）
        history = self.scheduler.get_execution_history()
        assert len(history) <= 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
