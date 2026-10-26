# Distributed Module - 分布式支持
#
# 注：node.py / registry.py 在原仓库中缺失（__init__ 引用了不存在的模块，
# 导致 `import agent_os_kernel.distributed` 直接 ModuleNotFoundError）。
# 现仅导出实际存在的 scheduler 与 migration。

from .scheduler import DistributedScheduler
from .migration import AgentMigration

__all__ = [
    'DistributedScheduler',
    'AgentMigration',
]
