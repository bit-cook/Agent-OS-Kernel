"""
Agent-OS-Kernel 状态机演示

展示状态机的使用方法
"""

from agent_os_kernel.core.state_machine import StateMachine


def demo_state_machine():
    """演示状态机"""
    print("=" * 60)
    print("Agent-OS-Kernel 状态机演示")
    print("=" * 60)

    # 记录状态流转历史
    history = []

    def make_on_enter(state_name):
        def on_enter():
            history.append(state_name)
        return on_enter

    # 创建状态机
    sm = StateMachine(
        initial_state="pending",
        name="order-processing",
    )

    # 添加状态（带进入回调，用于记录历史）
    sm.add_state("pending", on_enter=make_on_enter("pending"))
    sm.add_state("processing", on_enter=make_on_enter("processing"))
    sm.add_state("completed", on_enter=make_on_enter("completed"))
    sm.add_state("cancelled", on_enter=make_on_enter("cancelled"))

    # 添加转换（事件用字符串表示）
    sm.add_transition("pending", "processing", "begin")
    sm.add_transition("processing", "completed", "complete")
    sm.add_transition("pending", "cancelled", "cancel")
    sm.add_transition("processing", "cancelled", "cancel")

    # 启动状态机（标记为运行中，并触发初始状态的 on_enter）
    sm.start()
    print(f"\n初始状态: {sm.current_state}")
    print(f"当前可用事件: {sm.get_possible_events()}")

    # 执行转换
    print(f"\n触发 'begin' -> {sm.trigger_event('begin')}")
    print(f"开始处理后: {sm.current_state}")
    print(f"当前可用事件: {sm.get_possible_events()}")

    print(f"触发 'complete' -> {sm.trigger_event('complete')}")
    print(f"完成后: {sm.current_state}")

    # 非法事件（当前状态没有该转换）
    print(f"\n在 '{sm.current_state}' 状态触发 'cancel' -> {sm.trigger_event('cancel')}")
    print(f"状态保持不变: {sm.current_state}")

    # 状态查询
    print(f"\n状态查询:")
    print(f"  是否在 completed: {sm.is_in_state('completed')}")
    print(f"  是否存在 'cancelled' 状态: {sm.has_state('cancelled')}")
    print(f"  所有状态: {sorted(sm.states)}")
    print(f"  前一个状态: {sm.previous_state}")

    # 取消路径（重置后走 cancel）
    print(f"\n--- 取消路径 ---")
    sm.reset()
    print(f"重置后: {sm.current_state}")
    print(f"触发 'cancel' -> {sm.trigger_event('cancel')}")
    print(f"取消后: {sm.current_state}")

    # 获取历史
    print(f"\n状态历史: {' -> '.join(history)}")

    # 查看某个状态的转换
    print(f"\n从 'pending' 出发的转换:")
    for t in sm.get_transitions("pending"):
        print(f"  事件 {t.event}: {t.from_state} -> {t.to_state}")

    sm.stop()
    print(f"\n状态机已停止")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_state_machine()
