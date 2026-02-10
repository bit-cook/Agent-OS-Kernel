"""
Multi-Agent Communication Demo

展示 Agent 之间的通信、知识共享和协作功能。

功能：
1. Agent 消息传递
2. 知识共享
3. 群聊协作
4. 任务委派
"""

import asyncio
from agent_os_kernel.agents.communication import (
    create_messenger,
    create_knowledge_sharing,
    create_group_chat_manager,
    create_collaboration,
    MessageType,
    Message
)


async def demo_basic_messaging():
    """基本消息传递"""
    print("\n" + "=" * 50)
    print("1. 基本消息传递")
    print("=" * 50)
    
    messenger = create_messenger()
    
    # 注册 Agent
    await messenger.register_agent("agent-1", "Alice")
    await messenger.register_agent("agent-2", "Bob")
    await messenger.register_agent("agent-3", "Carol")
    
    # 点对点消息
    msg = Message.create(
        msg_type=MessageType.CHAT,
        sender_id="agent-1",
        sender_name="Alice",
        content="你好 Bob! 帮我看看这个设计有问题吗?",
        receiver_id="agent-2"
    )
    await messenger.send(msg)
    
    received = await messenger.receive("agent-2", timeout=2.0)
    if received:
        print(f"  ✓ Bob 收到: {received.content}")
    
    # 广播消息
    broadcast = Message.create(
        msg_type=MessageType.NOTIFICATION,
        sender_id="agent-1",
        sender_name="Alice",
        content="会议将在 5 分钟后开始",
    )
    await messenger.send(broadcast)
    print("  ✓ Alice 发送了广播消息")
    
    # 统计
    stats = messenger.get_statistics()
    print(f"  📊 消息统计: {stats}")


async def demo_knowledge_sharing():
    """知识共享"""
    print("\n" + "=" * 50)
    print("2. 知识共享")
    print("=" * 50)
    
    knowledge = create_knowledge_sharing()
    
    # 共享知识
    from agent_os_kernel.agents.communication.knowledge_share import (
        KnowledgePacket, KnowledgeType
    )
    
    # 共享一个经验
    packet = KnowledgePacket.create(
        knowledge_type=KnowledgeType.EXPERIENCE,
        title="处理长上下文的技巧",
        content="将长上下文分割成多个页面，使用虚拟内存机制管理",
        source_agent="agent-1",
        source_task="research",
        confidence=0.9,
        tags=["context", "optimization"]
    )
    await knowledge.share(packet)
    print(f"  ✓ 共享知识: {packet.title}")
    
    # 检索知识
    results = await knowledge.retrieve("上下文", limit=5)
    for packet, score in results:
        print(f"  📚 找到: {packet.title} (相关性: {score:.2f})")
    
    # 统计
    stats = await knowledge.get_statistics()
    print(f"  📊 知识库统计: {stats['total_knowledge']} 条知识")


async def demo_group_chat():
    """群聊协作"""
    print("\n" + "=" * 50)
    print("3. 群聊协作")
    print("=" * 50)
    
    chat = create_group_chat_manager()
    
    # 创建群聊
    chat_id = chat.create_chat(
        chat_id="design_review",
        topic="系统设计评审",
        max_members=5
    )
    print(f"  ✓ 创建群聊: {chat_id}")
    
    # 加入成员
    members = [
        ("agent-1", "Alice", "moderator"),
        ("agent-2", "Bob", "expert"),
        ("agent-3", "Carol", "speaker")
    ]
    
    for agent_id, name, role in members:
        await chat.join_chat(chat_id, agent_id, name, role)
    
    print(f"  ✓ {len(members)} 个成员加入")
    
    # 模拟讨论
    messages = [
        ("agent-1", "Alice", "大家好，讨论一下新的架构设计"),
        ("agent-2", "Bob", "我建议使用分层架构"),
        ("agent-3", "Carol", "同意，分层更清晰"),
        ("agent-2", "Bob", "好，第一层是接口层，第二层是业务层"),
        ("agent-1", "Alice", "达成共识！分层架构：接口层 + 业务层")
    ]
    
    for agent_id, name, content in messages:
        await chat.send_message(chat_id, agent_id, content)
    
    print(f"  ✓ 讨论完成: {len(messages)} 条消息")
    
    # 获取状态
    status = chat.get_status(chat_id)
    print(f"  📊 群聊状态: {status['messages_count']} 消息, {status['members_count']} 成员")


async def demo_collaboration():
    """协作任务"""
    print("\n" + "=" * 50)
    print("4. 协作任务")
    print("=" * 50)
    
    collab = create_collaboration()
    
    # 创建会话
    session_id = await collab.create_session(
        session_id="project-alpha",
        name="项目 Alpha",
        agents=[
            {"id": "agent-1", "name": "Alice"},
            {"id": "agent-2", "name": "Bob"},
            {"id": "agent-3", "name": "Carol"}
        ]
    )
    print(f"  ✓ 创建协作会话: {session_id}")
    
    # 并行任务
    tasks = [
        {"id": "task-1", "description": "设计数据库结构", "agent": "agent-1"},
        {"id": "task-2", "description": "实现 API 接口", "agent": "agent-2"},
        {"id": "task-3", "description": "开发前端页面", "agent": "agent-3"}
    ]
    
    await collab.run_parallel(session_id, tasks)
    print(f"  ✓ 完成 {len(tasks)} 个并行任务")
    
    # 聚合结果
    report = await collab.aggregate_results(session_id)
    print(f"  📊 报告: {report['summary']}")
    
    # 结束会话
    summary = await collab.end_session(session_id)
    print(f"  ✓ 会话结束: {summary['completed_tasks']}/{summary['total_tasks']} 任务完成")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 Multi-Agent Communication Demo")
    print("=" * 60)
    
    # 运行所有演示
    await demo_basic_messaging()
    await demo_knowledge_sharing()
    await demo_group_chat()
    await demo_collaboration()
    
    print("\n" + "=" * 60)
    print("✅ 所有演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
