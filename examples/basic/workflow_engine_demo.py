"""
Agent-OS-Kernel 工作流引擎演示

展示工作流引擎的使用方法
"""

from agent_os_kernel.core.workflow_engine import Task, TaskConfig, WorkflowEngine


async def demo_workflow():
    """演示工作流引擎"""
    print("=" * 60)
    print("Agent-OS-Kernel 工作流引擎演示")
    print("=" * 60)

    # 创建引擎
    engine = WorkflowEngine()

    # 创建工作流
    print("\n创建工作流...")
    workflow = engine.create_workflow("data-processing")
    print(f"  ✅ 工作流: {workflow.workflow_id}")

    # 定义任务函数（签名为 func(task_input, context)）
    async def extract(task_input, context):
        return "extracted data"

    async def transform(task_input, context):
        return f"transformed: {task_input['extract']}"

    async def load(task_input, context):
        return f"loaded: {task_input['transform']}"

    # 添加任务（依赖关系构成 DAG：extract -> transform -> load）
    workflow.add_task(Task(TaskConfig(task_id="extract", func=extract)))
    workflow.add_task(
        Task(TaskConfig(task_id="transform", func=transform, dependencies=["extract"]))
    )
    workflow.add_task(
        Task(TaskConfig(task_id="load", func=load, dependencies=["transform"]))
    )

    print(f"  ✅ 节点数: {len(workflow.tasks)}")
    print(f"  执行顺序: {workflow.get_execution_order()}")

    # 运行工作流
    print("\n运行工作流...")
    result = await engine.run("data-processing")
    print(f"  工作流状态: {result.status.value}")

    # 输出任务结果
    print("\n任务结果:")
    for task_id in ("extract", "transform", "load"):
        task_result = result.results.get(task_id)
        if task_result is not None:
            print(f"  {task_id}: {task_result.status.value} -> {task_result.result}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_workflow())
