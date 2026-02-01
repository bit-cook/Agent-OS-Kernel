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

五大子系统：
1. 内存管理（Context Manager）- 虚拟内存、KV-Cache 优化、内存层次
2. 外存管理（Storage）- PostgreSQL 五重角色（记忆、状态、向量、协调、审计）
3. 进程管理（Scheduler）- 抢占式调度、Checkpoint/恢复、IPC
4. I/O 管理（Tools）- Agent-Native CLI 标准
5. 安全与可观测性（Security）- 沙箱、审计日志、决策追溯

使用示例：
    >>> from agent_os_kernel import AgentOSKernel, StorageManager
    >>> 
    >>> # 使用 PostgreSQL 作为存储后端（五重角色）
    >>> storage = StorageManager.from_postgresql("postgresql://...")
    >>> kernel = AgentOSKernel(storage_backend=storage.backend)
    >>> 
    >>> # 创建 Agent
    >>> agent_pid = kernel.spawn_agent("Assistant", "Help me with coding")
    >>> 
    >>> # 运行内核
    >>> kernel.run(max_iterations=10)
    >>> 
    >>> # 创建检查点（状态持久化）
    >>> checkpoint_id = kernel.create_checkpoint(agent_pid)
    >>> 
    >>> # 从检查点恢复
    >>> new_pid = kernel.restore_checkpoint(checkpoint_id)
"""

__version__ = "0.2.0"
__author__ = "Bit-Cook"
__license__ = "MIT"

# 核心数据结构和枚举
from .core.types import (
    AgentState,
    ResourceQuota,
)

# 核心组件
from .core.context_manager import (
    ContextManager,
    ContextPage,
    PageStatus,
    MemoryHierarchy,
    KVCacheOptimizer,
)
from .core.scheduler import (
    AgentScheduler,
    AgentProcess,
    IPCChannel,
)
from .core.storage import (
    StorageManager,
    StorageBackend,
    PostgreSQLStorage,
    MemoryStorage,
)
from .core.security import (
    SandboxManager,
    SecurityPolicy,
    PermissionLevel,
)

# 工具系统
from .tools.base import (
    Tool,
    ToolResult,
    ToolErrorCode,
    ToolParameter,
    SimpleTool,
    CLITool,
    AgentNativeCLITool,
)
from .tools.registry import ToolRegistry

# 主内核
from .kernel import AgentOSKernel, KernelStats

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__license__",
    
    # 核心类型
    "AgentState",
    "ResourceQuota",
    "ToolErrorCode",
    
    # 上下文管理（虚拟内存）
    "ContextManager",
    "ContextPage",
    "PageStatus",
    "MemoryHierarchy",
    "KVCacheOptimizer",
    
    # 进程调度
    "AgentScheduler",
    "AgentProcess",
    "IPCChannel",
    
    # 存储（PostgreSQL 五重角色）
    "StorageManager",
    "StorageBackend",
    "PostgreSQLStorage",
    "MemoryStorage",
    
    # 安全
    "SandboxManager",
    "SecurityPolicy",
    "PermissionLevel",
    
    # 工具系统（Agent-Native CLI）
    "Tool",
    "ToolResult",
    "ToolParameter",
    "SimpleTool",
    "CLITool",
    "AgentNativeCLITool",
    "ToolRegistry",
    
    # 主内核
    "AgentOSKernel",
    "KernelStats",
]
