"""
Agent-OS-Kernel 状态机演示

展示状态机的使用方法
"""

from agent_os_kernel.core.state_machine import StateMachine, State, Event


def demo_state_machine():
    """演示状态机"""
    print("=" * 60)
    print("Agent-OS-Kernel 状态机演示")
    print("=" * 60)
    
    # 创建状态机
    sm = StateMachine(
        name="order-processing",
        initial_state=State.PENDING
    )
    
    # 添加状态
    sm.add_state(State.PENDING, "订单已创建，等待处理")
    sm.add_state(State.PROCESSING, "订单正在处理")
    sm.add_state(State.COMPLETED, "订单已完成")
    sm.add_state(State.CANCELLED, "订单已取消")
    
    # 添加转换
    sm.add_transition(State.PENDING, State.PROCESSING, Event.START)
    sm.add_transition(State.PROCESSING, State.COMPLETED, Event.COMPLETE)
    sm.add_transition(State.PENDING, State.CANCELLED, Event.CANCEL)
    sm.add_transition(State.PROCESSING, State.CANCELLED, Event.CANCEL)
    
    # 执行转换
    print(f"\n初始状态: {sm.current_state}")
    
    sm.trigger(Event.START)
    print(f"启动后: {sm.current_state}")
    
    sm.trigger(Event.COMPLETE)
    print(f"完成后: {sm.current_state}")
    
    # 获取历史
    history = sm.get_history()
    print(f"\n状态历史: {history}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_state_machine()
