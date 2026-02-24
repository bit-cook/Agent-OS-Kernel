"""
状态机测试模块
"""

import pytest
import time
from agent_os_kernel.core.state_machine import (
    StateMachine,
    HierarchicalStateMachine,
    ParallelStateMachine,
    TransitionType,
    state_machine
)


class TestStateMachine:
    """状态机基础测试"""
    
    def test_state_definition(self):
        """测试状态定义"""
        sm = StateMachine(initial_state="idle")
        
        # 初始状态应该被添加
        assert sm.has_state("idle")
        assert sm.current_state == "idle"
        
        # 添加更多状态
        sm.add_state("running")
        sm.add_state("completed")
        sm.add_state("error")
        
        assert sm.has_state("running")
        assert sm.has_state("completed")
        assert sm.has_state("error")
        assert len(sm.states) == 4
    
    def test_state_transition(self):
        """测试状态转换"""
        sm = StateMachine(initial_state="idle")
        sm.add_state("running")
        sm.add_state("completed")
        
        # 添加转换规则
        sm.add_transition("idle", "running", "start")
        sm.add_transition("running", "completed", "finish")
        sm.add_transition("completed", "idle", "reset")
        
        # 初始状态
        assert sm.current_state == "idle"
        
        # 触发 start 事件
        success = sm.trigger_event("start")
        assert success
        assert sm.current_state == "running"
        assert sm.previous_state == "idle"
        
        # 触发 finish 事件
        success = sm.trigger_event("finish")
        assert success
        assert sm.current_state == "completed"
        
        # 触发无效事件应该失败
        success = sm.trigger_event("invalid_event")
        assert not success
    
    def test_event_handling(self):
        """测试事件处理"""
        sm = StateMachine(initial_state="offline")
        sm.add_state("online")
        sm.add_state("busy")
        
        # 添加带条件的转换
        sm.add_transition("offline", "online", "connect")
        sm.add_transition("online", "busy", "start_work")
        sm.add_transition("busy", "online", "stop_work")
        
        # 测试事件触发
        assert sm.trigger_event("connect")
        assert sm.current_state == "online"
        
        assert sm.trigger_event("start_work")
        assert sm.current_state == "busy"
        
        assert sm.trigger_event("stop_work")
        assert sm.current_state == "online"
    
    def test_state_callbacks(self):
        """测试状态回调"""
        sm = StateMachine(initial_state="idle")
        sm.add_state("running")
        
        enter_calls = []
        exit_calls = []
        
        def on_enter_running():
            enter_calls.append("entered")
        
        def on_exit_idle():
            exit_calls.append("exited")
        
        sm.add_state("running", on_enter=on_enter_running)
        sm.add_transition("idle", "running", "start")
        
        # 添加 on_exit 回调
        sm._callbacks["idle"].on_exit = on_exit_idle
        
        # 触发转换
        sm.trigger_event("start")
        
        assert "entered" in enter_calls
        assert "exited" in exit_calls
    
    def test_guard_condition(self):
        """测试条件守卫"""
        sm = StateMachine(initial_state="locked")
        sm.add_state("unlocked")
        
        can_unlock = False
        
        def check_unlock():
            return can_unlock
        
        sm.add_transition("locked", "unlocked", "unlock", guard=check_unlock)
        
        # 初始状态
        assert sm.current_state == "locked"
        
        # 条件不满足时无法转换
        assert not sm.trigger_event("unlock")
        assert sm.current_state == "locked"
        
        # 满足条件后可以转换
        can_unlock = True
        assert sm.trigger_event("unlock")
        assert sm.current_state == "unlocked"
    
    def test_transition_action(self):
        """测试转换动作"""
        sm = StateMachine(initial_state="pending")
        sm.add_state("processing")
        sm.add_state("done")
        
        action_data = []
        
        def process_action(data):
            action_data.append(data)
        
        sm.add_transition(
            "pending",
            "processing",
            "start",
            action=process_action
        )
        sm.add_transition(
            "processing",
            "done",
            "complete"
        )
        
        # 触发带数据的转换
        sm.trigger_event("start", data={"task": "test"})
        
        assert len(action_data) == 1
        assert action_data[0]["task"] == "test"
    
    def test_start_stop(self):
        """测试启动和停止"""
        sm = StateMachine(initial_state="idle")
        sm.add_state("running")
        
        enter_calls = []
        
        def on_enter_running():
            enter_calls.append("running")
        
        sm.add_state("running", on_enter=on_enter_running)
        sm.add_transition("idle", "running", "start")
        
        sm.start()
        assert len(enter_calls) == 1
        
        sm.stop()
        assert sm.current_state == "running"
    
    def test_reset(self):
        """测试重置"""
        sm = StateMachine(initial_state="idle")
        sm.add_state("running")
        sm.add_state("completed")
        
        sm.add_transition("idle", "running", "start")
        sm.add_transition("running", "completed", "finish")
        
        # 状态机运行
        sm.start()
        sm.trigger_event("start")
        sm.trigger_event("finish")
        
        assert sm.current_state == "completed"
        
        # 重置
        sm.reset()
        assert sm.current_state == "idle"
    
    def test_possible_events(self):
        """测试获取可能的事件"""
        sm = StateMachine(initial_state="idle")
        sm.add_state("running")
        sm.add_state("completed")
        
        sm.add_transition("idle", "running", "start")
        sm.add_transition("idle", "error", "fail")
        
        events = sm.get_possible_events()
        assert "start" in events
        assert "fail" in events
        assert len(events) == 2
    
    def test_can_transition(self):
        """测试是否可以转换"""
        sm = StateMachine(initial_state="idle")
        sm.add_state("running")
        sm.add_state("completed")
        
        sm.add_transition("idle", "running", "start")
        sm.add_transition("running", "completed", "finish")
        
        assert sm.can_transition("start")
        assert not sm.can_transition("finish")
        assert not sm.can_transition("invalid")


