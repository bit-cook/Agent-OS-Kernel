# -*- coding: utf-8 -*-
"""
Distributed Lock Demo - 分布式锁示例

演示:
1. 互斥锁 (Mutex Lock)
2. 读写锁 (Read-Write Lock)
3. 锁续期 (Lock Renewal)
"""

import asyncio
import time
from agent_os_kernel.core.distributed_lock import (
    DistributedLock,
    ReadWriteLock,
    InMemoryLockBackend,
    ReadWriteLockBackend,
    create_distributed_lock,
    create_read_write_lock,
)


async def demo_mutex_lock():
    """演示互斥锁的基本用法"""
    print("\n" + "=" * 50)
    print("演示 1: 互斥锁 (Mutex Lock)")
    print("=" * 50)
    
    # 创建分布式锁实例
    lock = create_distributed_lock(InMemoryLockBackend())
    
    lock_name = "resource_1"
    
    print(f"\n1. 获取互斥锁...")
    owner_id = await lock.acquire_mutex(lock_name, expire=10.0)
    print(f"   锁获取成功，持有者ID: {owner_id}")
    
    # 检查锁状态
    is_locked = await lock.is_locked(lock_name)
    print(f"   锁状态: {'已锁定' if is_locked else '未锁定'}")
    
    # 获取锁信息
    info = await lock.get_lock_info(lock_name)
    print(f"   锁类型: {info['lock_type']}")
    print(f"   续期次数: {info['renewals']}")
    
    print(f"\n2. 模拟临界区操作...")
    # 模拟一些工作
    await asyncio.sleep(0.5)
    print("   [执行中] 正在处理资源...")
    await asyncio.sleep(0.3)
    print("   [完成] 资源处理完毕")
    
    print(f"\n3. 释放互斥锁...")
    success = await lock.release(lock_name, owner_id)
    print(f"   锁释放: {'成功' if success else '失败'}")
    
    is_locked = await lock.is_locked(lock_name)
    print(f"   锁状态: {'已锁定' if is_locked else '未锁定'}")
    
    print("\n" + "-" * 50)


async def demo_mutex_lock_with_context_manager():
    """演示使用上下文管理器的互斥锁"""
    print("\n" + "=" * 50)
    print("演示 2: 使用上下文管理器的互斥锁")
    print("=" * 50)
    
    lock = create_distributed_lock(InMemoryLockBackend())
    lock_name = "resource_2"
    
    print(f"\n使用上下文管理器获取锁: '{lock_name}'")
    
    async with lock.mutex_lock(lock_name, expire=10.0) as owner_id:
        print(f"   进入临界区，持有者: {owner_id}")
        print("   正在执行操作...")
        await asyncio.sleep(0.5)
        print("   操作完成，准备退出临界区")
    
    print("   已退出临界区，锁自动释放")
    print("\n" + "-" * 50)


async def demo_mutex_lock_contention():
    """演示互斥锁的竞争场景"""
    print("\n" + "=" * 50)
    print("演示 3: 互斥锁竞争")
    print("=" * 50)
    
    lock = create_distributed_lock(InMemoryLockBackend())
    lock_name = "contested_resource"
    
    results = []
    
    async def worker(worker_id: int):
        try:
            owner_id = await lock.acquire_mutex(lock_name, timeout=2.0, expire=5.0)
            print(f"   Worker {worker_id}: 获取锁成功 ({owner_id[:8]}...)")
            await asyncio.sleep(0.3)
            await lock.release(lock_name, owner_id)
            results.append(("success", worker_id))
            print(f"   Worker {worker_id}: 释放锁")
        except Exception as e:
            print(f"   Worker {worker_id}: 获取锁失败 - {e}")
            results.append(("failed", worker_id))
    
    print(f"\n启动 5 个 Worker 竞争获取锁...")
    workers = [worker(i) for i in range(5)]
    await asyncio.gather(*workers)
    
    successful = sum(1 for r in results if r[0] == "success")
    print(f"\n结果: {successful}/5 个 Worker 成功获取锁")
    print("\n" + "-" * 50)


async def demo_read_write_lock():
    """演示读写锁的用法"""
    print("\n" + "=" * 50)
    print("演示 4: 读写锁 (Read-Write Lock)")
    print("=" * 50)
    
    rw_lock = create_read_write_lock(ReadWriteLockBackend())
    lock_name = "shared_data"
    
    print("\n1. 测试读锁并发...")
    print("   尝试同时获取多个读锁...")
    
    # 模拟多个读取操作
    async def reader(reader_id: int):
        async with rw_lock.read(lock_name) as owner:
            print(f"   Reader {reader_id}: 读取数据中... (持有者: {owner[:8]}...)")
            await asyncio.sleep(0.2)
            return f"reader_{reader_id}_data"
    
    # 多个读取操作应该同时成功
    readers = [reader(i) for i in range(3)]
    results = await asyncio.gather(*readers)
    print(f"   读取结果: {len(results)} 个读操作全部成功")
    
    print("\n2. 测试写锁独占...")
    async with rw_lock.write(lock_name) as write_owner:
        print(f"   写锁获取成功 (持有者: {write_owner[:8]}...)")
        print("   正在写入数据（独占操作）...")
        await asyncio.sleep(0.3)
        print("   数据写入完成")
    
    print("\n3. 测试写锁阻塞读锁...")
    # 先获取写锁
    write_task = asyncio.create_task(
        rw_lock.acquire_write(lock_name, timeout=5.0)
    )
    await asyncio.sleep(0.1)  # 确保写锁开始等待
    
    # 尝试获取读锁（应该超时）
    try:
        await asyncio.wait_for(rw_lock.acquire_read(lock_name, timeout=0.2), timeout=0.3)
        print("   读锁获取成功（不应该发生）")
    except asyncio.TimeoutError:
        print("   读锁获取超时（写锁正在占用，符合预期）")
    
    # 取消写锁任务
    write_task.cancel()
    try:
        await write_task
    except asyncio.CancelledError:
        pass
    
    print("\n" + "-" * 50)


