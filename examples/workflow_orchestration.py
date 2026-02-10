"""
Workflow Orchestration Examples

工作流编排示例
"""

import asyncio
from agent_os_kernel import AgentOSKernel
from agent_os_kernel.llm import create_mock_provider


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.kernel = AgentOSKernel()
        self.workflows = {}
    
    def register_workflow(self, name: str, steps: list):
        """注册工作流"""
        self.workflows[name] = steps
        print(f"✓ Workflow registered: {name} ({len(steps)} steps)")
    
    async def execute_workflow(self, name: str):
        """执行工作流"""
        if name not in self.workflows:
            print(f"✗ Workflow not found: {name}")
            return
        
        steps = self.workflows[name]
        print(f"\n{'='*60}")
        print(f"Executing: {name}")
        print(f"{'='*60}")
        
        for i, step in enumerate(steps, 1):
            print(f"\n[{i}/{len(steps)}] {step['name']}")
            print(f"  Agent: {step['agent']}")
            print(f"  Task: {step['task']}")
            
            # 创建 Agent
            agent_id = self.kernel.spawn_agent(
                name=step['agent'],
                task=step['task'],
                priority=step.get('priority', 50)
            )
            print(f"  → Agent ID: {agent_id}")
        
        print(f"\n✓ Workflow {name} started")
        return True


async def demo_data_pipeline():
    """数据处理管道"""
    print("\n" + "=" * 60)
    print("Data Pipeline Workflow")
    print("=" * 60)
    
    engine = WorkflowEngine()
    
    # 注册数据处理工作流
    engine.register_workflow("data_pipeline", [
        {"name": "数据采集", "agent": "Collector", "task": "从 API 采集数据"},
        {"name": "数据清洗", "agent": "Cleaner", "task": "清洗和转换数据"},
        {"name": "数据分析", "agent": "Analyzer", "task": "执行数据分析"},
        {"name": "报告生成", "agent": "Reporter", "task": "生成分析报告"},
    ])
    
    await engine.execute_workflow("data_pipeline")


async def demo_code_review():
    """代码审查工作流"""
    print("\n" + "=" * 60)
    print("Code Review Workflow")
    print("=" * 60)
    
    engine = WorkflowEngine()
    
    engine.register_workflow("code_review", [
        {"name": "代码检查", "agent": "Linter", "task": "运行代码检查"},
        {"name": "静态分析", "agent": "StaticAnalyzer", "task": "执行静态分析"},
        {"name": "安全扫描", "agent": "SecurityScanner", "task": "扫描安全漏洞"},
        {"name": "性能分析", "agent": "Profiler", "task": "分析代码性能"},
        {"name": "审查汇总", "agent": "Reviewer", "task": "汇总所有问题"},
    ])
    
    await engine.execute_workflow("code_review")


async def demo_research_agent():
    """研究 Agent 工作流"""
    print("\n" + "=" * 60)
    print("Research Agent Workflow")
    print("=" * 60)
    
    engine = WorkflowEngine()
    
    engine.register_workflow("research", [
        {"name": "信息收集", "agent": "Researcher", "task": "收集相关信息"},
        {"name": "深度分析", "agent": "Analyzer", "task": "深度分析问题"},
        {"name": "方案设计", "agent": "Designer", "task": "设计解决方案"},
        {"name": "专家评审", "agent": "Expert", "task": "评审方案可行性"},
        {"name": "最终输出", "agent": "Writer", "task": "生成最终报告"},
    ])
    
    await engine.execute_workflow("research")


async def demo_parallel_execution():
    """并行执行"""
    print("\n" + "=" * 60)
    print("Parallel Execution")
    print("=" * 60)
    
    kernel = AgentOSKernel()
    
    # 创建多个并行 Agent
    agents = [
        ("Searcher1", "搜索相关内容"),
        ("Searcher2", "查找相关论文"),
        ("Searcher3", "收集用户反馈"),
        ("Searcher4", "分析竞争对手"),
    ]
    
    print("\nSpawning parallel agents:")
    agent_ids = []
    for name, task in agents:
        pid = kernel.spawn_agent(name=name, task=task, priority=30)
        agent_ids.append(pid)
        print(f"  ✓ {name}: {pid}")
    
    print(f"\nTotal agents: {len(agent_ids)}")
    print("✓ Parallel execution ready")


class MultiAgentTeam:
    """多 Agent 团队"""
    
    def __init__(self, team_name: str):
        self.name = team_name
        self.kernel = AgentOSKernel()
        self.members = {}
    
    def add_member(self, name: str, role: str, expertise: list):
        """添加团队成员"""
        self.members[name] = {
            "role": role,
            "expertise": expertise
        }
        print(f"✓ {name} joined as {role}")
    
    async def start_discussion(self, topic: str):
        """开始讨论"""
        print(f"\n{'='*60}")
        print(f"Team: {self.name}")
        print(f"Topic: {topic}")
        print(f"{'='*60}")
        
        for name, info in self.members.items():
            pid = self.kernel.spawn_agent(
                name=name,
                task=f"Discuss {topic} - Focus: {info['role']}",
                priority=50
            )
            print(f"  ✓ {name} ({info['role']}): {pid}")
        
        print(f"\n✓ Team discussion started with {len(self.members)} members")


async def demo_team():
    """团队协作示例"""
    print("\n" + "=" * 60)
    print("Multi-Agent Team")
    print("=" * 60)
    
    team = MultiAgentTeam("Project Alpha")
    
    team.add_member("Alice", "Architect", ["system design", "APIs"])
    team.add_member("Bob", "Backend Lead", ["Python", "databases"])
    team.add_member("Carol", "Frontend Lead", ["Vue.js", "TypeScript"])
    team.add_member("David", "DevOps", ["Docker", "Kubernetes"])
    
    await team.start_discussion("Microservices Architecture")


async def main():
    print("=" * 60)
    print("🚀 Workflow Orchestration Examples")
    print("=" * 60)
    
    await demo_data_pipeline()
    await demo_code_review()
    await demo_research_agent()
    await demo_parallel_execution()
    await demo_team()
    
    print("\n" + "=" * 60)
    print("✅ All workflows ready!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
