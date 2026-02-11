#!/usr/bin/env python3
"""ContextManager 使用示例"""

from agent_os_kernel.core.context_manager import ContextManager


def main():
    print("="*50)
    print("ContextManager 示例")
    print("="*50)
    
    # 1. 创建管理器
    print("\n1. 创建上下文管理器")
    
    ctx = ContextManager(max_context_tokens=10000)
    print(f"   最大token: {ctx.max_context_tokens}")
    
    # 2. 分配页面
    print("\n2. 分配上下文页面")
    
    page_id1 = ctx.allocate_page(
        agent_pid="agent-001",
        content="系统提示：你是一个有用的助手。",
        importance=0.9
    )
    page_id2 = ctx.allocate_page(
        agent_pid="agent-001",
        content="用户：你好！",
        importance=0.8
    )
    
    print(f"   页面1: {page_id1[:8]}...")
    print(f"   页面2: {page_id2[:8]}...")
    
    # 3. 获取上下文
    print("\n3. 获取完整上下文")
    
    context = ctx.get_agent_context("agent-001")
    print(f"   上下文长度: {len(context)} 字符")
    print(f"   内容预览: {context[:30]}...")
    
    # 4. Token估算
    print("\n4. Token估算")
    
    text = "这是一个测试文本。"
    tokens = ctx._estimate_tokens(text)
    print(f"   文本: '{text}'")
    print(f"   估算token: {tokens}")
    
    # 5. 释放
    print("\n5. 释放页面")
    
    released = ctx.release_agent_pages("agent-001")
    print(f"   释放页面数: {released}")
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)


if __name__ == "__main__":
    main()
