"""
Agent-OS-Kernel 工作流引擎演示

展示工作流引擎的使用方法
"""

from agent_os_kernel.core.workflow_engine import (
    Task,
    TaskConfig,
    TaskStatus,
    WorkflowEngine,
    WorkflowStatus,
)


async def demo_workflow():
    """演示工作流引擎"""
    print("=" * 60)
    print("Agent-OS-Kernel 工作流引擎演示")
    print("=" * 60)

    # 创建引擎
    engine = WorkflowEngine(max_concurrent=10)

    # 创建工作流
    print("\n创建工作流...")
    workflow = engine.create_workflow("data-processing", name="数据处理工作流")
    print(f"  ✅ 工作流: {workflow.workflow_id} ({workflow.name})")
    print(f"  初始状态: {workflow.status.value}")

    # 定义任务函数（签名为 func(task_input, context)，
    # task_input 是 {依赖任务ID: 该任务结果}）
    async def extract(task_input, context):
        print("    [extract] 提取数据")
        await asyncio.sleep(0.05)
        return {"source": context.get("source", "db"), "rows": 3}

    async def transform(task_input, context):
        rows = task_input["extract"]["rows"]
        print(f"    [transform] 转换 {rows} 行数据")
        await asyncio.sleep(0.05)
        return {"rows": rows, "cleaned": True}

    async def load(task_input, context):
        print("    [load] 加载数据")
        await asyncio.sleep(0.05)
        return {"loaded_rows": task_input["transform"]["rows"]}

    # 添加任务（通过依赖关系构成 DAG：extract -> transform -> load）
    extract_task = Task(TaskConfig(task_id="extract", func=extract))
    transform_task = Task(
        TaskConfig(task_id="transform", func=transform, dependencies=["extract"])
    )
    load_task = Task(
        TaskConfig(task_id="load", func=load, dependencies=["transform"])
    )

    workflow.add_task(extract_task)
    workflow.add_task(transform_task)
    workflow.add_task(load_task)

    print(f"  ✅ 节点数: {len(workflow.tasks)}")
    print(f"  执行顺序: {workflow.get_execution_order()}")
    print(f"  工作流校验: {'通过' if workflow.validate() else '失败'}")

    # 运行工作流
    print("\n运行工作流...")
    finished = await engine.run("data-processing", context={"source": "postgres"})
    print(f"\n  工作流状态: {finished.status.value}")

    # 输出各任务结果
    print("\n任务结果:")
    for task_id in ("extract", "transform", "load"):
        result = finished.results.get(task_id)
        if result is not None:
            print(
                f"  {task_id}: 状态={result.status.value}, "
                f"结果={result.result}, 耗时={result.duration:.3f}s"
            )

    # 引擎状态
    print(f"\n引擎中的工作流: {list(engine.workflows.keys())}")
    print(f"  运行中的工作流: {engine.running_workflows or '无'}")
    print(f"  获取工作流: {engine.get_workflow('data-processing').workflow_id}")
    print(f"  删除工作流: {engine.delete_workflow('data-processing')}")
    print(f"  删除后剩余: {list(engine.workflows.keys())}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_workflow())
