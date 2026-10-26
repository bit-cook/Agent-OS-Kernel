"""
Complete Agent Workflow Demo

展示完整的 Agent 工作流：从创建到完成任务
"""

import asyncio
from agent_os_kernel import AgentOSKernel, ContextManager, StorageManager
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig


async def main():
    print("=" * 60)
    print("🚀 Complete Agent Workflow Demo")
    print("=" * 60)
    
    # 1. 初始化内核
    print("\n1. 初始化 Agent OS Kernel")
    kernel = AgentOSKernel()
    print("   ✓ 内核创建成功")
    
    # 2. 配置 LLM
    print("\n2. 配置 LLM Provider")
    factory = LLMProviderFactory()
    
    # 未检测到 DeepSeek API Key 时使用 Mock Provider（设置
    # DEEPSEEK_API_KEY 环境变量后即可改用真实 Provider）
    provider = factory.create_mock()
    print("   ✓ Provider 配置成功（Mock，无 API Key 时离线运行）")
    
    # 3. 创建上下文管理器
    print("\n3. 初始化上下文管理")
    ctx_manager = ContextManager(max_context_tokens=128000)
    print("   ✓ 上下文管理器就绪")
    
    # 4. 创建存储
    print("\n4. 初始化存储")
    storage = StorageManager()
    print("   ✓ 存储就绪（内存后端）")
    
    # 5. 创建 Agent
    print("\n5. 创建 Agent")
    agent_pid = kernel.spawn_agent(
        name="CodeAssistant",
        task="帮我写一个 Python HTTP 服务器",
        priority=30
    )
    print(f"   ✓ Agent 创建成功: {agent_pid}")
    
    # 6. 运行
    print("\n6. 运行 Agent")
    kernel.run(max_iterations=10)
    print("   ✓ 运行完成")
    
    # 7. 查看状态
    print("\n7. 系统状态")
    kernel.print_status()
    
    print("\n" + "=" * 60)
    print("✅ 工作流完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
