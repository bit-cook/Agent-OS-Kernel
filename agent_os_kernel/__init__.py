# -*- coding: utf-8 -*-
"""
Agent OS Kernel - AI Agent 的操作系统内核

> 深受冯若航《AI Agent 的操作系统时刻》启发
> 试图填补 Agent 生态中"缺失的内核"

核心理念：
- LLM 是新 CPU，调度推理任务
- Context Window 是新 RAM，虚拟内存式管理
- Database 是新 Disk，PostgreSQL 五重角色
- Agent 是新 Process，真正的进程管理
- Tools 是设备驱动，Agent-Native CLI 标准
"""

__version__ = "1.0.0"
__author__ = "Bit-Cook"
__license__ = "MIT"

# ========== Core Types ==========
from .core.types import AgentState, ResourceQuota

# ========== Core Components ==========
from .core.context_manager import ContextManager
from .core.scheduler import AgentScheduler
from .core.storage import StorageManager
from .core.security import SecurityPolicy

# ========== Advanced Core ==========
from .core.agent_definition import AgentDefinition, TaskDefinition, CrewDefinition
from .core.checkpointer import Checkpointer
from .core.enhanced_memory import EnhancedMemory, MemoryType, ShortTermMemory, LongTermMemory
from .core.cost_tracker import CostTracker, CostLimit
from .core.observability import Observability, Event as ObsEvent
from .core.task_manager import TaskManager, TaskStatus
from .core.task_queue import TaskQueue, TaskPriority, TaskStatus as QueueTaskStatus
from .core.async_queue import AsyncQueue, Message, MessageStatus, QueueType as AsyncQueueType
from .core.batch_processor import BatchProcessor, Batch, AggregationType, SlidingWindowProcessor
from .core.stream_handler import StreamHandler, StreamType, StreamChunk, StreamManager
from .core.pipeline import Pipeline, PipelineItem, PipelineStage
from .core.cache_system import CacheSystem, CacheLevel, EvictionPolicy
from .core.lock_manager import LockManager, LockType, async_lock
from .core.state_machine import StateMachine, EventType
from .core.monitoring import Monitor, HealthStatus
from .core.worker import WorkerPool, WorkerStatus
from .core.config_manager import ConfigManager
from .core.workflow_engine import WorkflowEngine, Workflow, WorkflowNode
from .core.event_bus import Event as CoreEvent
from .core.circuit_breaker import CircuitBreaker, CircuitState, CircuitConfig
from .core.agent_registry import AgentRegistry, AgentMetadata
from .core.rate_limiter import RateLimiter, RateLimitConfig
from .core.agent_pool import AgentPool, PooledAgent
from .core.events import EventBus, Event, EventType, create_event_bus
from .core.state import StateManager, AgentState, create_state_manager
from .core.metrics import (
    MetricsCollector, Metric, MetricType,
    create_metrics_collector, timer
)
from .core.plugin_system import (
    PluginManager, BasePlugin, PluginState,
    create_plugin_manager
)

# ========== Tools ==========
from .tools.base import Tool, ToolResult, SimpleTool
from .tools.registry import ToolRegistry

# ========== LLM ==========
from .llm import LLMProviderFactory, LLMConfig

# ========== Communication ==========
from .agents.communication import (
    AgentMessenger, Message, MessageType,
    KnowledgeSharing, KnowledgePacket,
    GroupChatManager, ChatRole,
    AgentCollaboration, TaskType
)

# ========== Kernel ==========
from .kernel import AgentOSKernel, KernelStats

# ========== API ==========
from .api import AgentOSKernelAPI, run_server

__all__ = [
    # Version
    '__version__',
    '__author__',
    '__license__',
    
    # Types
    'AgentState',
    'ResourceQuota',
    
    # Core
    'ContextManager',
    'AgentScheduler',
    'StorageManager',
    'SecurityPolicy',
    
    # Advanced Core
    'EventBus',
    'Event',
    'EventType',
    'create_event_bus',
    'StateManager',
    'AgentState',
    'create_state_manager',
    'MetricsCollector',
    'Metric',
    'MetricType',
    'create_metrics_collector',
    'timer',
    'PluginManager',
    'BasePlugin',
    'PluginState',
    'create_plugin_manager',
    
    # Tools
    'Tool',
    'ToolResult',
    'SimpleTool',
    'ToolRegistry',
    
    # LLM
    'LLMProviderFactory',
    'LLMConfig',
    
    # Communication
    'AgentMessenger',
    'Message',
    'MessageType',
    'KnowledgeSharing',
    'KnowledgePacket',
    'GroupChatManager',
    'ChatRole',
    'AgentCollaboration',
    'TaskType',
    
    # Kernel
    'AgentOSKernel',
    'KernelStats',
    
    # Advanced Core - Agent Definition
    'AgentDefinition',
    'TaskDefinition',
    'Checkpointer',
    'EnhancedMemory',
    'MemoryType',
    'ShortTermMemory',
    'LongTermMemory',
    'CostTracker',
    'CostLimit',
    'Observability',
    'ObsEvent',
    'TaskManager',
    'TaskStatus',
    'TaskQueue',
    'TaskPriority',
    'ConfigManager',
    'AsyncQueue',
    'Message',
    'MessageStatus',
    'BatchProcessor',
    'AggregationType',
    'SlidingWindowProcessor',
    'StreamHandler',
    'StreamType',
    'Pipeline',
    'PipelineItem',
    'PipelineStage',
    'CacheSystem',
    'CacheLevel',
    'LockManager',
    'LockType',
    'StateMachine',
    'EventType',
    'Monitor',
    'HealthStatus',
    'WorkerPool',
    'WorkerStatus',
    'CrewDefinition',
    
    # Advanced Core - Workflow
    'WorkflowEngine',
    'Workflow',
    'WorkflowNode',
    
    # Advanced Core - Event
    'CoreEvent',
    
    # Advanced Core - Circuit Breaker
    'CircuitBreaker',
    'CircuitState',
    'CircuitConfig',
    
    # Advanced Core - Registry
    'AgentRegistry',
    'AgentMetadata',
    
    # Advanced Core - Rate Limiter
    'RateLimiter',
    'RateLimitConfig',
    
    # Advanced Core - Pool
    'AgentPool',
    'PooledAgent',
    
    # API
    'AgentOSKernelAPI',
    'run_server',
]
