"""
Local LLM Demo - 本地模型演示

演示如何在 Agent OS Kernel 中使用本地模型
"""

import asyncio

from agent_os_kernel.llm.provider import ChatMessage


async def demo_ollama():
    """Ollama 演示"""
    print("\n" + "=" * 60)
    print("Demo: Ollama Local Model")
    print("=" * 60)

    from agent_os_kernel.llm import LLMProviderFactory, LLMConfig

    try:
        factory = LLMProviderFactory()

        # Ollama 配置
        provider = factory.create(LLMConfig(
            provider="ollama",
            model="qwen2.5:7b",
            base_url="http://localhost:11434"
        ))

        print(f"✓ Ollama provider created: {provider.provider_name}")
        print(f"  Model: {provider.get_config().model}")

        # 测试聊天（当前 API：chat 接收 ChatMessage 对象列表）
        messages = [
            ChatMessage(role="user", content="你好，请介绍一下自己")
        ]

        result = await provider.chat(messages)
        print(f"✓ Response: {result.get('content', '')[:100]}...")

    except Exception as e:
        print(f"⚠️ Ollama not available: {e}")
        print("   Install: curl -fsSL https://ollama.ai | sh")
        print("   Then: ollama pull qwen2.5:7b")


async def demo_mock_local():
    """Mock 本地模型演示"""
    print("\n" + "=" * 60)
    print("Demo: Mock Local Model (Development)")
    print("=" * 60)

    from agent_os_kernel.llm import create_mock_provider

    provider = create_mock_provider()
    print(f"✓ Mock provider created: {provider.provider_name}")

    # 设置本地风格响应
    provider.set_response("local", "我是一个本地运行的 AI 助手，使用 Ollama/vLLM 提供支持。")

    # 当前 API：chat 接收 ChatMessage 对象列表（而非 dict）
    messages = [ChatMessage(role="user", content="local")]
    result = await provider.chat(messages)
    print(f"✓ Response: {result.get('content', '')}")


async def demo_factory():
    """工厂演示"""
    print("\n" + "=" * 60)
    print("Demo: Provider Factory")
    print("=" * 60)

    from agent_os_kernel.llm import LLMProviderFactory

    factory = LLMProviderFactory()

    # 列出所有 Provider
    providers = factory.list_providers()
    print(f"✓ Total providers: {len(providers)}")

    for info in providers:
        local = "🏠" if info.local else "☁️"
        print(f"  {local} {info.name}: {info.description}")

    # 过滤本地 Provider
    local_providers = [p for p in providers if p.local]
    print(f"\n✓ Local providers: {len(local_providers)}")
    for p in local_providers:
        print(f"  🏠 {p.name}: {p.default_model}")


async def demo_config():
    """配置演示"""
    print("\n" + "=" * 60)
    print("Demo: Configuration")
    print("=" * 60)

    import yaml

    # Ollama 配置
    ollama_config = {
        "llm": {
            "providers": [
                {
                    "name": "ollama-local",
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "base_url": "http://localhost:11434",
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            ]
        }
    }

    print("📄 Ollama Config:")
    print(yaml.dump(ollama_config, default_flow_style=False))

    # vLLM 配置
    vllm_config = {
        "llm": {
            "providers": [
                {
                    "name": "vllm-gpu",
                    "provider": "vllm",
                    "model": "meta-llama/Llama-3.1-8B-Instruct",
                    "base_url": "http://localhost:8000/v1",
                    "temperature": 0.1,
                    "max_tokens": 8192
                }
            ]
        }
    }

    print("📄 vLLM Config:")
    print(yaml.dump(vllm_config, default_flow_style=False))


async def demo_kernel_with_local():
    """内核集成演示"""
    print("\n" + "=" * 60)
    print("Demo: Kernel with Local Model")
    print("=" * 60)

    from agent_os_kernel import AgentOSKernel

    kernel = AgentOSKernel()
    print("✓ Kernel initialized")

    # 使用默认 Provider (可以配置为 Ollama)
    kernel.print_status()

    # 显示可用工具
    registry = kernel.tool_registry
    stats = registry.get_stats()
    print(f"✓ Available tools: {stats['total_tools']}")


async def demo_comparison():
    """性能对比演示"""
    print("\n" + "=" * 60)
    print("Demo: Local vs Cloud Comparison")
    print("=" * 60)

    from agent_os_kernel.llm import create_mock_provider

    print("\n📊 Cost Comparison:")
    print("-" * 40)
    print(f"{'Provider':<20} {'Cost/1M Tokens':<15} {'Privacy':<10}")
    print("-" * 40)
    print(f"{'Ollama (Local)':<20} {'$0.00':<15} {'✅ Full':<10}")
    print(f"{'vLLM (Local)':<20} {'$0.00':<15} {'✅ Full':<10}")
    print(f"{'OpenAI GPT-4':<20} {'$30.00':<15} {'❌ Data sent':<10}")
    print(f"{'Claude 3.5':<20} {'$15.00':<15} {'❌ Data sent':<10}")
    print(f"{'DeepSeek':<20} {'$0.28':<15} {'❌ Data sent':<10}")

    print("\n🚀 Advantages of Local Models:")
    print("  ✅ 隐私保护 - 数据不离开本地")
    print("  ✅ 零成本 - 无需 API 费用")
    print("  ✅ 离线可用 - 无需网络")
    print("  ✅ 定制化 - 可微调模型")
    print("  ✅ 速度快 - 无网络延迟")

    print("\n⚠️ Considerations:")
    print("  ⚠️ 需要 GPU 显存")
    print("  ⚠️ 模型大小限制")
    print("  ⚠️ 维护成本")


async def main():
    """运行所有演示"""
    print("=" * 60)
    print("🚀 Agent OS Kernel - Local LLM Demo")
    print("=" * 60)

    await demo_factory()
    await demo_mock_local()
    await demo_config()
    await demo_kernel_with_local()
    await demo_comparison()

    print("\n" + "=" * 60)
    print("✅ Local LLM Demo Complete!")
    print("=" * 60)
    print("\n📚 Learn More:")
    print("   docs/local-models.md")
    print("   https://ollama.ai")
    print("   https://docs.vllm.ai")


if __name__ == "__main__":
    asyncio.run(main())
