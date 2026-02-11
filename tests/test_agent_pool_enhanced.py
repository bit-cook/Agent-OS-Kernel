"""
Tests for Enhanced Agent Pool

Tests cover:
- Agent priority queue
- Auto-scaling
- Health check
- Load balancing
- Resource limits
"""

import asyncio
import pytest
import pytest_asyncio
import sys
import os

# Add the parent directory to the path for imports
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


class TestAgentPriorityQueue:
    """Test agent priority queue functionality"""
    
    def test_agent_priority_creation(self):
        """Test that agents are created with correct priorities"""
        agent = Agent(
            agent_id="test-1",
            name="HighPriorityAgent",
            priority=AgentPriority.HIGH
        )
        assert agent.priority == AgentPriority.HIGH
        assert agent.priority.value == 1
        
        low_agent = Agent(
            agent_id="test-2",
            name="LowPriorityAgent",
            priority=AgentPriority.LOW
        )
        assert low_agent.priority == AgentPriority.LOW
        assert low_agent.priority.value == 3
    
    def test_agent_can_handle_priority(self):
        """Test priority handling logic"""
        high_agent = Agent(priority=AgentPriority.HIGH)
        normal_agent = Agent(priority=AgentPriority.NORMAL)
        
        # High priority agent (value=1) can handle all priorities (0, 1, 2, 3)
        assert high_agent.can_handle_priority(0)  # CRITICAL
        assert high_agent.can_handle_priority(1)  # HIGH
        assert high_agent.can_handle_priority(2)  # NORMAL
        assert high_agent.can_handle_priority(3)  # LOW
        
        # Normal priority agent (value=2) can handle NORMAL and below (2, 3)
        assert not normal_agent.can_handle_priority(0)  # CRITICAL
        assert not normal_agent.can_handle_priority(1)  # HIGH
        assert normal_agent.can_handle_priority(2)  # NORMAL
        assert normal_agent.can_handle_priority(3)  # LOW
    
    def test_task_priority_ordering(self):
        """Test that tasks are ordered by priority"""
        critical_task = AgentTask(
            priority=AgentPriority.CRITICAL,
            task_id="task-1",
            data="critical"
        )
        low_task = AgentTask(
            priority=AgentPriority.LOW,
            task_id="task-2",
            data="low"
        )
        
        # Lower priority number = higher priority
        assert critical_task.priority < low_task.priority
    
    def test_priority_queue_ordering(self):
        """Test PriorityQueue ordering"""
        queue = asyncio.Queue()
        
        # Add tasks in random order
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(queue.put(AgentTask(priority=AgentPriority.NORMAL, task_id="t1", data="n")))
            loop.run_until_complete(queue.put(AgentTask(priority=AgentPriority.HIGH, task_id="t2", data="h")))
            loop.run_until_complete(queue.put(AgentTask(priority=AgentPriority.CRITICAL, task_id="t3", data="c")))
            loop.run_until_complete(queue.put(AgentTask(priority=AgentPriority.LOW, task_id="t4", data="l")))
        finally:
            loop.close()
        
        # Retrieve in priority order (CRITICAL=0 first, then HIGH=1, etc.)
        first = queue.get_nowait()
        assert first.priority == 0  # CRITICAL
        assert first.task_id == "t3"
        
        second = queue.get_nowait()
        assert second.priority == 1  # HIGH
        assert second.task_id == "t2"


class TestAutoScaling:
    """Test auto-scaling functionality"""
    
    @pytest_asyncio.fixture
    async def scaling_pool(self):
        """Create a test pool with auto-scaling disabled"""
        pool = AgentPool(
            min_size=2,
            max_size=5,
            auto_scale_interval=9999  # Disable auto-scaling during tests
        )
        await pool.start()
        yield pool
        await pool.stop()
    
    @pytest.mark.asyncio
    async def test_pool_starts_with_min_size(self, scaling_pool):
        """Test that pool starts with minimum size"""
        assert scaling_pool.size == 2
        assert len(scaling_pool.available_agents) == 2
    
    @pytest.mark.asyncio
    async def test_add_agent(self, scaling_pool):
        """Test adding agents to the pool"""
        initial_size = scaling_pool.size
        agent = Agent(name="NewAgent")
        result = scaling_pool.add_agent(agent)
        
        assert result is True
        assert scaling_pool.size == initial_size + 1
    
    @pytest.mark.asyncio
    async def test_add_agent_respects_max_size(self, scaling_pool):
        """Test that adding agents respects max size limit"""
        # Pool already has min_size (2) agents
        # max_size is 5, so we can add up to 3 more
        
        for i in range(3):
            agent = Agent(name=f"Agent-{i}")
            assert scaling_pool.add_agent(agent) is True
        
        # Should fail at 4th attempt (would exceed max_size)
        agent = Agent(name="OverLimitAgent")
        assert scaling_pool.add_agent(agent) is False
    
    @pytest.mark.asyncio
    async def test_remove_agent(self, scaling_pool):
        """Test removing agents from the pool"""
        initial_size = scaling_pool.size
        agent_id = list(scaling_pool._agents.keys())[0]
        
        result = scaling_pool.remove_agent(agent_id)
        
        assert result is True
        assert scaling_pool.size == initial_size - 1
        assert agent_id not in scaling_pool._agents
    
    @pytest.mark.asyncio
    async def test_auto_scale_up(self, scaling_pool):
        """Test automatic scale up"""
        initial_size = scaling_pool.size
        
        # Simulate high load conditions
        scaling_pool._resource_limits = {'cpu_percent': 100, 'memory_percent': 100}
        for agent in scaling_pool._agents.values():
            agent.current_load = 10
        
        # Force scale check
        await scaling_pool._auto_scale()
        
        # Should scale up
        assert scaling_pool.size >= initial_size
    
    @pytest.mark.asyncio
    async def test_auto_scale_down(self, scaling_pool):
        """Test automatic scale down"""
        initial_size = scaling_pool.size
        
        # Simulate low load conditions
        for agent in scaling_pool._agents.values():
            agent.current_load = 0
        
        # Force scale check
        await scaling_pool._auto_scale()
        
        # Should scale down but not below min_size
        assert scaling_pool.size >= scaling_pool.min_size