class TestHierarchicalStateMachine:
    """层级状态机测试"""
    
    def test_hierarchical_states(self):
        """测试层级状态"""
        sm = HierarchicalStateMachine(initial_state="parent")
        sm.add_state("parent")
        sm.add_substate("parent", "child1")
        sm.add_substate("parent", "child2")
        
        assert sm.has_state("parent")
        assert sm.has_state("child1")
        assert sm.has_state("child2")
        assert sm._parent_map["child1"] == "parent"
        assert sm._parent_map["child2"] == "parent"


class TestParallelStateMachine:
    """并行状态机测试"""
    
    def test_parallel_states(self):
        """测试并行状态"""
        sm = ParallelStateMachine(initial_states=["state1", "state2"])
        
        sm.add_state("state3")
        
        assert "state1" in sm.current_states
        assert "state2" in sm.current_states
        assert "state3" not in sm.current_states


class TestStateMachineDecorator:
    """状态机装饰器测试"""
    
    def test_decorator(self):
        """测试状态机装饰器"""
        @state_machine("idle")
        class MyMachine:
            def __init__(self):
                self.entered = []
                self.exited = []
            
            def on_enter_running(self):
                self.entered.append("running")
            
            def on_exit_idle(self):
                self.exited.append("idle")
        
        obj = MyMachine()
        sm = obj._state_machine
        
        sm.add_state("running")
        sm.add_transition("idle", "running", "start")
        
        assert sm.current_state == "idle"
        
        sm.trigger_event("start")
        
        assert "running" in obj.entered
        assert "idle" in obj.exited


class TestEdgeCases:
    """边界情况测试"""
    
    def test_duplicate_state(self):
        """测试重复添加状态"""
        sm = StateMachine(initial_state="test")
        
        # 添加相同状态多次应该没问题
        sm.add_state("test")
        sm.add_state("test")
        sm.add_state("test")
        
        assert len(sm.states) == 1
    
    def test_no_transitions(self):
        """测试没有转换规则"""
        sm = StateMachine(initial_state="alone")
        sm.add_state("other")
        
        # 没有从 idle 出发的转换
        assert not sm.trigger_event("any")
    
    def test_empty_state_machine(self):
        """测试空状态机"""
        sm = StateMachine(initial_state="only")
        
        assert len(sm.states) == 1
        assert sm.current_state == "only"
    
    def test_multiple_guards(self):
        """测试多个守卫条件"""
        sm = StateMachine(initial_state="start")
        sm.add_state("a")
        sm.add_state("b")
        
        guard_a = False
        guard_b = True
        
        def guard_a_fn():
            return guard_a
        
        def guard_b_fn():
            return guard_b
        
        sm.add_transition("start", "a", "go", guard=guard_a_fn)
        sm.add_transition("start", "b", "go", guard=guard_b_fn)
        
        # 只有 b 的条件满足
        assert sm.trigger_event("go")
        assert sm.current_state == "b"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
