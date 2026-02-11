#!/usr/bin/env python3
"""MemoryFeedback 使用示例"""

import asyncio
from agent_os_kernel.core.memory_feedback import (
    MemoryFeedbackSystem, FeedbackType
)


async def main():
    print("="*50)
    print("MemoryFeedback 示例")
    print("="*50)
    
    # 1. 创建反馈系统
    print("\n1. 创建反馈系统")
    
    feedback = MemoryFeedbackSystem()
    print("   ✓ 反馈系统创建成功")
    
    # 2. 创建反馈
    print("\n2. 创建反馈")
    
    await feedback.create_feedback(
        memory_id="mem-001",
        feedback_type=FeedbackType.CORRECT,
        feedback_content="正确的内容",
        reason="原回答有误"
    )
    
    await feedback.create_feedback(
        memory_id="mem-002",
        feedback_type=FeedbackType.SUPPLEMENT,
        feedback_content="补充信息",
        reason="需要更多上下文"
    )
    
    print("   ✓ 创建了2条反馈")
    
    # 3. 获取统计
    print("\n3. 获取统计")
    
    stats = feedback.get_stats()
    print(f"   总反馈数: {stats['total_feedbacks']}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
