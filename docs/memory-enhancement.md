# 内存增强

## 概述

Agent OS Kernel 整合了 MemOS 的核心理念，提供增强的记忆系统。

## Memory Feedback

### 基本使用

```python
from agent_os_kernel.core.memory_feedback import (
    MemoryFeedbackSystem, FeedbackType
)

# 创建反馈系统
feedback = MemoryFeedbackSystem()

# 创建反馈
await feedback.create_feedback(
    memory_id="mem-123",
    feedback_type=FeedbackType.CORRECT,
    feedback_content="正确的答案应该是...",
    reason="原答案有事实错误",
    original_content="错误答案"
)

# 应用反馈
await feedback.apply_feedback(feedback_id)

# 获取待处理反馈
pending = await feedback.get_pending_feedbacks()
```

### 反馈类型

| 类型 | 说明 |
|------|------|
| `CORRECT` | 纠正错误 |
| `SUPPLEMENT` | 补充信息 |
| `REPLACE` | 替换内容 |
| `DELETE` | 删除记忆 |

## Tool Memory

### 基本使用

```python
from agent_os_kernel.core.tool_memory import (
    ToolMemory, ToolStatus
)

# 创建工具记忆
tool_memory = ToolMemory(
    max_history=1000,
    retention_days=30
)

# 记录工具调用
await tool_memory.record_call(
    tool_name="search",
    arguments={"query": "AI Agent"},
    result={"results": [...]},
    status=ToolStatus.SUCCESS,
    duration_ms=150.5,
    agent_id="agent-001",
    task_id="task-001"
)
```

### 查询功能

```python
# 获取工具调用历史
history = await tool_memory.get_tool_history(
    tool_name="search",
    agent_id="agent-001",
    limit=10
)

# 获取工具统计
stats = await tool_memory.get_tool_statistics()

# 获取最常用的工具
top_tools = await tool_memory.get_frequently_used_tools(limit=5)

# 获取失败率高的工具
failed = await tool_memory.get_failed_tools()

# 获取慢速工具
slow = await tool_memory.get_slow_tools(threshold_ms=1000)
```

### 任务推荐

```python
# 为任务推荐工具
suggestions = await tool_memory.suggest_tools_for_task(
    "需要搜索并读取相关文档"
)
# 返回: ["search", "read_file", ...]
```

## 整合使用

```python
from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.memory_feedback import MemoryFeedbackSystem
from agent_os_kernel.core.tool_memory import ToolMemory

# 创建内核
kernel = AgentOSKernel()

# 集成记忆系统
kernel.memory_feedback = MemoryFeedbackSystem()
kernel.tool_memory = ToolMemory()

# 在 Agent 中使用
async def agent_task():
    # 记录工具调用
    await kernel.tool_memory.record_call(
        tool_name="search",
        arguments={"query": "info"},
        result=data,
        status=ToolStatus.SUCCESS,
        duration_ms=100
    )
    
    # 创建反馈
    await kernel.memory_feedback.create_feedback(
        memory_id="mem-001",
        feedback_type=FeedbackType.SUPPLEMENT,
        feedback_content="补充信息...",
        reason="发现遗漏"
    )
```

## API 参考

### MemoryFeedbackSystem

| 方法 | 说明 |
|------|------|
| `create_feedback()` | 创建反馈 |
| `apply_feedback()` | 应用反馈 |
| `get_pending_feedbacks()` | 获取待处理反馈 |
| `get_feedback_history()` | 获取反馈历史 |
| `delete_feedback()` | 删除反馈 |

### ToolMemory

| 方法 | 说明 |
|------|------|
| `record_call()` | 记录工具调用 |
| `get_tool_history()` | 获取调用历史 |
| `get_tool_statistics()` | 获取统计 |
| `get_frequently_used_tools()` | 获取常用工具 |
| `get_failed_tools()` | 获取失败工具 |
| `get_slow_tools()` | 获取慢速工具 |
| `suggest_tools_for_task()` | 推荐工具 |
| `clear_history()` | 清空历史 |
