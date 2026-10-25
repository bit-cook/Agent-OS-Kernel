#!/usr/bin/env python3

"""
CLI Demo - 统一 CLI 命令演示

演示 Agent-OS-Kernel 的唯一 CLI 实现（agent_os_kernel.cli.main）：
- doctor   - 环境自检
- status   - 查看内核状态
- create   - 创建 Agent
- list     - 列出 Agent
- demo     - 确定性演示运行

Usage:
    python cli_commands_demo.py

对应命令行：
    agent-os-kernel doctor
    agent-os-kernel status
    agent-os-kernel create -n "ResearchAssistant" -t "Research and summarize information"
    agent-os-kernel list
    agent-os-kernel demo --type checkpoint
"""

import os
import sys
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent_os_kernel.cli.main import CLI
from datetime import datetime, timezone


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    """主函数"""
    print_header("Agent-OS-Kernel CLI命令演示（统一 CLI）")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")

    cli = CLI()

    # 在临时目录中运行，避免污染用户工作区
    orig_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            print_header("1. doctor - 环境自检")
            result = cli.run(["doctor"])
            print(f"返回值: {result}")

            print_header("2. status - 查看内核状态")
            result = cli.run(["status"])
            print(f"返回值: {result}")

            print_header("3. create - 创建 Agent")
            result = cli.run([
                "create",
                "-n", "ResearchAssistant",
                "-t", "Research and summarize information",
                "-p", "60",
            ])
            print(f"返回值: {result}")

            print_header("4. list - 列出 Agent")
            result = cli.run(["list"])
            print(f"返回值: {result}")

            print_header("5. demo --type checkpoint - 确定性演示运行")
            result = cli.run(["demo", "--type", "checkpoint"])
            print(f"返回值: {result}")
        finally:
            os.chdir(orig_cwd)

    print_header("演示总结")
    print("""
本次演示涵盖了统一 CLI 的命令:

1. doctor  - 环境自检（顶层导入 / 内核实例化 / checkpoint 闭环 / 工具注册）
2. status  - 查看内核版本与 Agent 统计
3. create  - 创建 Agent（真实 spawn，状态持久化到 .agent-os-kernel-state.json）
4. list    - 列出 Agent（支持 --json）
5. demo    - 确定性 mock 运行（spawn → run → checkpoint → restore）

所有命令共享同一实现：agent-os-kernel <command>。
    """)

    print("=" * 60)
    print("  CLI命令演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
