"""
Agent-OS-Kernel 分布式演示

展示分布式功能的使用方法
"""

from agent_os_kernel.core.distributed import (
    DistributedManager,
    NodeInfo,
    CommunicationProtocol
)


async def demo_distributed():
    """演示分布式功能"""
    print("=" * 60)
    print("Agent-OS-Kernel 分布式演示")
    print("=" * 60)
    
    # 创建分布式管理器
    manager = DistributedManager(
        node_id="demo-node-01",
        protocol=CommunicationProtocol.GRPC
    )
    
    # 注册节点
    node = NodeInfo(
        node_id="demo-node-01",
        host="localhost",
        port=50051,
        capabilities=["llm", "storage", "compute"]
    )
    await manager.register_node(node)
    
    # 获取集群状态
    status = await manager.get_cluster_status()
    print(f"\n集群状态:")
    print(f"  节点数: {status.active_nodes}")
    print(f"  健康节点: {status.healthy_nodes}")
    
    # 分布式执行
    task_id = await manager.submit_task(
        task_name="demo-task",
        payload={"data": "test"},
        target_nodes=["demo-node-01"]
    )
    print(f"\n任务已提交: {task_id}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_distributed())
