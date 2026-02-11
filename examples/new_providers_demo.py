#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
New LLM Providers Demo - 新 LLM 提供商演示

演示如何使用新增的 LLM 提供商:
- AI21 Labs (Jurassic 系列)
- Cerebras (Llama, Qwen 系列)
- Cloudflare Workers AI (边缘 AI)

Usage:
    python examples/new_providers_demo.py
"""

import asyncio
import os
from typing import List, Dict

# 设置环境变量 (实际使用时请使用真实的 API keys)
os.environ.setdefault("AI21_API_KEY", "your-ai21-api-key")
os.environ.setdefault("CEREBRAS_API_KEY", "your-cerebras-api-key")
os.environ.setdefault("CLOUDFLARE_API_TOKEN", "your-cloudflare-api-token")
os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", "your-account-id")


async def demo_ai21_provider():
    """演示 AI21 Provider"""
    print("\n" + "=" * 60)
    print("🤖 AI21 Labs Provider Demo (Jurassic Series)")
    print("=" * 60)

    from agent_os_kernel.llm.ai21_provider import AI21Provider
    from agent_os_kernel.llm.provider import LLMConfig, ProviderType

    # 创建配置
    config = LLMConfig(
        provider=ProviderType.AI21,
        model="j2-ultra",  # 或 j2-core, j2-7b-instruct
        api_key=os.getenv("AI21_API_KEY"),
        max_tokens=1000,
        temperature=0.7
    )

    # 创建 Provider
    provider = AI21Provider(config)

    print(f"\nProvider: {provider.provider_name}")
    print(f"Model: {provider.config.model}")
    print(f"Supported Models: {provider.supported_models}")

    try:
        # 初始化
        await provider.initialize()
        print("✅ Provider initialized successfully")

        # 模拟消息
        from agent_os_kernel.llm.provider import Message
        messages = [
            Message(role="system", content="You are a helpful AI assistant."),
            Message(role="user", content="What are the key features of Jurassic-2?")
        ]

        print("\n📤 Sending request to AI21...")
        # 注意: 实际调用需要有效的 API key
        # response = await provider.complete(messages)
        # print(f"📥 Response: {response.content}")

        print("✅ AI21 Provider demo completed")

    except Exception as e:
        print(f"⚠️  AI21 Demo (expected without API key): {e}")
    finally:
        await provider.shutdown()


async def demo_cerebras_provider():
    """演示 Cerebras Provider"""
    print("\n" + "=" * 60)
    print("⚡ Cerebras Provider Demo (High-Speed Inference)")
    print("=" * 60)

    from agent_os_kernel.llm.cerebras_provider import CerebrasProvider
    from agent_os_kernel.llm.provider import LLMConfig, ProviderType

    # 创建配置
    config = LLMConfig(
        provider=ProviderType.CEREBRAS,
        model="llama-3.1-8b",  # 或 llama-3.1-70b, qwen-2.5-7b-instruct
        api_key=os.getenv("CEREBRAS_API_KEY"),
        max_tokens=1000,
        temperature=0.7
    )

    # 创建 Provider
    provider = CerebrasProvider(config)

    print(f"\nProvider: {provider.provider_name}")
    print(f"Model: {provider.config.model}")
    print(f"Supported Models:")
    for model in provider.supported_models:
        print(f"  - {model}")

    try:
        # 初始化
        await provider.initialize()
        print("✅ Provider initialized successfully")

        # 模拟消息
        from agent_os_kernel.llm.provider import Message
        messages = [
            Message(role="user", content="Explain why Cerebras is fast.")
        ]

        print("\n📤 Sending request to Cerebras...")
        # 注意: 实际调用需要有效的 API key
        # response = await provider.complete(messages)
        # print(f"📥 Response: {response.content}")

        # 测试 token 计数
        test_text = "Cerebras provides high-speed AI inference through its Wafer-Scale Engine."
        tokens = await provider.count_tokens(test_text)
        print(f"\n📊 Token estimation for test text: {tokens}")

        print("✅ Cerebras Provider demo completed")

    except Exception as e:
        print(f"⚠️  Cerebras Demo (expected without API key): {e}")
    finally:
        await provider.shutdown()


async def demo_cloudflare_provider():
    """演示 Cloudflare Provider"""
    print("\n" + "=" * 60)
    print("🌥️  Cloudflare Workers AI Demo (Edge AI)")
    print("=" * 60)

    from agent_os_kernel.llm.cloudflare_provider import CloudflareProvider
    from agent_os_kernel.llm.provider import LLMConfig, ProviderType

    # 创建配置
    config = LLMConfig(
        provider=ProviderType.CLOUDFLARE,
        model="@cf/meta/llama-3-8b-instruct",  # 或 @cf/meta/llama-3-70b-instruct
        api_key=os.getenv("CLOUDFLARE_API_TOKEN"),
        max_tokens=1000,
        temperature=0.7
    )

    # 创建 Provider
    provider = CloudflareProvider(config)

    print(f"\nProvider: {provider.provider_name}")
    print(f"Model: {provider.config.model}")

    print("\n📋 Available Models:")
    print("\n  Chat Models:")
    chat_models = await provider.list_models_by_type("chat")
    for model in chat_models[:5]:  # 只显示前5个
        print(f"    - {model['id']} ({model['name']})")

    print("\n  Embedding Models:")
    embedding_models = await provider.list_models_by_type("embedding")
    for model in embedding_models:
        print(f"    - {model['id']} ({model['name']})")

    try:
        # 初始化
        await provider.initialize()
        print("\n✅ Provider initialized successfully")

        # 模拟消息
        from agent_os_kernel.llm.provider import Message
        messages = [
            Message(role="system", content="You are a helpful AI assistant."),
            Message(role="user", content="What are the benefits of edge AI?")
        ]

        print("\n📤 Sending request to Cloudflare...")
        # 注意: 实际调用需要有效的 API key
        # response = await provider.complete(messages)
        # print(f"📥 Response: {response.content}")

        print("✅ Cloudflare Provider demo completed")

    except Exception as e:
        print(f"⚠️  Cloudflare Demo (expected without API key): {e}")
    finally:
        await provider.shutdown()


async def demo_provider_comparison():
    """提供商对比演示"""
    print("\n" + "=" * 60)
    print("📊 Provider Comparison")
    print("=" * 60)

    from agent_os_kernel.llm.factory import get_factory, ProviderType

    factory = get_factory()
    providers = factory.list_providers()

    print("\n🤖 All Available Providers:")
    print("-" * 60)

    for info in providers:
        print(f"\n📌 {info.name}")
        print(f"   Type: {info.type.value}")
        print(f"   Description: {info.description}")
        print(f"   API Key Required: {'Yes' if info.requires_api_key else 'No'}")
        print(f"   Local: {'Yes' if info.local else 'No'}")
        print(f"   Default Model: {info.default_model}")


async def demo_provider_factory():
    """使用 Factory 创建 Provider"""
    print("\n" + "=" * 60)
    print("🏭 Provider Factory Demo")
    print("=" * 60)

    from agent_os_kernel.llm.factory import get_factory
    from agent_os_kernel.llm.provider import ProviderType

    factory = get_factory()

    # 获取特定 Provider 信息
    ai21_info = factory.get_provider_info("ai21")
    cerebras_info = factory.get_provider_info("cerebras")
    cloudflare_info = factory.get_provider_info("cloudflare")

    print("\n📋 New Provider Details:")
    print(f"\n  AI21 Labs:")
    print(f"    - Type: {ai21_info.type.value}")
    print(f"    - Name: {ai21_info.name}")
    print(f"    - Requires API Key: {ai21_info.requires_api_key}")
    print(f"    - Default Model: {ai21_info.default_model}")

    print(f"\n  Cerebras:")
    print(f"    - Type: {cerebras_info.type.value}")
    print(f"    - Name: {cerebras_info.name}")
    print(f"    - Requires API Key: {cerebras_info.requires_api_key}")
    print(f"    - Default Model: {cerebras_info.default_model}")

    print(f"\n  Cloudflare Workers AI:")
    print(f"    - Type: {cloudflare_info.type.value}")
    print(f"    - Name: {cloudflare_info.name}")
    print(f"    - Requires API Key: {cloudflare_info.requires_api_key}")
    print(f"    - Default Model: {cloudflare_info.default_model}")


async def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("🚀 New LLM Providers Demo 🚀")
    print("🚀" * 30)

    # 运行所有演示
    await demo_ai21_provider()
    await demo_cerebras_provider()
    await demo_cloudflare_provider()
    await demo_provider_comparison()
    await demo_provider_factory()

    print("\n" + "=" * 60)
    print("✅ All Demos Completed!")
    print("=" * 60)

    print("\n📚 Usage Instructions:")
    print("-" * 60)
    print("""
1. AI21 Labs:
   - Sign up at https://www.ai21.com/
   - Get API key from dashboard
   - Set environment variable: AI21_API_KEY

2. Cerebras:
   - Sign up at https://cloud.cerebras.ai/
   - Get API key from dashboard
   - Set environment variable: CEREBRAS_API_KEY

3. Cloudflare Workers AI:
   - Sign up at https://cloudflare.com/
   - Enable Workers AI in dashboard
   - Get API token with AI permissions
   - Set environment variables:
     - CLOUDFLARE_API_TOKEN
     - CLOUDFLARE_ACCOUNT_ID
    """)


if __name__ == "__main__":
    asyncio.run(main())
