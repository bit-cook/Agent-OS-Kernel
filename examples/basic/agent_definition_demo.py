"""
Agent-OS-Kernel Agent定义演示

展示Agent定义的使用方法
"""

from agent_os_kernel.core.agent_definition import AgentDefinition, TaskDefinition, CrewDefinition


def demo_agent_definition():
    """演示Agent定义"""
    print("=" * 60)
    print("Agent-OS-Kernel Agent定义演示")
    print("=" * 60)
    
    # 创建任务定义
    task = TaskDefinition(
        task_id="research-task",
        description="Research AI trends",
        expected_output="Report on AI trends"
    )
    print(f"\n✅ 任务创建: {task.task_id}")
    
    # 创建Agent定义
    agent = AgentDefinition(
        agent_id="researcher",
        name="Research Agent",
        role="Senior Researcher",
        description="Expert in AI research"
    )
    print(f"✅ Agent创建: {agent.name}")
    
    # 创建Crew定义
    crew = CrewDefinition(
        crew_id="research-crew",
        name="Research Crew",
        description="AI research team"
    )
    crew.add_agent(agent)
    crew.add_task(task)
    print(f"✅ Crew创建: {crew.name}")
    print(f"   Agent数量: {len(crew.agents)}")
    print(f"   任务数量: {len(crew.tasks)}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    demo_agent_definition()
