#!/usr/bin/env python3
"""
Context Management Demo - 上下文管理演示

演示Agent-OS-Kernel的上下文管理功能:
- 页面分配与释放
- 上下文分层 (L1/L2/L3 Cache)
- Token管理
- 上下文压缩
- 上下文持久化

Usage:
    python context_management_demo.py
"""

import sys
import os
import time
from datetime import datetime, timezone

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Agent-OS-Kernel'))

from agent_os_kernel.core import ContextManager, AgentPool
from agent_os_kernel import AgentOSKernel


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step: str, description: str = ""):
    """打印步骤"""
    print(f"\n▶ {step}")
    if description:
        print(f"  {description}")


def demo_context_manager_creation():
    """演示创建上下文管理器"""
    print_step("1. 创建上下文管理器")
    
    print("\n创建 ContextManager 实例...")
    
    ctx = ContextManager(
        max_context_tokens=128000  # 默认128K
    )
    
    print(f"✓ ContextManager 创建成功")
    print(f"  最大Token: {ctx.max_context_tokens}")


def demo_page_allocation():
    """演示页面分配"""
    print_step("2. 页面分配 (Allocation)")
    
    ctx = ContextManager(max_context_tokens=128000)
    
    print("\n分配系统提示页面...")
    system_page = ctx.allocate_page(
        agent_pid="agent-001",
        content="""You are a helpful AI assistant specialized in research and analysis.
Your goal is to provide accurate, well-reasoned responses.""",
        importance=1.0,  # 最高重要性
        page_type="system"
    )
    print(f"✓ 系统页面分配成功: {system_page[:8]}...")
    
    print("\n分配任务页面...")
    task_page = ctx.allocate_page(
        agent_pid="agent-001",
        content="Research the latest developments in quantum computing.",
        importance=0.9,
        page_type="task"
    )
    print(f"✓ 任务页面分配成功: {task_page[:8]}...")
    
    print("\n分配工具定义页面...")
    tools_page = ctx.allocate_page(
        agent_pid="agent-001",
        content="Available tools: search, read_file, write_file, python_execute",
        importance=0.8,
        page_type="tools"
    )
    print(f"✓ 工具页面分配成功: {tools_page[:8]}...")
    
    print("\n分配对话历史页面...")
    history_page = ctx.allocate_page(
        agent_pid="agent-001",
        content="User: Hello! Assistant: Hi, how can I help?",
        importance=0.7,
        page_type="history"
    )
    print(f"✓ 对话历史页面分配成功: {history_page[:8]}...")
    
    print(f"\n共分配了 4 个页面")


def demo_context_retrieval():
    """演示上下文获取"""
    print_step("3. 上下文获取 (Retrieval)")
    
    ctx = ContextManager(max_context_tokens=128000)
    
    # 分配一些页面
    pages = []
    for i in range(3):
        page = ctx.allocate_page(
            agent_pid="agent-002",
            content=f"Content for page {i+1}. " * 50,
            importance=0.9 - i * 0.1,
            page_type="content"
        )
        pages.append(page)
    
    print("\n获取完整上下文...")
    full_context = ctx.get_agent_context("agent-002")
    print(f"✓ 上下文获取成功")
    print(f"  上下文长度: {len(full_context)} 字符")
    print(f"  估算Token数: {ctx._estimate_tokens(full_context)}")
    
    print("\n按重要性排序的上下文片段:")
    agent_page_ids = ctx.agent_pages.get("agent-002", [])
    for i, page_id in enumerate(agent_page_ids, 1):
        page = ctx.pages_in_memory.get(page_id)
        if page:
            print(f"  {i}. [{page.importance_score:.2f}] {page.page_type}: {len(page.content)} chars")


