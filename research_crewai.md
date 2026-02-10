# CrewAI 研究

## 基本信息
- 项目名称: CrewAI
- GitHub: https://github.com/crewai/crewai
- Star: 30k+
- 类型: 多 Agent 编排框架

## 核心特性

### 1. Agent 定义
```python
from crewai import Agent

researcher = Agent(
    role="Senior Researcher",
    goal="Discover breakthrough technologies",
    backstory="Expert researcher with 10 years experience",
    tools=[search_tool, scrape_tool]
)
```

### 2. Task 定义
```python
from crewai import Task

task = Task(
    description="Research AI breakthroughs",
    agent=researcher,
    expected_output="Detailed report"
)
```

### 3. Crew 编排
```python
from crewai import Crew, Process

crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential,  # 或 Process.hierarchical
    memory=True,  # 共享记忆
    embedder={
        "provider": "openai",
        "model": "text-embedding-3-small"
    }
)
```

### 4. 协作模式
- Sequential: 顺序执行
- Hierarchical: 层级监督
- Consensual: 共识决策

## 可借鉴点

### 1. Agent 定义模式
- role/goal/backstory 三元组
- 清晰的 Agent 身份定义
- 工具绑定

### 2. Task 抽象
- 明确的输入输出
- 预期输出格式
- 依赖关系

### 3. 记忆系统
- 跨 Agent 共享记忆
- 向量存储集成
- RAG 支持

### 4. 流程编排
- 多种执行模式
- 任务依赖
- 输出验证

## 代码结构参考

```
crewai/
├── core/
│   ├── agent.py
│   ├── task.py
│   ├── crew.py
│   └── process.py
├── tools/
│   ├── base.py
│   ├── toolkit.py
│   └── rag/
├── memory/
│   ├── short_term.py
│   ├── long_term.py
│   └── entity.py
└── utils/
```

## 对比我们的设计

| 特性 | CrewAI | Agent-OS-Kernel |
|------|--------|-----------------|
| Agent 定义 | role/goal/backstory | name/task/priority |
| Task 抽象 | 明确 | 待完善 |
| 记忆系统 | 完整 | 基础 |
| 编排模式 | 多种 | 基础 |
| 工具集成 | 丰富 | MCP |

## 建议采纳

1. ✅ 借鉴 role/goal/backstory 定义
2. ✅ 完善 Task 抽象
3. ✅ 增强记忆系统
4. ✅ 添加 hierarchical 模式
