#!/usr/bin/env python3
"""
CLI Commands Demo - CLI命令演示

演示如何使用 Agent-OS-Kernel 的CLI命令:
- kernel status - 查看内核状态
- kernel agents list - 列出所有Agent
- kernel agents create - 创建新Agent
- kernel metrics show - 显示系统指标
- kernel config edit - 编辑配置

Usage:
    python cli_commands_demo.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Agent-OS-Kernel'))

from agent_os_kernel.cli.commands import (
    KernelCommands,
    create_command_parser,
    run_command
)
from datetime import datetime, timezone


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_status_command():
    """演示 kernel status 命令"""
    print_header("1. kernel status - 查看内核状态")
    
    commands = KernelCommands()
    
    # 创建模拟参数
    class Args:
        json = False
    
    args = Args()
    
    print("\n执行: kernel status")
    print("-" * 40)
    
    result = commands.status(args)
    
    print(f"\n返回值: {result}")
    print("状态命令演示完成!")


def demo_agents_list_command():
    """演示 kernel agents list 命令"""
    print_header("2. kernel agents list - 列出Agent")
    
    commands = KernelCommands()
    
    # 表格格式
    class Args:
        json = False
    
    args = Args()
    
    print("\n执行: kernel agents list")
    print("-" * 40)
    
    result = commands.agents_list(args)
    
    # JSON格式
    print("\n\nJSON格式输出:")
    print("-" * 40)
    args.json = True
    commands.agents_list(args)
    
    print(f"\n返回值: {result}")
    print("Agent列表命令演示完成!")


def demo_agents_create_command():
    """演示 kernel agents create 命令"""
    print_header("3. kernel agents create - 创建Agent")
    
    commands = KernelCommands()
    
    # 创建模拟参数
    class Args:
        name = "ResearchAssistant"
        task = "Research and summarize information"
        priority = 60
    
    args = Args()
    
    print("\n执行: kernel agents create --name 'ResearchAssistant' --task 'Research...' --priority 60")
    print("-" * 40)
    print(f"Agent名称: {args.name}")
    print(f"任务描述: {args.task}")
    print(f"优先级: {args.priority}")
    
    result = commands.agents_create(args)
    
    print(f"\n返回值: {result}")
    print("Agent创建命令演示完成!")


def demo_metrics_command():
    """演示 kernel metrics show 命令"""
    print_header("4. kernel metrics show - 显示指标")
    
    commands = KernelCommands()
    
    # 表格格式
    class Args:
        json = False
    
    args = Args()
    
    print("\n执行: kernel metrics show")
    print("-" * 40)
    
    result = commands.metrics_show(args)
    
    # JSON格式
    print("\n\nJSON格式输出:")
    print("-" * 40)
    args.json = True
    commands.metrics_show(args)
    
    print(f"\n返回值: {result}")
    print("指标显示命令演示完成!")


def demo_config_edit_command():
    """演示 kernel config edit 命令"""
    print_header("5. kernel config edit - 编辑配置")
    
    commands = KernelCommands()
    
    # 创建模拟参数
    class Args:
        key = "debug.enabled"
        value = "true"
    
    args = Args()
    
    print("\n执行: kernel config edit --key 'debug.enabled' --value 'true'")
    print("-" * 40)
    print(f"配置键: {args.key}")
    print(f"配置值: {args.value}")
    
    result = commands.config_edit(args)
    
    print(f"\n返回值: {result}")
    print("配置编辑命令演示完成!")


def demo_parser_usage():
    """演示命令行解析器的使用"""
    print_header("6. 命令行解析器使用")
    
    print("\n直接使用命令行参数:")
    print("-" * 40)
    
    # 模拟命令行调用
    sys.argv = ['cli_commands_demo.py', 'status']
    print("执行: python cli_commands_demo.py status")
    result = run_command(['status'])
    print(f"返回值: {result}")
    
    print("\n使用 create 子命令:")
    print("-" * 40)
    result = run_command([
        'agents', 'create',
        '--name', 'DemoAgent',
        '--task', 'Demo task',
        '--priority', '70'
    ])
    print(f"返回值: {result}")


def main():
    """主函数"""
    print_header("Agent-OS-Kernel CLI命令演示")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("演示各种CLI命令的使用方法")
    
    # 1. 状态命令
    demo_status_command()
    
    # 2. Agent列表命令
    demo_agents_list_command()
    
    # 3. Agent创建命令
    demo_agents_create_command()
    
    # 4. 指标显示命令
    demo_metrics_command()
    
    # 5. 配置编辑命令
    demo_config_edit_command()
    
    # 6. 解析器使用
    demo_parser_usage()
    
    # 总结
    print_header("演示总结")
    print("""
本次演示涵盖了以下CLI命令:

1. kernel status - 查看内核运行状态
   - 支持表格和JSON格式输出
   - 显示版本、运行时间、Agent数量等

2. kernel agents list - 列出所有Agent
   - 显示Agent ID、名称、状态、优先级
   - 支持JSON格式便于程序处理

3. kernel agents create - 创建新Agent
   - 指定名称、任务、优先级
   - 返回创建的Agent ID

4. kernel metrics show - 显示系统指标
   - 包括Token使用、API调用、缓存命中率等
   - 支持JSON格式便于监控集成

5. kernel config edit - 编辑配置
   - 支持点分路径配置键
   - 自动解析JSON值

所有命令都支持 --json 参数以JSON格式输出，
便于在脚本和监控系统中的使用。
    """)
    
    print("=" * 60)
    print("  CLI命令演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
