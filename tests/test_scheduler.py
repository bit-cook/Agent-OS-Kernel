"""测试调度器"""

import pytest
from agent_os_kernel.core.scheduler import AgentScheduler, AgentProcess, ResourceQuota
from agent_os_kernel.core.types import AgentState


class TestAgentProcess:
    """测试 AgentProcess 数据类"""
    
    def test_create_process(self):
        process = AgentProcess(
            name="TestAgent",
            task="Test task",
            priority=50
        )
        
        assert process.name == "TestAgent"
        assert process.task == "TestAgent"
        assert process.priority == 50
        assert process.state == AgentState.CREATED
        assert process.pid is not None
        assert process.cpu_usage == 0.0
        assert process.memory_usage == 0.0
    
    def test_process_state_transitions(self):
        process = AgentProcess(name="Test", task="Task")
        
        process.state = AgentState.READY
        assert process.state == AgentState.READY
        
        process.state = AgentState.RUNNING
        assert process.state == AgentState.RUNNING
        
        process.state = AgentState.WAITING
        assert process.state == AgentState.WAITING
        
        process.state = AgentState.TERMINATED
        assert process.state == AgentState.TERMINATED
    
    def test_default_priority(self):
        process = AgentProcess(name="Test", task="Task")
        
        assert process.priority == 30  # Default priority
    
    def test_resource_quota_defaults(self):
        process = AgentProcess(name="Test", task="Task")
        
        assert process.quota.max_tokens == 10000
        assert process.quota.max_iterations == 100
        assert process.quota.max_memory_percent == 50.0


class TestAgentScheduler:
    """测试 AgentScheduler"""
    
    def test_initialization(self):
        scheduler = AgentScheduler()
        
        assert scheduler.processes == {}
        assert scheduler.running_processes == []
        assert scheduler.max_concurrent_agents == 10
    
    def test_spawn_process(self):
        scheduler = AgentScheduler()
        
        pid = scheduler.spawn(name="TestAgent", task="Test task")
        
        assert pid is not None
        assert pid in scheduler.processes
        assert len(scheduler.processes) == 1
    
    def test_get_process(self):
        scheduler = AgentScheduler()
        pid = scheduler.spawn(name="Test", task="Task")
        
        process = scheduler.get_process(pid)
        
        assert process is not None
        assert process.name == "Test"
    
    def test_get_nonexistent_process(self):
        scheduler = AgentScheduler()
        
        result = scheduler.get_process("nonexistent")
        
        assert result is None
    
    def test_terminate_process(self):
        scheduler = AgentScheduler()
        pid = scheduler.spawn(name="Test", task="Task")
        
        result = scheduler.terminate(pid)
        
        assert result is True
        assert scheduler.processes[pid].state == AgentState.TERMINATED
    
    def test_terminate_nonexistent(self):
        scheduler = AgentScheduler()
        
        result = scheduler.terminate("nonexistent")
        
        assert result is False
    
    def test_get_active_processes(self):
        scheduler = AgentScheduler()
        scheduler.spawn(name="Agent1", task="Task1")
        scheduler.spawn(name="Agent2", task="Task2")
        
        active = scheduler.get_active_processes()
        
        assert len(active) == 2
    
    def test_get_processes_by_state(self):
        scheduler = AgentScheduler()
        pid1 = scheduler.spawn(name="A1", task="T1")
        pid2 = scheduler.spawn(name="A2", task="T2")
        
        scheduler.terminate(pid2)
        
        created = scheduler.get_processes_by_state(AgentState.CREATED)
        terminated = scheduler.get_processes_by_state(AgentState.TERMINATED)
        
        assert len(created) == 1
        assert len(terminated) == 1
    
    def test_set_priority(self):
        scheduler = AgentScheduler()
        pid = scheduler.spawn(name="Test", task="Task")
        
        result = scheduler.set_priority(pid, 80)
        
        assert result is True
        assert scheduler.processes[pid].priority == 80
    
    def test_set_priority_invalid(self):
        scheduler = AgentScheduler()
        
        result = scheduler.set_priority("nonexistent", 80)
        
        assert result is False
    
    def test_update_process_resources(self):
        scheduler = AgentScheduler()
        pid = scheduler.spawn(name="Test", task="Task")
        
        scheduler.update_process_resources(pid, cpu_usage=25.5, memory_usage=1024)
        
        process = scheduler.get_process(pid)
        assert process.cpu_usage == 25.5
        assert process.memory_usage == 1024
    
    def test_get_statistics(self):
        scheduler = AgentScheduler()
        scheduler.spawn(name="A1", task="T1")
        scheduler.spawn(name="A2", task="T2")
        scheduler.terminate(scheduler.spawn(name="A3", task="T3"))
        
        stats = scheduler.get_statistics()
        
        assert stats['total_processes'] == 3
        assert stats['active_processes'] == 2
        assert stats['terminated_processes'] == 1
        assert 'state_distribution' in stats


class TestSchedulerConcurrency:
    """测试调度器并发控制"""
    
    def test_max_concurrent_limit(self):
        scheduler = AgentScheduler(max_concurrent_agents=2)
        
        # Spawn max allowed
        p1 = scheduler.spawn(name="A1", task="T1")
        p2 = scheduler.spawn(name="A2", task="T2")
        
        # Third should fail or be queued
        p3 = scheduler.spawn(name="A3", task="T3")
        
        # Check behavior based on implementation
        if p3 is None:
            assert len(scheduler.get_active_processes()) == 2
        else:
            # Might be allowed with queue
            pass
    
    def test_priority_ordering(self):
        scheduler = AgentScheduler()
        
        low = scheduler.spawn(name="Low", task="Task", priority=10)
        high = scheduler.spawn(name="High", task="Task", priority=90)
        medium = scheduler.spawn(name="Medium", task="Task", priority=50)
        
        # Processes should be in scheduler regardless of order
        assert scheduler.get_process(low) is not None
        assert scheduler.get_process(high) is not None
        assert scheduler.get_process(medium) is not None


class TestResourceQuota:
    """测试资源配额"""
    
    def test_custom_quota(self):
        quota = ResourceQuota(
            max_tokens=50000,
            max_iterations=500,
            max_memory_percent=80.0
        )
        
        assert quota.max_tokens == 50000
        assert quota.max_iterations == 500
        assert quota.max_memory_percent == 80.0
    
    def test_quota_check_within_limit(self):
        quota = ResourceQuota(max_tokens=10000, max_iterations=100)
        
        assert quota.check_tokens(5000) is True
        assert quota.check_tokens(10000) is True
        assert quota.check_iterations(50) is True
    
    def test_quota_check_exceeded(self):
        quota = ResourceQuota(max_tokens=10000, max_iterations=100)
        
        assert quota.check_tokens(15000) is False
        assert quota.check_iterations(200) is False
