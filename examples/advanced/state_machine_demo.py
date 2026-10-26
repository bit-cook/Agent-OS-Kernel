# -*- coding: utf-8 -*-

"""状态机演示"""

import asyncio
from agent_os_kernel.core.state_machine import StateMachine


async def main():
    print("="*60)
    print("State Machine Demo")
    print("="*60)

    # 创建订单处理状态机（initial_state 为必填参数）
    order_fsm = StateMachine(
        initial_state="created",
        name="order_processing"
    )

    # 状态转换历史（通过 transition action 记录）
    history = []

    def record_transition(from_state, to_state, event):
        def action(data=None):
            history.append({"from": from_state, "to": to_state, "event": event})
        return action

    # 定义状态进入/退出回调
    def on_created():
        print("  📦 订单已创建")

    def on_processing():
        print("  🔄 正在处理")

    def on_shipped():
        print("  📤 订单已发货")

    def on_delivered():
        print("  ✅ 订单已送达")

    def on_cancelled():
        print("  ❌ 订单已取消")

    # 添加状态
    order_fsm.add_state("created", on_enter=on_created)
    order_fsm.add_state("processing", on_enter=on_processing)
    order_fsm.add_state("shipped", on_enter=on_shipped)
    order_fsm.add_state("delivered", on_enter=on_delivered)
    order_fsm.add_state("cancelled", on_enter=on_cancelled)

    # 添加转换（action 用于记录历史）
    order_fsm.add_transition("created", "processing", "start_processing",
                             action=record_transition("created", "processing", "start_processing"))
    order_fsm.add_transition("processing", "shipped", "ship",
                             action=record_transition("processing", "shipped", "ship"))
    order_fsm.add_transition("shipped", "delivered", "deliver",
                             action=record_transition("shipped", "delivered", "deliver"))
    order_fsm.add_transition("created", "cancelled", "cancel",
                             action=record_transition("created", "cancelled", "cancel"))
    order_fsm.add_transition("processing", "cancelled", "cancel",
                             action=record_transition("processing", "cancelled", "cancel"))

    print("\n🚀 启动状态机...")
    order_fsm.start()  # 触发初始状态的 on_enter

    print(f"  当前状态: {order_fsm.current_state}")
    print(f"  可用事件: {order_fsm.get_possible_events()}")

    print("\n📋 发送事件...")
    for event in ["start_processing", "ship", "deliver"]:
        triggered = order_fsm.trigger_event(event)
        print(f"  事件 {event}: {'成功' if triggered else '失败'}, "
              f"当前状态: {order_fsm.current_state}")

    # 检查是否到达终态（没有可用转换即为终态）
    is_final = not order_fsm.get_possible_events()
    print(f"\n  是否完成: {is_final} (所在状态: {order_fsm.current_state})")

    # 历史记录
    print(f"\n📜 状态历史:")
    for i, entry in enumerate(history, 1):
        print(f"  {i}. {entry['from']} -> {entry['to']} ({entry['event']})")

    # 统计
    state_count = len(order_fsm.states)
    transition_count = sum(len(order_fsm.get_transitions(s)) for s in order_fsm.states)
    print(f"\n📊 状态机统计:")
    print(f"  状态数: {state_count}")
    print(f"  转换数: {transition_count}")
    print(f"  前一状态: {order_fsm.previous_state}")

    # 演示取消流程（重置后取消）
    print("\n📋 重置并取消订单...")
    order_fsm.reset()
    print(f"  重置后状态: {order_fsm.current_state}")
    order_fsm.trigger_event("cancel")
    print(f"  取消后状态: {order_fsm.current_state}")

    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