def demo_context_tiering():
    """演示上下文分层"""
    print_step("4. 上下文分层 (Tiered Context)")
    
    ctx = ContextManager(max_context_tokens=128000)
    
    print("\n上下文层级结构:")
    print("""
┌─────────────────────────────────────────────────────────┐
│                    上下文层级结构                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  L1 Cache (热数据)                                       │
│  ├── System Prompt (重要性: 1.0)                        │
│  ├── Task Description (重要性: 0.9)                     │
│  └── Tool Definitions (重要性: 0.8)                     │
│                                                          │
│  L2 Cache (温数据)                                       │
│  ├── Recent History (重要性: 0.7)                       │
│  └── Working Memory (重要性: 0.6)                       │
│                                                          │
│  L3 Cache (冷数据)                                       │
│  ├── Old History (重要性: 0.5)                          │
│  └── Archived Context (重要性: 0.4)                     │
│                                                          │
│  Storage (持久化)                                        │
│  └── Checkpoints (重要性: 0.3)                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
    """)
    
    # 分配不同层级的页面
    ctx.allocate_page("agent-003", "System prompt", 1.0, "system")
    ctx.allocate_page("agent-003", "Task description", 0.9, "task")
    ctx.allocate_page("agent-003", "Tool definitions", 0.8, "tools")
    ctx.allocate_page("agent-003", "Recent messages", 0.7, "history")
    ctx.allocate_page("agent-003", "Old conversations", 0.5, "history")
    
    # 获取分层上下文
    print("实际分层上下文:")
    agent_page_ids = ctx.agent_pages.get("agent-003", [])
    for page_id in agent_page_ids:
        page = ctx.pages_in_memory.get(page_id)
        if page:
            tier = ctx.memory_hierarchy.classify_page(page)
            print(f"  {tier}: {page.page_type} ({len(page.content)} chars)")


def demo_token_management():
    """演示Token管理"""
    print_step("5. Token管理 (Token Management)")
    
    ctx = ContextManager(max_context_tokens=128000)
    
    # 分配页面
    ctx.allocate_page("agent-004", "Short text", 0.9, "content")
    ctx.allocate_page("agent-004", "Medium length text " * 100, 0.8, "content")
    ctx.allocate_page("agent-004", "Long text " * 500, 0.7, "content")
    
    print("\nToken使用情况:")
    print(f"  最大Token: {ctx.max_context_tokens}")
    print(f"  当前使用: {ctx.current_usage}")
    
    print("\n预估不同文本的Token数:")
    test_texts = [
        ("短文本", "Hello, world!"),
        ("中文本", "This is a sample paragraph with multiple sentences."),
        ("长文本", "Lorem ipsum " * 100),
    ]
    
    for name, text in test_texts:
        tokens = ctx._estimate_tokens(text)
        print(f"  {name}: {tokens} tokens")


def demo_context_compression():
    """演示上下文压缩"""
    print_step("6. 上下文压缩 (Compression)")
    
    print("\n上下文压缩功能:")
    print("  ContextManager 支持多种压缩策略:")
    print("  - KV-Cache 优化: 静态内容前置，最大化缓存命中率")
    print("  - 语义重要性: 基于内容的语义分析")
    print("  - 页面置换: LRU + 重要性评分")
    
    # 演示压缩概念
    import zlib
    
    long_text = "This is a sample sentence. " * 100
    
    print(f"\n原始文本长度: {len(long_text)} 字符")
    
    # 简单的压缩演示
    compressed = zlib.compress(long_text.encode('utf-8'))
    print(f"压缩后长度: {len(compressed)} 字符")
    print(f"压缩率: {len(compressed)/len(long_text):.2%}")
    
    # 解压
    decompressed = zlib.decompress(compressed).decode('utf-8')
    print(f"解压后长度: {len(decompressed)} 字符")
    
    print("\n压缩算法:")
    print("  - zlib: Python标准库压缩")
    print("  - KV-Cache优化器: 静态内容识别和前置")
    print("  - 语义压缩: 基于意义的摘要(可选功能)")


def demo_context_persistence():
    """演示上下文持久化"""
    print_step("7. 上下文持久化 (Persistence)")
    
    ctx = ContextManager(max_context_tokens=128000)
    
    # 分配页面
    ctx.allocate_page("agent-005", "Important context", 1.0, "system")
    ctx.allocate_page("agent-005", "Task context", 0.9, "task")
    
    print("\n上下文持久化功能:")
    print("  ContextManager 支持持久化存储:")
    print("  - save_context(): 保存上下文到存储后端")
    print("  - load_context(): 从存储后端加载上下文")
    print("  - 自动检查点: 定期保存Agent状态")
    print("  - 跨会话恢复: 从检查点恢复Agent")
    
    # 模拟保存
    agent_context = ctx.get_agent_context("agent-005")
    print(f"\n当前上下文长度: {len(agent_context)} 字符")
    print("存储后端: PostgreSQL (通过 StorageManager)")
    
    # 获取存储中的页面
    pages_in_memory = len(ctx.pages_in_memory)
    pages_in_storage = len(ctx.swapped_pages)
    print(f"  内存中页面: {pages_in_memory}")
    print(f"  存储中页面: {pages_in_storage}")