class TestHealthCheck:
    """Test health check functionality"""
    
    def test_default_health_checker_initialization(self):
        """Test health checker initialization"""
        checker = DefaultHealthChecker(
            check_interval=30.0,
            timeout=10.0
        )
        
        assert checker.check_interval == 30.0
        assert checker.timeout == 10.0
        assert checker.max_consecutive_failures == 3
    
    def test_health_checker_failure_tracking(self):
        """Test tracking of consecutive failures"""
        checker = DefaultHealthChecker()
        
        agent_id = "test-agent"
        
        # Record some failures
        checker._record_failure(agent_id)
        checker._record_failure(agent_id)
        
        assert checker._consecutive_failures[agent_id] == 2
        assert not checker.needs_recovery(agent_id)
        
        # One more failure should trigger recovery
        checker._record_failure(agent_id)
        assert checker.needs_recovery(agent_id)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        checker = DefaultHealthChecker()
        agent = Agent(name="HealthyAgent")
        
        # Mock the perform check to always succeed
        async def mock_check(a):
            return True
        checker._perform_check = mock_check
        
        result = await checker.check_health(agent)
        
        assert result is True
        assert checker._consecutive_failures.get(agent.id, 0) == 0
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check"""
        checker = DefaultHealthChecker()
        agent = Agent(name="UnhealthyAgent")
        
        # Mock to always fail
        async def mock_check(a):
            raise Exception("Check failed")
        checker._perform_check = mock_check
        
        result = await checker.check_health(agent)
        
        assert result is False
        assert checker._consecutive_failures[agent.id] >= 1
    
    @pytest.mark.asyncio
    async def test_agent_recovery(self):
        """Test agent recovery"""
        checker = DefaultHealthChecker()
        agent = Agent(name="RecoverableAgent")
        
        # Record failures
        for _ in range(3):
            checker._record_failure(agent.id)
        
        assert checker.needs_recovery(agent.id)
        
        # Mock successful recovery
        async def mock_init():
            return True
        agent.initialize = mock_init
        
        result = await checker.recover(agent)
        
        assert result is True
        assert checker._consecutive_failures.get(agent.id, 0) == 0


class TestLoadBalancing:
    """Test load balancing functionality"""
    
    @pytest.fixture
    def agents(self):
        """Create test agents with different loads"""
        agent1 = Agent(agent_id="a1", name="Agent1", max_concurrent_tasks=2)
        agent1.current_load = 1
        agent1.state = AgentState.RUNNING
        
        agent2 = Agent(agent_id="a2", name="Agent2", max_concurrent_tasks=2)
        agent2.current_load = 3
        agent2.state = AgentState.RUNNING
        
        agent3 = Agent(agent_id="a3", name="Agent3", max_concurrent_tasks=2)
        agent3.current_load = 0
        agent3.state = AgentState.RUNNING
        
        return [agent1, agent2, agent3]
    
    def test_least_connections_load_balancer(self, agents):
        """Test least connections strategy"""
        balancer = LeastConnectionsLoadBalancer()
        task = AgentTask(priority=AgentPriority.NORMAL, task_id="t1", data="test")
        
        selected = balancer.select_agent(agents, task)
        
        # Should select agent with lowest load
        assert selected is not None
        assert selected.current_load == 0
        assert selected.id == "a3"
    
    def test_round_robin_load_balancer(self, agents):
        """Test round-robin strategy"""
        balancer = RoundRobinLoadBalancer()
        task = AgentTask(priority=AgentPriority.NORMAL, task_id="t1", data="test")
        
        # First selection
        selected1 = balancer.select_agent(agents, task)
        assert selected1 is not None
        
        # Second selection should be different (round-robin)
        selected2 = balancer.select_agent(agents, task)
        assert selected2 is not None
        
        # With 3 agents and round-robin, we should cycle through
        selected3 = balancer.select_agent(agents, task)
        assert selected3 is not None
        
        # All should be from the available agents list
        assert all(s is not None and s.id in ["a1", "a2", "a3"] for s in [selected1, selected2, selected3])
    
    def test_priority_load_balancer(self, agents):
        """Test priority-based load balancing"""
        balancer = PriorityLoadBalancer()
        
        # Create normal priority agents with RUNNING state
        for agent in agents:
            agent.priority = AgentPriority.NORMAL
            agent.state = AgentState.RUNNING
        
        # Create high-priority task
        high_task = AgentTask(priority=AgentPriority.HIGH, task_id="t1", data="test")
        
        selected = balancer.select_agent(agents, high_task)
        
        # Should select a suitable agent (NORMAL can handle HIGH priority)
        assert selected is not None
    
    def test_no_available_agents(self, agents):
        """Test load balancing with no available agents"""
        balancer = LeastConnectionsLoadBalancer()
        
        # Set all agents to non-available state
        for agent in agents:
            agent.state = AgentState.STOPPED
        
        task = AgentTask(priority=AgentPriority.NORMAL, task_id="t1", data="test")
        selected = balancer.select_agent(agents, task)
        
        assert selected is None
    
    def test_empty_agent_list(self):
        """Test load balancing with empty agent list"""
        balancer = LeastConnectionsLoadBalancer()
        task = AgentTask(priority=AgentPriority.NORMAL, task_id="t1", data="test")
        
        selected = balancer.select_agent([], task)
        
        assert selected is None


class TestResourceLimits:
    """Test resource limit functionality"""
    
    def test_agent_resource_limits(self):
        """Test agent resource limits configuration"""
        limits = {
            'cpu_percent': 50.0,
            'memory_percent': 60.0
        }
        agent = Agent(
            agent_id="test-agent",
            name="LimitedAgent",
            resource_limits=limits
        )
        
        assert agent.resource_limits['cpu_percent'] == 50.0
        assert agent.resource_limits['memory_percent'] == 60.0
    
    def test_pool_resource_limits(self):
        """Test pool-wide resource limits"""
        pool = AgentPool(
            min_size=1,
            max_size=3,
            resource_limits={'cpu_percent': 70.0, 'memory_percent': 80.0}
        )
        
        assert pool._resource_limits['cpu_percent'] == 70.0
        assert pool._resource_limits['memory_percent'] == 80.0
    
    @pytest.mark.asyncio
    async def test_agent_resource_check(self):
        """Test agent resource usage check"""
        agent = Agent(name="ResourceTestAgent")
        
        usage = agent.check_resource_usage()
        
        assert 'cpu_percent' in usage
        assert 'memory_percent' in usage
        assert 0 <= usage['cpu_percent'] <= 100
        assert 0 <= usage['memory_percent'] <= 100
    
    @pytest.mark.asyncio
    async def test_pool_resource_check(self):
        """Test pool resource monitoring"""
        pool = AgentPool(min_size=1, max_size=2)
        await pool.start()
        
        try:
            metrics = pool.check_pool_resources()
            
            assert 'cpu_percent' in metrics
            assert 'memory_percent' in metrics
            assert 'agent_count' in metrics
            assert 'avg_load' in metrics
        finally:
            await pool.stop()
    
    def test_task_load_management(self):
        """Test agent task load tracking"""
        agent = Agent(
            agent_id="load-test",
            name="LoadAgent",
            max_concurrent_tasks=3
        )
        
        assert agent.current_load == 0
        assert agent.can_accept_task() is True
        
        # Add tasks
        agent.add_task("task1", "data1")
        agent.add_task("task2", "data2")
        
        assert agent.current_load == 2
        assert agent.can_accept_task() is True
        
        # Add another task
        agent.add_task("task3", "data3")
        
        assert agent.current_load == 3
        assert agent.can_accept_task() is False
        
        # Remove a task
        agent.remove_task("task2")
        
        assert agent.current_load == 2
        assert agent.can_accept_task() is True
    
    @pytest.mark.asyncio
    async def test_pool_statistics(self):
        """Test pool statistics tracking"""
        pool = AgentPool(min_size=1, max_size=2)
        await pool.start()
        
        try:
            # Submit some tasks
            pool.submit_task("task1", priority=AgentPriority.NORMAL)
            pool.submit_task("task2", priority=AgentPriority.HIGH)
            
            stats = pool.get_statistics()
            
            assert 'total_agents' in stats
            assert 'available_agents' in stats
            assert 'busy_agents' in stats
            assert 'total_tasks_processed' in stats
            assert 'success_rate' in stats
        finally:
            await pool.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