async def demo_lock_renewal():
    """演示锁续期机制"""
    print("\n" + "=" * 50)
    print("演示 5: 锁续期 (Lock Renewal)")
    print("=" * 50)
    
    lock = create_distributed_lock(InMemoryLockBackend())
    lock_name = "long_running_task"
    
    print("\n1. 获取锁并设置较短过期时间...")
    owner = await lock.acquire_mutex(lock_name, expire=0.5)
    print(f"   锁获取成功，持有者: {owner[:8]}...")
    
    info = await lock.get_lock_info(lock_name)
    print(f"   过期时间: {info['expire_time']:.3f}")
    print(f"   续期次数: {info['renewals']}")
    
    print("\n2. 定期续期...")
    renewal_count = 0
    
    def renewal_callback(success: bool, lock_name: str, owner_id: str):
        nonlocal renewal_count
        if success:
            renewal_count += 1
            print(f"   [续期回调] 第 {renewal_count} 次续期成功")
    
    # 启动定期续期
    renewal_task = await lock.renew_periodically(
        lock_name, owner, expire=0.5, interval=0.2, callback=renewal_callback
    )
    
    # 等待多次续期
    print("   等待锁续期...")
    await asyncio.sleep(0.7)
    
    # 取消续期
    renewal_task.cancel()
    try:
        await renewal_task
    except asyncio.CancelledError:
        pass
    
    info = await lock.get_lock_info(lock_name)
    print(f"\n   最终续期次数: {info['renewals']}")
    
    print("\n3. 手动续期...")
    success = await lock.renew(lock_name, owner, expire=1.0)
    print(f"   手动续期: {'成功' if success else '失败'}")
    
    info = await lock.get_lock_info(lock_name)
    print(f"   续期后总次数: {info['renewals']}")
    
    # 清理
    await lock.release(lock_name, owner)
    print("\n" + "-" * 50)


async def demo_lock_renewal_with_long_task():
    """演示锁续期在实际长任务中的应用"""
    print("\n" + "=" * 50)
    print("演示 6: 锁续期在实际长任务中的应用")
    print("=" * 50)
    
    lock = create_distributed_lock(InMemoryLockBackend())
    lock_name = "database_migration"
    
    print("\n场景: 执行数据库迁移任务 (需要 3 秒)")
    print("锁过期时间: 1 秒")
    print("续期间隔: 0.5 秒")
    
    # 获取锁
    owner = await lock.acquire_mutex(lock_name, expire=1.0)
    print(f"\n获取锁成功: {owner[:8]}...")
    
    renewal_count = 0
    
    def on_renewal(success, name, oid):
        nonlocal renewal_count
        renewal_count += 1
        elapsed = renewal_count * 0.5
        status = "✓" if success else "✗"
        print(f"   [{status}] 续期 {renewal_count} 次 (已运行 {elapsed:.1f} 秒)")
    
    # 启动续期
    renewal_task = await lock.renew_periodically(
        lock_name, owner, expire=1.0, interval=0.5, callback=on_renewal
    )
    
    # 执行长任务
    print("\n执行数据库迁移...")
    for i in range(6):
        await asyncio.sleep(0.5)
        phase = i + 1
        print(f"   阶段 {phase}/6: 迁移数据中...")
    
    # 取消续期
    renewal_task.cancel()
    try:
        await renewal_task
    except asyncio.CancelledError:
        pass
    
    # 释放锁
    await lock.release(lock_name, owner)
    
    print(f"\n任务完成! 总续期次数: {renewal_count}")
    print("\n" + "-" * 50)


async def demo_lock_info():
    """演示获取锁信息"""
    print("\n" + "=" * 50)
    print("演示 7: 获取锁信息")
    print("=" * 50)
    
    lock = create_distributed_lock(InMemoryLockBackend())
    
    # 创建多个锁
    locks = ["lock_a", "lock_b", "lock_c"]
    owners = {}
    
    print("\n获取多个锁:")
    for name in locks:
        owner = await lock.acquire_mutex(name, expire=30.0)
        owners[name] = owner
        print(f"   {name}: {owner[:8]}...")
    
    print("\n所有锁的信息:")
    for name in locks:
        info = await lock.get_lock_info(name)
        if info:
            print(f"\n   锁名称: {info['lock_name']}")
            print(f"   持有者: {info['owner_id']}")
            print(f"   类型: {info['lock_type']}")
            print(f"   获取时间: {info['acquire_time']:.3f}")
            print(f"   过期时间: {info['expire_time']:.3f}")
            print(f"   续期次数: {info['renewals']}")
            print(f"   已过期: {'是' if info['is_expired'] else '否'}")
    
    # 清理
    for name, owner in owners.items():
        await lock.release(name, owner)
    
    print("\n" + "-" * 50)


async def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("  分布式锁 (Distributed Lock) 演示")
    print("=" * 60)
    
    # 运行所有演示
    await demo_mutex_lock()
    await demo_mutex_lock_with_context_manager()
    await demo_mutex_lock_contention()
    await demo_read_write_lock()
    await demo_lock_renewal()
    await demo_lock_renewal_with_long_task()
    await demo_lock_info()
    
    print("\n" + "=" * 60)
    print("  演示完成!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
