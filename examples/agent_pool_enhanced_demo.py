"""
Agent Pool Enhanced Demo

Demonstrates:
- Priority queue functionality
- Auto-scaling capabilities
- Health check system
- Load balancing strategies
- Resource limit enforcement
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel.core.agent_pool_enhanced import (
    Agent,
    AgentPool,
    AgentState,
    AgentPriority,
    AgentTask,
    DefaultHealthChecker,
    LeastConnectionsLoadBalancer,
    RoundRobinLoadBalancer,
    PriorityLoadBalancer,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_priority_queue():
    """Demonstrate priority queue functionality"""
    logger.info("=" * 60)
    logger.info("DEMO: Agent Priority Queue")
    logger.info("=" * 60)
    
    # Create agents with different priorities
    critical_agent = Agent(
        name="CriticalAgent",
        priority=AgentPriority.CRITICAL,
        max_concurrent_tasks=2
    )
    normal_agent = Agent(
        name="NormalAgent",
        priority=AgentPriority.NORMAL,
        max_concurrent_tasks=2
    )
    low_agent = Agent(
        name="LowAgent",
        priority=AgentPriority.LOW,
        max_concurrent_tasks=2
    )
    
    logger.info(f"Created agents:")
    logger.info(f"  - CriticalAgent: priority {critical_agent.priority}")
    logger.info(f"  - NormalAgent: priority {normal_agent.priority}")
    logger.info(f"  - LowAgent: priority {low_agent.priority}")
    
    # Test priority handling
    logger.info("\n--- Priority Handling Test ---")
    
    # Critical agent can handle all priorities
    logger.info("Critical agent can handle CRITICAL tasks: %s", 
                critical_agent.can_handle_priority(AgentPriority.CRITICAL.value))
    logger.info("Critical agent can handle LOW tasks: %s", 
                critical_agent.can_handle_priority(AgentPriority.LOW.value))
    
    # Low agent can only handle LOW and below
    logger.info("Low agent can handle CRITICAL tasks: %s", 
                low_agent.can_handle_priority(AgentPriority.CRITICAL.value))
    logger.info("Low agent can handle LOW tasks: %s", 
                low_agent.can_handle_priority(AgentPriority.LOW.value))
    
    # Create priority queue with tasks
    logger.info("\n--- Task Priority Ordering ---")
    task_queue = asyncio.Queue()
    
    # Add tasks in random order
    await task_queue.put(AgentTask(priority=AgentPriority.NORMAL, task_id="TN", data="Normal Task"))
    await task_queue.put(AgentTask(priority=AgentPriority.HIGH, task_id="TH", data="High Task"))
    await task_queue.put(AgentTask(priority=AgentPriority.CRITICAL, task_id="TC", data="Critical Task"))
    await task_queue.put(AgentTask(priority=AgentPriority.LOW, task_id="TL", data="Low Task"))
    
    logger.info("Tasks added in order: NORMAL, HIGH, CRITICAL, LOW")
    logger.info("Retrieving tasks by priority:")
    
    while not task_queue.empty():
        task = task_queue.get_nowait()
        logger.info("  - %s (priority: %s)", task.task_id, AgentPriority(task.priority).name)
    
    logger.info("\n✓ Priority queue demo complete\n")


async def demo_auto_scaling():
    """Demonstrate auto-scaling functionality"""
    logger.info("=" * 60)
    logger.info("DEMO: Auto-Scaling")
    logger.info("=" * 60)
    
    pool = AgentPool(
        min_size=2,
        max_size=5,
        auto_scale_interval=1.0  # Check every second for demo
    )
    
    await pool.start()
    logger.info(f"Pool started with {pool.size} agents (min={pool.min_size}, max={pool.max_size})")
    
    # Initial state
    logger.info("\n--- Initial State ---")
    stats = pool.get_statistics()
    logger.info(f"Agent count: {stats['total_agents']}")
    logger.info(f"Available agents: {stats['available_agents']}")
    
    # Simulate high load
    logger.info("\n--- Simulating High Load ---")
    for agent in pool._agents.values():
        agent.current_load = 5
        logger.info(f"Agent {agent.name}: load = {agent.current_load}")
    
    # Trigger scale up
    logger.info("\nTriggering scale-up check...")
    await pool._auto_scale()
    logger.info(f"After scale-up: {pool.size} agents")
    
    # Simulate low load
    logger.info("\n--- Simulating Low Load ---")
    for agent in pool._agents.values():
        agent.current_load = 0
        logger.info(f"Agent {agent.name}: load = {agent.current_load}")
    
    # Trigger scale down
    logger.info("\nTriggering scale-down check...")
    await pool._auto_scale()
    logger.info(f"After scale-down: {pool.size} agents (minimum: {pool.min_size})")
    
    await pool.stop()
    logger.info("\n✓ Auto-scaling demo complete\n")


async def demo_health_check():
    """Demonstrate health check system"""
    logger.info("=" * 60)
    logger.info("DEMO: Health Check System")
    logger.info("=" * 60)
    
    # Create custom health checker
    health_checker = DefaultHealthChecker(
        check_interval=5.0,
        timeout=2.0
    )
    
    pool = AgentPool(
        min_size=2,
        max_size=3,
        health_checker=health_checker,
        auto_scale_interval=9999
    )
    
    await pool.start()
    
    logger.info("\n--- Pool Health Status ---")
    metrics = pool.check_pool_resources()
    logger.info("CPU Usage: %.1f%%", metrics['cpu_percent'])
    logger.info("Memory Usage: %.1f%%", metrics['memory_percent'])
    logger.info("Average Load: %.2f", metrics['avg_load'])
    
    # Add a test agent
    test_agent = Agent(name="TestHealthAgent")
    pool.add_agent(test_agent)
    logger.info(f"\nAdded test agent: {test_agent.name}")
    
    # Simulate failures
    logger.info("\n--- Simulating Health Check Failures ---")
    
    # Mock health check to fail
    original_check = health_checker._perform_check
    health_checker._perform_check = asyncio.coroutine(lambda a: False)
    
    # Run health checks
    await pool._health_check()
    
    failures = health_checker._consecutive_failures.get(test_agent.id, 0)
    logger.info(f"Agent {test_agent.name} consecutive failures: {failures}")
    logger.info(f"Needs recovery: {health_checker.needs_recovery(test_agent.id)}")
    
    # Restore and demonstrate recovery
    logger.info("\n--- Demonstrating Recovery ---")
    health_checker._perform_check = asyncio.coroutine(lambda a: True)
    
    # Simulate recovery
    original_init = test_agent.initialize
    test_agent.initialize = asyncio.coroutine(lambda: True)
    
    success = await health_checker.recover(test_agent)
    logger.info(f"Recovery successful: {success}")
    logger.info(f"Failures after recovery: {health_checker._consecutive_failures.get(test_agent.id, 0)}")
    
    await pool.stop()
    logger.info("\n✓ Health check demo complete\n")


async def demo_load_balancing():
    """Demonstrate load balancing strategies"""
    logger.info("=" * 60)
    logger.info("DEMO: Load Balancing Strategies")
    logger.info("=" * 60)
    
    # Create test agents with different loads
    agents = [
        Agent(agent_id="a1", name="Server-1", max_concurrent_tasks=10),
        Agent(agent_id="a2", name="Server-2", max_concurrent_tasks=10),
        Agent(agent_id="a3", name="Server-3", max_concurrent_tasks=10),
    ]
    
    # Set different loads
    agents[0].current_load = 8
    agents[1].current_load = 3
    agents[2].current_load = 1
    
    logger.info("Initial agent loads:")
    for agent in agents:
        logger.info(f"  - {agent.name}: {agent.current_load} tasks")
    
    # Test Least Connections
    logger.info("\n--- Least Connections Strategy ---")
    lb_least = LeastConnectionsLoadBalancer()
    task = AgentTask(priority=AgentPriority.NORMAL, task_id="task1", data="test")
    
    selected = lb_least.select_agent(agents, task)
    logger.info(f"Least Connections selected: {selected.name} (load: {selected.current_load})")
    
    # Test Round Robin
    logger.info("\n--- Round Robin Strategy ---")
    lb_rr = RoundRobinLoadBalancer()
    
    logger.info("Selecting 4 tasks in round-robin:")
    for i in range(4):
        selected = lb_rr.select_agent(agents, task)
        logger.info(f"  Task {i+1}: {selected.name}")
    
    # Test Priority-based
    logger.info("\n--- Priority-based Strategy ---")
    
    # Create mixed priority agents
    priority_agents = [
        Agent(agent_id="p1", name="Priority-High", priority=AgentPriority.HIGH),
        Agent(agent_id="p2", name="Priority-Normal", priority=AgentPriority.NORMAL),
        Agent(agent_id="p3", name="Priority-Low", priority=AgentPriority.LOW),
    ]
    priority_agents[0].current_load = 1
    priority_agents[1].current_load = 1
    priority_agents[2].current_load = 1
    
    lb_priority = PriorityLoadBalancer()
    
    high_task = AgentTask(priority=AgentPriority.HIGH, task_id="task-h", data="high")
    low_task = AgentTask(priority=AgentPriority.LOW, task_id="task-l", data="low")
    
    selected_high = lb_priority.select_agent(priority_agents, high_task)
    selected_low = lb_priority.select_agent(priority_agents, low_task)
    
    logger.info(f"High-priority task assigned to: {selected_high.name}")
    logger.info(f"Low-priority task assigned to: {selected_low.name}")
    
    logger.info("\n✓ Load balancing demo complete\n")


async def demo_resource_limits():
    """Demonstrate resource limit enforcement"""
    logger.info("=" * 60)
    logger.info("DEMO: Resource Limits")
    logger.info("=" * 60)
    
    # Create pool with strict resource limits
    pool = AgentPool(
        min_size=1,
        max_size=3,
        resource_limits={
            'cpu_percent': 50.0,
            'memory_percent': 60.0
        }
    )
    
    logger.info(f"Pool resource limits:")
    logger.info(f"  CPU: {pool._resource_limits['cpu_percent']}%")
    logger.info(f"  Memory: {pool._resource_limits['memory_percent']}%")
    
    await pool.start()
    
    # Check agent resources
    logger.info("\n--- Agent Resource Usage ---")
    for agent in pool._agents.values():
        usage = agent.check_resource_usage()
        within_limits = agent.is_within_limits()
        logger.info(f"{agent.name}:")
        logger.info(f"  CPU: {usage['cpu_percent']:.1f}%")
        logger.info(f"  Memory: {usage['memory_percent']:.1f}%")
        logger.info(f"  Within limits: {within_limits}")
    
    # Test task load limits
    logger.info("\n--- Task Load Management ---")
    agent = list(pool._agents.values())[0]
    
    logger.info(f"Max concurrent tasks: {agent.max_concurrent_tasks}")
    logger.info(f"Current load: {agent.current_load}")
    
    # Add tasks up to limit
    for i in range(agent.max_concurrent_tasks):
        success = agent.add_task(f"task-{i}", f"data-{i}")
        logger.info(f"  Adding task-{i}: {'success' if success else 'failed'}")
    
    logger.info(f"Final load: {agent.current_load}")
    logger.info(f"Can accept more: {agent.can_accept_task()}")
    
    # Try to add one more
    extra_success = agent.add_task("task-extra", "data")
    logger.info(f"  Adding extra task: {'success' if extra_success else 'failed'}")
    
    # Pool statistics
    logger.info("\n--- Pool Statistics ---")
    stats = pool.get_statistics()
    logger.info(f"Total agents: {stats['total_agents']}")
    logger.info(f"Available: {stats['available_agents']}")
    logger.info(f"Success rate: {stats['success_rate']:.2%}")
    logger.info(f"Uptime: {stats['uptime_seconds']:.1f}s")
    
    await pool.stop()
    logger.info("\n✓ Resource limits demo complete\n")


async def run_all_demos():
    """Run all demonstrations"""
    logger.info("\n" + "=" * 60)
    logger.info("AGENT POOL ENHANCED - FULL DEMONSTRATION")
    logger.info("=" * 60 + "\n")
    
    await demo_priority_queue()
    await demo_auto_scaling()
    await demo_health_check()
    await demo_load_balancing()
    await demo_resource_limits()
    
    logger.info("=" * 60)
    logger.info("ALL DEMOS COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_demos())
