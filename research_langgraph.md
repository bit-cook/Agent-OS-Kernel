# LangGraph 研究

## 基本信息
- 项目名称: LangGraph
- GitHub: https://github.com/langchain-ai/langgraph
- Star: 15k+
- 类型: 图结构 Agent 编排

## 核心特性

### 1. StateGraph
```python
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    messages: list
    context: dict
    next: str

workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_node("evaluate", evaluate_node)

# 添加边
workflow.add_edge("agent", "evaluate")
workflow.add_conditional_edges(
    "evaluate",
    should_continue,
    {True: "tools", False: END}
)
```

### 2. Checkpointer
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"]
)
```

### 3. 多 Agent 协作
```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model, 
    tools,
    name="researcher"
)
```

### 4. 时间旅行
```python
# 恢复到之前的状态
checkpoint = app.get_state(
    config={"configurable": {"thread_id": "1"}}
)
app.update_state(config, new_values)
```

## 可借鉴点

### 1. 图结构设计
- 节点 = Agent/工具
- 边 = 状态转换
- 条件边 = 动态路由

### 2. 状态管理
- Checkpointer 持久化
- 时间旅行调试
- 中断恢复

### 3. 编译优化
```python
app = workflow.compile(
    checkpointer=...,
    interrupt_before=[...],
    debug=True
)
```

### 4. 多种模式
- 单 Agent (ReAct)
- 多 Agent (Supervisor)
- 复杂流程 (Graph)

## 代码结构参考

```
langgraph/
├── graph/
│   ├── state.py
│   ├── node.py
│   ├── edge.py
│   └── compiler.py
├── checkpoint/
│   ├── memory.py
│   ├── sqlite.py
│   └── postgres.py
├── prebuilt/
│   ├── react_agent.py
│   └── supervisor.py
└── channel/
    ├── last_value.py
    ├── topic.py
    └── барьер.py
```

## 对比我们的设计

| 特性 | LangGraph | Agent-OS-Kernel |
|------|-----------|-----------------|
| 流程编排 | 图结构 | 线性调度 |
| 状态持久化 | Checkpointer | 基础存储 |
| 调试能力 | 时间旅行 | 基础日志 |
| 多 Agent | Supervisor | 基础协作 |
| 中断恢复 | 支持 | 待完善 |

## 建议采纳

1. ✅ 引入图结构编排
2. ✅ 增强状态管理
3. ✅ 添加时间旅行调试
4. ✅ 支持中断恢复
