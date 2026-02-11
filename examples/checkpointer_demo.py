#!/usr/bin/env python3
"""Checkpointer 使用示例"""

import asyncio
from agent_os_kernel.core.checkpointer import Checkpointer


async def main():
    print("="*50)
    print("Checkpointer 示例")
    print("="*50)
    
    cp = Checkpointer()
    
    # 1. 创建检查点
    print("\n1. 创建检查点")
    
    cp_id = await cp.create(
        "session-001",
        {"state": "用户会话数据", "user": "Alice"},
        tag="session"
    )
    
    print(f"   检查点ID: {cp_id[:8]}...")
    
    # 2. 恢复检查点
    print("\n2. 恢复检查点")
    
    state = await cp.restore(cp_id)
    print(f"   恢复数据: {state}")
    
    # 3. 列出检查点
    print("\n3. 列出检查点")
    
    checkpoints = await cp.list_checkpoints()
    print(f"   检查点数: {len(checkpoints)}")
    
    # 4. 获取统计
    print("\n4. 获取统计")
    
    stats = cp.get_stats()
    print(f"   总检查点: {stats['total_checkpoints']}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
