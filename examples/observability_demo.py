#!/usr/bin/env python3
"""Observability 使用示例"""

from agent_os_kernel.core.observability import (
    Observability, EventType
)


def main():
    print("="*50)
    print("Observability 示例")
    print("="*50)
    
    # 1. 创建可观测性系统
    print("\n1. 创建可观测性系统")
    
    obs = Observability()
    print("   ✓ 可观测性系统创建成功")
    
    # 2. 启动会话
    print("\n2. 启动会话")
    
    session = obs.start_session("analysis-session")
    print(f"   会话ID: {session.id}")
    print(f"   会话名称: {session.name}")
    
    # 3. 记录事件
    print("\n3. 记录事件")
    
    obs.record_event(EventType.AGENT_START, agent_id="agent-001")
    obs.record_event(EventType.TASK_START, agent_id="agent-001", data={"task": "分析"})
    obs.record_event(EventType.TASK_END, agent_id="agent-001", data={"result": "完成"})
    obs.record_event(EventType.AGENT_END, agent_id="agent-001")
    
    print("   ✓ 记录了4个事件")
    
    # 4. 获取统计
    print("\n4. 获取统计")
    
    stats = obs.get_stats()
    print(f"   总事件数: {stats['total_events']}")
    print(f"   会话状态: {stats['session']['status']}")
    
    # 5. 结束会话
    print("\n5. 结束会话")
    
    session = obs.end_session("completed")
    print(f"   会话状态: {session.status}")
    print(f"   事件数: {session.events_count}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    main()
