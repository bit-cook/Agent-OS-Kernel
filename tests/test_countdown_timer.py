# -*- coding: utf-8 -*-
"""
倒计时计时器测试模块
"""

import pytest
import asyncio
import time
from datetime import datetime
from agent_os_kernel.core.countdown_timer import (
    CountdownTimer,
    CountdownTimerManager,
    TimerAlert,
    TimerState
)


class TestTimerAlert:
    """测试TimerAlert类"""
    
    def test_alert_creation(self):
        """测试提醒创建"""
        callback_called = []
        
        def callback():
            callback_called.append(True)
        
        alert = TimerAlert(
            alert_id="test-001",
            trigger_at=5.0,
            callback=callback,
            repeat=False
        )
        
        assert alert.alert_id == "test-001"
        assert alert.trigger_at == 5.0
        assert alert.repeat is False
        assert alert._trigger_count == 0
    
    def test_alert_should_trigger(self):
        """测试提醒触发检查"""
        callback_called = []
        
        def callback():
            callback_called.append(True)
        
        alert = TimerAlert(
            alert_id="test-002",
            trigger_at=3.0,
            callback=callback,
            repeat=False
        )
        
        # 未达到触发时间
        assert alert.should_trigger(2.0) is False
        assert alert._trigger_count == 0
        
        # 达到触发时间
        assert alert.should_trigger(3.0) is True
        assert alert._trigger_count == 1
        
        # 已触发过，不再触发
        assert alert.should_trigger(3.5) is False
    
    def test_alert_repeat(self):
        """测试重复提醒"""
        callback_count = [0]
        
        def callback():
            callback_count[0] += 1
        
        alert = TimerAlert(
            alert_id="test-003",
            trigger_at=2.0,
            callback=callback,
            repeat=True,
            repeat_interval=2.0,
            max_repeats=3
        )
        
        # 第一次触发
        assert alert.should_trigger(2.0) is True
        assert alert._trigger_count == 1
        
        # 未到下一次触发时间
        assert alert.should_trigger(3.0) is False
        
        # 第二次触发
        assert alert.should_trigger(4.0) is True
        assert alert._trigger_count == 2
        
        # 第三次触发
        assert alert.should_trigger(6.0) is True
        assert alert._trigger_count == 3
        
        # 达到最大重复次数，不再触发
        assert alert.should_trigger(8.0) is False


class TestCountdownTimer:
    """测试CountdownTimer类"""
    
    def test_timer_creation(self):
        """测试计时器创建"""
        timer = CountdownTimer(
            timer_id="timer-001",
            name="Test Timer",
            duration_seconds=60.0
        )
        
        assert timer.timer_id == "timer-001"
        assert timer.name == "Test Timer"
        assert timer.duration_seconds == 60.0
        assert timer.state == TimerState.STOPPED
        assert timer.remaining_seconds == 60.0
    
    def test_timer_auto_start(self):
        """测试自动启动"""
        timer = CountdownTimer(
            timer_id="timer-002",
            name="Auto Start Timer",
            duration_seconds=30.0,
            auto_start=True
        )
        
        assert timer.state == TimerState.RUNNING
        assert timer.start_time is not None
    
    def test_timer_start_pause_stop(self):
        """测试计时器启动、暂停、停止"""
        timer = CountdownTimer(
            timer_id="timer-003",
            name="Start Pause Timer",
            duration_seconds=100.0
        )
        
        # 初始状态
        assert timer.state == TimerState.STOPPED
        
        # 启动
        timer.start()
        assert timer.state == TimerState.RUNNING
        
        # 暂停
        timer.pause()
        assert timer.state == TimerState.PAUSED
        
        # 恢复运行
        timer.start()
        assert timer.state == TimerState.RUNNING
        
        # 停止
        timer.stop()
        assert timer.state == TimerState.STOPPED
    
    def test_timer_reset(self):
        """测试计时器重置"""
        timer = CountdownTimer(
            timer_id="timer-004",
            name="Reset Timer",
            duration_seconds=50.0,
            auto_start=True
        )
        
        time.sleep(0.1)
        timer.reset()
        
        assert timer.state == TimerState.STOPPED
        assert timer.remaining_seconds == 50.0
        assert timer.start_time is None
    
    def test_timer_cancel(self):
        """测试计时器取消"""
        timer = CountdownTimer(
            timer_id="timer-005",
            name="Cancel Timer",
            duration_seconds=120.0
        )
        
        timer.start()
        timer.cancel()
        
        assert timer.state == TimerState.CANCELLED
    
    def test_timer_progress(self):
        """测试计时器进度"""
        timer = CountdownTimer(
            timer_id="timer-006",
            name="Progress Timer",
            duration_seconds=10.0
        )
        
        timer.start()
        assert timer.progress == 0.0
        
        timer.pause()
        timer.paused_elapsed = 5.0
        
        assert timer.remaining_seconds == 5.0
        assert timer.progress == 0.5
    
    def test_timer_add_alerts(self):
        """测试添加提醒"""
        timer = CountdownTimer(
            timer_id="timer-007",
            name="Alert Timer",
            duration_seconds=60.0
        )
        
        alert_callback_called = []
        
        def alert_callback():
            alert_callback_called.append(True)
        
        alert_id = timer.add_alert_at(
            seconds=10.0,
            callback=alert_callback
        )
        
        assert len(timer.alerts) == 1
        assert timer.alerts[0].trigger_at == 10.0
    
    def test_timer_remaining_time_string(self):
        """测试剩余时间字符串格式化"""
        timer = CountdownTimer(
            timer_id="timer-008",
            name="String Timer",
            duration_seconds=3661.0  # 1小时1分1秒
        )
        
        timer.start()
        timer.pause()
        timer.paused_elapsed = 61.0  # 1分1秒
        
        remaining_str = timer.get_remaining_time_string()
        assert remaining_str == "01:00:00"


