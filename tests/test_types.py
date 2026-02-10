"""测试类型定义"""

import pytest
from datetime import datetime
from agent_os_kernel.core.types import (
    AgentState,
    PageType,
    StorageBackend,
    ToolCategory,
    ResourceQuota,
    ToolParameter,
    ToolDefinition,
    Checkpoint,
    AuditLog,
    PerformanceMetrics,
    PluginInfo,
)


class TestAgentState:
    """测试 AgentState"""
    
    def test_all_states_exist(self):
        assert AgentState.CREATED.value == "created"
        assert AgentState.READY.value == "ready"
        assert AgentState.RUNNING.value == "running"
        assert AgentState.WAITING.value == "waiting"
        assert AgentState.TERMINATED.value == "terminated"
        assert AgentState.ERROR.value == "error"
    
    def test_state_transitions(self):
        state = AgentState.CREATED
        assert state == AgentState.CREATED


class TestPageType:
    """测试 PageType"""
    
    def test_all_types(self):
        assert PageType.SYSTEM.value == "system"
        assert PageType.TOOLS.value == "tools"
        assert PageType.USER.value == "user"
        assert PageType.TASK.value == "task"
        assert PageType.MEMORY.value == "memory"
        assert PageType.WORKING.value == "working"
        assert PageType.CONTEXT.value == "context"


class TestStorageBackend:
    """测试 StorageBackend"""
    
    def test_backends(self):
        assert StorageBackend.MEMORY.value == "memory"
        assert StorageBackend.FILE.value == "file"
        assert StorageBackend.POSTGRESQL.value == "postgresql"
        assert StorageBackend.VECTOR.value == "vector"


class TestResourceQuota:
    """测试 ResourceQuota"""
    
    def test_default_values(self):
        quota = ResourceQuota()
        
        assert quota.max_tokens == 10000
        assert quota.max_iterations == 100
        assert quota.max_memory_percent == 50.0
        assert quota.max_cpu_percent == 80.0
        assert quota.max_concurrent_tools == 5
    
    def test_custom_values(self):
        quota = ResourceQuota(
            max_tokens=50000,
            max_iterations=500,
            max_memory_percent=80.0
        )
        
        assert quota.max_tokens == 50000
        assert quota.max_iterations == 500
        assert quota.max_memory_percent == 80.0
    
    def test_check_tokens(self):
        quota = ResourceQuota(max_tokens=10000)
        
        assert quota.check_tokens(5000) is True
        assert quota.check_tokens(10000) is True
        assert quota.check_tokens(15000) is False
    
    def test_check_iterations(self):
        quota = ResourceQuota(max_iterations=100)
        
        assert quota.check_iterations(50) is True
        assert quota.check_iterations(100) is True
        assert quota.check_iterations(150) is False
    
    def test_check_memory(self):
        quota = ResourceQuota(max_memory_percent=80.0)
        
        assert quota.check_memory(50.0) is True
        assert quota.check_memory(80.0) is True
        assert quota.check_memory(90.0) is False
    
    def test_unlimited_check(self):
        quota = ResourceQuota(max_tokens=0, max_iterations=0)
        
        assert quota.check_tokens(1000000) is True
        assert quota.check_iterations(1000000) is True


class TestToolParameter:
    """测试 ToolParameter"""
    
    def test_required_parameter(self):
        param = ToolParameter(
            name="expression",
            type="string",
            description="Math expression",
            required=True
        )
        
        assert param.name == "expression"
        assert param.required is True
    
    def test_optional_parameter(self):
        param = ToolParameter(
            name="precision",
            type="integer",
            description="Decimal places",
            required=False,
            default=2
        )
        
        assert param.required is False
        assert param.default == 2


class TestToolDefinition:
    """测试 ToolDefinition"""
    
    def test_create_definition(self):
        tool = ToolDefinition(
            name="calculator",
            description="Perform math calculations",
            category=ToolCategory.CALCULATOR,
            version="1.0.0",
            author="Agent-OS-Kernel"
        )
        
        "calculator"
        assert tool.category == ToolCategory.CALC assert tool.name ==ULATOR
        assert tool.version == "1.0.0"
    
    def test_to_dict(self):
        tool = ToolDefinition(
            name="test_tool",
            description="Test tool"
        )
        
        result = tool.to_dict()
        
        assert result['name'] == "test_tool"
        assert result['description'] == "Test tool"
        assert result['category'] == "custom"
        assert result['parameters'] == []


class TestCheckpoint:
    """测试 Checkpoint"""
    
    def test_create_checkpoint(self):
        checkpoint = Checkpoint(
            agent_pid="agent_123",
            agent_name="TestAgent",
            description="Test checkpoint"
        )
        
        assert checkpoint.agent_pid == "agent_123"
        assert checkpoint.checkpoint_id is not None
        assert checkpoint.timestamp is not None
    
    def test_checkpoint_state(self):
        checkpoint = Checkpoint(
            agent_pid="agent_123",
            state={"step": 5, "data": "test"}
        )
        
        assert checkpoint.state["step"] == 5
        assert checkpoint.state["data"] == "test"
    
    def test_to_dict(self):
        checkpoint = Checkpoint(
            agent_pid="agent_123",
            agent_name="Test"
        )
        
        result = checkpoint.to_dict()
        
        assert result['agent_pid'] == "agent_123"
        assert 'checkpoint_id' in result
        assert 'timestamp' in result


class TestAuditLog:
    """测试 AuditLog"""
    
    def test_create_audit_log(self):
        log = AuditLog(
            agent_pid="agent_123",
            action="tool_call",
            resource="calculator",
            result="success"
        )
        
        assert log.agent_pid == "agent_123"
        assert log.action == "tool_call"
        assert log.result == "success"
    
    def test_audit_log_to_dict(self):
        log = AuditLog(
            agent_pid="agent_123",
            action="test",
            resource="test",
            details={"key": "value"}
        )
        
        result = log.to_dict()
        
        assert result['details'] == {"key": "value"}
        assert result['duration_ms'] == 0.0


class TestPerformanceMetrics:
    """测试 PerformanceMetrics"""
    
    def test_create_metrics(self):
        metrics = PerformanceMetrics(
            cpu_usage=50.0,
            memory_usage=60.0,
            context_hit_rate=0.95,
            active_agents=5
        )
        
        assert metrics.cpu_usage == 50.0
        assert metrics.memory_usage == 60.0
        assert metrics.active_agents == 5
    
    def test_metrics_to_dict(self):
        metrics = PerformanceMetrics()
        
        result = metrics.to_dict()
        
        assert 'timestamp' in result
        assert result['cpu_usage'] == 0.0


class TestPluginInfo:
    """测试 PluginInfo"""
    
    def test_create_plugin_info(self):
        info = PluginInfo(
            name="test_plugin",
            version="1.0.0",
            author="test",
            description="Test plugin",
            entry_point="plugins.test",
            dependencies=["numpy"],
            hooks=["on_start", "on_end"]
        )
        
        assert info.name == "test_plugin"
        assert info.version == "1.0.0"
        assert len(info.dependencies) == 1
    
    def test_plugin_info_to_dict(self):
        info = PluginInfo(
            name="test",
            version="1.0",
            author="a",
            description="d",
            entry_point="e"
        )
        
        result = info.to_dict()
        
        assert result['name'] == "test"
        assert result['hooks'] == []
