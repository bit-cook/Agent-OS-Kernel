"""
Claude Integration Example

展示 Claude API 的深度集成。
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig


async def demo_claude():
    """Claude 集成示例"""
    print("=" * 60)
    print("Claude 集成示例")
    print("=" * 60)
    
    # 检查 API Key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  请设置 ANTHROPIC_API_KEY 环境变量")
        return
    
    print(f"\n✅ API Key 已配置")
    
    # 创建 Provider
    factory = LLMProviderFactory()
    
    config = LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        max_tokens=8192,
        temperature=0.7
    )
    
    print(f"\n📦 创建 Claude Provider...")
    provider = factory.create(config)
    
    # 初始化
    print(f"\n🚀 初始化 Provider...")
    await provider.initialize()
    
    # 测试调用
    messages = [
        {"role": "user", "content": "你好，请简单介绍一下你自己。"}
    ]
    
    print(f"\n💬 发送测试请求...")
    response = await provider.complete(messages)
    
    print(f"\n📝 Claude 回复:")
    print("-" * 40)
    print(response.content[:500])
    print("-" * 40)
    
    # 关闭
    await provider.shutdown()
    
    print(f"\n✅ Claude 集成测试完成!")
    
    return provider


async def demo_claude_tools():
    """Claude 工具调用示例"""
    print("\n" + "=" * 60)
    print("Claude 工具调用示例")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY 未设置")
        return
    
    factory = LLMProviderFactory()
    
    config = LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        max_tokens=8192
    )
    
    provider = factory.create(config)
    await provider.initialize()
    
    # 定义工具
    tools = [
        {
            "name": "calculator",
            "description": "计算数学表达式",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式"
                    }
                },
                "required": ["expression"]
            }
        },
        {
            "name": "search",
            "description": "搜索信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    }
                },
                "required": ["query"]
            }
        }
    ]
    
    messages = [
        {"role": "user", "content": "计算 123 * 456，然后搜索 AI 的最新发展"}
    ]
    
    print(f"\n🔧 发送工具调用请求...")
    response = await provider.complete(messages, tools=tools)
    
    print(f"\n📝 响应:")
    print(response.content)
    
    if response.tool_calls:
        print(f"\n🔧 工具调用:")
        for tool_call in response.tool_calls:
            print(f"   - {tool_call}")
    
    await provider.shutdown()


async def demo_claude_streaming():
    """Claude 流式输出示例"""
    print("\n" + "=" * 60)
    print("Claude 流式输出示例")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY 未设置")
        return
    
    factory = LLMProviderFactory()
    
    config = LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key=api_key
    )
    
    provider = factory.create(config)
    await provider.initialize()
    
    messages = [
        {"role": "user", "content": "写一首关于 AI 的短诗"}
    ]
    
    print(f"\n🌊 流式输出:")
    print("-" * 40)
    
    stream = await provider.stream_complete(messages)
    
    async for chunk in stream.chunks:
        print(chunk, end="", flush=True)
    
    print("\n" + "-" * 40)
    
    await provider.shutdown()


async def demo_claude_context():
    """Claude 上下文管理示例"""
    print("\n" + "=" * 60)
    print("Claude 上下文管理示例")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY 未设置")
        return
    
    factory = LLMProviderFactory()
    
    config = LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        max_tokens=4096
    )
    
    provider = factory.create(config)
    await provider.initialize()
    
    # 模拟长对话
    conversation = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
    ]
    
    # 添加 50 条消息
    for i in range(50):
        conversation.append({
            "role": "user",
            "content": f"用户消息 {i+1}: 这是第 {i+1} 条消息。"
        })
        conversation.append({
            "role": "assistant",
            "content": f"助手回复 {i+1}: 收到，这是第 {i+1} 条回复。"
        })
    
    conversation.append({
        "role": "user",
        "content": "总结我们的对话"
    })
    
    # 统计 Token
    from agent_os_kernel.llm import Message
    
    msgs = [Message(**m) for m in conversation if m["role"] != "system"]
    token_count = await provider.count_tokens("\n".join([m.content for m in msgs]))
    
    print(f"\n📊 对话统计:")
    print(f"   消息数: {len(conversation)}")
    print(f"   估算 Token: {token_count}")
    print(f"   最大限制: {config.max_tokens}")
    
    # 如果超过限制，使用压缩
    if token_count > config.max_tokens:
        print(f"\n🔧 上下文超过限制，使用压缩...")
        # 这里可以集成 Context Compressor
        print(f"   (请参考 optimization_demo.py 中的压缩示例)")
    
    await provider.shutdown()


async def demo_with_kernel():
    """在 Agent 中使用 Claude"""
    print("\n" + "=" * 60)
    print("在 Agent 中使用 Claude")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY 未设置")
        return
    
    # 创建内核
    kernel = AgentOSKernel()
    
    # 配置 Claude Provider
    print(f"\n⚙️  配置 Agent...")
    
    agent_pid = kernel.spawn_agent(
        name="ClaudeAssistant",
        task="你是一个使用 Claude 的专业助手",
        priority=50
    )
    
    print(f"✅ Agent 创建: {agent_pid[:16]}...")
    
    # 获取 Agent 状态
    status = kernel.scheduler.get_process_status(agent_pid)
    print(f"\n📊 Agent 状态:")
    print(f"   名称: {status.get('name', 'N/A')}")
    print(f"   状态: {status.get('state', 'N/A')}")
    
    # 清理
    kernel.scheduler.terminate_process(agent_pid, reason="demo complete")
    
    return kernel


async def main():
    """主函数"""
    print("\n🚀 Claude 集成示例")
    print("=" * 60)
    
    # 1. 基础集成
    await demo_claude()
    
    # 2. 工具调用
    await demo_claude_tools()
    
    # 3. 流式输出
    await demo_claude_streaming()
    
    # 4. 上下文管理
    await demo_claude_context()
    
    # 5. 在 Agent 中使用
    await demo_with_kernel()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例完成!")
    print("=" * 60)
    
    print("\n📚 进一步阅读:")
    print("   - Anthropic Docs: https://docs.anthropic.com/")
    print("   - Claude API: https://docs.anthropic.com/claude-reference/")


if __name__ == "__main__":
    asyncio.run(main())
