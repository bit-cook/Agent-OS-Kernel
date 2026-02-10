# 最佳实践指南

## Agent 设计

### 1. 任务分解

将复杂任务分解为多个简单 Agent：

```python
# ✅ 好: 专门化的 Agent
research_agent = kernel.spawn_agent(
    name="ResearchAgent",
    task="Research AI developments",
    priority=70
)

analysis_agent = kernel.spawn_agent(
    name="AnalysisAgent", 
    task="Analyze research data",
    priority=60
)

# ❌ 避免: 过于复杂的单 Agent
complex_agent = kernel.spawn_agent(
    name="ComplexAgent",
    task="Do everything at once",
    priority=30
)
```

### 2. 优先级设置

根据任务重要性设置优先级：

| 优先级 | 用途 | 说明 |
|--------|------|------|
| 90-100 | 紧急 | 用户直接交互 |
| 70-89 | 高 | 重要后台任务 |
| 40-69 | 中 | 标准任务 |
| 1-39 | 低 | 后台/批处理 |

### 3. 上下文管理

合理使用页面类型：

```python
# 系统提示 (高重要性，常驻)
kernel.context_manager.allocate_page(
    agent_pid=pid,
    content=system_prompt,
    importance=0.95,
    page_type="system"
)

# 任务描述 (中重要性)
kernel.context_manager.allocate_page(
    agent_pid=pid,
    content=task_description,
    importance=0.8,
    page_type="task"
)

# 工作内存 (低重要性，可置换)
kernel.context_manager.allocate_page(
    agent_pid=pid,
    content=intermediate_results,
    importance=0.3,
    page_type="working"
)
```

## 性能优化

### 1. 批量操作

```python
# ✅ 好: 批量添加页面
pages = []
for i in range(100):
    pages.append(kernel.context_manager.allocate_page(
        agent_pid=pid,
        content=f"Data {i}",
        importance=0.5
    ))

# ❌ 避免: 逐个添加
for i in range(100):
    kernel.context_manager.allocate_page(...)  # 每次都有开销
```

### 2. 检查点策略

```python
# 对于长时间运行的任务，定期创建检查点
for i in range(1000):
    do_work(i)
    
    # 每 100 次迭代创建检查点
    if i % 100 == 0:
        checkpoint_id = kernel.create_checkpoint(
            pid,
            f"Iteration {i}"
        )
```

### 3. 资源配额

```python
# 设置合理的资源限制
kernel.scheduler.processes[pid].quota.max_tokens = 50000
kernel.scheduler.processes[pid].quota.max_iterations = 500
```

## 安全最佳实践

### 1. 工具白名单

```python
# 只启用必要的工具
enabled_tools = [
    "calculator",
    "read_file",
    "json"
]

for tool in kernel.tool_registry.list_tools():
    if tool['name'] not in enabled_tools:
        kernel.tool_registry.disable(tool['name'])
```

### 2. 路径限制

```python
# 限制文件访问路径
file_tool.set_allowed_paths([
    "./workspace",
    "./data"
])
```

### 3. 审计日志

```python
# 记录重要操作
kernel.storage.log_audit({
    'action': 'agent_spawn',
    'agent_pid': pid,
    'resource': 'kernel',
    'result': 'success',
    'details': {'name': name, 'priority': priority}
})
```

## 错误处理

### 1. Agent 级别

```python
try:
    pid = kernel.spawn_agent(name, task, priority)
except Exception as e:
    logger.error(f"Failed to spawn agent: {e}")
    # 清理已创建的资源
    kernel.scheduler.terminate_process(pid)
```

### 2. 工具调用

```python
result = kernel.tool_registry.execute(tool_name, **params)

if not result['success']:
    logger.error(f"Tool call failed: {result['error']}")
    # 重试或回退
```

### 3. 检查点恢复

```python
if checkpoint_id:
    try:
        new_pid = kernel.restore_checkpoint(checkpoint_id)
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        # 从头开始或使用上一个检查点
```

## 监控与调试

### 1. 日志级别

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_os_kernel")
```

### 2. 性能指标

```python
# 收集指标
kernel.metrics.record_cpu(cpu_percent)
kernel.metrics.record_memory(memory_percent)
kernel.metrics.record_context_hit_rate(hit_rate)
```

### 3. 健康检查

```python
status = kernel.get_openclaw_status()

if status['overall_health'] == 'error':
    # 告警或重启
    alert("System health is critical!")
```

## 部署建议

### 1. Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "agent_os_kernel.py"]
```

### 2. 生产配置

```python
# 使用多个 worker
# gunicorn -w 4 -b 0.0.0.0:8080 app:app

# 使用连接池
kernel.storage._pool = pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    ...
)
```

### 3. 监控集成

```python
# Prometheus 指标
from prometheus_client import start_http_server

start_http_server(9090)
```

## 故障排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Agent 无法创建 | 参数错误 | 检查 name, task, priority |
| 上下文满 | 达到 token 限制 | 清理旧页面或增加限制 |
| 工具调用失败 | 权限不足 | 检查工具配置 |
| 检查点恢复失败 | 数据损坏 | 使用上一个检查点 |

### 调试命令

```bash
# 查看日志
tail -f logs/kernel.log

# 查看 Agent 状态
curl http://localhost:8080/api/agents

# 查看性能指标
curl http://localhost:8080/api/metrics
```
