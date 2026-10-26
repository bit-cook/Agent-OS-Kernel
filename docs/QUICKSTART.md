# Agent-OS-Kernel 快速入门指南

> 本文所有代码示例均针对当前版本（0.2.0）实测可运行。

## 安装

```bash
# 克隆项目
git clone https://github.com/bit-cook/Agent-OS-Kernel.git
cd Agent-OS-Kernel

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装（含全部可选依赖）
pip install -e ".[all]"
```

## 快速开始

### 1. 初始化内核

```python
import agent_os_kernel
from agent_os_kernel import AgentOSKernel

print(f"Kernel version: {agent_os_kernel.__version__}")

kernel = AgentOSKernel(
    max_context_tokens=128000,   # 上下文窗口（token）
    time_slice=60.0,             # 调度时间片（秒）
    enable_sandbox=False,        # True 需要 Docker
)
```

### 2. 创建与运行 Agent

```python
# 创建 Agent（类比操作系统 fork）
agent_pid = kernel.spawn_agent(
    name="Assistant",
    task="分析这份日志并总结异常",
    priority=50,
)

# 查看状态
info = kernel.get_agent(agent_pid)
print(info["name"], info["status"])

# 列出全部 Agent
for agent in kernel.list_agents():
    print(agent["name"], agent["status"])
```

### 3. Checkpoint 与恢复

```python
# 创建检查点（含该 Agent 的全部上下文页面）
checkpoint_id = kernel.create_checkpoint(
    agent_pid,
    description="处理一半时存档",
)

# 之后任意时刻恢复到新进程
new_pid = kernel.restore_checkpoint(checkpoint_id)

# 优雅关闭
kernel.shutdown()
```

### 4. Agent 池

```python
from agent_os_kernel.core.agent_pool import AgentPool
from agent_os_kernel.core.agent_definition import AgentDefinition

pool = AgentPool(max_size=10, idle_timeout=300.0)

# 借用
agent = await pool.acquire(AgentDefinition(
    name="worker-1",
    role="worker",
    goal="处理任务",
    backstory="通用工人",
))

# 归还
await pool.release(agent)

# 统计
pool.get_stats()
```

### 5. 事件系统

```python
from agent_os_kernel.core.event_bus import EventBus, Event

bus = EventBus(max_queue_size=10000)

# 订阅
async def on_event(event: Event):
    print(event.event_type, event.payload)

sub_id = bus.subscribe("agent.created", on_event)  # 同步方法

# 发布
await bus.publish(Event(
    event_id="e-1",
    event_type="agent.created",
    payload={"agent_id": "a-1"},
))
```

### 6. 熔断器

```python
from agent_os_kernel.core.circuit_breaker import CircuitBreaker, CircuitConfig

cb = CircuitBreaker(
    name="llm-api",
    config=CircuitConfig(failure_threshold=5, timeout_seconds=30),
)

# 受保护调用（同步/异步）
result = await cb.call_async(risky_async_function)
```

### 7. 上下文管理（虚拟内存式）

```python
from agent_os_kernel.core.context_manager import ContextManager

ctx = ContextManager(max_context_tokens=128000)

# 分配页面
page_id = ctx.allocate_page(
    agent_pid="agent-1",
    content="大量上下文内容...",
    importance=0.8,
)

# 获取优化后的上下文（KV-Cache 友好的顺序）
context = ctx.get_agent_context("agent-1")
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_kernel.py -v

# 生成覆盖率报告
pytest --cov=agent_os_kernel tests/
```

## 运行示例

```bash
# 环境自检（黄金路径第一步）
python -m agent_os_kernel doctor

# 确定性演示（mock provider，无需 API key）
python -m agent_os_kernel demo

# 启动 API 服务器（默认仅监听 127.0.0.1）
python -m agent_os_kernel serve --port 8000
```

## 常见问题

### Q: 如何添加新的 LLM 提供商？

继承 `agent_os_kernel.llm.provider.LLMProvider` 并实现四个抽象方法
（`provider_name` / `supported_models` / `get_config` / `chat`），
参考 `agent_os_kernel/llm/openai_impl.py`。

### Q: 执行类工具安全吗？

默认 fail-closed：没有 Docker 沙箱时 `PythonExecuteTool` 返回
`isolation_unavailable` 而不是静默在宿主执行；文件工具被限制在
workspace 根内（防 `../` 与 symlink 逃逸）。详见 `docs/security.md`。

## 下一步

- [API 文档](API.md)
- [部署指南](DEPLOYMENT.md)
- [安全说明](security.md)
- [架构设计](architecture.md)
