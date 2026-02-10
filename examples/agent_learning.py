"""
Agent 自学习示例

展示如何使用轨迹记录和策略优化：
1. 轨迹记录
2. 策略分析
3. 自动优化
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.learning import TrajectoryRecorder, AgentOptimizer
from agent_os_kernel.core.learning.trajectory import TrajectoryPhase


async def demo_trajectory_recording():
    """轨迹记录示例"""
    print("=" * 60)
    print("轨迹记录示例")
    print("=" * 60)
    
    # 创建记录器
    recorder = TrajectoryRecorder(storage_dir="./demo_trajectories")
    
    # 模拟 Agent 执行
    kernel = AgentOSKernel()
    
    # 创建 Agent
    pid = kernel.spawn_agent(name="LearningAgent", task="学习如何解决问题", priority=50)
    agent_name = "LearningAgent"
    
    print(f"\n🤖 Agent: {agent_name} ({pid[:16]}...)")
    
    # 开始记录
    traj_id = recorder.start_recording(agent_name, pid, "学习如何解决问题")
    print(f"📝 开始记录轨迹: {traj_id}")
    
    # 模拟执行步骤
    print("\n📊 记录执行步骤:")
    
    # 思考阶段
    recorder.add_step(
        phase=TrajectoryPhase.THINKING,
        thought="分析问题的核心要素",
        confidence=0.8
    )
    print("  🧠 思考: 分析问题的核心要素")
    
    # 规划阶段
    recorder.add_step(
        phase=TrajectoryPhase.PLANNING,
        action={"plan": "分三步解决"},
        confidence=0.7
    )
    print("  📋 规划: 分三步解决")
    
    # 执行阶段
    recorder.add_step(
        phase=TrajectoryPhase.EXECUTING,
        tool_call={"name": "calculator", "params": {"expression": "100/5"}},
        observation="计算完成: 20",
        confidence=0.9
    )
    print("  ⚡ 执行: calculator(100/5) = 20")
    
    # 反思阶段
    recorder.add_step(
        phase=TrajectoryPhase.REFLECTING,
        reflection="第一步成功，继续下一步",
        confidence=0.85
    )
    print("  🤔 反思: 第一步成功，继续下一步")
    
    # 完成记录
    trajectory = recorder.finish_recording(
        outcome="任务完成",
        success=True,
        total_tokens=500,
        total_tools_used=3
    )
    
    print(f"\n✅ 轨迹记录完成:")
    print(f"   ID: {trajectory.trajectory_id}")
    print(f"   步骤数: {len(trajectory.steps)}")
    print(f"   成功率: {trajectory.success}")
    print(f"   持续时间: {trajectory.duration():.2f}s")
    
    return recorder


async def demo_trajectory_analysis(recorder: TrajectoryRecorder):
    """轨迹分析示例"""
    print("\n" + "=" * 60)
    print("轨迹分析示例")
    print("=" * 60)
    
    # 模拟多个轨迹
    print("\n📈 模拟更多轨迹数据...")
    
    for i in range(5):
        traj_id = recorder.start_recording(
            agent_name="LearningAgent",
            agent_pid=f"pid_{i}",
            task=f"任务 {i+1}"
        )
        
        # 随机成功/失败
        success = i < 4  # 80% 成功率
        
        steps = 3 + i % 3
        for j in range(steps):
            recorder.add_step(
                phase=TrajectoryPhase.EXECUTING,
                action={"step": j},
                confidence=0.6 + (0.1 * j) if success else 0.4
            )
        
        recorder.finish_recording(
            outcome="成功" if success else "失败",
            success=success,
            total_tokens=300 + i * 50,
            total_tools_used=2 + j
        )
    
    print("✅ 生成了 5 条轨迹数据")
    
    # 分析策略
    print("\n🔍 开始策略分析...")
    optimizer = AgentOptimizer(recorder)
    analysis = optimizer.analyze("LearningAgent")
    
    print(f"\n📊 分析结果:")
    print(f"   成功率: {analysis.success_rate:.1%}")
    print(f"   平均 Token: {analysis.avg_tokens:.0f}")
    print(f"   平均耗时: {analysis.avg_duration:.1f}s")
    
    if analysis.strengths:
        print(f"\n💪 优势:")
        for strength in analysis.strengths:
            print(f"   ✅ {strength}")
    
    if analysis.weaknesses:
        print(f"\n⚠️ 劣势:")
        for weakness in analysis.weaknesses:
            print(f"   ❌ {weakness}")
    
    if analysis.suggestions:
        print(f"\n💡 优化建议:")
        for suggestion in analysis.suggestions[:3]:
            print(f"   [{suggestion.priority}] {suggestion.description}")
    
    return optimizer


async def demo_optimization(optimizer: AgentOptimizer):
    """优化示例"""
    print("\n" + "=" * 60)
    print("自动优化示例")
    print("=" * 60)
    
    # 生成报告
    print("\n📋 生成优化报告...")
    report = optimizer.get_report("LearningAgent")
    
    print(f"\n📊 报告摘要:")
    summary = report['summary']
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    # 生成优化后的 Prompt
    print("\n📝 生成的 Prompt 模板:")
    template = optimizer.generate_prompt_template("LearningAgent")
    print("-" * 40)
    print(template)
    print("-" * 40)
    
    # 应用优化
    print("\n🚀 应用优化...")
    result = optimizer.batch_optimize("LearningAgent")
    print(f"   应用了 {result['applied']} 个优化建议")
    
    return optimizer


async def demo_metrics():
    """指标示例"""
    print("\n" + "=" * 60)
    print("指标监控示例")
    print("=" * 60)
    
    recorder = TrajectoryRecorder()
    
    # 创建一些轨迹
    for i in range(10):
        traj_id = recorder.start_recording(
            agent_name="MetricsAgent",
            agent_pid=f"metrics_{i}",
            task=f"测试任务 {i}"
        )
        
        for j in range(3):
            recorder.add_step(
                phase=TrajectoryPhase.EXECUTING,
                action={"step": j}
            )
        
        recorder.finish_recording(
            outcome="成功" if i % 2 == 0 else "失败",
            success=i % 2 == 0,
            total_tokens=200 + i * 30,
            total_tools_used=2
        )
    
    # 获取指标
    metrics = recorder.get_average_metrics("MetricsAgent")
    print("\n📈 指标:")
    for key, value in metrics.items():
        print(f"   {key}: {value}")
    
    # 获取成功率
    rate = recorder.get_success_rate("MetricsAgent")
    print(f"\n🎯 成功率: {rate:.1%}")
    
    # 获取常见模式
    patterns = recorder.get_common_patterns("MetricsAgent")
    print(f"\n🔄 常见模式 (Top 3):")
    for pattern, count in list(patterns.items())[:3]:
        print(f"   {pattern}: {count}次")
    
    return recorder


async def main():
    """主函数"""
    print("\n🚀 Agent 自学习系统示例")
    print("=" * 60)
    
    # 1. 轨迹记录
    recorder = await demo_trajectory_recording()
    
    # 2. 轨迹分析
    optimizer = await demo_trajectory_analysis(recorder)
    
    # 3. 自动优化
    await demo_optimization(optimizer)
    
    # 4. 指标监控
    await demo_metrics()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例完成!")
    print("=" * 60)
    
    print("\n📚 进一步阅读:")
    print("   - 轨迹学习: AIWaves Agents 论文")
    print("   - 策略优化: Reinforcement Learning")
    print("   - 经验积累: Experience Replay")


if __name__ == "__main__":
    asyncio.run(main())
