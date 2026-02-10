"""
高级工作流编排示例

展示复杂的多 Agent 工作流模式：
1. 层级 Agent (Manager + Workers)
2. 流水线处理
3. 争议解决机制
4. 结果聚合
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from agent_os_kernel import AgentOSKernel


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowTask:
    """工作流任务"""
    task_id: str
    name: str
    description: str
    assigned_agent: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.kernel = AgentOSKernel()
        self.tasks: Dict[str, WorkflowTask] = {}
        self.task_queue: List[str] = []
        self.workflow_status: WorkflowStatus = WorkflowStatus.PENDING
    
    def define_parallel_tasks(self, tasks: List[Dict]) -> List[str]:
        """定义并行任务"""
        task_ids = []
        for task_def in tasks:
            task = WorkflowTask(
                task_id=f"task_{len(self.tasks)}",
                name=task_def.get('name', 'Untitled'),
                description=task_def.get('description', ''),
                assigned_agent=task_def.get('agent'),
                dependencies=task_def.get('dependencies', [])
            )
            self.tasks[task.task_id] = task
            task_ids.append(task.task_id)
            self.task_queue.append(task.task_id)
        return task_ids
    
    async def run_parallel(self, max_concurrent: int = 3) -> Dict[str, Any]:
        """并行执行任务"""
        self.workflow_status = WorkflowStatus.RUNNING
        results = {}
        active = []
        completed = set()
        
        print("\n🚀 开始并行执行工作流")
        print("=" * 60)
        
        while len(completed) < len(self.task_queue):
            # 启动新任务
            while len(active) < max_concurrent and self.task_queue:
                task_id = self.task_queue.pop(0)
                
                # 检查依赖
                task = self.tasks[task_id]
                if not self._dependencies_satisfied(task, completed):
                    self.task_queue.append(task_id)
                    continue
                
                # 分配 Agent 执行
                await self._execute_task(task)
                active.append(task_id)
                print(f"▶️ 启动任务: {task.name} ({task_id})")
            
            # 等待完成
            if active:
                # 简化：假设任务立即完成
                for tid in active:
                    completed.add(tid)
                    task = self.tasks[tid]
                    task.status = WorkflowStatus.COMPLETED
                    task.completed_at = datetime.now()
                    results[tid] = task.result
                    print(f"✅ 完成任务: {task.name}")
                active.clear()
        
        self.workflow_status = WorkflowStatus.COMPLETED
        return results
    
    def _dependencies_satisfied(self, task: WorkflowTask, completed: set) -> bool:
        """检查依赖是否满足"""
        for dep in task.dependencies:
            if dep not in completed:
                return False
        return True
    
    async def _execute_task(self, task: WorkflowTask):
        """执行单个任务"""
        task.started_at = datetime.now()
        
        if task.assigned_agent:
            # 使用 Agent 执行
            agent = self.kernel.spawn_agent(
                name=task.assigned_agent,
                task=task.description,
                priority=50
            )
            # 模拟执行
            await asyncio.sleep(0.1)
            self.kernel.scheduler.terminate_process(agent, reason="task complete")
            task.result = {"agent": agent, "status": "completed"}
        else:
            # 模拟执行
            await asyncio.sleep(0.05)
            task.result = {"status": "completed"}
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            'status': self.workflow_status.value,
            'total_tasks': len(self.tasks),
            'completed': sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.COMPLETED),
            'failed': sum(1 for t in self.tasks.values() if t.status == WorkflowStatus.FAILED)
        }


class HierarchicalAgentSystem:
    """层级 Agent 系统"""
    
    def __init__(self):
        self.kernel = AgentOSKernel()
        self.managers: Dict[str, str] = {}  # manager_name -> agent_pid
        self.workers: Dict[str, List[str]] = {}  # manager_name -> [worker_pids]
    
    def create_manager_worker_team(
        self,
        manager_name: str,
        worker_names: List[str],
        manager_task: str,
        worker_task_template: str
    ) -> Dict[str, str]:
        """创建管理-工作 Agent 团队"""
        print(f"\n🏗️ 创建团队: {manager_name} + {len(worker_names)} workers")
        
        # 创建 Manager
        manager_pid = self.kernel.spawn_agent(
            name=manager_name,
            task=manager_task,
            priority=80  # Manager 高优先级
        )
        self.managers[manager_name] = manager_pid
        
        # 创建 Workers
        worker_pids = []
        for i, worker_name in enumerate(worker_names):
            worker_pid = self.kernel.spawn_agent(
                name=worker_name,
                task=worker_task_template.replace("{id}", str(i)),
                priority=30 + i * 10  # 递增优先级
            )
            worker_pids.append(worker_pid)
        self.workers[manager_name] = worker_pids
        
        print(f"  ✅ Manager: {manager_name} ({manager_pid[:16]}...)")
        for i, (name, pid) in enumerate(zip(worker_names, worker_pids)):
            print(f"  ✅ Worker {i+1}: {name} ({pid[:16]}...)")
        
        return {
            'manager': manager_name,
            'manager_pid': manager_pid,
            'workers': list(zip(worker_names, worker_pids))
        }
    
    def delegate_tasks(self, manager_name: str, tasks: List[Dict]):
        """委派任务"""
        if manager_name not in self.workers:
            print(f"❌ Manager not found: {manager_name}")
            return
        
        workers = self.workers[manager_name]
        print(f"\n📋 {manager_name} 委派 {len(tasks)} 任务给 {len(workers)} workers")
        
        for i, task in enumerate(tasks):
            worker_pid = workers[i % len(workers)]
            worker = self.kernel.scheduler.processes.get(worker_pid)
            if worker:
                print(f"  → {worker.name}: {task['name']}")
    
    async def shutdown_all(self):
        """关闭所有 Agent"""
        print("\n🛑 关闭所有 Agent...")
        
        for pid in self.managers.values():
            self.kernel.scheduler.terminate_process(pid, reason="shutdown")
        
        for worker_list in self.workers.values():
            for pid in worker_list:
                self.kernel.scheduler.terminate_process(pid, reason="shutdown")
        
        self.managers.clear()
        self.workers.clear()
        print("✅ 所有 Agent 已关闭")


class DebateSystem:
    """辩论/争议解决系统"""
    
    def __init__(self):
        self.kernel = AgentOSKernel()
        self.debaters: List[str] = []
        self.opinions: List[Dict] = []
    
    def setup_debate(self, topic: str, debaters: List[Dict]):
        """设置辩论"""
        print(f"\n🎭 设置辩论: {topic}")
        print("=" * 60)
        
        for i, debater in enumerate(debaters):
            pid = self.kernel.spawn_agent(
                name=debater['name'],
                task=f"关于 '{topic}'，从 {debater['perspective']} 角度分析",
                priority=50
            )
            self.debaters.append(pid)
            print(f"  {i+1}. {debater['name']} ({debater['perspective']})")
    
    async def run_debate(self, rounds: int = 3) -> Dict[str, Any]:
        """运行辩论"""
        print(f"\n🗣️ 开始辩论 ({rounds} 轮)")
        
        for round_num in range(rounds):
            print(f"\n--- 第 {round_num + 1} 轮 ---")
            
            round_opinions = []
            for pid in self.debaters:
                agent = self.kernel.scheduler.processes.get(pid)
                if agent:
                    opinion = f"{agent.name} 的观点 (第{round_num + 1}轮)"
                    round_opinions.append({
                        'agent': agent.name,
                        'opinion': opinion,
                        'round': round_num + 1
                    })
                    self.opinions.append({
                        'agent': agent.name,
                        'round': round_num + 1,
                        'opinion': opinion
                    })
                    print(f"  💬 {agent.name}: {opinion[:50]}...")
            
            # 模拟等待
            await asyncio.sleep(0.1)
        
        return {
            'total_rounds': rounds,
            'opinions': self.opinions,
            'consensus': self._find_consensus()
        }
    
    def _find_consensus(self) -> Optional[str]:
        """寻找共识"""
        if not self.opinions:
            return None
        # 简化：返回最后一个观点作为共识
        return self.opinions[-1]['opinion']
    
    async def shutdown(self):
        """关闭辩论"""
        for pid in self.debaters:
            self.kernel.scheduler.terminate_process(pid, reason="debate complete")
        self.debaters.clear()
        self.opinions.clear()


async def demo_workflow_engine():
    """工作流引擎示例"""
    print("=" * 60)
    print("高级工作流编排示例")
    print("=" * 60)
    
    # 1. 并行任务执行
    print("\n📊 示例 1: 并行任务执行")
    workflow = WorkflowEngine()
    
    # 定义任务
    tasks = [
        {"name": "数据收集", "description": "从多个来源收集数据"},
        {"name": "数据清洗", "description": "清洗和预处理数据"},
        {"name": "数据分析", "description": "执行数据分析"},
        {"name": "报告生成", "description": "生成分析报告"}
    ]
    
    workflow.define_parallel_tasks(tasks)
    await workflow.run_parallel(max_concurrent=2)
    
    print(f"\n📈 工作流状态: {workflow.get_workflow_status()}")
    
    return workflow


async def demo_hierarchical_system():
    """层级 Agent 系统示例"""
    print("\n" + "=" * 60)
    print("示例 2: 层级 Agent 系统 (Manager + Workers)")
    print("=" * 60)
    
    system = HierarchicalAgentSystem()
    
    # 创建团队
    team = system.create_manager_worker_team(
        manager_name="ProjectManager",
        worker_names=["Worker1", "Worker2", "Worker3"],
        manager_task="协调和管理项目任务",
        worker_task_template="执行具体任务 {id}"
    )
    
    # 委派任务
    tasks = [
        {"name": "任务 A"},
        {"name": "任务 B"},
        {"name": "任务 C"}
    ]
    system.delegate_tasks("ProjectManager", tasks)
    
    return system


async def demo_debate_system():
    """辩论系统示例"""
    print("\n" + "=" * 60)
    print("示例 3: 辩论/争议解决系统")
    print("=" * 60)
    
    debate = DebateSystem()
    
    # 设置辩论
    debate.setup_debate(
        topic="AI 是否应该拥有自我意识",
        debaters=[
            {"name": "ProAI", "perspective": "支持 AI 意识"},
            {"name": "AntiAI", "perspective": "反对 AI 意识"},
            {"name": "NeutralAI", "perspective": "中立观点"}
        ]
    )
    
    # 运行辩论
    result = await debate.run_debate(rounds=2)
    print(f"\n📝 辩论结果: {result['consensus']}")
    
    return debate


async def demo_complete_workflow():
    """完整工作流演示"""
    print("\n" + "=" * 60)
    print("完整工作流演示")
    print("=" * 60)
    
    # 创建工作流
    workflow = WorkflowEngine()
    
    # 定义复杂工作流
    pipeline = [
        {"name": "需求分析", "agent": "Analyst"},
        {"name": "架构设计", "agent": "Architect"},
        {"name": "前端开发", "agent": "FrontendDev"},
        {"name": "后端开发", "agent": "BackendDev"},
        {"name": "测试", "agent": "Tester"},
        {"name": "部署", "agent": "DevOps"}
    ]
    
    workflow.define_parallel_tasks(pipeline)
    
    print("\n🚀 开始完整工作流...")
    results = await workflow.run_parallel(max_concurrent=3)
    
    print(f"\n✅ 工作流完成!")
    print(f"📊 结果: {len(results)} 任务完成")
    
    return workflow


async def main():
    """主函数"""
    print("\n🚀 高级工作流编排系统")
    print("=" * 60)
    
    # 示例 1: 工作流引擎
    await demo_workflow_engine()
    
    # 示例 2: 层级系统
    system = await demo_hierarchical_system()
    await system.shutdown_all()
    
    # 示例 3: 辩论系统
    debate = await demo_debate_system()
    await debate.shutdown()
    
    # 示例 4: 完整工作流
    await demo_complete_workflow()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
