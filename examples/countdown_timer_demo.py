# -*- coding: utf-8 -*-
"""
倒计时计时器示例代码

演示倒计时计时器的各种功能：
1. 基本倒计时
2. 定时提醒
3. 多次提醒
4. 异步支持
"""

import asyncio
import time
import threading
from agent_os_kernel.core.countdown_timer import (
    CountdownTimer,
    CountdownTimerManager,
    TimerAlert,
    TimerState
)


def example_basic_countdown():
    """示例1：基本倒计时"""
    print("=" * 50)
    print("示例1：基本倒计时")
    print("=" * 50)
    
    # 创建管理器
    manager = CountdownTimerManager()
    
    # 创建倒计时为5秒的计时器
    timer = asyncio.run(manager.create_timer(
        name="基本倒计时示例",
        duration_seconds=5.0,
        auto_start=False
    ))
    
    print(f"计时器已创建: {timer.name}")
    print(f"总时长: {timer.duration_seconds} 秒")
    print(f"初始状态: {timer.state.value}")
    
    # 在后台线程中运行计时器
    def run_timer():
        print("开始倒计时...")
        manager.run_countdown_sync(timer.timer_id, check_interval=0.1)
        print("倒计时完成！")
    
    thread = threading.Thread(target=run_timer)
    thread.start()
    
    # 主线程中监控进度
    while thread.is_alive():
        status = manager.get_timer_status(timer.timer_id)
        if status:
            print(f"  剩余时间: {status['remaining_time_string']} | 进度: {status['progress']*100:.1f}%")
        time.sleep(0.3)
    
    thread.join()
    manager.shutdown()
    print()


def example_single_alert():
    """示例2：单次提醒"""
    print("=" * 50)
    print("示例2：单次提醒")
    print("=" * 50)
    
    manager = CountdownTimerManager()
    
    # 创建10秒倒计时
    timer = asyncio.run(manager.create_timer(
        name="提醒示例",
        duration_seconds=10.0
    ))
    
    alert_triggered = {"count": 0}
    
    def alert_callback():
        alert_triggered["count"] += 1
        print(f"  🔔 提醒触发！这是第 {alert_triggered['count']} 次提醒")
    
    # 添加在5秒时触发的提醒
    asyncio.run(manager.add_alert(
        timer.timer_id,
        TimerAlert(
            alert_id="midpoint-alert",
            trigger_at=5.0,
            callback=alert_callback
        )
    ))
    
    print(f"已添加5秒时的提醒")
    
    def run_timer():
        print("开始10秒倒计时...")
        manager.run_countdown_sync(timer.timer_id, check_interval=0.1)
        print("倒计时完成！")
    
    thread = threading.Thread(target=run_timer)
    thread.start()
    
    # 监控进度
    while thread.is_alive():
        status = manager.get_timer_status(timer.timer_id)
        if status:
            print(f"  进度: {status['progress']*100:.1f}% ({status['remaining_time_string']})")
        time.sleep(0.5)
    
    thread.join()
    print(f"提醒被触发了 {alert_triggered['count']} 次")
    manager.shutdown()
    print()


def example_multiple_alerts():
    """示例3：多次提醒"""
    print("=" * 50)
    print("示例3：多次提醒")
    print("=" * 50)
    
    manager = CountdownTimerManager()
    
    # 创建6秒倒计时
    timer = asyncio.run(manager.create_timer(
        name="多次提醒示例",
        duration_seconds=6.0
    ))
    
    alert_count = {"total": 0}
    
    def alert_2s():
        alert_count["total"] += 1
        print(f"  🔔 2秒提醒 (第{alert_count['total']}次)")
    
    def alert_4s():
        alert_count["total"] += 1
        print(f"  🔔 4秒提醒 (第{alert_count['total']}次)")
    
    def alert_complete():
        alert_count["total"] += 1
        print(f"  🎉 倒计时完成！ (第{alert_count['total']}次)")
    
    # 添加多个提醒
    asyncio.run(manager.add_alert(
        timer.timer_id,
        TimerAlert(
            alert_id="alert-2s",
            trigger_at=2.0,
            callback=alert_2s
        )
    ))
    
    asyncio.run(manager.add_alert(
        timer.timer_id,
        TimerAlert(
            alert_id="alert-4s",
            trigger_at=4.0,
            callback=alert_4s
        )
    ))
    
    # 完成回调
    timer.on_complete = alert_complete
    
    print(f"已添加2秒、4秒提醒和完成回调")
    
    def run_timer():
        print("开始6秒倒计时...")
        manager.run_countdown_sync(timer.timer_id, check_interval=0.05)
    
    thread = threading.Thread(target=run_timer)
    thread.start()
    
    # 监控
    while thread.is_alive():
        status = manager.get_timer_status(timer.timer_id)
        if status:
            bar_length = 20
            filled = int(bar_length * status['progress'])
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"  [{bar}] {status['progress']*100:.1f}%")
        time.sleep(0.3)
    
    thread.join()
    print(f"\n总共触发了 {alert_count['total']} 次提醒/回调")
    manager.shutdown()
    print()


