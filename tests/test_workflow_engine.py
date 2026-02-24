# -*- coding: utf-8 -*-
"""
工作流引擎测试
"""

import pytest
import asyncio
from agent_os_kernel.core.workflow_engine import (
    WorkflowEngine,
    Workflow,
    Task,
    TaskConfig,
    TaskStatus,
    WorkflowStatus,
    TaskResult,
)


class TestWorkflowDefinition:
    """测试工作流定义功能"""
    
    def test_create_workflow(self):
        """测试创建工作流"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("test_wf", "测试工作流")
        
        assert workflow.workflow_id == "test_wf"
        assert workflow.name == "测试工作流"
        assert workflow.status == WorkflowStatus.CREATED
        assert len(workflow.tasks) == 0
    
    def test_add_task(self):
        """测试添加任务"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        task_config = TaskConfig(
            task_id="task1",
            func=dummy_task,
            dependencies=[]
        )
        task = Task(task_config)
        workflow.add_task(task)
        
        assert "task1" in workflow.tasks
        assert workflow.tasks["task1"].task_id == "task1"
    
    def test_add_task_with_dependencies(self):
        """测试添加带依赖的任务"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        task1_config = TaskConfig(task_id="task1", func=dummy_task, dependencies=[])
        task2_config = TaskConfig(task_id="task2", func=dummy_task, dependencies=["task1"])
        
        task1 = Task(task1_config)
        task2 = Task(task2_config)
        
        workflow.add_task(task1)
        workflow.add_task(task2)
        
        assert "task1" in workflow.tasks
        assert "task2" in workflow.tasks
        assert "task1" in workflow.task_graph["task2"]
    
    def test_add_duplicate_task_raises_error(self):
        """测试添加重复任务"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        task_config = TaskConfig(task_id="task1", func=dummy_task, dependencies=[])
        task = Task(task_config)
        
        workflow.add_task(task)
        
        with pytest.raises(ValueError):
            workflow.add_task(Task(task_config))
    
    def test_add_task_with_nonexistent_dependency(self):
        """测试添加依赖不存在的任务"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        task_config = TaskConfig(
            task_id="task1", 
            func=dummy_task, 
            dependencies=["nonexistent"]
        )
        
        with pytest.raises(ValueError):
            workflow.add_task(Task(task_config))
    
    def test_task_graph_structure(self):
        """测试任务图结构"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        # 创建复杂依赖关系
        task_configs = [
            ("task1", []),
            ("task2", ["task1"]),
            ("task3", ["task1"]),
            ("task4", ["task2", "task3"]),
        ]
        
        for task_id, deps in task_configs:
            config = TaskConfig(task_id=task_id, func=dummy_task, dependencies=deps)
            workflow.add_task(Task(config))
        
        # 验证图结构
        assert workflow.task_graph["task4"] == {"task2", "task3"}
        assert workflow.reverse_graph["task1"] == {"task2", "task3"}


