"""
MCP (Model Context Protocol) 集成示例

展示如何使用 MCP 协议连接外部工具服务器：
1. 连接 MCP 服务器
2. 发现和注册工具
3. 调用 MCP 工具
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.tools.mcp.registry import init_mcp_registry, get_mcp_registry


async def demo_mcp_basic():
    """MCP 基础示例"""
    print("=" * 60)
    print("MCP 基础示例")
    print("=" * 60)
    
    # 创建内核
    kernel = AgentOSKernel()
    
    # 初始化 MCP 注册表
    mcp_registry = init_mcp_registry(kernel.tool_registry)
    
    # 添加 MCP 服务器
    # 示例 1: Playwright MCP 服务器 (用于网页浏览)
    mcp_registry.add_server(
        name="playwright",
        command="npx",
        args=["@playwright/mcp@latest", "--headless"],
        env={"NODE_ENV": "production"}
    )
    
    # 示例 2: Filesystem MCP 服务器
    mcp_registry.add_server(
        name="filesystem",
        command="",
        url="http://localhost:3001/mcp"  # HTTP 方式
    )
    
    print("\n📡 已添加 MCP 服务器: playwright, filesystem")
    
    # 连接服务器
    print("\n🔌 连接 MCP 服务器...")
    
    # 连接 Playwright (STDIO 方式)
    connected = await mcp_registry.connect_server("playwright")
    if connected:
        print("✅ Playwright 服务器已连接")
    else:
        print("⚠️ Playwright 服务器连接失败 (需要手动启动)")
    
    # 发现工具
    print("\n🔍 发现 MCP 工具...")
    tools_count = await mcp_registry.discover_tools()
    print(f"✅ 发现 {tools_count} 个 MCP 工具")
    
    # 列出已注册的 MCP 工具
    wrapped_tools = mcp_registry.list_wrapped_tools()
    for tool in wrapped_tools[:5]:  # 只显示前5个
        print(f"  - {tool['name']} ({tool['server']})")
    
    return mcp_registry


async def demo_mcp_tool_calls():
    """MCP 工具调用示例"""
    print("\n" + "=" * 60)
    print("MCP 工具调用示例")
    print("=" * 60)
    
    mcp_registry = get_mcp_registry()
    if not mcp_registry:
        print("❌ MCP 注册表未初始化")
        return
    
    # 检查服务器状态
    health = await mcp_registry.health_check()
    print("\n🏥 MCP 服务器状态:")
    for server, status in health.items():
        print(f"  {server}: {'✅ 在线' if status else '❌ 离线'}")
    
    # 如果 Playwright 在线，演示调用
    if health.get("playwright", False):
        print("\n🧪 调用 Playwright 工具...")
        
        # 注意：实际调用需要有效的 MCP 服务器
        result = await mcp_registry.call_tool(
            "mcp_browser_navigate",
            url="https://example.com"
        )
        
        if result['success']:
            print("✅ 工具调用成功")
            print(f"📊 结果: {str(result['data'])[:200]}...")
        else:
            print(f"❌ 工具调用失败: {result['error']}")
    else:
        print("\n⚠️ Playwright 服务器离线，跳过工具调用演示")


async def demo_mcp_with_kernel():
    """在 Agent 中使用 MCP 工具"""
    print("\n" + "=" * 60)
    print("Agent 中使用 MCP 工具")
    print("=" * 60)
    
    kernel = AgentOSKernel()
    mcp_registry = init_mcp_registry(kernel.tool_registry)
    
    # 模拟添加 MCP 服务器
    mcp_registry.add_server(
        name="filesystem",
        command="npx",
        args=["@modelcontextprotocol/server-filesystem", "/tmp"]
    )
    
    # 连接并发现工具
    await mcp_registry.connect_server("filesystem")
    await mcp_registry.discover_tools()
    
    # 创建 Agent
    pid = kernel.spawn_agent(
        name="MCPWorker",
        task="使用 MCP 工具操作文件系统",
        priority=50
    )
    
    print(f"✅ Agent 创建: {pid[:16]}...")
    
    # Agent 可以使用 MCP 工具
    tools = kernel.tool_registry.list_tools()
    mcp_tools = [t for t in tools if t['name'].startswith('mcp_')]
    
    print(f"\n🔧 Agent 可用的 MCP 工具: {len(mcp_tools)} 个")
    for tool in mcp_tools[:3]:
        print(f"  - {tool['name']}: {tool['description'][:50]}...")
    
    # 清理
    kernel.scheduler.terminate_process(pid, reason="demo complete")
    await mcp_registry.close_all()
    
    return kernel


async def demo_common_mcp_servers():
    """常用 MCP 服务器示例"""
    print("\n" + "=" * 60)
    print("常用 MCP 服务器")
    print("=" * 60)
    
    servers = [
        {
            "name": "Playwright",
            "command": "npx",
            "args": ["@playwright/mcp@latest", "--headless"],
            "description": "网页浏览和自动化"
        },
        {
            "name": "Filesystem",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem", "/path/to/dir"],
            "description": "文件系统操作"
        },
        {
            "name": "Git",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-git"],
            "description": "Git 版本控制"
        },
        {
            "name": "Postgres",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-postgres"],
            "description": "PostgreSQL 数据库"
        },
        {
            "name": "Memory",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-memory"],
            "description": "知识图谱和记忆"
        }
    ]
    
    print("\n📦 推荐的 MCP 服务器:")
    for server in servers:
        print(f"\n  🔹 {server['name']}")
        print(f"     命令: {server['command']} {' '.join(server['args'])}")
        print(f"     功能: {server['description']}")
    
    print("\n💡 安装 MCP 服务器:")
    print("   npm install -g @playwright/mcp@latest")
    print("   npm install -g @modelcontextprotocol/server-filesystem")
    print("   ...")


async def main():
    """主函数"""
    print("\n🚀 MCP 集成示例")
    print("=" * 60)
    
    # 1. 基础示例
    await demo_mcp_basic()
    
    # 2. 工具调用示例
    await demo_mcp_tool_calls()
    
    # 3. Agent 中使用
    await demo_mcp_with_kernel()
    
    # 4. 常用服务器
    await demo_common_mcp_servers()
    
    print("\n" + "=" * 60)
    print("✅ MCP 示例完成!")
    print("=" * 60)
    
    print("\n📚 进一步阅读:")
    print("   - MCP 规范: https://modelcontextprotocol.io")
    print("   - MCP 服务器列表: https://github.com/modelcontextprotocol/servers")
    print("   - 官方文档: https://anthropic-docs.vercel.app")


if __name__ == "__main__":
    asyncio.run(main())
