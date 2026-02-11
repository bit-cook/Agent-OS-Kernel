"""
Agent-OS-Kernel Worker演示

展示Worker池的使用方法
"""

from agent_os_kernel.core.worker import WorkerPool, WorkerStatus


def demo_worker_pool():
    """演示Worker池"""
    print("=" * 60)
    print("Agent-OS-Kernel Worker池演示")
    print("=" * 60)
    
    # 创建池
    pool = WorkerPool(max_workers=4)
    print(f"\n✅ Worker池创建成功")
    print(f"   最大Worker数: {pool.max_workers}")
    
    # 获取统计
    stats = pool.get_stats()
    print(f"\nWorker统计:")
    print(f"  总Worker: {stats['total_workers']}")
    print(f"  可用Worker: {stats['available_workers']}")
    print(f"  成功任务: {stats['success_tasks']}")
    print(f"  失败任务: {stats['failed_tasks']}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_worker_pool()
