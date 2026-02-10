# -*- coding: utf-8 -*-
"""记忆增强演示 - 整合 MemOS 核心特性"""

import asyncio
from agent_os_kernel.core.memory_feedback import (
    MemoryFeedbackSystem, FeedbackType
)
from agent_os_kernel.core.tool_memory import ToolMemory, ToolStatus


async def main():
    print("="*60)
    print("Memory Enhancement Demo (MemOS Integration)")
    print("="*60)
    
    # ========== Memory Feedback ==========
    print("\n📝 Memory Feedback System")
    print("-"*40)
    
    feedback = MemoryFeedbackSystem()
    
    # 创建反馈
    await feedback.create_feedback(
        memory_id="mem-001",
        feedback_type=FeedbackType.CORRECT,
        feedback_content="Python 是解释型语言",
        reason="原答案说 Python 是编译型语言",
        original_content="Python 是编译型语言"
    )
    
    await feedback.create_feedback(
        memory_id="mem-002",
        feedback_type=FeedbackType.SUPPLEMENT,
        feedback_content="Agent OS Kernel 支持多 Agent 协作",
        reason="补充说明",
        original_content=""
    )
    
    # 应用反馈
    feedbacks = await feedback.get_pending_feedbacks()
    print(f"待处理反馈: {len(feedbacks)}")
    
    if feedbacks:
        await feedback.apply_feedback(feedbacks[0].feedback_id)
        print(f"已应用: {feedbacks[0].feedback_id}")
    
    # 统计
    stats = feedback.get_stats()
    print(f"\n📊 反馈统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # ========== Tool Memory ==========
    print("\n\n🔧 Tool Memory System")
    print("-"*40)
    
    tool_memory = ToolMemory(max_history=100)
    
    # 记录工具调用
    tools = [
        ("search", ToolStatus.SUCCESS, 150.5),
        ("search", ToolStatus.SUCCESS, 120.3),
        ("read_file", ToolStatus.SUCCESS, 45.2),
        ("calculator", ToolStatus.SUCCESS, 10.1),
        ("execute_python", ToolStatus.FAILED, 5000.0),
        ("search", ToolStatus.SUCCESS, 180.7),
    ]
    
    for i, (tool, status, duration) in enumerate(tools):
        await tool_memory.record_call(
            tool_name=tool,
            arguments={"query": f"test-{i}"},
            result={"success": True},
            status=status,
            duration_ms=duration,
            agent_id="agent-001",
            task_id=f"task-{i}"
        )
        print(f"📦 {tool}: {status.value} ({duration:.1f}ms)")
    
    # 获取统计
    stats = await tool_memory.get_tool_statistics()
    print(f"\n📊 工具统计:")
    print(f"  总调用: {stats['total_calls']}")
    print(f"  成功率: {stats['success_rate']:.1f}%")
    print(f"  工具数: {stats['tools_count']}")
    
    # 最常用工具
    top = await tool_memory.get_frequently_used_tools(3)
    print(f"\n🔝 最常用工具:")
    for tool in top:
        print(f"  {tool['tool_name']}: {tool['total_calls']} 次")
    
    # 失败工具
    failed = await tool_memory.get_failed_tools()
    print(f"\n❌ 失败工具:")
    for tool in failed:
        print(f"  {tool['tool_name']}: {tool['failed_count']} 次失败")
    
    # 慢速工具
    slow = await tool_memory.get_slow_tools(threshold_ms=100)
    print(f"\n🐌 慢速工具 (>100ms):")
    for tool in slow:
        print(f"  {tool['tool_name']}: {tool['avg_duration_ms']:.1f}ms 平均")
    
    # 任务推荐
    suggestions = await tool_memory.suggest_tools_for_task("需要搜索并计算结果")
    print(f"\n💡 任务推荐:")
    print(f"  建议工具: {suggestions}")
    
    print("\n" + "="*60)
    print("✅ 演示完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
