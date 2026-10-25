# -*- coding: utf-8 -*-

"""
Agent-OS-Kernel - AI Agent 的操作系统内核

提供完整的 Agent 运行时基础设施。

顶层只导出稳定公共 API（黄金路径）：

    from agent_os_kernel import AgentOSKernel

    kernel = AgentOSKernel()
    agent_pid = kernel.spawn_agent(name="CodeAssistant", task="帮我写一个 Python 爬虫", priority=30)
    kernel.run(max_iterations=100)

内部实现位于 ``agent_os_kernel.core`` / ``agent_os_kernel.llm`` 等子包，
不属于稳定 API，可能在不增加主版本号的情况下调整。
"""

from .kernel import AgentOSKernel, KernelStats
from .core.types import AgentState
from .core.context_manager import ContextManager, ContextPage
from .core.storage import StorageManager, StorageBackend
from .core.security import SecurityPolicy, PermissionLevel
from .core.metrics import create_metrics_collector

__version__ = "0.2.0"
__author__ = "Bit-Cook"
__license__ = "MIT"

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    # 稳定公共 API（黄金路径）
    "AgentOSKernel",
    "KernelStats",
    "AgentState",
    "ContextManager",
    "ContextPage",
    "StorageManager",
    "StorageBackend",
    "SecurityPolicy",
    "PermissionLevel",
    "create_metrics_collector",
]
