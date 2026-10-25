# -*- coding: utf-8 -*-
"""CLI Module - 命令行接口

唯一 CLI 实现位于 ``agent_os_kernel.cli.main``（历史遗留的第二套实现
commands.py 已按审计决议移除）。
"""

from .main import CLI, main

__all__ = [
    "CLI",
    "main",
]
