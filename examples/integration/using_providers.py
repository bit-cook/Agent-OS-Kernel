"""
Provider Usage Examples

展示如何使用不同的 LLM Provider
"""

import asyncio
from agent_os_kernel import AgentOSKernel
from agent_os_kernel.llm import (
    LLMProviderFactory,
    LLMConfig,
    create_mock_provider,
)


async def demo_mock_provider():
    """Mock Provider 示例"""
    print("\n" + "=" * 60)
    print("1. Mock Provider (无需 API Key)")
    print("=" * 60)
    
    # 创建 Mock Provider
    provider = create_mock_provider()
    
    # 测试聊天
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! What can you do?"}
    ]
    
    result = await provider.chat(messages)
    
    print(f"\n模型: {result['model']}")
    print(f"响应: {result['content'][:200]}...")
    print(f"\nToken 使用:")
    usage = result['usage']
    print(f"  - Prompt: {usage['prompt_tokens']}")
    print(f"  - Completion: {usage['completion_tokens']}")
    print(f"  - Total: {usage['total_tokens']}")
    
    # 测试指标
    metrics = provider.get_metrics()
    print(f"\n指标: {metrics}")


async def demo_mock_responses():
    """Mock 自定义响应示例"""
    print("\n" + "=" * 60)
    print("2. Mock 自定义响应")
    print("=" * 60)
    
    provider = create_mock_provider()
    
    # 设置自定义响应
    provider.set_response("python", 
        "Here's a Python example:\n\n```python\nprint('Hello!')\n```")
    provider.set_response("help",
        "I can help with:\n- Writing code\n- Answering questions\n- Analyzing data")
    
    # 测试触发
    tests = ["Write some python code", "Help me please"]
    
    for msg in tests:
        result = await provider.chat([{"role": "user", "content": msg}])
        print(f"\n输入: {msg}")
        print(f"响应: {result['content'][:100]}...")


async def demo_kernel_with_mock():
    """内核 + Mock Provider 示例"""
    print("\n" + "=" * 60)
    print("3. AgentOSKernel + Mock Provider")
    print("=" * 60)
    
    # 创建内核
    kernel = AgentOSKernel()
    
    # 创建 Agent
    agent_pid = kernel.spawn_agent(
        name="MockAgent",
        task="Answer questions",
        priority=50
    )
    
    print(f"\n创建 Agent: {agent_pid}")
    
    # 获取 Agent 信息
    agent = kernel.get_agent(agent_pid)
    print(f"Agent 名称: {agent.get('name')}")
    print(f"Agent 任务: {agent.get('task')}")
    print(f"Agent 优先级: {agent.get('priority')}")
    
    # 列出所有 Agent
    agents = kernel.list_agents()
    print(f"\n总 Agent 数: {len(agents)}")


async def demo_provider_factory():
    """Provider 工厂示例"""
    print("\n" + "=" * 60)
    print("4. Provider Factory")
    print("=" * 60)
    
    factory = LLMProviderFactory()
    
    # 创建 Mock Provider
    mock = factory.create_mock()
    print(f"\nMock Provider: {mock.provider_name}")
    print(f"支持的模型: {mock.supported_models}")
    
    # 获取指标
    await mock.chat([{"role": "user", "content": "test"}])
    metrics = mock.get_metrics()
    print(f"请求次数: {metrics['total_requests']}")


def demo_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("5. 错误处理 (Mock)")
    print("=" * 60)
    
    from agent_os_kernel.llm.mock_provider import MockErrorProvider
    
    # 创建会出错的 Provider
    provider = MockErrorProvider()
    provider.set_error_rate(0.3)  # 30% 错误率
    
    # 测试错误处理
    success = 0
    errors = 0
    
    for i in range(10):
        try:
            result = asyncio.run(provider.chat([{"role": "user", "content": "test"}]))
            if result:
                success += 1
        except Exception as e:
            errors += 1
    
    print(f"\n成功: {success}/10")
    print(f"错误: {errors}/10")


async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 Agent OS Kernel - Provider Examples")
    print("=" * 60)
    
    await demo_mock_provider()
    await demo_mock_responses()
    await demo_kernel_with_mock()
    await demo_provider_factory()
    demo_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例完成!")
    print("=" * 60)
    
    print("\n📚 了解更多:")
    print("  - 真实 Provider: OpenAI, Anthropic, DeepSeek")
    print("  - 本地 Provider: Ollama, vLLM")
    print("  - 文档: docs/")


if __name__ == "__main__":
    asyncio.run(main())
