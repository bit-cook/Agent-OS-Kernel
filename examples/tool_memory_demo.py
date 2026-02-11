#!/usr/bin/env python3
"""ToolMemory 使用示例"""

import asyncio
from agent_os_kernel.core.tool_memory import (
    ToolMemory, ToolStatus
)


async def main():
    print("="*50)
    print("ToolMemory 示例")
    print("="*50)
    
    # 1. 创建工具内存
    print("\n1. 创建工具内存系统")
    
    tool_mem = ToolMemory()
    print("   ✓ 工具内存创建成功")
    
    # 2. 记录工具调用
    print("\n2. 记录工具调用")
    
    await tool_mem.record_call(
        tool_name="file_read",
        arguments={"path": "/test/file.txt"},
        result={"content": "file data"},
        status=ToolStatus.SUCCESS,
        duration_ms=150,
        agent_id="agent-001"
    )
    
    await tool_mem.record_call(
        tool_name="web_request",
        arguments={"url": "https://example.com"},
        result={"status": 200},
        status=ToolStatus.SUCCESS,
        duration_ms=500,
        agent_id="agent-001"
    )
    
    print("   ✓ 记录了2次工具调用")
    
    # 3. 获取统计
    print("\n3. 获取统计")
    
    stats = tool_mem.get_stats()
    print(f"   总调用数: {stats['total_calls']}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
