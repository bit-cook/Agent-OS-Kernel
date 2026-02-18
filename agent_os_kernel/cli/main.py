# -*- coding: utf-8 -*-
"""CLI - 命令行接口

提供完整的命令行工具，支持:
- Agent 创建和管理
- 任务执行
- 项目初始化
- 配置管理
- 监控和调试
"""

import argparse
import sys
import os
from typing import Optional
from datetime import datetime
from datetime import timezone, timezone

# 逻辑风险提示：
# - 这里出现重复导入（timezone, timezone），属于明显的代码瑕疵；通常不会影响运行，但会影响静态检查与可维护性。
# - 本文件实现的 CLI 与 agent_os_kernel/__main__.py 的“demo runner”入口存在职责冲突：
#   如果对外 console_scripts 绑定到 __main__.py，这里这些命令实际不会被用户用到。


class CLI:
    """命令行接口"""
    
    def __init__(self):
        self.kernel = None
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建参数解析器"""
        parser = argparse.ArgumentParser(
            description="Agent OS Kernel CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  agent-os init                    # 初始化项目
  agent-os create -n "Researcher" -t "Research AI"  # 创建 Agent
  agent-os list                    # 列出所有 Agent
  agent-os serve --port 8000       # 启动 API 服务器
            """
        )
        
        parser.add_argument("--config", "-c", default="config.yaml")
        parser.add_argument("--verbose", "-v", action="store_true")
        
        subparsers = parser.add_subparsers(dest="command", title="commands")
        
        self._add_init_command(subparsers)
        self._add_create_command(subparsers)
        self._add_list_command(subparsers)
        self._add_delete_command(subparsers)
        self._add_demo_command(subparsers)
        self._add_serve_command(subparsers)
        self._add_status_command(subparsers)
        
        return parser
    
    def _add_init_command(self, subparsers):
        cmd = subparsers.add_parser("init", help="初始化项目")
        cmd.add_argument("--force", "-f", action="store_true")
        cmd.add_argument("--template", "-t", default="basic")
    
    def _add_create_command(self, subparsers):
        cmd = subparsers.add_parser("create", help="创建 Agent")
        cmd.add_argument("--name", "-n", required=True)
        cmd.add_argument("--task", "-t", required=True)
        cmd.add_argument("--model", "-m", default="gpt-4o")
        cmd.add_argument("--priority", "-p", type=int, default=50)
    
    def _add_list_command(self, subparsers):
        cmd = subparsers.add_parser("list", help="列出 Agent")
        cmd.add_argument("--json", action="store_true")
    
    def _add_delete_command(self, subparsers):
        cmd = subparsers.add_parser("delete", help="删除 Agent")
        cmd.add_argument("--agent-id", "-a", required=True)
    
    def _add_demo_command(self, subparsers):
        cmd = subparsers.add_parser("demo", help="运行演示")
        cmd.add_argument("--type", "-t", default="basic")
    
    def _add_serve_command(self, subparsers):
        cmd = subparsers.add_parser("serve", help="启动服务器")
        cmd.add_argument("--host", "-H", default="0.0.0.0")
        cmd.add_argument("--port", "-p", type=int, default=8000)
    
    def _add_status_command(self, subparsers):
        cmd = subparsers.add_parser("status", help="显示状态")
        cmd.add_argument("--json", action="store_true")
    
    def run(self, args=None):
        """运行 CLI"""
        parsed = self.parser.parse_args(args)
        
        if not parsed.command:
            self.parser.print_help()
            return 0
        
        return self._execute_command(parsed)
    
    def _execute_command(self, args):
        """执行命令"""
        command = args.command
        
        handlers = {
            "init": self._cmd_init,
            "create": self._cmd_create,
            "list": self._cmd_list,
            "delete": self._cmd_delete,
            "demo": self._cmd_demo,
            "serve": self._cmd_serve,
            "status": self._cmd_status,
        }
        
        handler = handlers.get(command)
        return handler(args) if handler else 1
    
    def _cmd_init(self, args):
        """初始化项目"""
        import yaml
        config = {
            "kernel": {"max_agents": 10},
            "llm": {"default_provider": "mock"}
        }
        with open("config.yaml", "w") as f:
            yaml.dump(config, f)
        print("项目初始化完成!")
        return 0
    
    def _cmd_create(self, args):
        """创建 Agent"""
        from ..core import AgentOSKernel
        kernel = AgentOSKernel()
        agent_id = kernel.spawn_agent(name=args.name, task=args.task)
        print(f"Agent 创建成功: {agent_id}")
        return 0
    
    def _cmd_list(self, args):
        """列出 Agent"""
        from ..core import AgentOSKernel
        kernel = AgentOSKernel()
        # 逻辑风险提示：这里调用了 kernel.list_agents()。
        # 但在当前主内核实现（agent_os_kernel/kernel.py）中未看到该方法定义，
        # 如果两者未对齐，运行 list 命令会直接抛 AttributeError。
        agents = kernel.list_agents()
        print(f"{'ID':<8} {'Name':<20} {'Status':<12}")
        for a in agents:
            print(f"{a.get('agent_id', 'N/A'):<8} {a.get('name', 'N/A'):<20} {a.get('status', 'unknown'):<12}")
        return 0
    
    def _cmd_delete(self, args):
        """删除 Agent"""
        # 逻辑风险提示：当前 delete/demo/serve/status 多数为占位实现（仅 print），
        # 并未真正调用内核/存储层做状态变更。
        # 如果文档对外宣称这些命令可用，用户会遇到“看似成功但什么也没发生”的逻辑落差。
        print(f"删除 Agent: {args.agent_id}")
        return 0
    
    def _cmd_demo(self, args):
        """运行演示"""
        print(f"运行演示: {args.type}")
        return 0
    
    def _cmd_serve(self, args):
        """启动服务器"""
        # 逻辑风险提示：这里未真正启动 FastAPI/uvicorn（当前仅输出），
        # 与 requirements.txt 中包含 fastapi/uvicorn 的预期不一致。
        print(f"启动服务器: {args.host}:{args.port}")
        return 0
    
    def _cmd_status(self, args):
        """显示状态"""
        print(f"时间: {datetime.now(timezone.utc).isoformat()}")
        print("内核: 运行中")
        return 0


def main():
    """CLI 入口点"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
