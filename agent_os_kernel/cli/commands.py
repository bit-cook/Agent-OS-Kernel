# -*- coding: utf-8 -*-
"""CLI Commands - CLI命令集合

提供完整的命令行命令，支持:
- kernel status - 查看内核状态
- kernel agents list - 列出所有Agent
- kernel agents create - 创建新Agent
- kernel metrics show - 显示系统指标
- kernel config edit - 编辑配置

Usage:
    kernel status
    kernel agents list [--json]
    kernel agents create --name <name> --task <task> [--priority <priority>]
    kernel metrics show [--json]
    kernel config edit --key <key> --value <value>
"""

import argparse
import sys
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from datetime import timezone, timezone
from pathlib import Path


class KernelCommands:
    """内核命令集合"""

    def __init__(self):
        self.kernel = None

    def _get_kernel(self):
        """获取内核实例"""
        if self.kernel is None:
            try:
                from agent_os_kernel import AgentOSKernel
                self.kernel = AgentOSKernel()
            except ImportError:
                return None
        return self.kernel

    def status(self, args: argparse.Namespace) -> int:
        """
        查看内核状态
        
        Args:
            args: 命令参数
            
        Returns:
            状态码 (0=成功)
        """
        kernel = self._get_kernel()
        
        print("=" * 60)
        print("Agent-OS-Kernel 状态")
        print("=" * 60)
        print(f"时间: {datetime.now(timezone.utc).isoformat()}")
        
        if kernel:
            stats = kernel.stats
            print(f"版本: {stats.version}")
            print(f"运行时间: {datetime.now(timezone.utc).fromtimestamp(stats.start_time).isoformat()}")
            print(f"总Agent数: {stats.total_agents}")
            print(f"活跃Agent数: {stats.active_agents}")
            print(f"总迭代次数: {stats.total_iterations}")
            print(f"总Token数: {stats.total_tokens}")
            print(f"API调用次数: {stats.total_api_calls}")
            print(f"缓存命中率: {stats.avg_cache_hit_rate:.2%}")
            
            if hasattr(kernel, 'context_manager'):
                cm = kernel.context_manager
                print(f"\n上下文管理器:")
                print(f"  最大Token: {cm.max_context_tokens}")
                print(f"  已用Token: {cm._get_used_tokens() if hasattr(cm, '_get_used_tokens') else 'N/A'}")
            
            if hasattr(kernel, 'scheduler'):
                print(f"\n调度器:")
                print(f"  时间片: {kernel.scheduler.time_slice}s")
            
            print("\n状态: 运行中 ✓")
        else:
            print("\n内核: 未初始化 (使用模拟数据)")
            print("模拟状态:")
            print("  版本: 0.2.0")
            print("  总Agent数: 0")
            print("  活跃Agent数: 0")
        
        print("=" * 60)
        return 0

    def agents_list(self, args: argparse.Namespace) -> int:
        """
        列出所有Agent
        
        Args:
            args: 命令参数 (--json)
            
        Returns:
            状态码 (0=成功)
        """
        kernel = self._get_kernel()
        
        if args.json:
            # JSON格式输出
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agents": []
            }
            
            if kernel and hasattr(kernel, 'scheduler'):
                try:
                    processes = kernel.scheduler.list_processes()
                    for proc in processes:
                        result["agents"].append({
                            "agent_id": proc.pid if hasattr(proc, 'pid') else str(proc),
                            "name": proc.name if hasattr(proc, 'name') else "Unknown",
                            "status": proc.status if hasattr(proc, 'status') else "unknown",
                            "priority": proc.priority if hasattr(proc, 'priority') else 50
                        })
                except Exception as e:
                    result["error"] = str(e)
            else:
                # 模拟数据
                result["agents"] = [
                    {"agent_id": "demo-001", "name": "Researcher", "status": "running", "priority": 50},
                    {"agent_id": "demo-002", "name": "Writer", "status": "idle", "priority": 60}
                ]
            
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 表格格式输出
            print("=" * 60)
            print("Agent 列表")
            print("=" * 60)
            print(f"{'ID':<12} {'名称':<20} {'状态':<12} {'优先级':<10}")
            print("-" * 60)
            
            agents_found = False
            
            if kernel and hasattr(kernel, 'scheduler'):
                try:
                    processes = kernel.scheduler.list_processes()
                    for proc in processes:
                        agents_found = True
                        print(f"{proc.pid:<12} {proc.name:<20} {proc.status:<12} {proc.priority:<10}")
                except Exception as e:
                    print(f"获取Agent列表失败: {e}")
            
            if not agents_found:
                # 模拟数据
                print(f"{'demo-001':<12} {'Researcher':<20} {'running':<12} {'50':<10}")
                print(f"{'demo-002':<12} {'Writer':<20} {'idle':<12} {'60':<10}")
            
            print("=" * 60)
            print(f"总计: 2 个Agent (演示)")
        
        return 0

    def agents_create(self, args: argparse.Namespace) -> int:
        """
        创建新Agent
        
        Args:
            args: 命令参数 (--name, --task, --priority)
            
        Returns:
            状态码 (0=成功)
        """
        kernel = self._get_kernel()
        
        name = args.name
        task = args.task
        priority = getattr(args, 'priority', 50)
        
        print("=" * 60)
        print("创建 Agent")
        print("=" * 60)
        print(f"名称: {name}")
        print(f"任务: {task}")
        print(f"优先级: {priority}")
        print("-" * 60)
        
        if kernel:
            try:
                agent_id = kernel.spawn_agent(
                    name=name,
                    task=task,
                    priority=priority
                )
                print(f"Agent创建成功!")
                print(f"Agent ID: {agent_id}")
                return 0
            except Exception as e:
                print(f"创建失败: {e}")
                return 1
        else:
            # 模拟创建
            import uuid
            agent_id = f"agent-{uuid.uuid4().hex[:8]}"
            print(f"Agent创建成功 (模拟)!")
            print(f"Agent ID: {agent_id}")
            print("注意: 内核未初始化，使用模拟模式")
            return 0

    def metrics_show(self, args: argparse.Namespace) -> int:
        """
        显示系统指标
        
        Args:
            args: 命令参数 (--json)
            
        Returns:
            状态码 (0=成功)
        """
        kernel = self._get_kernel()
        
        if args.json:
            # JSON格式输出
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": {}
            }
            
            if kernel:
                stats = kernel.stats
                result["metrics"] = {
                    "version": stats.version,
                    "total_agents": stats.total_agents,
                    "active_agents": stats.active_agents,
                    "total_iterations": stats.total_iterations,
                    "total_tokens": stats.total_tokens,
                    "total_api_calls": stats.total_api_calls,
                    "cache_hit_rate": stats.avg_cache_hit_rate
                }
                
                # 添加上下文指标
                if hasattr(kernel, 'context_manager'):
                    cm = kernel.context_manager
                    result["metrics"]["context"] = {
                        "max_tokens": cm.max_context_tokens,
                        "used_tokens": cm._get_used_tokens() if hasattr(cm, '_get_used_tokens') else 0
                    }
                
                # 添加调度指标
                if hasattr(kernel, 'scheduler'):
                    result["metrics"]["scheduler"] = {
                        "time_slice": kernel.scheduler.time_slice,
                        "active_tasks": len(kernel.scheduler._processes) if hasattr(kernel.scheduler, '_processes') else 0
                    }
                
                # 添加指标收集器指标
                if hasattr(kernel, 'metrics_collector'):
                    mc = kernel.metrics_collector
                    result["metrics"]["collector"] = {
                        "metrics_count": len(mc._metrics) if hasattr(mc, '_metrics') else 0
                    }
            else:
                # 模拟数据
                result["metrics"] = {
                    "version": "0.2.0",
                    "total_agents": 5,
                    "active_agents": 3,
                    "total_iterations": 1500,
                    "total_tokens": 450000,
                    "total_api_calls": 250,
                    "cache_hit_rate": 0.75
                }
            
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 表格格式输出
            print("=" * 60)
            print("系统指标")
            print("=" * 60)
            
            if kernel:
                stats = kernel.stats
                print(f"{'指标':<25} {'值':<20}")
                print("-" * 50)
                print(f"{'版本':<25} {stats.version:<20}")
                print(f"{'总Agent数':<25} {stats.total_agents:<20}")
                print(f"{'活跃Agent数':<25} {stats.active_agents:<20}")
                print(f"{'总迭代次数':<25} {stats.total_iterations:<20}")
                print(f"{'总Token数':<25} {stats.total_tokens:<20}")
                print(f"{'API调用次数':<25} {stats.total_api_calls:<20}")
                print(f"{'缓存命中率':<25} {stats.avg_cache_hit_rate:.2%}")
                
                # 上下文指标
                if hasattr(kernel, 'context_manager'):
                    cm = kernel.context_manager
                    print(f"\n{'上下文管理':<25}")
                    print(f"{'  最大Token':<25} {cm.max_context_tokens:<20}")
                    if hasattr(cm, '_get_used_tokens'):
                        print(f"{'  已用Token':<25} {cm._get_used_tokens():<20}")
                
                # 调度指标
                if hasattr(kernel, 'scheduler'):
                    print(f"\n{'调度器':<25}")
                    print(f"{'  时间片':<25} {kernel.scheduler.time_slice}s")
            else:
                # 模拟数据
                print(f"{'指标':<25} {'值':<20}")
                print("-" * 50)
                print(f"{'版本':<25} {'0.2.0':<20}")
                print(f"{'总Agent数':<25} {'5':<20}")
                print(f"{'活跃Agent数':<25} {'3':<20}")
                print(f"{'总迭代次数':<25} {'1500':<20}")
                print(f"{'总Token数':<25} {'450000':<20}")
                print(f"{'API调用次数':<25} {'250':<20}")
                print(f"{'缓存命中率':<25} {'75.00%':<20}")
            
            print("=" * 60)
        
        return 0

    def config_edit(self, args: argparse.Namespace) -> int:
        """
        编辑配置
        
        Args:
            args: 命令参数 (--key, --value)
            
        Returns:
            状态码 (0=成功)
        """
        from agent_os_kernel.core import ConfigManager
        import asyncio
        
        key = args.key
        value = args.value
        
        print("=" * 60)
        print("编辑配置")
        print("=" * 60)
        print(f"键: {key}")
        print(f"值: {value}")
        print("-" * 60)
        
        # 尝试解析JSON值
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value
        
        try:
            config_manager = ConfigManager()
            asyncio.run(config_manager.initialize())
            
            # 保存配置
            config_path = Path("config/user_config.json")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有配置
            existing_config = {}
            if config_path.exists():
                existing_config = json.loads(config_path.read_text())
            
            # 更新配置
            keys = key.split('.')
            current = existing_config
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = parsed_value
            
            # 写入配置
            config_path.write_text(json.dumps(existing_config, indent=2, ensure_ascii=False))
            
            print(f"配置已保存: {config_path}")
            print(f"配置键: {key}")
            print(f"配置值: {parsed_value}")
            
            asyncio.run(config_manager.shutdown())
            return 0
            
        except Exception as e:
            print(f"编辑配置失败: {e}")
            # 保存到简单的JSON文件
            config_data = {key: parsed_value}
            config_path = Path("config.json")
            config_path.write_text(json.dumps(config_data, indent=2))
            print(f"已保存到: {config_path}")
            return 0


