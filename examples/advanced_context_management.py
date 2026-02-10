"""
高级上下文管理示例

展示如何使用 Agent OS Kernel 的虚拟内存式上下文管理：
1. 自动页面置换
2. 重要性评分
3. KV-Cache 优化
4. 语义相似度检索
"""

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.context_manager import ContextPage, PageStatus


def demo_context_paging():
    """演示上下文分页机制"""
    
    # 创建内核（限制 token 数量来演示置换）
    kernel = AgentOSKernel(
        max_context_tokens=100,  # 限制以触发置换
        enable_swap=True
    )
    
    # 添加不同类型的页面
    system_prompt = """
    你是一个专业的数据分析助手。
    你的专长：Python 编程、数据分析、机器学习
    """
    
    # 系统提示（高重要性，应常驻）
    kernel.context_manager.add_page(
        agent_pid="analyst",
        content=system_prompt,
        tokens=len(system_prompt.split()),
        importance_score=0.95,
        page_type="system"
    )
    
    # 用户任务（中重要性）
    user_task = "请分析这份销售数据并给出建议"
    kernel.context_manager.add_page(
        agent_pid="analyst",
        content=user_task,
        tokens=len(user_task.split()),
        importance_score=0.8,
        page_type="task"
    )
    
    # 长期记忆（可变重要性）
    memory = "用户之前喜欢用 Pandas 进行数据处理"
    page = kernel.context_manager.add_page(
        agent_pid="analyst",
        content=memory,
        tokens=len(memory.split()),
        importance_score=0.6,
        page_type="memory"
    )
    
    # 工作内存（低重要性，可置换）
    working = "临时计算结果：平均销售额 = 15000"
    kernel.context_manager.add_page(
        agent_pid="analyst",
        content=working,
        tokens=len(working.split()),
        importance_score=0.3,
        page_type="working"
    )
    
    # 查看内存状态
    stats = kernel.context_manager.get_memory_stats()
    print(f"内存使用: {stats['usage_percent']:.1f}%")
    print(f"总页数: {stats['total_pages']}")
    
    # 当内存不足时，系统会自动置换低重要性页面
    # 添加大量内容触发置换
    for i in range(10):
        kernel.context_manager.add_page(
            agent_pid="analyst",
            content=f"临时数据 {i}: {i * 100}",
            tokens=5,
            importance_score=0.1,  # 低重要性
            page_type="working"
        )
    
    # 查看置换后的状态
    stats = kernel.context_manager.get_memory_stats()
    print(f"置换后内存使用: {stats['usage_percent']:.1f}%")
    
    # 检索被换出的页面
    swapped_pages = kernel.context_manager.get_swapped_pages("analyst")
    print(f"被换出的页面数: {len(swapped_pages)}")


def demo_importance_scoring():
    """演示重要性评分系统"""
    
    kernel = AgentOSKernel(max_context_tokens=1000)
    
    # 创建不同重要性的页面
    pages = [
        ("核心指令", "你是一个helpful assistant", 0.9),
        ("用户问题", "什么是机器学习？", 0.7),
        ("上下文", "对话历史：...", 0.5),
        ("临时结果", "中间计算：2+2=4", 0.2),
        ("无关内容", "用户说今天天气不错", 0.1),
    ]
    
    for name, content, importance in pages:
        kernel.context_manager.add_page(
            agent_pid="demo",
            content=content,
            tokens=len(content.split()),
            importance_score=importance,
            page_type="general"
        )
    
    # 获取所有页面及其重要性
    all_pages = kernel.context_manager.get_agent_pages("demo")
    
    # 按重要性排序
    sorted_pages = sorted(
        all_pages,
        key=lambda p: p.importance_score,
        reverse=True
    )
    
    print("页面重要性排序：")
    for page in sorted_pages:
        print(f"  {page.importance_score:.2f} - {page.page_type}")


def demo_swap_in_out():
    """演示页面换入换出"""
    
    kernel = AgentOSKernel(max_context_tokens=50, enable_swap=True)
    
    # 填充内存
    for i in range(20):
        kernel.context_manager.add_page(
            agent_pid="test",
            content=f"数据块 {i}: " + "x" * 20,
            tokens=5,
            importance_score=0.3
        )
    
    # 获取当前状态
    in_memory = len([p for p in kernel.context_manager.get_agent_pages("test") 
                    if p.status == PageStatus.IN_MEMORY])
    swapped = len([p for p in kernel.context_manager.get_agent_pages("test") 
                   if p.status == PageStatus.SWAPPED])
    
    print(f"内存中: {in_memory} 页面")
    print(f"已换出: {swapped} 页面")
    
    # 访问被换出的页面（触发换入）
    swapped_pages = kernel.context_manager.get_swapped_pages("test")
    if swapped_pages:
        page_id = swapped_pages[0].page_id
        kernel.context_manager.get_page(page_id)  # 这会触发换入
        
        print("触发了页面换入")


if __name__ == "__main__":
    print("=" * 50)
    print("高级上下文管理示例")
    print("=" * 50)
    
    print("\n1. 上下文分页演示：")
    demo_context_paging()
    
    print("\n2. 重要性评分演示：")
    demo_importance_scoring()
    
    print("\n3. 换入换出演示：")
    demo_swap_in_out()
    
    print("\n✓ 示例完成！")
