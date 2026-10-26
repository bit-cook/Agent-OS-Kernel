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
    manager = LockManager(default_timeout=30.0, max_concurrent=100)

    # 获取互斥锁
    lock = await manager.acquire(
        name="database",
        owner_id="worker-1",
        lock_type=LockType.MUTEX,
        timeout_seconds=30,
    )

    if lock:
        print("\n获取互斥锁成功")
        print(f"  锁 ID: {lock.lock_id}")
        print(f"  持有者: {lock.owner_id}")
        print(f"  状态: {lock.status.value}")

        # 执行操作
        print("执行受保护的操作...")

        # 释放锁
        released = await manager.release("database", "worker-1")
        print(f"锁已释放: {'成功' if released else '失败'}")
        print(f"  是否仍锁定: {manager.is_locked('database')}")

    # 获取读写锁（读锁可被多个持有者同时获取）
    read_lock = await manager.acquire(
        name="config",
        owner_id="worker-2",
        lock_type=LockType.READ_WRITE,
        timeout_seconds=10,
    )

    if read_lock:
        print("\n获取读锁成功")
        print(f"  锁 ID: {read_lock.lock_id}")

        # 第二个持有者也可以拿到同一个读锁
        another = await manager.acquire(
            name="config",
            owner_id="worker-3",
            lock_type=LockType.READ_WRITE,
            timeout_seconds=10,
        )
        print(f"  第二个读锁持有者: {'成功' if another else '失败'}")

        print("执行读操作...")
        await manager.release("config", "worker-2")
        await manager.release("config", "worker-3")
        print(f"  读锁释放后是否仍锁定: {manager.is_locked('config')}")

    # 信号量
    ok = await manager.acquire_semaphore("api-slots", "worker-4", max_concurrent=2)
    print(f"\n获取信号量: {'成功' if ok else '失败'}")
    await manager.release("api-slots", "worker-4")

    # 获取统计
    stats = manager.get_stats()
    print(f"\n锁统计:")
    print(f"  累计获取: {stats['acquired']}")
    print(f"  累计释放: {stats['released']}")
    print(f"  活动锁: {stats['active_locks']}")
    print(f"  超时次数: {stats['timeouts']}")

    # 锁详情
    info = manager.get_lock_info("database")
    print(f"\n锁 'database' 详情: {info}")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_lock_manager())
