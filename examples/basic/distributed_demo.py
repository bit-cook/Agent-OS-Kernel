"""
Agent-OS-Kernel 分布式演示

展示分布式功能的使用方法
"""

import asyncio

from agent_os_kernel.distributed import DistributedScheduler
from agent_os_kernel.distributed.scheduler import LoadBalancer


async def demo_distributed():
    """演示分布式功能"""
    print("=" * 60)
    print("Agent-OS-Kernel 分布式演示")
    print("=" * 60)
    
    # 创建分布式调度器
    scheduler = DistributedScheduler(
        node_id="demo-node-01",
        host="localhost",
        port=8001
    )
    await scheduler.start()
    
    # 注册节点（register_node 接收扁平参数，而非 NodeInfo 对象）
    print("\n注册节点...")
    ok1 = await scheduler.register_node(
        node_id="demo-node-01",
        hostname="localhost",
        port=8001,
        capabilities=["llm", "storage", "compute"],
        resources={"cpu": 8.0, "memory_gb": 32.0}
    )
    print(f"  demo-node-01: {'注册成功' if ok1 else '已存在'}")
    
    ok2 = await scheduler.register_node(
        node_id="demo-node-02",
        hostname="localhost",
        port=8002,
        capabilities=["llm", "compute"],
        resources={"cpu": 4.0, "memory_gb": 16.0}
    )
    print(f"  demo-node-02: {'注册成功' if ok2 else '已存在'}")
    
    # 获取集群状态（get_cluster_status 返回 dict）
    status = await scheduler.get_cluster_status()
    print(f"\n集群状态:")
    print(f"  调度器: {status['scheduler_id']}")
    print(f"  节点数: {status['total_nodes']}")
    print(f"  平均负载: {status['avg_load']:.2f}")
    print(f"  待处理任务: {status['pending_tasks']}")
    for node in status["nodes"]:
        print(f"    - {node['node_id']} @ {node['hostname']}:{node['port']} "
              f"负载={node['load']:.2f} 能力={node['capabilities']}")
    
    # 提交分布式任务（submit_task 需要 task_id + agent_config）
    print("\n提交任务...")
    task_id = await scheduler.submit_task(
        task_id="demo-task-001",
        agent_config={"name": "worker", "data": "test"},
        priority=1,
        preferred_nodes=["demo-node-01"]
    )
    print(f"  任务已提交: {task_id}")
    
    # 等待异步调度完成
    await asyncio.sleep(0.2)
    status = await scheduler.get_cluster_status()
    print(f"  调度后待处理任务: {status['pending_tasks']}")
    print(f"  节点负载: {[(n['node_id'], round(n['load'], 2)) for n in status['nodes']]}")
    
    # 心跳更新
    print("\n发送心跳...")
    await scheduler.receive_heartbeat("demo-node-02", load=0.3, agents_count=2)
    print("  demo-node-02 心跳已更新")
    
    # 负载均衡：按资源需求选择最佳节点
    balancer = LoadBalancer(scheduler)
    best = await balancer.get_best_node(requirements={"cpu": 8.0, "memory_gb": 16.0})
    print(f"\n满足 cpu>=8 的最佳节点: {best.node_id if best else 'None'}")
    
    health = await balancer.health_check()
    print(f"健康检查: {health}")
    
    # 故障转移：把 demo-node-01 下线，任务应转移到其他节点
    print("\n执行故障转移（demo-node-01 下线）...")
    await scheduler.unregister_node("demo-node-01")
    status = await scheduler.get_cluster_status()
    print(f"  剩余节点: {[n['node_id'] for n in status['nodes']]}")
    
    # 停止调度器
    await scheduler.stop()
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_distributed())
