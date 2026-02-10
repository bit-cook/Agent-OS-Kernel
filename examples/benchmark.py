"""
性能基准测试

测试 Agent OS Kernel 的核心性能指标：
1. 上下文管理吞吐量
2. 调度器效率
3. 工具调用延迟
4. 并发处理能力
"""

import time
import statistics
from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.context_manager import ContextPage
from agent_os_kernel.core.scheduler import AgentScheduler
from agent_os_kernel.core.metrics import MetricsCollector


def benchmark_context_operations(iterations: int = 1000):
    """基准测试上下文操作"""
    print(f"\n{'='*60}")
    print(f"基准测试: 上下文操作 (迭代 {iterations} 次)")
    print(f"{'='*60}")
    
    manager = AgentOSKernel().context_manager
    
    # 测试添加页面
    times_add = []
    for i in range(iterations):
        start = time.perf_counter()
        page = manager.add_page(
            agent_pid="bench",
            content=f"Benchmark content {i}" * 10,
            tokens=10,
            importance_score=0.5
        )
        times_add.append(time.perf_counter() - start)
    
    avg_add = statistics.mean(times_add) * 1000  # ms
    p95_add = sorted(times_add)[int(iterations * 0.95)] * 1000
    
    print(f"添加页面 - 平均: {avg_add:.3f}ms, P95: {p95_add:.3f}ms")
    
    # 测试检索页面
    times_get = []
    for _ in range(iterations):
        start = time.perf_counter()
        manager.get_page(page.page_id)
        times_get.append(time.perf_counter() - start)
    
    avg_get = statistics.mean(times_get) * 1000
    p95_get = sorted(times_get)[int(iterations * 0.95)] * 1000
    
    print(f"检索页面 - 平均: {avg_get:.3f}ms, P95: {p95_get:.3f}ms")
    
    return {
        'add_avg': avg_add,
        'add_p95': p95_add,
        'get_avg': avg_get,
        'get_p95': p95_get
    }


def benchmark_scheduler(iterations: int = 500):
    """基准测试调度器"""
    print(f"\n{'='*60}")
    print(f"基准测试: 调度器 (迭代 {iterations} 次)")
    print(f"{'='*60}")
    
    scheduler = AgentScheduler()
    
    # 测试创建进程
    times_spawn = []
    for i in range(iterations):
        start = time.perf_counter()
        pid = scheduler.spawn(name=f"Bench{i}", task="Bench task")
        times_spawn.append(time.perf_counter() - start)
    
    avg_spawn = statistics.mean(times_spawn) * 1000
    p95_spawn = sorted(times_spawn)[int(iterations * 0.95)] * 1000
    
    print(f"创建进程 - 平均: {avg_spawn:.3f}ms, P95: {p95_spawn:.3f}ms")
    
    # 测试获取状态
    pid = scheduler.spawn(name="StatusTest", task="Test")
    times_status = []
    for _ in range(iterations):
        start = time.perf_counter()
        scheduler.get_process(pid)
        times_status.append(time.perf_counter() - start)
    
    avg_status = statistics.mean(times_status) * 1000
    p95_status = sorted(times_status)[int(iterations * 0.95)] * 1000
    
    print(f"获取状态 - 平均: {avg_status:.3f}ms, P95: {p95_status:.3f}ms")
    
    return {
        'spawn_avg': avg_spawn,
        'spawn_p95': p95_spawn,
        'status_avg': avg_status,
        'status_p95': p95_status
    }


def benchmark_concurrent_agents(num_agents: int = 100):
    """基准测试并发 Agent"""
    print(f"\n{'='*60}")
    print(f"基准测试: 并发 Agent ({num_agents} 个)")
    print(f"{'='*60}")
    
    kernel = AgentOSKernel()
    
    start = time.perf_counter()
    pids = []
    for i in range(num_agents):
        pid = kernel.spawn_agent(name=f"Agent{i}", task=f"Task {i}")
        pids.append(pid)
    elapsed = time.perf_counter() - start
    
    print(f"创建 {num_agents} 个 Agent: {elapsed*1000:.2f}ms")
    print(f"平均每个 Agent: {elapsed*1000/num_agents:.3f}ms")
    
    # 清理
    for pid in pids:
        kernel.terminate_agent(pid)
    
    return {'total_time': elapsed}


