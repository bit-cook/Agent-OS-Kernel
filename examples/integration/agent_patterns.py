"""
Agent Design Patterns

展示常用的 Agent 设计模式
"""

import asyncio
from enum import Enum
from agent_os_kernel import AgentOSKernel


class AgentRole(Enum):
    """Agent 角色"""
    PLANNER = "planner"      # 规划者
    EXECUTOR = "executor"    # 执行者
    REVIEWER = "reviewer"    # 评审者
    COORDINATOR = "coordinator"  # 协调者


class PatternDemo:
    """设计模式演示"""
    
    @staticmethod
    def pattern_chain():
        """Chain Pattern: 链式处理"""
        print("\n=== Chain Pattern ===")
        print("Input -> Agent1 -> Agent2 -> Agent3 -> Output")
        
        kernel = AgentOSKernel()
        
        # 创建处理链
        agents = [
            ("Validator", "验证输入"),
            ("Processor", "处理数据"),
            ("Formatter", "格式化输出")
        ]
        
        for name, task in agents:
            kernel.spawn_agent(name=name, task=task)
        
        print("✓ 链式处理创建完成")
    
    @staticmethod
    def pattern_supervisor():
        """Supervisor Pattern: 监督模式"""
        print("\n=== Supervisor Pattern ===")
        print("Supervitor -> Worker1, Worker2, Worker3")
        
        kernel = AgentOSKernel()
        
        # 监督者
        supervisor = kernel.spawn_agent(
            name="Supervisor",
            task="监督所有 Worker 并处理错误",
            priority=100
        )
        
        # 工作节点
        for i in range(3):
            kernel.spawn_agent(
                name=f"Worker-{i}",
                task=f"执行任务 {i}",
                priority=10
            )
        
        print("✓ 监督模式创建完成")
    
    @staticmethod
    def pattern_router():
        """Router Pattern: 路由模式"""
        print("\n=== Router Pattern ===")
        print("Request -> Router -> [Specialist1, Specialist2, ...]")
        
        kernel = AgentOSKernel()
        
        # 路由 Agent
        kernel.spawn_agent(
            name="Router",
            task="根据请求类型路由到专业 Agent",
            priority=50
        )
        
        # 专业 Agent
        specialists = [
            ("CodeExpert", "代码问题"),
            ("DataExpert", "数据问题"),
            ("DevOpsExpert", "运维问题")
        ]
        
        for name, specialty in specialists:
            kernel.spawn_agent(name=name, task=specialty)
        
        print("✓ 路由模式创建完成")
    
    @staticmethod
    def pattern_parallel():
        """Parallel Pattern: 并行模式"""
        print("\n=== Parallel Pattern ===")
        print("Task -> [Agent1, Agent2, Agent3] -> Aggregate")
        
        kernel = AgentOSKernel()
        
        # 并行 Agent
        for i in range(4):
            kernel.spawn_agent(
                name=f"Parallel-{i}",
                task=f"并行执行任务 {i}",
                priority=20
            )
        
        print("✓ 并行模式创建完成")
    
    @staticmethod
    def pattern_pipeline():
        """Pipeline Pattern: 流水线模式"""
        print("\n=== Pipeline Pattern ===")
        print("Stage1 -> Stage2 -> Stage3 -> Stage4 -> Output")
        
        kernel = AgentOSKernel()
        
        stages = [
            ("Ingestion", "数据摄取"),
            ("Processing", "数据处理"),
            ("Analysis", "数据分析"),
            ("Reporting", "报告生成")
        ]
        
        for name, task in stages:
            kernel.spawn_agent(name=name, task=task)
        
        print("✓ 流水线模式创建完成")
    
    @staticmethod
    def pattern_hierarchical():
        """Hierarchical Pattern: 层级模式"""
        print("\n=== Hierarchical Pattern ===")
        print("Manager -> TeamLead -> Worker -> Worker")
        
        kernel = AgentOSKernel()
        
        # 层级结构
        hierarchy = [
            ("CEO", "战略决策", 100),
            ("CTO", "技术管理", 80),
            ("TeamLead", "团队领导", 60),
            ("Developer", "开发实现", 40)
        ]
        
        for name, task, priority in hierarchy:
            kernel.spawn_agent(name=name, task=task, priority=priority)
        
        print("✓ 层级模式创建完成")


async def main():
    print("=" * 60)
    print("🎯 Agent Design Patterns Demo")
    print("=" * 60)
    
    demo = PatternDemo()
    
    # 演示各种模式
    demo.pattern_chain()
    demo.pattern_supervisor()
    demo.pattern_router()
    demo.pattern_parallel()
    demo.pattern_pipeline()
    demo.pattern_hierarchical()
    
    print("\n" + "=" * 60)
    print("✅ 所有设计模式演示完成!")
    print("=" * 60)
    
    print("\n📚 参考:")
    print("- Chain: 处理流程自动化")
    print("- Supervisor: 错误处理和恢复")
    print("- Router: 任务分发")
    print("- Parallel: 加速执行")
    print("- Pipeline: 数据流处理")
    print("- Hierarchical: 组织结构")


if __name__ == "__main__":
    asyncio.run(main())