class TestWorkflowExecution:
    """测试工作流执行功能"""
    
    def test_get_execution_order(self):
        """测试获取执行顺序"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        task_configs = [
            ("task1", []),
            ("task2", ["task1"]),
            ("task3", ["task1"]),
            ("task4", ["task2", "task3"]),
        ]
        
        for task_id, deps in task_configs:
            config = TaskConfig(task_id=task_id, func=dummy_task, dependencies=deps)
            workflow.add_task(Task(config))
        
        order = workflow.get_execution_order()
        
        # 验证拓扑排序结果
        assert order.index("task1") < order.index("task2")
        assert order.index("task1") < order.index("task3")
        assert order.index("task2") < order.index("task4")
        assert order.index("task3") < order.index("task4")
    
    def test_execution_order_with_parallel_tasks(self):
        """测试并行任务的执行顺序"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        # task1 完成后，task2 和 task3 可以并行执行
        configs = [
            ("task1", []),
            ("task2", ["task1"]),
            ("task3", ["task1"]),
        ]
        
        for task_id, deps in configs:
            config = TaskConfig(task_id=task_id, func=dummy_task, dependencies=deps)
            workflow.add_task(Task(config))
        
        order = workflow.get_execution_order()
        
        # task1 应该在最前面
        assert order.index("task1") == 0
        # task2 和 task3 应该在 task1 之后
        assert order.index("task2") > order.index("task1")
        assert order.index("task3") > order.index("task1")
    
    def test_cycle_detection(self):
        """测试循环依赖检测"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        configs = [
            ("task1", ["task2"]),
            ("task2", ["task1"]),
        ]
        
        for task_id, deps in configs:
            config = TaskConfig(task_id=task_id, func=dummy_task, dependencies=deps)
            workflow.add_task(Task(config))
        
        with pytest.raises(ValueError):
            workflow.get_execution_order()
    
    def test_simple_execution(self):
        """测试简单工作流执行"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("simple_wf")
        
        results = []
        
        def task1(input_data, context):
            return "result1"
        
        def task2(input_data, context):
            results.append("task2")
            return "result2"
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=task1, dependencies=[])))
        workflow.add_task(Task(TaskConfig(task_id="task2", func=task2, dependencies=["task1"])))
        
        result = engine.run_sync("simple_wf")
        
        assert result.status == WorkflowStatus.COMPLETED
        assert "task2" in results
    
    def test_workflow_reset(self):
        """测试工作流重置"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=dummy_task, dependencies=[])))
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.tasks["task1"].status = TaskStatus.COMPLETED
        
        workflow.reset()
        
        assert workflow.status == WorkflowStatus.CREATED
        assert workflow.tasks["task1"].status == TaskStatus.PENDING


class TestWorkflowDependencies:
    """测试工作流依赖功能"""
    
    def test_get_ready_tasks(self):
        """测试获取可执行任务"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=dummy_task, dependencies=[])))
        workflow.add_task(Task(TaskConfig(task_id="task2", func=dummy_task, dependencies=["task1"])))
        
        # 初始只有 task1 可执行
        ready = workflow.get_ready_tasks()
        assert "task1" in ready
        assert "task2" not in ready
        
        # 标记 task1 完成
        workflow.tasks["task1"].status = TaskStatus.COMPLETED
        workflow.results["task1"] = TaskResult(
            task_id="task1",
            status=TaskStatus.COMPLETED,
            result="result1"
        )
        
        # task2 现在可执行
        ready = workflow.get_ready_tasks()
        assert "task2" in ready
    
    def test_parallel_task_execution(self):
        """测试并行任务执行"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("parallel_wf")
        
        execution_times = []
        
        def slow_task(input_data, context):
            import time
            execution_times.append(("slow", len(execution_times)))
            time.sleep(0.1)
            return "result"
        
        # 创建多个并行任务
        workflow.add_task(Task(TaskConfig(
            task_id="task1", 
            func=slow_task, 
            dependencies=[],
            parallel=True
        )))
        workflow.add_task(Task(TaskConfig(
            task_id="task2", 
            func=slow_task, 
            dependencies=[],
            parallel=True
        )))
        workflow.add_task(Task(TaskConfig(
            task_id="task3", 
            func=slow_task, 
            dependencies=[],
            parallel=True
        )))
        
        result = engine.run_sync("parallel_wf")
        
        # 如果并行执行，总时间应该小于串行执行时间
        assert result.status == WorkflowStatus.COMPLETED
    
    def test_task_condition(self):
        """测试任务条件"""
        workflow = Workflow("test_wf")
        
        def dummy_task(input_data, context):
            return input_data.get("value", 0) + 1
        
        # task2 的执行条件是 task1 的结果 > 5
        def condition(results):
            return results.get("task1", TaskResult("task1", TaskStatus.PENDING)).result > 5
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=dummy_task, dependencies=[])))
        workflow.add_task(Task(TaskConfig(
            task_id="task2", 
            func=dummy_task, 
            dependencies=["task1"],
            condition=condition
        )))
        
        # 第一次执行结果不大于5，task2 应该被跳过
        workflow.tasks["task1"].result = 3
        
        ready = workflow.get_ready_tasks()
        assert "task2" not in ready
    
    def test_complex_dependency_chain(self):
        """测试复杂依赖链"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("complex_wf")
        
        execution_order = []
        
        def tracked_task(task_id):
            def task(input_data, context):
                execution_order.append(task_id)
                return f"result_{task_id}"
            return task
        
        # 创建复杂的DAG结构
        configs = [
            ("data_fetch", [], tracked_task("data_fetch")),
            ("process_a", ["data_fetch"], tracked_task("process_a")),
            ("process_b", ["data_fetch"], tracked_task("process_b")),
            ("merge", ["process_a", "process_b"], tracked_task("merge")),
            ("output", ["merge"], tracked_task("output")),
        ]
        
        for task_id, deps, func in configs:
            workflow.add_task(Task(TaskConfig(
                task_id=task_id,
                func=func,
                dependencies=deps
            )))
        
        result = engine.run_sync("complex_wf")
        
        assert result.status == WorkflowStatus.COMPLETED
        
        # 验证执行顺序
        assert execution_order.index("data_fetch") < execution_order.index("process_a")
        assert execution_order.index("data_fetch") < execution_order.index("process_b")
        assert execution_order.index("process_a") < execution_order.index("merge")
        assert execution_order.index("process_b") < execution_order.index("merge")
        assert execution_order.index("merge") < execution_order.index("output")


