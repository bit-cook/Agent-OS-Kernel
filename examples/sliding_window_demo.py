"""
Agent-OS-Kernel 滑动窗口演示

展示滑动窗口处理器的使用方法
"""

from agent_os_kernel.core.batch_processor import SlidingWindowProcessor


def demo_sliding_window():
    """演示滑动窗口"""
    print("=" * 60)
    print("Agent-OS-Kernel 滑动窗口演示")
    print("=" * 60)
    
    # 创建窗口
    window = SlidingWindowProcessor(window_size=5)
    
    # 添加数据
    print("\n添加数据...")
    for i in range(10):
        window.add(i)
        data = window.get_all()
        print(f"  添加 {i}: {data}")
    
    # 窗口大小保持为5
    print(f"\n最终窗口: {window.get_all()}")
    print(f"窗口大小: {len(window.get_all())}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_sliding_window()