def create_command_parser() -> argparse.ArgumentParser:
    """
    创建命令解析器
    
    Returns:
        解析器实例
    """
    parser = argparse.ArgumentParser(
        description="Agent-OS-Kernel CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  kernel status              # 查看状态
  kernel agents list         # 列出Agent
  kernel agents create --name "Assistant" --task "Help users"  # 创建Agent
  kernel metrics show        # 显示指标
  kernel config edit --key "debug" --value "true"  # 编辑配置
        """
    )
    
    parser.add_argument("--config", "-c", default="config.yaml", help="配置文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="可用的命令"
    )
    
    # kernel status
    status_parser = subparsers.add_parser("status", help="查看内核状态")
    status_parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    # kernel agents
    agents_parser = subparsers.add_parser("agents", help="Agent管理")
    agents_subparsers = agents_parser.add_subparsers(
        dest="agents_command",
        title="agents commands"
    )
    
    # kernel agents list
    list_parser = agents_subparsers.add_parser("list", help="列出所有Agent")
    list_parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    # kernel agents create
    create_parser = agents_subparsers.add_parser("create", help="创建新Agent")
    create_parser.add_argument("--name", "-n", required=True, help="Agent名称")
    create_parser.add_argument("--task", "-t", required=True, help="任务描述")
    create_parser.add_argument("--priority", "-p", type=int, default=50, help="优先级 (0-100)")
    
    # kernel metrics
    metrics_parser = subparsers.add_parser("metrics", help="系统指标")
    metrics_subparsers = metrics_parser.add_subparsers(
        dest="metrics_command",
        title="metrics commands"
    )
    
    # kernel metrics show
    show_parser = metrics_subparsers.add_parser("show", help="显示指标")
    show_parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    # kernel config
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        title="config commands"
    )
    
    # kernel config edit
    edit_parser = config_subparsers.add_parser("edit", help="编辑配置")
    edit_parser.add_argument("--key", "-k", required=True, help="配置键 (支持点分路径如 'section.key')")
    edit_parser.add_argument("--value", "-v", required=True, help="配置值 (JSON格式)")
    
    return parser


def run_command(args: Optional[List[str]] = None) -> int:
    """
    运行命令
    
    Args:
        args: 命令参数列表
        
    Returns:
        状态码 (0=成功)
    """
    parser = create_command_parser()
    parsed = parser.parse_args(args)
    
    if not parsed.command:
        parser.print_help()
        return 0
    
    commands = KernelCommands()
    
    # 处理子命令
    if parsed.command == "status":
        return commands.status(parsed)
    
    elif parsed.command == "agents":
        agents_cmd = getattr(parsed, 'agents_command', None)
        if agents_cmd == "list":
            return commands.agents_list(parsed)
        elif agents_cmd == "create":
            return commands.agents_create(parsed)
        else:
            parser.print_help()
            return 1
    
    elif parsed.command == "metrics":
        metrics_cmd = getattr(parsed, 'metrics_command', None)
        if metrics_cmd == "show":
            return commands.metrics_show(parsed)
        else:
            parser.print_help()
            return 1
    
    elif parsed.command == "config":
        config_cmd = getattr(parsed, 'config_command', None)
        if config_cmd == "edit":
            return commands.config_edit(parsed)
        else:
            parser.print_help()
            return 1
    
    else:
        parser.print_help()
        return 1


def main():
    """CLI入口点"""
    sys.exit(run_command())


if __name__ == "__main__":
    main()
