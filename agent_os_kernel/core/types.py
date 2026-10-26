# -*- coding: utf-8 -*-
"""核心类型定义"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class AgentState(Enum):
    """Agent 状态"""
    CREATED = "created"      # 创建
    READY = "ready"          # 就绪
    RUNNING = "running"      # 运行中
    WAITING = "waiting"      # 等待
    TERMINATED = "terminated" # 已终止
    ERROR = "error"          # 错误


class PageType(Enum):
    """上下文页面类型"""
    SYSTEM = "system"        # 系统提示
    TOOLS = "tools"          # 工具定义
    USER = "user"           # 用户输入
    TASK = "task"           # 任务描述
    MEMORY = "memory"       # 长期记忆
    WORKING = "working"     # 工作内存
    CONTEXT = "context"     # 上下文历史


class StorageBackend(Enum):
    """存储后端类型"""
    MEMORY = "memory"
    FILE = "file"
    POSTGRESQL = "postgresql"
    VECTOR = "vector"


class ToolCategory(Enum):
    """工具类别"""
    CALCULATOR = "calculator"
    FILE_IO = "file_io"
    SEARCH = "search"
    NETWORK = "network"
    DATA = "data"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class ResourceQuota:
    """资源配额"""
    max_tokens: int = 10000
    max_iterations: int = 100
    max_memory_percent: float = 50.0
    max_cpu_percent: float = 80.0
    max_concurrent_tools: int = 5
    
    def check_tokens(self, tokens: int) -> bool:
        return self.max_tokens <= 0 or tokens <= self.max_tokens
    
    def check_iterations(self, iterations: int) -> bool:
        return self.max_iterations <= 0 or iterations <= self.max_iterations
    
    def check_memory(self, percent: float) -> bool:
        return self.max_memory_percent <= 0 or percent <= self.max_memory_percent


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum: List[Any] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory = ToolCategory.CUSTOM
    parameters: List[ToolParameter] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    license: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [p.__dict__ for p in self.parameters],
            "version": self.version,
            "author": self.author,
            "license": self.license
        }


@dataclass
class Checkpoint:
    """检查点"""
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_pid: str = ""
    agent_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    context_pages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "agent_pid": self.agent_pid,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "state": self.state,
            "context_pages": self.context_pages,
            "metadata": self.metadata
        }


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_pid: str = ""
    action: str = ""
    resource: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    result: str = ""
    duration_ms: float = 0.0
    ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_pid": self.agent_pid,
            "action": self.action,
            "resource": self.resource,
            "details": self.details,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "ip_address": self.ip_address
        }


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    context_hit_rate: float = 0.0
    swap_count: int = 0
    active_agents: int = 0
    queued_agents: int = 0
    tool_calls_per_second: float = 0.0
    average_response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "context_hit_rate": self.context_hit_rate,
            "swap_count": self.swap_count,
            "active_agents": self.active_agents,
            "queued_agents": self.queued_agents,
            "tool_calls_per_second": self.tool_calls_per_second,
            "average_response_time_ms": self.average_response_time_ms
        }


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    author: str
    description: str
    entry_point: str
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "hooks": self.hooks
        }
