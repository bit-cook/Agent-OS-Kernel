"""
Agent OS Kernel CLI Entry Point

Usage:
    python -m agent_os_kernel
    python -m agent_os_kernel --help

中文说明（逻辑风险提示）：
1) 该文件目前更像“demo 分发器”（根据 --demo 选择 examples 下的示例运行），
   并不是完整的内核管理 CLI。
2) 如果 pyproject.toml 的 console_scripts 指向 agent_os_kernel.__main__:main，
   那么用户安装后执行的入口会落到这里，而不是 agent_os_kernel/cli/main.py。
   这会造成：文档/预期的 init/create/list/serve 等命令不可用或行为不一致。
3) --version 的值若与包版本（pyproject.toml / AgentOSKernel.VERSION）不一致，
   会导致排障与发布版本对齐困难。
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Agent OS Kernel - Operating System for AI Agents"
    )
    parser.add_argument(
        "--version",
        action="version",
        # 注意：这里的版本号是硬编码字符串。
        # 若与 pyproject.toml 的 project.version（例如 0.2.0）或 kernel.py 的 AgentOSKernel.VERSION 不一致，
        # 会产生“对外显示版本”和“实际代码版本”冲突的逻辑问题。
        version="1.0.0"
    )
    parser.add_argument(
        "--demo",
        choices=["basic", "messaging", "workflow"],
        default="basic",
        help="Run demo"
    )
    
    args = parser.parse_args()
    
    if args.demo == "basic":
        from examples.basic_usage import main as demo_main
    elif args.demo == "messaging":
        from examples.multi_agent_demo import main as demo_main
    elif args.demo == "workflow":
        from examples.complete_workflow import main as demo_main

    # 注意：这里直接从 examples.* 导入 demo。
    # 这意味着：
    # - 运行入口依赖源码树中存在 examples 包/模块；
    # - 在某些打包/安装形态下 examples 可能不会随包发布，从而出现 ImportError。
    # 如需稳定的 CLI，需要明确将“demo runner”和“正式 CLI”分离并统一入口。
    
    try:
        import asyncio
        asyncio.run(demo_main())
    except ImportError:
        print("Demo module not found")
        print("Available demos: basic, messaging, workflow")
        sys.exit(1)


if __name__ == "__main__":
    main()