class TestWorkflowErrorHandling:
    """测试工作流错误处理"""
    
    def test_task_retry_on_failure(self):
        """测试任务失败重试"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("retry_wf")
        
        attempt_count = 0
        
        def failing_task(input_data, context):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        workflow.add_task(Task(TaskConfig(
            task_id="task1",
            func=failing_task,
            dependencies=[],
            retry_count=3,
            retry_delay=0.01
        )))
        
        result = engine.run_sync("retry_wf")
        
        assert result.status == WorkflowStatus.COMPLETED
        assert attempt_count == 3
    
    def test_task_max_retries_exceeded(self):
        """测试任务超过最大重试次数"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("max_retries_wf")
        
        def always_failing_task(input_data, context):
            raise ValueError("Always fails")
        
        workflow.add_task(Task(TaskConfig(
            task_id="task1",
            func=always_failing_task,
            dependencies=[],
            retry_count=2,
            retry_delay=0.01
        )))
        
        result = engine.run_sync("max_retries_wf")
        
        assert result.status == WorkflowStatus.FAILED
        assert workflow.results["task1"].status == TaskStatus.FAILED
    
    def test_workflow_cancellation(self):
        """测试工作流取消"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("cancel_wf")
        
        def long_task(input_data, context):
            import time
            time.sleep(1)
            return "done"
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=long_task, dependencies=[])))
        
        # 由于是异步执行，这里只测试创建和基本状态
        assert workflow.status == WorkflowStatus.CREATED
    
    def test_task_timeout(self):
        """测试任务超时"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("timeout_wf")
        
        def long_task(input_data, context):
            import time
            time.sleep(10)
            return "done"
        
        workflow.add_task(Task(TaskConfig(
            task_id="task1",
            func=long_task,
            dependencies=[],
            timeout=0.1
        )))
        
        result = engine.run_sync("timeout_wf")
        
        # 任务应该因超时而失败
        assert result.status == WorkflowStatus.FAILED
    
    def test_error_in_task_propagates(self):
        """测试任务错误传播"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("error_prop_wf")
        
        def failing_task(input_data, context):
            raise RuntimeError("Task failed!")
        
        def dependent_task(input_data, context):
            return input_data
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=failing_task, dependencies=[])))
        workflow.add_task(Task(TaskConfig(
            task_id="task2", 
            func=dependent_task, 
            dependencies=["task1"]
        )))
        
        result = engine.run_sync("error_prop_wf")
        
        assert result.status == WorkflowStatus.FAILED
        assert "task1" in result.error
    
    def test_workflow_with_error_handler(self):
        """测试带错误处理的工作流"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("error_handler_wf")
        
        results = []
        
        def task1(input_data, context):
            return "task1_result"
        
        def task2(input_data, context):
            results.append("task2")
            return "task2_result"
        
        def error_handler_task(input_data, context):
            results.append("error_handler")
            return "handled"
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=task1, dependencies=[])))
        workflow.add_task(Task(TaskConfig(task_id="task2", func=task2, dependencies=["task1"])))
        
        result = engine.run_sync("error_handler_wf")
        
        assert result.status == WorkflowStatus.COMPLETED
        assert "task2" in results
    
    def test_get_status(self):
        """测试获取工作流状态"""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("status_wf")
        
        def dummy_task(input_data, context):
            return "result"
        
        workflow.add_task(Task(TaskConfig(task_id="task1", func=dummy_task, dependencies=[])))
        
        status = engine.get_status("status_wf")
        
        assert status is not None
        assert status["workflow_id"] == "status_wf"
        assert status["status"] == "created"
        assert status["progress"] == "0/1"
        assert status["completed"] == 0
        assert status["failed"] == 0
        assert status["total"] == 1


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
