"""
Integration Tests - 完整集成测试
"""

import sys
sys.path.insert(0, '.')

import asyncio


async def test_kernel_init():
    """测试内核初始化"""
    print("\n" + "=" * 60)
    print("Integration Test: Kernel Initialization")
    print("=" * 60)
    
    from agent_os_kernel import AgentOSKernel
    
    kernel = AgentOSKernel()
    print("✓ Kernel created")
    
    # 检查内核组件
    assert kernel.context_manager is not None
    assert kernel.scheduler is not None
    assert kernel.tool_registry is not None
    print("✓ All subsystems initialized")
    
    print("✓ Kernel init test passed")
    return True


async def test_agent_spawning():
    """测试 Agent 创建"""
    print("\n" + "=" * 60)
    print("Integration Test: Agent Spawning")
    print("=" * 60)
    
    from agent_os_kernel import AgentOSKernel
    
    kernel = AgentOSKernel()
    
    # 创建 Agent
    agent_id = kernel.spawn_agent(
        name="TestAgent",
        task="Test task",
        priority=50
    )
    print(f"✓ Agent spawned: {agent_id}")
    
    # 列出 Agent
    agents = kernel.list_agents()
    print(f"✓ Listed agents: {len(agents)}")
    
    # 获取 Agent
    agent = kernel.get_agent(agent_id)
    assert agent is not None
    print(f"✓ Got agent: {agent.get('name')}")
    
    print("✓ Agent spawning test passed")
    return True


async def test_communication():
    """测试通信模块"""
    print("\n" + "=" * 60)
    print("Integration Test: Communication")
    print("=" * 60)
    
    from agent_os_kernel.agents.communication import (
        create_messenger,
        create_knowledge_sharing,
        Message,
        MessageType
    )
    
    # 创建消息系统
    messenger = create_messenger()
    await messenger.register_agent("agent-1", "Agent1")
    await messenger.register_agent("agent-2", "Agent2")
    print("✓ Agents registered")
    
    # 发送消息
    msg = Message.create(
        msg_type=MessageType.CHAT,
        sender_id="agent-1",
        sender_name="Agent1",
        content="Hello!",
        receiver_id="agent-2"
    )
    await messenger.send(msg)
    print("✓ Message sent")
    
    # 接收消息
    received = await messenger.receive("agent-2", timeout=2.0)
    assert received is not None
    print(f"✓ Message received: {received.content}")
    
    # 创建知识系统
    knowledge = create_knowledge_sharing()
    print("✓ Knowledge system created")
    
    print("✓ Communication test passed")
    return True


async def test_provider_factory():
    """测试 Provider 工厂"""
    print("\n" + "=" * 60)
    print("Integration Test: Provider Factory")
    print("=" * 60)
    
    from agent_os_kernel.llm import LLMProviderFactory
    
    factory = LLMProviderFactory()
    print("✓ Factory created")
    
    # 创建 Mock Provider
    mock = factory.create_mock()
    assert mock is not None
    print("✓ Mock provider created")
    
    # 检查 Provider 信息
    info = factory.get_provider_info("openai")
    assert info is not None
    print(f"✓ Provider info: {info.name}")
    
    print("✓ Provider factory test passed")
    return True


async def main():
    """运行所有集成测试"""
    print("=" * 60)
    print("Agent OS Kernel - Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Kernel Init", test_kernel_init),
        ("Agent Spawning", test_agent_spawning),
        ("Communication", test_communication),
        ("Provider Factory", test_provider_factory),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = await test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
