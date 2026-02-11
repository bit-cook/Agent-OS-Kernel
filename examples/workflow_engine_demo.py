"""
Agent-OS-Kernel 工作流引擎演示

展示工作流引擎的使用方法
"""

from agent_os_kernel.core.workflow_engine import WorkflowEngine, WorkflowNode


async def demo_workflow():
    """演示工作流引擎"""
    print("=" * 60)
    print("Agent-OS-Kernel 工作流引擎演示")
    print("=" * 60)
    
    # 创建引擎
    engine = WorkflowEngine()
    
    # 创建工作流
    print("\n创建工作流...")
    workflow = await engine.create_workflow("data-processing")
    print(f"  ✅ 工作流: {workflow.workflow_id}")
    
    # 添加节点
    async def extract():
        return "extracted data"
    
    async def transform(data):
        return f"transformed: {data}"
    
    async def load(data):
        return f"loaded: {data}"
    
    # 添加节点
    extract_node = engine.add_node(workflow.id, "extract", extract)
    transform_node = engine.add_node(workflow.id, "transform", transform)
    load_node = engine.add_node(workflow.id, "load", load)
    
    print(f"  ✅ 节点数: {len(workflow.nodes)}")
    
    # 设置入口点
    engine.set_entry_point(workflow.id, "extract")
    print(f"  ✅ 入口点: extract")
    
    # 获取统计
    stats = engine.get_statistics()
    print(f"\n引擎统计:")
    print(f"  工作流数: {stats.total_workflows}")
    print(f"  节点数: {stats.total_nodes}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_workflow())
