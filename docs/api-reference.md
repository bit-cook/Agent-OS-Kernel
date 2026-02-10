# API 参考文档

## 核心类

### AgentOSKernel

主内核类，集成所有子系统。

```python
from agent_os_kernel import AgentOSKernel

kernel = AgentOSKernel(
    max_context_tokens=128000,
    storage_backend="memory"
)

# 创建 Agent
pid = kernel.spawn_agent(
    name="MyAgent",
    task="Task description",
    priority=50
)

# 运行内核
kernel.run(max_iterations=100)

# 创建检查点
checkpoint_id = kernel.create_checkpoint(pid, "Description")

# 从检查点恢复
new_pid = kernel.restore_checkpoint(checkpoint_id)
```

#### 方法

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `spawn_agent` | name, task, priority | str | 创建 Agent |
| `terminate_agent` | pid | bool | 终止 Agent |
| `get_agent_status` | pid | dict | 获取 Agent 状态 |
| `create_checkpoint` | pid, description | str | 创建检查点 |
| `restore_checkpoint` | checkpoint_id | str | 恢复检查点 |
| `run` | max_iterations | None | 运行调度循环 |
| `get_statistics` | None | dict | 获取统计信息 |

---

## 上下文管理器

### ContextManager

虚拟内存式上下文管理。

```python
from agent_os_kernel.core import ContextManager

manager = ContextManager(max_tokens=1000)

# 添加页面
page = manager.add_page(
    agent_pid="agent1",
    content="Content",
    tokens=10,
    importance_score=0.8,
    page_type="user"
)

# 检索页面
retrieved = manager.get_page(page.page_id)

# 获取所有页面
pages = manager.get_agent_pages("agent1")

# 获取内存统计
stats = manager.get_memory_stats()
```

#### 方法

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `add_page` | agent_pid, content, tokens, importance_score, page_type | ContextPage | 添加页面 |
| `get_page` | page_id | ContextPage | 获取页面 |
| `remove_page` | page_id | bool | 删除页面 |
| `get_agent_pages` | agent_pid | List[ContextPage] | 获取 Agent 所有页面 |
| `swap_out_if_needed` | None | int | 换出低优先级页面 |
| `get_memory_stats` | None | dict | 获取内存统计 |
| `clear_agent_pages` | agent_pid | None | 清除 Agent 页面 |

---

## 调度器

### AgentScheduler

Agent 进程调度器。

```python
from agent_os_kernel.core import AgentScheduler

scheduler = AgentScheduler(max_concurrent_agents=10)

# 创建进程
pid = scheduler.spawn(name="Agent", task="Task", priority=50)

# 获取进程
process = scheduler.get_process(pid)

# 设置优先级
scheduler.set_priority(pid, 80)

# 终止进程
scheduler.terminate(pid)

# 获取统计
stats = scheduler.get_statistics()
```

#### 方法

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `spawn` | name, task, priority | str | 创建进程 |
| `terminate` | pid | bool | 终止进程 |
| `get_process` | pid | AgentProcess | 获取进程 |
| `set_priority` | pid, priority | bool | 设置优先级 |
| `get_active_processes` | None | List[AgentProcess] | 获取活跃进程 |
| `get_processes_by_state` | state | List[AgentProcess] | 按状态获取 |
| `get_statistics` | None | dict | 获取统计 |

---

## 存储

### StorageManager

持久化存储管理器。

```python
from agent_os_kernel.core import StorageManager

manager = StorageManager(backend="memory")

# 保存数据
manager.save("key", {"data": "value"})

# 检索数据
data = manager.retrieve("key")

# 检查存在
exists = manager.exists("key")

# 列出所有键
keys = manager.list_keys()

# 删除
manager.delete("key")
```

#### 方法

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `save` | key, value | None | 保存数据 |
| `retrieve` | key | Any | 检索数据 |
| `delete` | key | bool | 删除数据 |
| `exists` | key | bool | 检查存在 |
| `list_keys` | None | List[str] | 列出所有键 |
| `bulk_save` | data_dict | None | 批量保存 |
| `clear` | None | None | 清空存储 |

---

## 工具

### ToolRegistry

工具注册表。

```python
from agent_os_kernel.tools import ToolRegistry

registry = ToolRegistry()

# 列出工具
tools = registry.list_tools()

# 执行工具
result = registry.execute("calculator", expression="2+2")

# 获取工具
tool = registry.get("calculator")
```

#### 内置工具

| 工具名称 | 功能 | 示例 |
|----------|------|------|
| `calculator` | 数学计算 | `expression="2+2"` |
| `read_file` | 读取文件 | `path="/etc/hosts"` |
| `write_file` | 写入文件 | `path="test.txt", content="hi"` |
| `search` | 搜索 | `query="python"` |
| `json` | JSON 操作 | `action="parse", data='{}'` |

---

## 安全

### SecurityPolicy

安全策略。

```python
from agent_os_kernel.core import SecurityPolicy

policy = SecurityPolicy(
    sandbox_enabled=True,
    rate_limit_requests=100,
    audit_enabled=True
)

# 检查权限
allowed = policy.check_permission("read_file", PermissionLevel.READ)

# 检查速率限制
allowed = policy.check_rate_limit()

# 检查危险模式
has_danger = policy.contains_dangerous_pattern("rm -rf /")
```

---

## 指标

### MetricsCollector

性能指标收集器。

```python
from agent_os_kernel.core import MetricsCollector

collector = MetricsCollector()

# 记录指标
collector.record_cpu(50.0)
collector.record_memory(60.0)
collector.record_context_hit_rate(0.95)
collector.record_swap()

# 获取指标
metrics = collector.get_metrics(active_agents=5)

# 获取历史
history = collector.get_history(seconds=60)
```

### RateLimiter

速率限制器。

```python
from agent_os_kernel.core import RateLimiter

limiter = RateLimiter(max_requests=100, window_seconds=60)

# 检查是否允许
if limiter.allow():
    # 执行操作
    pass

# 获取剩余请求数
remaining = limiter.remaining()
```

### CircuitBreaker

熔断器。

```python
from agent_os_kernel.core import CircuitBreaker

breaker = CircuitBreaker(failure_threshold=5, recovery_time=60)

# 检查是否允许
if breaker.allow():
    try:
        # 执行操作
        pass
        breaker.record_success()
    except Exception as e:
        breaker.record_failure()
        raise
```
