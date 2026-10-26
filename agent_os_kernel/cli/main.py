# -*- coding: utf-8 -*-
"""CLI - 命令行接口

提供完整的命令行工具，支持:
- Agent 创建和管理（状态持久化到 .agent-os-kernel-state.json）
- 任务执行
- 项目初始化
- 配置管理
- 监控和调试

所有命令都真实执行：没有占位符，没有虚假成功。
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

STATE_FILE = ".agent-os-kernel-state.json"


def _load_state() -> dict:
    """加载 CLI 状态文件"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"agents": []}
    return {"agents": []}


def _save_state(state: dict):
    """保存 CLI 状态文件"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


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
  agent-os-kernel doctor                # 环境自检
  agent-os-kernel init                  # 初始化项目
  agent-os-kernel create -n "Researcher" -t "Research AI"  # 创建 Agent
  agent-os-kernel list                  # 列出所有 Agent
  agent-os-kernel demo                  # 运行确定性演示（mock provider）
  agent-os-kernel serve --port 8000     # 启动 API 服务器（默认仅本机）
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
        self._add_doctor_command(subparsers)
        
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
        cmd.add_argument("--type", "-t", default="basic",
                         choices=["basic", "checkpoint"])
    
    def _add_serve_command(self, subparsers):
        cmd = subparsers.add_parser("serve", help="启动服务器（默认仅监听 127.0.0.1）")
        cmd.add_argument("--host", "-H", default="127.0.0.1",
                         help="监听地址；绑定非 loopback 地址属于显式公开暴露，需自行配置认证")
        cmd.add_argument("--port", "-p", type=int, default=8000)
    
    def _add_status_command(self, subparsers):
        cmd = subparsers.add_parser("status", help="显示状态")
        cmd.add_argument("--json", action="store_true")
    
    def _add_doctor_command(self, subparsers):
        subparsers.add_parser("doctor", help="环境自检（黄金路径第一步）")
    
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
            "doctor": self._cmd_doctor,
        }
        
        handler = handlers.get(command)
        if not handler:
            print(f"未知命令: {command}", file=sys.stderr)
            return 1
        try:
            return handler(args)
        except Exception as e:
            print(f"命令执行失败: {e}", file=sys.stderr)
            return 1
    
    def _cmd_init(self, args):
        """初始化项目"""
        if os.path.exists("config.yaml") and not args.force:
            print("config.yaml 已存在（使用 --force 覆盖）")
            return 1
        
        import yaml
        config = {
            "kernel": {"max_agents": 10},
            "llm": {"default_provider": "mock"}
        }
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
        print("项目初始化完成! 已生成 config.yaml")
        return 0
    
    def _cmd_create(self, args):
        """创建 Agent（真实 spawn，状态持久化到状态文件）"""
        from ..kernel import AgentOSKernel
        kernel = AgentOSKernel()
        agent_id = kernel.spawn_agent(name=args.name, task=args.task, priority=args.priority)
        
        state = _load_state()
        state["agents"].append({
            "agent_id": agent_id,
            "name": args.name,
            "task": args.task,
            "priority": args.priority,
            "model": args.model,
            "status": "ready",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        _save_state(state)
        
        print(f"Agent 创建成功: {agent_id}")
        print(f"  名称: {args.name}")
        print(f"  任务: {args.task}")
        print(f"  优先级: {args.priority}")
        print(f"（状态已保存到 {STATE_FILE}；内核进程内状态在命令结束后释放）")
        return 0
    
    def _cmd_list(self, args):
        """列出 Agent（从状态文件读取真实记录）"""
        state = _load_state()
        agents = state.get("agents", [])
        
        if args.json:
            print(json.dumps(agents, ensure_ascii=False, indent=2))
            return 0
        
        if not agents:
            print("没有 Agent。使用 'agent-os-kernel create' 创建。")
            return 0
        
        print(f"{'ID':<10} {'Name':<20} {'Status':<10} {'Priority':<9} {'Task'}")
        print("-" * 70)
        for a in agents:
            print(f"{a.get('agent_id', 'N/A')[:8]:<10} "
                  f"{a.get('name', 'N/A'):<20} "
                  f"{a.get('status', 'unknown'):<10} "
                  f"{a.get('priority', '-'):<9} "
                  f"{a.get('task', '')}")
        return 0
    
    def _cmd_delete(self, args):
        """删除 Agent（从状态文件真实移除）"""
        state = _load_state()
        agents = state.get("agents", [])
        remaining = [a for a in agents if a.get("agent_id") != args.agent_id
                     and not a.get("agent_id", "").startswith(args.agent_id)]
        
        if len(remaining) == len(agents):
            print(f"Agent 不存在: {args.agent_id}", file=sys.stderr)
            return 1
        
        state["agents"] = remaining
        _save_state(state)
        print(f"已删除 Agent: {args.agent_id}")
        return 0
    
    def _cmd_demo(self, args):
        """运行演示（MockProvider 真实 LLM 路径：spawn → run → checkpoint → restore）"""
        from ..kernel import AgentOSKernel
        from ..llm.provider import LLMConfig
        from ..llm.mock_provider import MockProvider

        # 确定性 mock provider：无需 API key，响应可配置
        mock = MockProvider(LLMConfig(provider="mock", model="mock-model", api_key="mock-key"))
        if args.type == "checkpoint":
            # 检查点演示需要 agent 在 run 后仍存活：不给 [DONE]
            mock.set_response("code", "演示推理：任务进行中...")
        else:
            mock.set_response("code", "演示推理：任务已完成。\n[DONE]")
        kernel = AgentOSKernel(llm_provider=mock)

        print("=== Agent OS Kernel 演示（MockProvider，确定性） ===")
        pid = kernel.spawn_agent(name="DemoAgent", task="演示任务：计算 2+2", priority=30)
        kernel.run(max_iterations=2)
        stats = kernel.get_stats()
        cost = kernel.cost_tracker.get_global_stats()
        print(f"运行完成: {stats['total_iterations']} 次迭代, "
              f"{stats['active_agents']} 个活动 Agent")
        print(f"LLM 用量: {cost['total_tokens']} tokens, {cost['total_requests']} 次请求, "
              f"成本 ${cost['total_cost']:.6f}（provider=mock）")

        if args.type == "checkpoint":
            cid = kernel.create_checkpoint(pid, description="demo")
            if cid:
                print(f"检查点已创建: {cid[:8]}...")
                new_pid = kernel.restore_checkpoint(cid)
                if new_pid:
                    print(f"已从检查点恢复，新 PID: {new_pid[:8]}...")
                    print("✓ 检查点/恢复闭环演示成功")
            else:
                print("检查点创建失败", file=sys.stderr)
                return 1

        kernel.shutdown()
        return 0
    
    def _cmd_serve(self, args):
        """启动 API 服务器"""
        if args.host not in ("127.0.0.1", "localhost", "::1"):
            print(f"警告: 正在绑定非 loopback 地址 {args.host} —— 这是显式公开暴露。", file=sys.stderr)
            print("生产部署必须配置认证（API Key）并部署在网络隔离层之后。", file=sys.stderr)
        
        try:
            from ..api.server import run_server
        except ImportError as e:
            print(f"API 服务器依赖缺失: {e}", file=sys.stderr)
            print("请安装: pip install fastapi uvicorn", file=sys.stderr)
            return 1
        
        print(f"启动服务器: http://{args.host}:{args.port}  (docs: /docs, dashboard: /ui)")
        run_server(host=args.host, port=args.port)
        return 0
    
    def _cmd_status(self, args):
        """显示状态（真实内核版本 + 状态文件统计）"""
        from .. import __version__
        state = _load_state()
        agents = state.get("agents", [])
        
        status = {
            "kernel_version": __version__,
            "agents_total": len(agents),
            "time": datetime.now(timezone.utc).isoformat(),
        }
        
        if args.json:
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(f"内核版本: {status['kernel_version']}")
            print(f"Agent 总数: {status['agents_total']}")
            print(f"时间: {status['time']}")
        return 0
    
    def _cmd_doctor(self, args):
        """环境自检：验证黄金路径所需的一切"""
        checks = []
        
        # 1. 顶层公共 API 可导入
        try:
            from .. import AgentOSKernel, __version__
            checks.append(("顶层导入 AgentOSKernel/KernelStats", True, f"v{__version__}"))
        except Exception as e:
            checks.append(("顶层导入 AgentOSKernel/KernelStats", False, str(e)))
        
        # 2. 内核可实例化
        kernel = None
        try:
            from .. import AgentOSKernel
            kernel = AgentOSKernel()
            checks.append(("内核实例化", True, f"v{kernel.VERSION}"))
        except Exception as e:
            checks.append(("内核实例化", False, str(e)))
        
        # 3. spawn → checkpoint → restore 闭环
        try:
            pid = kernel.spawn_agent(name="DoctorAgent", task="self-check")
            cid = kernel.create_checkpoint(pid)
            restored = kernel.restore_checkpoint(cid) if cid else None
            ok = bool(cid and restored)
            checks.append(("spawn/checkpoint/restore 闭环", ok,
                           f"checkpoint={cid[:8] + '...' if cid else None}, restored={bool(restored)}"))
        except Exception as e:
            checks.append(("spawn/checkpoint/restore 闭环", False, str(e)))
        
        # 4. 工具注册
        try:
            tools = kernel.tool_registry.get_schemas()
            checks.append(("内置工具注册", len(tools) > 0, f"{len(tools)} 个工具"))
        except Exception as e:
            checks.append(("内置工具注册", False, str(e)))
        
        all_ok = all(ok for _, ok, _ in checks)
        for name, ok, detail in checks:
            mark = "✓" if ok else "✗"
            print(f"{mark} {name}: {detail}")
        
        print()
        if all_ok:
            print("环境自检通过。可以开始使用 Agent OS Kernel。")
            return 0
        print("环境自检发现问题，请根据上方详情修复。", file=sys.stderr)
        return 1


def main():
    """CLI 入口点"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
