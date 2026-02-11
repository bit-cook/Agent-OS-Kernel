"""
Agent-OS-Kernel 锁管理器演示

展示锁管理器的使用方法
"""

from agent_os_kernel.core.lock_manager import LockManager, LockType


async def demo_lock_manager():
    """演示锁管理器"""
    print("=" * 60)
    print("Agent-OS-Kernel 锁管理器演示")
    print("=" * 60)
    
    # 创建锁管理器
    manager = LockManager()
    
    # 获取互斥锁
    lock = await manager.acquire_lock(
        resource="database",
        lock_type=LockType.MUTEX,
        timeout=30
    )
    
    if lock:
        print("\n获取互斥锁成功")
        
        # 执行操作
        print("执行受保护的操作...")
        
        # 释放锁
        await manager.release_lock(lock)
        print("锁已释放")
    
    # 获取读写锁
    read_lock = await manager.acquire_lock(
        resource="config",
        lock_type=LockType.READ,
        timeout=10
    )
    
    if read_lock:
        print("\n获取读锁成功")
        print("执行读操作...")
        await manager.release_lock(read_lock)
    
    # 获取统计
    stats = manager.get_statistics()
    print(f"\n锁统计:")
    print(f"  活动锁: {stats.active_locks}")
    print(f"  等待锁: {stats.waiting_locks}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_lock_manager())