class TestCountdownTimerManager:
    """测试CountdownTimerManager类"""
    
    def test_manager_create_timer(self):
        """测试管理器创建计时器"""
        manager = CountdownTimerManager()
        
        timer = asyncio.run(manager.create_timer(
            name="Manager Timer 1",
            duration_seconds=60.0
        ))
        
        assert timer is not None
        assert timer.name == "Manager Timer 1"
        assert timer.timer_id in manager.timers
    
    def test_manager_delete_timer(self):
        """测试管理器删除计时器"""
        manager = CountdownTimerManager()
        
        timer = asyncio.run(manager.create_timer(
            name="Delete Timer",
            duration_seconds=30.0
        ))
        
        timer_id = timer.timer_id
        result = asyncio.run(manager.delete_timer(timer_id))
        
        assert result is True
        assert timer_id not in manager.timers
    
    def test_manager_get_timer(self):
        """测试管理器获取计时器"""
        manager = CountdownTimerManager()
        
        timer = asyncio.run(manager.create_timer(
            name="Get Timer",
            duration_seconds=45.0
        ))
        
        retrieved = asyncio.run(manager.get_timer(timer.timer_id))
        
        assert retrieved is not None
        assert retrieved.timer_id == timer.timer_id
    
    def test_manager_list_timers(self):
        """测试管理器列出计时器"""
        manager = CountdownTimerManager()
        
        asyncio.run(manager.create_timer(name="Timer 1", duration_seconds=30.0))
        asyncio.run(manager.create_timer(name="Timer 2", duration_seconds=60.0))
        
        timers = asyncio.run(manager.list_timers())
        
        assert len(timers) == 2
    
    def test_countdown(self):
        """测试基本倒计时功能"""
        manager = CountdownTimerManager()
        
        alert_times = []
        
        def on_complete():
            pass
        
        timer = asyncio.run(manager.create_timer(
            name="Countdown Test",
            duration_seconds=1.0,
            on_complete=on_complete
        ))
        
        # 同步运行倒计时
        import threading
        result = {"completed": False}
        
        def run_timer():
            manager.run_countdown_sync(timer.timer_id, check_interval=0.05)
            result["completed"] = True
        
        thread = threading.Thread(target=run_timer)
        thread.start()
        thread.join(timeout=5.0)
        
        assert result["completed"] is True
        manager.shutdown()
    
    def test_multiple_alerts(self):
        """测试多次提醒功能"""
        manager = CountdownTimerManager()
        
        alert_calls = []
        
        def alert_callback(value):
            alert_calls.append(value)
        
        timer = asyncio.run(manager.create_timer(
            name="Multiple Alerts Test",
            duration_seconds=2.0
        ))
        
        # 添加多个提醒
        asyncio.run(manager.add_alert(
            timer.timer_id,
            TimerAlert(
                alert_id="alert-1",
                trigger_at=0.5,
                callback=alert_callback,
                callback_args=(1,)
            )
        ))
        
        asyncio.run(manager.add_alert(
            timer.timer_id,
            TimerAlert(
                alert_id="alert-2",
                trigger_at=1.0,
                callback=alert_callback,
                callback_args=(2,)
            )
        ))
        
        asyncio.run(manager.add_alert(
            timer.timer_id,
            TimerAlert(
                alert_id="alert-3",
                trigger_at=1.5,
                callback=alert_callback,
                callback_args=(3,)
            )
        ))
        
        # 同步运行
        def run_timer():
            manager.run_countdown_sync(timer.timer_id, check_interval=0.05)
        
        import threading
        thread = threading.Thread(target=run_timer)
        thread.start()
        thread.join(timeout=5.0)
        
        # 验证所有提醒都被触发
        assert len(alert_calls) == 3
        assert 1 in alert_calls
        assert 2 in alert_calls
        assert 3 in alert_calls
        manager.shutdown()
    
    def test_async_support(self):
        """测试异步支持"""
        manager = CountdownTimerManager()
        
        async_results = []
        
        async def async_callback(value):
            await asyncio.sleep(0.01)
            async_results.append(value)
        
        timer = asyncio.run(manager.create_timer(
            name="Async Test",
            duration_seconds=1.0
        ))
        
        asyncio.run(manager.add_alert(
            timer.timer_id,
            TimerAlert(
                alert_id="async-alert",
                trigger_at=0.5,
                callback=async_callback,
                callback_args=("async_value",)
            )
        ))
        
        # 异步运行
        async def run_async():
            await manager.run_countdown_async(timer.timer_id, check_interval=0.05)
        
        asyncio.run(run_async())
        
        # 验证异步回调被调用
        assert len(async_results) == 1
        assert async_results[0] == "async_value"
        manager.shutdown()
    
    def test_timer_cancel(self):
        """测试计时器取消功能"""
        manager = CountdownTimerManager()
        
        timer = asyncio.run(manager.create_timer(
            name="Cancel Test",
            duration_seconds=10.0
        ))
        
        asyncio.run(manager.start_timer(timer.timer_id))
        
        # 在后台运行计时器
        import threading
        cancel_called = {"value": False}
        
        def run_with_cancel():
            def cancel_timer():
                import time
                time.sleep(0.2)
                asyncio.run(manager.cancel_timer(timer.timer_id))
            
            cancel_thread = threading.Thread(target=cancel_timer)
            cancel_thread.start()
            
            manager.run_countdown_sync(timer.timer_id, check_interval=0.05)
            cancel_called["value"] = True
            cancel_thread.join()
        
        thread = threading.Thread(target=run_with_cancel)
        thread.start()
        thread.join(timeout=5.0)
        
        assert cancel_called["value"] is True
        assert timer.state == TimerState.CANCELLED
        manager.shutdown()


class TestTimerState:
    """测试计时器状态"""
    
    def test_timer_state_transitions(self):
        """测试状态转换"""
        timer = CountdownTimer(
            timer_id="state-test",
            name="State Test",
            duration_seconds=100.0
        )
        
        # 初始状态
        assert timer.state == TimerState.STOPPED
        
        # 启动 -> 运行
        timer.start()
        assert timer.state == TimerState.RUNNING
        
        # 暂停 -> 暂停
        timer.pause()
        assert timer.state == TimerState.PAUSED
        
        # 暂停 -> 恢复运行
        timer.start()
        assert timer.state == TimerState.RUNNING
        
        # 停止 -> 停止
        timer.stop()
        assert timer.state == TimerState.STOPPED
        
        # 取消 -> 取消
        timer.start()
        timer.cancel()
        assert timer.state == TimerState.CANCELLED
    
    def test_invalid_state_transitions(self):
        """测试无效状态转换"""
        timer = CountdownTimer(
            timer_id="invalid-test",
            name="Invalid Test",
            duration_seconds=50.0
        )
        
        # 尝试暂停未运行的计时器
        result = timer.pause()
        assert result is False
        assert timer.state == TimerState.STOPPED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