def example_repeating_alerts():
    """示例4：重复提醒"""
    print("=" * 50)
    print("示例4：重复提醒")
    print("=" * 50)
    
    manager = CountdownTimerManager()
    
    # 创建5秒倒计时，每1秒重复一次，最多3次
    timer = asyncio.run(manager.create_timer(
        name="重复提醒示例",
        duration_seconds=5.0
    ))
    
    repeat_count = [0]
    
    def repeating_alert():
        repeat_count[0] += 1
        print(f"  🔄 重复提醒 #{repeat_count[0]}")
    
    asyncio.run(manager.add_alert(
        timer.timer_id,
        TimerAlert(
            alert_id="repeat-alert",
            trigger_at=1.0,
            callback=repeating_alert,
            repeat=True,
            repeat_interval=1.0,
            max_repeats=3
        )
    ))
    
    print("已添加每1秒重复的提醒，最多3次")
    
    def run_timer():
        print("开始5秒倒计时...")
        manager.run_countdown_sync(timer.timer_id, check_interval=0.05)
    
    thread = threading.Thread(target=run_timer)
    thread.start()
    thread.join()
    
    print(f"\n重复提醒被触发了 {repeat_count[0]} 次")
    manager.shutdown()
    print()


def example_async_support():
    """示例5：异步支持"""
    print("=" * 50)
    print("示例5：异步支持")
    print("=" * 50)
    
    manager = CountdownTimerManager()
    
    async_results = []
    
    async def async_alert_callback(message):
        """异步提醒回调"""
        await asyncio.sleep(0.1)  # 模拟异步操作
        async_results.append(message)
        print(f"  ⚡ 异步回调执行: {message}")
    
    timer = asyncio.run(manager.create_timer(
        name="异步支持示例",
        duration_seconds=3.0
    ))
    
    asyncio.run(manager.add_alert(
        timer.timer_id,
        TimerAlert(
            alert_id="async-alert-1",
            trigger_at=1.0,
            callback=async_alert_callback,
            callback_args=("第一个异步提醒",)
        )
    ))
    
    asyncio.run(manager.add_alert(
        timer.timer_id,
        TimerAlert(
            alert_id="async-alert-2",
            trigger_at=2.0,
            callback=async_alert_callback,
            callback_args=("第二个异步提醒",)
        )
    ))
    
    print("已添加两个异步提醒回调")
    
    # 使用异步方式运行
    async def run_async():
        await manager.run_countdown_async(timer.timer_id, check_interval=0.05)
        print("异步倒计时完成！")
    
    asyncio.run(run_async())
    
    print(f"\n异步回调执行结果: {async_results}")
    manager.shutdown()
    print()


def example_pause_resume():
    """示例6：暂停和恢复"""
    print("=" * 50)
    print("示例6：暂停和恢复")
    print("=" * 50)
    
    manager = CountdownTimerManager()
    
    timer = asyncio.run(manager.create_timer(
        name="暂停恢复示例",
        duration_seconds=10.0
    ))
    
    asyncio.run(manager.start_timer(timer.timer_id))
    
    def run_with_pause():
        def pause_timer():
            time.sleep(2)
            asyncio.run(manager.pause_timer(timer.timer_id))
            print("  ⏸️ 计时器暂停")
            
            time.sleep(2)
            asyncio.run(manager.start_timer(timer.timer_id))
            print("  ▶️ 计时器恢复")
        
        pause_thread = threading.Thread(target=pause_timer)
        pause_thread.start()
        
        manager.run_countdown_sync(timer.timer_id, check_interval=0.1)
        pause_thread.join()
    
    print("开始10秒倒计时（将在2秒后暂停2秒）...")
    run_with_pause()
    
    manager.shutdown()
    print()


def example_complete_callback():
    """示例7：完成回调"""
    print("=" * 50)
    print("示例7：完成回调")
    print("=" * 50)
    
    manager = CountdownTimerManager()
    
    def on_complete_callback(*args, **kwargs):
        print(f"  ✅ 完成回调被调用！")
        print(f"     参数: {args}")
        print(f"     关键字参数: {kwargs}")
    
    timer = asyncio.run(manager.create_timer(
        name="完成回调示例",
        duration_seconds=2.0,
        on_complete=on_complete_callback,
        on_complete_args=("完成",),
        on_complete_kwargs={"status": "success"}
    ))
    
    print("开始2秒倒计时...")
    
    def run_timer():
        manager.run_countdown_sync(timer.timer_id, check_interval=0.05)
    
    thread = threading.Thread(target=run_timer)
    thread.start()
    thread.join()
    
    print(f"最终状态: {timer.state.value}")
    manager.shutdown()
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("  倒计时计时器 (Countdown Timer) 示例演示")
    print("=" * 60 + "\n")
    
    examples = [
        ("基本倒计时", example_basic_countdown),
        ("单次提醒", example_single_alert),
        ("多次提醒", example_multiple_alerts),
        ("重复提醒", example_repeating_alerts),
        ("异步支持", example_async_support),
        ("暂停和恢复", example_pause_resume),
        ("完成回调", example_complete_callback),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        print(f"\n[{i}/{len(examples)}] {name}")
        try:
            func()
        except KeyboardInterrupt:
            print("\n用户中断")
            break
        except Exception as e:
            print(f"错误: {e}")
    
    print("\n" + "=" * 60)
    print("  所有示例演示完成！")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
