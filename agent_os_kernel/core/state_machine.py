"""
状态机模块 - State Machine Module

提供完整的状态机功能，包括：
- 状态定义
- 状态转换
- 事件处理
- 状态回调
"""

from typing import Dict, List, Callable, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import threading


class TransitionType(Enum):
    """转换类型"""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"


@dataclass
class Transition:
    """状态转换定义"""
    from_state: str
    to_state: str
    event: str
    guard: Optional[Callable[[], bool]] = None
    action: Optional[Callable[[Any], None]] = None
    transition_type: TransitionType = TransitionType.SYNCHRONOUS


@dataclass
class StateCallbacks:
    """状态回调"""
    on_enter: Optional[Callable[[], None]] = None
    on_exit: Optional[Callable[[], None]] = None
    on_update: Optional[Callable[[float], None]] = None


class StateMachine:
    """
    状态机实现
    
    示例:
        sm = StateMachine(initial_state="idle")
        sm.add_state("idle")
        sm.add_state("running")
        sm.add_state("completed")
        sm.add_transition("idle", "running", "start")
        sm.add_transition("running", "completed", "finish")
        
        sm.start()
        sm.trigger_event("start")
    """
    
    def __init__(
        self,
        initial_state: str,
        name: str = "StateMachine"
    ):
        """
        初始化状态机
        
        Args:
            initial_state: 初始状态名称
            name: 状态机名称
        """
        self.name = name
        self._initial_state = initial_state
        self._current_state = initial_state
        self._previous_state: Optional[str] = None
        self._states: Set[str] = set()
        self._transitions: Dict[str, List[Transition]] = {}
        self._callbacks: Dict[str, StateCallbacks] = {}
        self._event_queue: List[tuple] = []
        self._is_running = False
        self._lock = threading.RLock()
        
        # 注册初始状态
        self.add_state(initial_state)
    
    @property
    def current_state(self) -> str:
        """获取当前状态"""
        return self._current_state
    
    @property
    def previous_state(self) -> Optional[str]:
        """获取前一个状态"""
        return self._previous_state
    
    @property
    def initial_state(self) -> str:
        """获取初始状态"""
        return self._initial_state
    
    @property
    def states(self) -> Set[str]:
        """获取所有状态"""
        return self._states.copy()
    
    def add_state(
        self,
        state: str,
        on_enter: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        on_update: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        添加状态
        
        Args:
            state: 状态名称
            on_enter: 进入状态时的回调
            on_exit: 离开状态时的回调
            on_update: 状态更新时的回调（dt为时间增量）
        """
        with self._lock:
            self._states.add(state)
            self._transitions[state] = []
            self._callbacks[state] = StateCallbacks(
                on_enter=on_enter,
                on_exit=on_exit,
                on_update=on_update
            )
    
    def add_transition(
        self,
        from_state: str,
        to_state: str,
        event: str,
        guard: Optional[Callable[[], bool]] = None,
        action: Optional[Callable[[Any], None]] = None,
        transition_type: TransitionType = TransitionType.SYNCHRONOUS
    ) -> None:
        """
        添加状态转换
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            event: 触发事件
            guard: 条件守卫函数
            action: 转换动作函数
            transition_type: 转换类型
        """
        with self._lock:
            if from_state not in self._states:
                self.add_state(from_state)
            if to_state not in self._states:
                self.add_state(to_state)
            
            transition = Transition(
                from_state=from_state,
                to_state=to_state,
                event=event,
                guard=guard,
                action=action,
                transition_type=transition_type
            )
            self._transitions[from_state].append(transition)
    
    def add_transitions(
        self,
        transitions: List[Dict[str, Any]]
    ) -> None:
        """
        批量添加状态转换
        
        Args:
            transitions: 转换配置列表
        """
        for t in transitions:
            self.add_transition(
                from_state=t.get('from_state'),
                to_state=t.get('to_state'),
                event=t.get('event'),
                guard=t.get('guard'),
                action=t.get('action'),
                transition_type=t.get('transition_type', TransitionType.SYNCHRONOUS)
            )
    
    def get_transitions(self, state: str) -> List[Transition]:
        """获取指定状态的所有转换"""
        return self._transitions.get(state, [])
    
    def can_transition(self, event: str) -> bool:
        """
        检查是否可以进行指定事件的转换
        
        Args:
            event: 事件名称
            
        Returns:
            是否可以转换
        """
        with self._lock:
            for transition in self._transitions.get(self._current_state, []):
                if transition.event == event:
                    if transition.guard is None or transition.guard():
                        return True
            return False
    
    def trigger_event(self, event: str, data: Any = None) -> bool:
        """
        触发事件
        
        Args:
            event: 事件名称
            data: 事件数据
            
        Returns:
            是否成功触发转换
        """
        with self._lock:
            # 查找匹配的转换
            for transition in self._transitions.get(self._current_state, []):
                if transition.event == event:
                    # 检查条件守卫
                    if transition.guard is not None and not transition.guard():
                        return False
                    
                    # 执行状态退出回调
                    self._execute_callback(self._current_state, 'on_exit')
                    
                    # 记录前一个状态
                    self._previous_state = self._current_state
                    
                    # 执行转换动作
                    if transition.action:
                        transition.action(data)
                    
                    # 更新当前状态
                    self._current_state = transition.to_state
                    
                    # 执行状态进入回调
                    self._execute_callback(self._current_state, 'on_enter')
                    
                    return True
            return False
    
    def _execute_callback(self, state: str, callback_type: str) -> None:
        """执行状态回调"""
        callbacks = self._callbacks.get(state)
        if callbacks:
            callback = getattr(callbacks, callback_type, None)
            if callback:
                callback()
    
    def start(self) -> None:
        """启动状态机"""
        with self._lock:
            self._is_running = True
            self._execute_callback(self._current_state, 'on_enter')
    
    def stop(self) -> None:
        """停止状态机"""
        with self._lock:
            self._is_running = False
            self._execute_callback(self._current_state, 'on_exit')
    
    def reset(self) -> None:
        """重置状态机"""
        with self._lock:
            self.stop()
            self._current_state = self._initial_state
            self._previous_state = None
            self.start()
    
    def update(self, dt: float = 0.0) -> None:
        """
        更新状态机
        
        Args:
            dt: 时间增量（秒）
        """
        with self._lock:
            if self._is_running:
                self._execute_callback(self._current_state, 'on_update')
    
    def is_in_state(self, state: str) -> bool:
        """
        检查是否在指定状态
        
        Args:
            state: 状态名称
            
        Returns:
            是否在指定状态
        """
        return self._current_state == state
    
    def has_state(self, state: str) -> bool:
        """
        检查状态是否存在
        
        Args:
            state: 状态名称
            
        Returns:
            状态是否存在
        """
        return state in self._states
    
    def get_possible_events(self) -> List[str]:
        """获取当前状态下所有可能的事件"""
        events = []
        for transition in self._transitions.get(self._current_state, []):
            if transition.guard is None or transition.guard():
                events.append(transition.event)
        return events
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} '{self.name}': {self._current_state}>"


class HierarchicalStateMachine(StateMachine):
    """
    层级状态机
    
    支持状态的层级结构，子状态可以继承父状态的转换
    """
    
    def __init__(
        self,
        initial_state: str,
        name: str = "HierarchicalStateMachine"
    ):
        super().__init__(initial_state, name)
        self._parent_map: Dict[str, str] = {}
        self._history_state: Optional[str] = None
    
    def add_substate(
        self,
        parent_state: str,
        substate: str,
        on_enter: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None
    ) -> None:
        """
        添加子状态
        
        Args:
            parent_state: 父状态名称
            substate: 子状态名称
        """
        self.add_state(parent_state)
        self.add_state(substate, on_enter, on_exit)
        self._parent_map[substate] = parent_state
    
    def enter_parent_state(self, parent_state: str) -> bool:
        """
        进入父状态（进入其初始子状态）
        
        Args:
            parent_state: 父状态名称
            
        Returns:
            是否成功进入
        """
        if parent_state not in self._states:
            return False
        
        # 执行父状态进入回调
        self._execute_callback(parent_state, 'on_exit')
        self._previous_state = self._current_state
        
        # 查找初始子状态
        initial_substate = f"{parent_state}_initial"
        if initial_substate in self._states:
            self._current_state = initial_substate
        else:
            self._current_state = parent_state
        
        self._execute_callback(self._current_state, 'on_enter')
        return True


class ParallelStateMachine(StateMachine):
    """
    并行状态机
    
    支持多个状态同时处于活动状态
    """
    
    def __init__(
        self,
        initial_states: List[str],
        name: str = "ParallelStateMachine"
    ):
        super().__init__(initial_states[0] if initial_states else "", name)
        self._active_states: Set[str] = set(initial_states)
        self._initial_states = initial_states
    
    @property
    def current_states(self) -> Set[str]:
        """获取所有当前状态"""
        return self._active_states.copy()
    
    def add_state(
        self,
        state: str,
        on_enter: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        on_update: Optional[Callable[[float], None]] = None
    ) -> None:
        super().add_state(state, on_enter, on_exit, on_update)
        if state in self._initial_states:
            self._active_states.add(state)
    
    def trigger_event(self, event: str, data: Any = None) -> bool:
        """
        触发事件（所有匹配的状态都会尝试转换）
        
        Args:
            event: 事件名称
            data: 事件数据
            
        Returns:
            是否有任何状态成功转换
        """
        with self._lock:
            success = False
            for state in list(self._active_states):
                for transition in self._transitions.get(state, []):
                    if transition.event == event:
                        if transition.guard is None or transition.guard():
                            # 执行状态退出回调
                            self._execute_callback(state, 'on_exit')
                            
                            # 记录前一个状态
                            self._previous_state = state
                            
                            # 执行转换动作
                            if transition.action:
                                transition.action(data)
                            
                            # 更新当前状态
                            self._active_states.remove(state)
                            self._active_states.add(transition.to_state)
                            
                            # 执行状态进入回调
                            self._execute_callback(transition.to_state, 'on_enter')
                            
                            success = True
            return success


def state_machine(
    initial_state: str,
    name: str = "StateMachine"
) -> Callable[[type], type]:
    """
    状态机装饰器
    
    用于将类转换为状态机
    
    示例:
        @state_machine("idle")
        class MyClass:
            def on_enter_idle(self): ...
            def on_exit_idle(self): ...
    """
    def decorator(cls: type) -> type:
        sm = StateMachine(initial_state, name)
        
        # 自动发现状态方法
        for attr_name in dir(cls):
            if attr_name.startswith('on_enter_'):
                state = attr_name[9:]
                method = getattr(cls, attr_name)
                if callable(method):
                    sm.add_state(state, on_enter=method)
            elif attr_name.startswith('on_exit_'):
                state = attr_name[8:]
                method = getattr(cls, attr_name)
                if callable(method):
                    if state not in sm._callbacks:
                        sm.add_state(state)
                    sm._callbacks[state].on_exit = method
        
        # 存储状态机实例
        setattr(cls, '_state_machine', sm)
        
        # 添加代理方法
        original_init = cls.__init__
        
        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # 初始化后设置实例引用
            sm._instance = self
        
        cls.__init__ = new_init
        
        return cls
    
    return decorator


__all__ = [
    'StateMachine',
    'HierarchicalStateMachine',
    'ParallelStateMachine',
    'Transition',
    'StateCallbacks',
    'TransitionType',
    'state_machine'
]