def benchmark_memory_usage(num_pages: int = 1000):
    """基准测试内存使用"""
    print(f"\n{'='*60}")
    print(f"基准测试: 内存使用 ({num_pages} 个页面)")
    print(f"{'='*60}")
    
    kernel = AgentOSKernel()
    
    # 添加页面
    start = time.perf_counter()
    for i in range(num_pages):
        kernel.context_manager.add_page(
            agent_pid="mem_test",
            content=f"Memory test content {i}" * 20,
            tokens=20,
            importance_score=i / num_pages
        )
    elapsed = time.perf_counter() - start
    
    stats = kernel.context_manager.get_memory_stats()
    
    print(f"添加 {num_pages} 个页面: {elapsed*1000:.2f}ms")
    print(f"总 Token 数: {stats['used_tokens']}")
    print(f"内存使用率: {stats['usage_percent']:.2f}%")
    
    return {
        'total_time': elapsed,
        'total_tokens': stats['used_tokens'],
        'usage_percent': stats['usage_percent']
    }


def benchmark_tool_calls(num_calls: int = 100):
    """基准测试工具调用"""
    print(f"\n{'='*60}")
    print(f"基准测试: 工具调用 ({num_calls} 次)")
    print(f"{'='*60}")
    
    kernel = AgentOSKernel()
    
    # 测试计算器工具
    times = []
    for i in range(num_calls):
        start = time.perf_counter()
        result = kernel.tool_registry.execute("calculator", expression=f"{i}+{i*2}")
        times.append(time.perf_counter() - start)
    
    avg = statistics.mean(times) * 1000
    p95 = sorted(times)[int(num_calls * 0.95)] * 1000
    p99 = sorted(times)[int(num_calls * 0.99)] * 1000
    
    print(f"计算器工具 - 平均: {avg:.3f}ms, P95: {p95:.3f}ms, P99: {p99:.3f}ms")
    
    return {
        'avg': avg,
        'p95': p95,
        'p99': p99
    }


def benchmark_metrics_collection(iterations: int = 1000):
    """基准测试指标收集"""
    print(f"\n{'='*60}")
    print(f"基准测试: 指标收集 ({iterations} 次)")
    print(f"{'='*60}")
    
    collector = MetricsCollector()
    
    # 记录数据
    start = time.perf_counter()
    for i in range(iterations):
        collector.record_cpu(50 + i % 50)
        collector.record_memory(60 + i % 30)
    elapsed = time.perf_counter() - start
    
    print(f"记录 {iterations} 条指标: {elapsed*1000:.2f}ms")
    print(f"平均每条: {elapsed*1000000/iterations:.2f}μs")
    
    # 读取数据
    start = time.perf_counter()
    for _ in range(iterations):
        collector.get_metrics()
    elapsed = time.perf_counter() - start
    
    print(f"读取 {iterations} 次指标: {elapsed*1000:.2f}ms")
    
    return {'total_time': elapsed}


def run_all_benchmarks():
    """运行所有基准测试"""
    print("\n" + "="*60)
    print("Agent OS Kernel 性能基准测试")
    print("="*60)
    
    results = {}
    
    results['context'] = benchmark_context_operations(iterations=1000)
    results['scheduler'] = benchmark_scheduler(iterations=500)
    results['concurrent'] = benchmark_concurrent_agents(num_agents=100)
    results['memory'] = benchmark_memory_usage(num_pages=1000)
    results['tool_calls'] = benchmark_tool_calls(num_calls=100)
    results['metrics'] = benchmark_metrics_collection(iterations=1000)
    
    print("\n" + "="*60)
    print("基准测试总结")
    print("="*60)
    
    print("\n核心操作延迟:")
    print(f"  上下文添加: {results['context']['add_avg']:.3f}ms")
    print(f"  上下文检索: {results['context']['get_avg']:.3f}ms")
    print(f"  进程创建: {results['scheduler']['spawn_avg']:.3f}ms")
    print(f"  状态查询: {results['scheduler']['status_avg']:.3f}ms")
    
    print("\n吞吐量:")
    print(f"  并发 Agent (100个): {results['concurrent']['total_time']*1000:.2f}ms")
    print(f"  内存页面 (1000个): {results['memory']['total_time']*1000:.2f}ms")
    
    print("\n工具性能:")
    print(f"  计算器调用: {results['tool_calls']['avg']:.3f}ms")
    
    return results


if __name__ == "__main__":
    run_all_benchmarks()
