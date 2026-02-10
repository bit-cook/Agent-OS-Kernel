"""
Multi-Agent Collaboration Demo

展示 Agent 之间的通信、知识共享和协作功能。

功能：
1. 消息传递
2. 知识共享
3. 群聊协作
4. 任务委派
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel.agents.communication import (
    create_messenger,
    create_knowledge_sharing,
    create_group_chat_manager,
    create_collaboration,
    MessageType
)


async def demo_messenger():
    """消息传递示例"""
    print("=" * 60)
    print("消息传递系统示例")
    print("=" * 60)
    
    # 创建消息系统
    messenger = create_messenger()
    
    # 注册 Agent
    agents = [
        ("agent-1", "Alice"),
        ("agent-2", "Bob"),
        ("agent-3", "Carol")
    ]
    
    for agent_id, name in agents:
        await messenger.register_agent(agent_id, name)
    
    print(f"\n📋 已注册 {len(agents)} 个 Agent")
    
    # 1. 点对点消息
    print("\n💬 发送点对点消息...")
    
    from agent_os_kernel.agents.communication import Message
    
    msg = Message.create(
        msg_type=MessageType.CHAT,
        sender_id="agent-1",
        sender_name="Alice",
        content="你好 Bob! 我们来讨论一下项目计划。",
        receiver_id="agent-2"
    )
    
    await messenger.send(message)
    
    received = await messenger.receive("agent-2", timeout=2.0)
    
    if received:
        print(f"  ✅ Bob 收到: {received.content[:50]}...")
    
    # 2. 广播消息
    print("\n📢 发送广播消息...")
    
    broadcast = Message.create(
        msg_type=MessageType.NOTIFICATION,
        sender_id="agent-1",
        sender_name="Alice",
        content="会议将在 10 分钟后开始。",
        priority=80
    )
    
    await messenger.send(broadcast)
    
    # 3. 获取统计
    print("\n📊 消息统计:")
    stats = messenger.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return messenger


async def demo_knowledge_sharing():
    """知识共享示例"""
    print("\n" + "=" * 60)
    print("知识共享系统示例")
    print("=" * 60)
    
    # 创建知识共享系统
    knowledge = create_knowledge_sharing()
    
    # Agent 1 分享知识
    from agent_os_kernel.agents.communication.knowledge_share import KnowledgePacket, KnowledgeType
    
    print("\n📚 Agent 分享知识...")
    
    packets = [
        KnowledgePacket.create(
            knowledge_type=KnowledgeType.PROCEDURE,
            title="如何高效使用向量数据库",
            content="1. 选择合适的向量维度；2. 使用 HNSW 索引；3. 定期更新向量",
            source_agent="agent-1",
            source_task="vector_research",
            confidence=0.9,
            tags=["vector", "database", "optimization"]
        ),
        KnowledgePacket.create(
            knowledge_type=KnowledgeType.LESSON,
            title="并发编程的教训",
            content="1. 避免共享状态；2. 使用异步IO；3. 注意死锁问题",
            source_agent="agent-2",
            source_task="concurrency_research",
            confidence=0.85,
            tags=["concurrency", "programming"]
        ),
        KnowledgePacket.create(
            knowledge_type=KnowledgeType.FACT,
            title="PostgreSQL 特性",
            content="PostgreSQL 支持 JSON、向量、全文搜索等多种数据类型",
            source_agent="agent-3",
            source_task="database_research",
            confidence=0.95,
            tags=["postgresql", "database"]
        )
    ]
    
    for packet in packets:
        await knowledge.share(packet)
    
    print(f"   ✅ 分享了 {len(packets)} 条知识")
    
    # 检索知识
    print("\n🔍 检索知识...")
    
    results = await knowledge.retrieve(
        query="向量数据库优化",
        limit=5
    )
    
    for packet, score in results:
        print(f"   - [{score:.2f}] {packet.title}: {packet.content[:50]}...")
    
    # 统计
    print("\n📊 知识统计:")
    stats = await knowledge.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return knowledge


async def demo_group_chat():
    """群聊示例"""
    print("\n" + "=" * 60)
    print("群聊系统示例")
    print("=" * 60)
    
    # 创建群聊管理器
    chat_manager = create_group_chat_manager()
    
    # 创建群聊
    chat_id = chat_manager.create_chat(
        chat_id="project_discussion",
        topic="项目技术方案讨论",
        max_members=5
    )
    
    print(f"\n💬 创建群聊: {chat_id}")
    
    # 加入成员
    members = [
        ("agent-1", "Alice", "moderator", ["project", "planning"]),
        ("agent-2", "Bob", "expert", ["backend", "api"]),
        ("agent-3", "Carol", "speaker", ["frontend", "ui"])
    ]
    
    for agent_id, name, role, expertise in members:
        await chat_manager.join_chat(
            chat_id=chat_id,
            agent_id=agent_id,
            agent_name=name,
            role=role,
            expertise=expertise
        )
    
    print(f"   ✅ {len(members)} 个成员加入")
    
    # 发送消息
    messages = [
        ("agent-1", "Alice", "大家好，我们来讨论一下技术方案。"),
        ("agent-2", "Bob", "我建议使用 FastAPI 作为后端框架。"),
        ("agent-3", "Carol", "前端我推荐 Vue 3 + TypeScript。"),
        ("agent-2", "Bob", "同意！另外数据库用 PostgreSQL。"),
        ("agent-1", "Alice", "好达成共识！使用：\n- 后端: FastAPI\n- 前端: Vue 3\n- 数据库: PostgreSQL")
    ]
    
    print("\n💬 群聊消息:")
    for agent_id, name, content in messages:
        msg = await chat_manager.send_message(
            chat_id=chat_id,
            agent_id=agent_id,
            content=content
        )
        if msg:
            print(f"   {name}: {content[:60]}...")
    
    # 获取状态
    status = chat_manager.get_status(chat_id)
    print(f"\n📊 群聊状态:")
    print(f"   主题: {status['topic']}")
    print(f"   阶段: {status['phase']}")
    print(f"   消息数: {status['messages_count']}")
    
    return chat_manager


async def demo_collaboration():
    """协作示例"""
    print("\n" + "=" * 60)
    print("多 Agent 协作系统示例")
    print("=" * 60)
    
    # 创建协作系统
    collaboration = create_collaboration()
    
    # 创建协作会话
    session_id = await collaboration.create_session(
        session_id="project-alpha",
        name="项目 Alpha",
        agents=[
            {"id": "agent-1", "name": "Alice"},
            {"id": "agent-2", "name": "Bob"},
            {"id": "agent-3", "name": "Carol"}
        ]
    )
    
    print(f"\n🚀 创建协作会话: {session_id}")
    
    # 定义并行任务
    tasks = [
        {"id": "task-1", "description": "设计数据库结构", "agent": "agent-1", "priority": 1},
        {"id": "task-2", "description": "实现 API 接口", "agent": "agent-2", "priority": 2},
        {"id": "task-3", "description": "开发前端页面", "agent": "agent-3", "priority": 3}
    ]
    
    print("\n📋 执行并行任务...")
    
    # 并行执行
    task_ids = await collaboration.run_parallel(session_id, tasks)
    
    print(f"   ✅ 完成任务: {len(task_ids)} 个")
    
    # 聚合结果
    print("\n📊 聚合结果...")
    
    report = await collaboration.aggregate_results(session_id)
    
    print(f"   总任务: {report['total_tasks']}")
    print(f"   完成: {report['completed_tasks']}")
    print(f"   总结: {report['summary']}")
    
    # 结束会话
    summary = await collaboration.end_session(session_id)
    
    return collaboration


async def demo_complete_pipeline():
    """完整协作流水线"""
    print("\n" + "=" * 60)
    print("完整协作流水线")
    print("=" * 60)
    
    # 创建组件
    messenger = create_messenger()
    knowledge = create_knowledge_sharing()
    chat = create_group_chat_manager()
    collab = create_collaboration(
        messenger=messenger,
        knowledge_sharing=knowledge,
        group_chat=chat
    )
    
    # 启动
    await collab.start()
    
    # 1. 创建群聊讨论
    chat_id = chat.create_chat("brainstorm", "AI Agent 设计讨论")
    
    agents = [
        ("agent-1", "Alice", "moderator"),
        ("agent-2", "Bob", "expert"),
        ("agent-3", "Carol", "speaker")
    ]
    
    for agent_id, name, role in agents:
        await chat.join_chat(chat_id, agent_id, name, role)
        await messenger.register_agent(agent_id, name)
    
    print("\n🧠 头脑风暴讨论:")
    
    # 模拟讨论
    ideas = [
        ("agent-1", "Alice", "我们需要设计一个灵活的 Agent 框架。"),
        ("agent-2", "Bob", "我建议使用模块化设计，支持插件扩展。"),
        ("agent-3", "Carol", "同时要考虑性能和易用性。"),
        ("agent-2", "Bob", "好观点！我认为可以借鉴 AutoGen 的群聊模式。"),
        ("agent-1", "Alice", "达成共识：模块化 + AutoGen 风格 + 高性能")
    ]
    
    for agent_id, name, content in ideas:
        await chat.send_message(chat_id, agent_id, content)
        await messenger.send(
            Message.create(
                msg_type=MessageType.KNOWLEDGE,
                sender_id=agent_id,
                sender_name=name,
                content=content,
                receiver_id=None  # 广播
            )
        )
    
    print("   ✅ 讨论完成")
    
    # 2. 提取知识
    print("\n📚 提取知识...")
    
    from .knowledge_share import KnowledgePacket, KnowledgeType
    
    knowledge_items = [
        ("模块化设计", "使用插件机制实现模块化", "agent-2"),
        ("性能优化", "考虑异步和缓存策略", "agent-3"),
        ("用户体验", "平衡功能和易用性", "agent-1")
    ]
    
    for title, content, agent in knowledge_items:
        packet = KnowledgePacket.create(
            knowledge_type=KnowledgeType.INSIGHT,
            title=title,
            content=content,
            source_agent=agent,
            source_task="brainstorm",
            confidence=0.8
        )
        await knowledge.share(packet)
    
    print(f"   ✅ 提取 {len(knowledge_items)} 条知识")
    
    # 3. 执行协作任务
    print("\n🚀 执行协作任务...")
    
    await collab.create_session(
        session_id="implementation",
        name="实现阶段",
        agents=[
            {"id": "agent-1", "name": "Alice"},
            {"id": "agent-2", "name": "Bob"},
            {"id": "agent-3", "name": "Carol"}
        ]
    )
    
    tasks = [
        {"id": "impl-1", "description": "实现 Agent 基类", "agent": "agent-1"},
        {"id": "impl-2", "description": "实现消息系统", "agent": "agent-2"},
        {"id": "impl-3", "description": "实现群聊", "agent": "agent-3"},
        {"id": "impl-4", "description": "整合测试", "agent": "agent-1"}
    ]
    
    await collab.run_parallel("implementation", tasks)
    
    # 4. 聚合结果
    report = await collab.aggregate_results("implementation")
    
    print("\n📊 最终报告:")
    print(f"   任务: {report['total_tasks']}")
    print(f"   完成: {report['completed_tasks']}")
    
    # 5. 共享最终知识
    print("\n📚 共享最终知识...")
    
    final_knowledge = KnowledgePacket.create(
        knowledge_type=KnowledgeType.PROCEDURE,
        title="Agent 框架开发流程",
        content=f"通过协作完成：{report['summary']}",
        source_agent="system",
        source_task="implementation",
        confidence=0.9,
        tags=["process", "collaboration"]
    )
    await knowledge.share(final_knowledge)
    
    # 统计
    print("\n📈 系统统计:")
    
    print("   消息:")
    stats = messenger.get_statistics()
    for k, v in stats.items():
        print(f"   - {k}: {v}")
    
    print("   知识:")
    kstats = await knowledge.get_statistics()
    for k, v in kstats.items():
        print(f"   - {k}: {v}")
    
    await collab.stop()
    
    return collab


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 Multi-Agent Collaboration Demo")
    print("=" * 60)
    
    # 1. 消息传递
    await demo_messenger()
    
    # 2. 知识共享
    await demo_knowledge_sharing()
    
    # 3. 群聊
    await demo_group_chat()
    
    # 4. 协作
    await demo_collaboration()
    
    # 5. 完整流水线
    await demo_complete_pipeline()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例完成!")
    print("=" * 60)
    
    print("\n📚 进一步阅读:")
    print("   - AutoGen: https://microsoft.github.io/autogen/")
    print("   - AIOS: https://github.com/agiresearch/AIOS")


if __name__ == "__main__":
    asyncio.run(main())