def demo_context_eviction():
    """演示上下文淘汰"""
    print_step("8. 上下文淘汰 (Eviction)")
    
    ctx = ContextManager(
        max_context_tokens=1000  # 小限制以演示淘汰
    )
    
    print("\n模拟低Token限制下的上下文淘汰...")
    
    # 分配大量页面
    initial_count = len(ctx.pages_in_memory)
    for i in range(10):
        ctx.allocate_page(
            "agent-006",
            f"Page {i+1} content " * 50,
            importance=1.0 - i * 0.1,
            page_type="content"
        )
    
    print(f"分配前页面数: {initial_count}")
    print(f"分配后页面数: {len(ctx.pages_in_memory)}")
    print(f"当前使用Token: {ctx.current_usage}/{ctx.max_context_tokens}")
    
    print("\n淘汰策略:")
    print("  - LRU: 最近最少使用")
    print("  - LFU: 最不经常使用")
    print("  - 重要性: 基于重要性分数")
    print("  - 混合策略: 综合考虑以上因素")


def demo_kernel_integration():
    """演示与内核的集成"""
    print_step("9. 与内核集成 (Kernel Integration)")
    
    print("\n初始化带上下文管理的内核...")
    kernel = AgentOSKernel(max_context_tokens=128000)
    print("✓ 内核初始化完成")
    
    print("\n创建Agent (自动分配上下文页面)...")
    agent_id = kernel.spawn_agent(
        name="ContextDemoAgent",
        task="Demonstrate context management features"
    )
    print(f"✓ Agent创建成功: {agent_id}")
    
    print("\nAgent的上下文分配:")
    ctx = kernel.context_manager
    agent_context = ctx.get_agent_context(agent_id)
    print(f"  上下文长度: {len(agent_context)} 字符")
    print(f"  Token使用: {ctx.current_usage} / {ctx.max_context_tokens}")


def demo_summary():
    """演示总结"""
    print_step("10. 功能总结")
    
    print("""
上下文管理核心功能:

┌─────────────────────────────────────────────────────────┐
│               ContextManager 核心功能                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. 虚拟内存式管理                                       │
│     - 类似操作系统的虚拟内存机制                          │
│     - 按需加载和换出上下文页面                            │
│                                                          │
│  2. 多级缓存架构                                         │
│     - L1: 热数据 (System, Task, Tools)                  │
│     - L2: 温数据 (Recent History)                       │
│     - L3: 冷数据 (Old History)                          │
│                                                          │
│  3. Token预算控制                                        │
│     - 自动估算Token使用                                  │
│     - 超限时触发淘汰或压缩                                │
│                                                          │
│  4. 重要性分级                                           │
│     - 系统提示: 1.0 (最高)                               │
│     - 任务描述: 0.9                                      │
│     - 工具定义: 0.8                                      │
│     - 对话历史: 0.7 (动态调整)                           │
│                                                          │
│  5. 持久化支持                                           │
│     - 检查点保存                                         │
│     - 跨会话恢复                                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
    """)


def main():
    """主函数"""
    print_header("Agent-OS-Kernel 上下文管理演示")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("演示上下文管理的各项功能")
    
    # 1. 创建上下文管理器
    demo_context_manager_creation()
    
    # 2. 页面分配
    demo_page_allocation()
    
    # 3. 上下文获取
    demo_context_retrieval()
    
    # 4. 上下文分层
    demo_context_tiering()
    
    # 5. Token管理
    demo_token_management()
    
    # 6. 上下文压缩
    demo_context_compression()
    
    # 7. 上下文持久化
    demo_context_persistence()
    
    # 8. 上下文淘汰
    demo_context_eviction()
    
    # 9. 与内核集成
    demo_kernel_integration()
    
    # 10. 总结
    demo_summary()
    
    print_header("演示完成")
    print("上下文管理演示已结束!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
