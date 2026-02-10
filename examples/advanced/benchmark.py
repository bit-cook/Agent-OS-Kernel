"""
Performance Benchmarks

展示 Agent OS Kernel 的性能指标
"""

import time
from agent_os_kernel.core.metrics import (
    MetricsCollector,
    MetricType
)


def benchmark_context_switching():
    """上下文切换基准"""
    print("\n" + "=" * 50)
    print("Benchmark: Context Switching")
    print("=" * 50)
    
    metrics = MetricsCollector()
    
    # 模拟上下文切换
    iterations = 1000
    
    start = time.time()
    for i in range(iterations):
        metrics.counter("context_switches_total")
        metrics.counter("context_pages_total")
    elapsed = time.time() - start
    
    print(f"  Iterations: {iterations}")
    print(f"  Time: {elapsed:.4f}s")
    print(f"  Rate: {iterations/elapsed:.0f} ops/sec")
    print(f"  Metrics: {metrics.get_stats()['total_metrics']}")
    
    return elapsed


def benchmark_agent_spawning():
    """Agent 创建基准"""
    print("\n" + "=" * 50)
    print("Benchmark: Agent Spawning")
    print("=" * 50)
    
    metrics = MetricsCollector()
    
    # 模拟 Agent 创建
    iterations = 100
    
    start = time.time()
    for i in range(iterations):
        metrics.counter("agent_started_total")
    elapsed = time.time() - start
    
    print(f"  Iterations: {iterations}")
    print(f"  Time: {elapsed:.4f}s")
    print(f"  Rate: {iterations/elapsed:.1f} agents/sec")
    
    return elapsed


def benchmark_message_passing():
    """消息传递基准"""
    print("\n" + "=" * 50)
    print("Benchmark: Message Passing")
    print("=" * 50)
    
    from agent_os_kernel.agents.communication import create_messenger
    import asyncio
    
    async def run():
        messenger = create_messenger()
        
        await messenger.register_agent("sender", "Sender")
        await messenger.register_agent("receiver", "Receiver")
        
        # 发送消息
        iterations = 500
        
        start = time.time()
        for i in range(iterations):
            from agent_os_kernel.agents.communication import Message, MessageType
            msg = Message.create(
                msg_type=MessageType.CHAT,
                sender_id="sender",
                sender_name="Sender",
                content=f"Message {i}",
                receiver_id="receiver"
            )
            await messenger.send(msg)
        
        elapsed = time.time() - start
        print(f"  Iterations: {iterations}")
        print(f"  Time: {elapsed:.4f}s")
        print(f"  Rate: {iterations/elapsed:.0f} msgs/sec")
        
        return elapsed
    
    return asyncio.run(run())


def benchmark_knowledge_retrieval():
    """知识检索基准"""
    print("\n" + "=" * 50)
    print("Benchmark: Knowledge Retrieval")
    print("=" * 50)
    
    from agent_os_kernel.agents.communication import create_knowledge_sharing
    import asyncio
    
    async def run():
        knowledge = create_knowledge_sharing()
        
        from agent_os_kernel.agents.communication.knowledge_share import (
            KnowledgePacket, KnowledgeType
        )
        
        # 添加知识
        for i in range(100):
            packet = KnowledgePacket.create(
                knowledge_type=KnowledgeType.FACT,
                title=f"Knowledge {i}",
                content=f"This is knowledge item number {i}",
                source_agent="test",
                source_task="benchmark",
                confidence=0.8,
                tags=["test", f"tag{i % 10}"]
            )
            await knowledge.share(packet)
        
        # 检索
        iterations = 50
        
        start = time.time()
        for i in range(iterations):
            results = await knowledge.retrieve(f"tag{i % 10}", limit=10)
        
        elapsed = time.time() - start
        
        print(f"  Knowledge items: 100")
        print(f"  Iterations: {iterations}")
        print(f"  Time: {elapsed:.4f}s")
        print(f"  Rate: {iterations/elapsed:.1f} queries/sec")
        
        return elapsed
    
    return asyncio.run(run())


def main():
    print("=" * 60)
    print("🚀 Agent OS Kernel Performance Benchmarks")
    print("=" * 60)
    
    results = {}
    
    # 运行基准测试
    try:
        results["context_switching"] = benchmark_context_switching()
    except Exception as e:
        print(f"Context switching benchmark failed: {e}")
    
    try:
        results["agent_spawning"] = benchmark_agent_spawning()
    except Exception as e:
        print(f"Agent spawning benchmark failed: {e}")
    
    try:
        results["message_passing"] = benchmark_message_passing()
    except Exception as e:
        print(f"Message passing benchmark failed: {e}")
    
    try:
        results["knowledge_retrieval"] = benchmark_knowledge_retrieval()
    except Exception as e:
        print(f"Knowledge retrieval benchmark failed: {e}")
    
    # 汇总
    print("\n" + "=" * 60)
    print("📊 Benchmark Summary")
    print("=" * 60)
    
    for name, elapsed in results.items():
        rate = 1 / elapsed if elapsed > 0 else 0
        print(f"  {name:20s}: {rate:>10.1f} ops/sec")
    
    print("\n" + "=" * 60)
    print("✅ Benchmarks Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
