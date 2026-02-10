"""
多 Agent 协调示例

展示如何使用 Agent-OS-Kernel 进行多 Agent 协作：
1. Agent 编排
2. 消息传递
3. 任务分配
4. 结果聚合
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.types import AgentState
from typing import Dict, List, Any


class MultiAgentCoordinator:
    """多 Agent 协调器"""
    
    def __init__(self):
        self.kernel = AgentOSKernel()
        self.agent_roles = {}
        self.message_queues: Dict[str, List[Dict]] = {}
    
    def register_agent(self, name: str, role: str, task: str) -> str:
        """注册 Agent"""
        priority = self._role_priority(role)
        pid = self.kernel.spawn_agent(name=name, task=task, priority=priority)
        self.agent_roles[pid] = role
        self.message_queues[pid] = []
        print(f"✅ 注册 Agent: {name} ({role}) - {pid[:16]}...")
        return pid
    
    def _role_priority(self, role: str) -> int:
        """根据角色分配优先级"""
        priorities = {
            'coordinator': 90,
            'manager': 70,
            'worker': 50,
            'helper': 30
        }
        return priorities.get(role, 40)
    
    def send_message(self, from_pid: str, to_pid: str, message: str, priority: str = 'normal'):
        """发送消息"""
        msg = {
            'from': from_pid,
            'content': message,
            'priority': priority,
            'timestamp': str(asyncio.get_event_loop().time())
        }
        self.message_queues[to_pid].append(msg)
        print(f"📨 {from_pid[:8]}... → {to_pid[:8]}...: {message[:50]}...")
    
    def broadcast(self, from_pid: str, message: str):
        """广播消息给所有 Agent"""
        for pid in self.message_queues:
            if pid != from_pid:
                self.send_message(from_pid, pid, message)
    
    def get_messages(self, pid: str) -> List[Dict]:
        """获取消息"""
        messages = self.message_queues.get(pid, [])
        self.message_queues[pid] = []
        return messages
    
    def get_status(self) -> Dict[str, Any]:
        """获取协调器状态"""
        agents = []
        for pid, agent in self.kernel.scheduler.processes.items():
            role = self.agent_roles.get(pid, 'unknown')
            msg_count = len(self.message_queues.get(pid, []))
            agents.append({
                'pid': pid,
                'name': agent.name,
                'role': role,
                'state': agent.state.value,
                'pending_messages': msg_count
            })
        
        return {
            'total_agents': len(agents),
            'agents': agents,
            'total_messages': sum(len(q) for q in self.message_queues.values())
        }
    
    def terminate_all(self):
        """终止所有 Agent"""
        for pid in list(self.kernel.scheduler.processes.keys()):
            self.kernel.scheduler.terminate_process(pid, reason='coordinator_shutdown')
        self.agent_roles.clear()
        self.message_queues.clear()
        print("🛑 所有 Agent 已终止")


class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, coordinator: MultiAgentCoordinator):
        self.coordinator = coordinator
    
    def plan_parallel_task(self, task: str, subtasks: List[str], workers: List[str]) -> Dict:
        """规划并行任务"""
        plan = {
            'task': task,
            'strategy': 'parallel',
            'assignments': {},
            'dependencies': []
        }
        
        # 分配任务
        for i, subtask in enumerate(subtasks):
            worker = workers[i % len(workers)]
            plan['assignments'][subtask] = worker
            print(f"📋 {subtask} → {worker}")
        
        return plan
    
    def plan_sequential_task(self, task: str, steps: List[str], worker: str) -> Dict:
        """规划顺序任务"""
        plan = {
            'task': task,
            'strategy': 'sequential',
            'steps': steps,
            'worker': worker,
            'current_step': 0
        }
        
        for i, step in enumerate(steps):
            print(f"📋 步骤 {i+1}: {step} → {worker}")
        
        return plan
    
    def execute_plan(self, plan: Dict) -> Dict:
        """执行任务计划"""
        results = {}
        
        if plan['strategy'] == 'parallel':
            # 并行执行 - 简化为顺序执行演示
            for subtask, worker in plan['assignments'].items():
                self.coordinator.send_message(
                    'planner',
                    worker,
                    f"执行任务: {subtask}"
                )
                results[subtask] = {'status': 'assigned', 'worker': worker}
        
        elif plan['strategy'] == 'sequential':
            # 顺序执行
            worker = plan['worker']
            for i, step in enumerate(plan['steps']):
                self.coordinator.send_message(
                    'planner',
                    worker,
                    f"执行步骤 {i+1}: {step}"
                )
                results[f"step_{i+1}"] = {'status': 'assigned', 'task': step}
        
        return results


class ResultAggregator:
    """结果聚合器"""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, source: str, result: Any):
        """添加结果"""
        self.results.append({
            'source': source,
            'result': result,
            'timestamp': str(asyncio.get_event_loop().time())
        })
        print(f"📦 收到结果: {source} → {str(result)[:50]}...")
    
    def aggregate(self, method: str = 'list') -> Any:
        """聚合结果"""
        if method == 'list':
            return self.results
        elif method == 'summary':
            return {
                'total': len(self.results),
                'sources': [r['source'] for r in self.results],
                'latest': self.results[-1] if self.results else None
            }
        elif method == 'json':
            return {'results': self.results}
        
        return self.results
    
    def clear(self):
        """清空结果"""
        self.results.clear()
        print("🗑️ 结果已清空")


async def demo_multi_agent():
    """演示多 Agent 协调"""
    print("=" * 60)
    print("多 Agent 协调演示")
    print("=" * 60)
    
    import asyncio
    
    # 创建协调器
    coordinator = MultiAgentCoordinator()
    
    # 注册不同角色的 Agent
    coordinator.register_agent(
        name="CoordinatorAgent",
        role="coordinator",
        task="负责整体协调"
    )
    
    worker1 = coordinator.register_agent(
        name="WorkerAgent1",
        role="worker",
        task="执行具体任务"
    )
    
    worker2 = coordinator.register_agent(
        name="WorkerAgent2",
        role="worker",
        task="执行具体任务"
    )
    
    worker3 = coordinator.register_agent(
        name="WorkerAgent3",
        role="helper",
        task="提供辅助支持"
    )
    
    print("\n📊 协调器状态:")
    status = coordinator.get_status()
    print(f"   总 Agent 数: {status['total_agents']}")
    print(f"   总消息数: {status['total_messages']}")
    
    # 演示消息传递
    print("\n📨 消息传递演示:")
    coordinator.send_message(worker1, worker2, "Hello from Worker 1!")
    coordinator.broadcast(worker1, "Broadcast message from Worker 1")
    
    # 查看消息
    for pid in [worker2, worker3]:
        messages = coordinator.get_messages(pid)
        print(f"   {pid[:8]}... 收到 {len(messages)} 条消息")
    
    # 演示任务规划
    print("\n📋 任务规划演示:")
    planner = TaskPlanner(coordinator)
    
    plan = planner.plan_parallel_task(
        task="并行数据分析",
        subtasks=["数据收集", "数据清洗", "数据分析", "报告生成"],
        workers=[worker1, worker2, worker3, worker1]
    )
    
    results = planner.execute_plan(plan)
    print(f"   任务已分配: {len(results)} 个子任务")
    
    # 演示结果聚合
    print("\n📦 结果聚合演示:")
    aggregator = ResultAggregator()
    
    aggregator.add_result(worker1, {'data': 'result1'})
    aggregator.add_result(worker2, {'data': 'result2'})
    aggregator.add_result(worker3, {'data': 'result3'})
    
    summary = aggregator.aggregate('summary')
    print(f"   聚合结果: {summary}")
    
    # 清理
    print("\n🛑 清理:")
    coordinator.terminate_all()
    print("   演示完成！")


async def demo_workflow():
    """演示完整工作流"""
    print("\n" + "=" * 60)
    print("完整工作流演示")
    print("=" * 60)
    
    coordinator = MultiAgentCoordinator()
    
    # 创建 Agent 团队
    planner = coordinator.register_agent("Planner", "coordinator", "任务规划")
    workers = [
        coordinator.register_agent(f"Worker{i}", "worker", f"执行任务 {i}")
        for i in range(4)
    ]
    
    # 工作流步骤
    steps = [
        "接收任务",
        "分解子任务",
        "分配给 Worker",
        "收集结果",
        "生成报告"
    ]
    
    for i, step in enumerate(steps):
        print(f"📌 步骤 {i+1}: {step}")
        
        #Planner 发送任务
        for worker in workers:
            coordinator.send_message(planner, worker, step)
        
        # 模拟 Worker 处理
        for worker in workers:
            aggregator = ResultAggregator()
            aggregator.add_result(worker, f"{step} 完成")
        
        await asyncio.sleep(0.1)  # 模拟处理时间
    
    print("\n✅ 工作流完成!")
    coordinator.terminate_all()


if __name__ == "__main__":
    import asyncio
    
    print("\n🚀 多 Agent 协调系统")
    print("=" * 60)
    
    # 运行演示
    asyncio.run(demo_multi_agent())
    asyncio.run(demo_workflow())
    
    print("\n" + "=" * 60)
    print("🎉 演示完成!")
    print("=" * 60)
