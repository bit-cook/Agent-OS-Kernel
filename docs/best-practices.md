# 最佳实践指南

## 项目结构最佳实践

```
agent-os-kernel/
├── src/                    # 源代码
│   ├── core/              # 核心模块
│   ├── llm/              # LLM Provider
│   ├── tools/             # 工具系统
│   ├── agents/            # Agent 模块
│   └── api/               # API 服务
├── examples/              # 示例代码
├── tests/                 # 测试
├── docs/                  # 文档
└── scripts/               # 脚本
```

## Agent 设计最佳实践

### 1. 单一职责原则

```python
# ✅ 好: 每个 Agent 一个职责
agent1 = kernel.spawn_agent(
    name="CodeReviewer",
    task="审查代码质量和安全问题"
)

agent2 = kernel.spawn_agent(
    name="DocumentationWriter",
    task="编写技术文档"
)

# ❌ 避免: Agent 职责过多
agent = kernel.spawn_agent(
    name="SuperAgent",
    task="写代码、审查、部署、监控、写文档..."
)
```

### 2. 优先级设置

```python
# 高优先级 - 实时任务
kernel.spawn_agent(
    name="RealtimeAgent",
    task="处理用户请求",
    priority=10  # 0-100, 越小越优先
)

# 低优先级 - 后台任务
kernel.spawn_agent(
    name="BackgroundAgent",
    task="数据清理",
    priority=90
)
```

### 3. 上下文管理

```python
# ✅ 好: 合理分配上下文
page_id = context_manager.allocate_page(
    agent_pid=agent_id,
    content=important_content,
    importance=0.9  # 高重要性
)

# ❌ 避免: 所有内容同等重要
for content in all_contents:
    context_manager.allocate_page(
        agent_pid=agent_id,
        content=content,
        importance=0.5  # 所有内容同等重要
    )
```

## 配置最佳实践

### 1. 环境变量

```bash
# .env
DEEPSEEK_API_KEY=sk-xxx
KIMI_API_KEY=kim-xxx
POSTGRES_URL=postgresql://...
REDIS_URL=redis://...
```

```yaml
# config.yaml
api_keys:
  deepseek: "${DEEPSEEK_API_KEY}"
  kimi: "${KIMI_API_KEY}"
```

### 2. 安全配置

```python
from agent_os_kernel import SecurityPolicy

# ✅ 好: 明确的安全策略
policy = SecurityPolicy(
    permission_level=PermissionLevel.STANDARD,
    max_memory_mb=512,
    allowed_paths=["/workspace"],
    blocked_paths=["/etc", "/root", "/home"],
    network_enabled=True,
    allowed_hosts=["api.openai.com"]
)

# ❌ 避免: 过于宽松的策略
policy = SecurityPolicy(
    permission_level=PermissionLevel.PERMISSIVE
)
```

## 测试最佳实践

### 1. 使用 Mock Provider

```python
from agent_os_kernel.llm import create_mock_provider

# ✅ 好: 使用 Mock 测试
provider = create_mock_provider()
result = await provider.chat(messages)

# ❌ 避免: 每次都调用真实 API
provider = create_openai_provider(api_key="real-key")
result = await provider.chat(messages)  # 消耗 API quota
```

### 2. 测试覆盖

```python
# ✅ 好: 测试所有路径
def test_agent_workflow():
    agent = kernel.spawn_agent(name="Test", task="Test")
    
    # 测试成功路径
    result = agent.execute(success_input)
    assert result.success
    
    # 测试失败路径
    result = agent.execute(error_input)
    assert not result.success
    assert result.error is not None
```

## 性能最佳实践

### 1. 上下文缓存

```python
# ✅ 好: 缓存频繁访问的上下文
from agent_os_kernel import ContextManager

cm = ContextManager(
    max_context_tokens=128000,
    enable_cache=True
)

# 缓存系统提示
cm.allocate_page(
    agent_pid=agent_id,
    content=system_prompt,
    importance=1.0,  # 最高优先级
    page_type="system"  # 特殊类型，不易被置换
)
```

### 2. 批量操作

```python
# ✅ 好: 批量提交任务
tasks = [
    {"task": "任务1"},
    {"task": "任务2"},
    {"task": "任务3"},
]

for task in tasks:
    kernel.spawn_agent(**task)

# ❌ 避免: 逐个提交
for task in tasks:
    kernel.spawn_agent(**task)
    time.sleep(1)  # 不必要的等待
```

## 日志最佳实践

```python
import logging

# ✅ 好: 结构化日志
logger = logging.getLogger(__name__)

logger.info("Agent created", extra={
    "agent_id": agent_id,
    "agent_name": name,
    "task": task
})

# ✅ 好: 使用不同的日志级别
logger.debug("Detailed info")
logger.info("General info")
logger.warning("Warning")
logger.error("Error")
```

## 错误处理最佳实践

```python
from agent_os_kernel.core.exceptions import (
    AgentError,
    AgentTimeoutError,
    SecurityError
)

# ✅ 好: 明确的错误处理
try:
    result = await agent.execute(task)
except AgentTimeoutError:
    # 超时处理
    await agent.restart()
except SecurityError:
    # 安全错误
    logger.error("Security violation")
except AgentError as e:
    # 一般错误
    logger.error(f"Agent error: {e}")
```

## 监控最佳实践

```python
from agent_os_kernel import MetricsCollector

metrics = MetricsCollector()

# ✅ 好: 记录关键指标
metrics.counter("agent_started")
metrics.counter("task_completed")
metrics.histogram("execution_time", duration)

# ✅ 好: 使用标签
metrics.counter(
    "api_calls",
    labels={"provider": "deepseek", "model": "chat"}
)
```

## 部署最佳实践

### Docker

```dockerfile
# ✅ 好: 多阶段构建
FROM python:3.11-slim AS builder
COPY . /app
RUN pip install --no-cache /app

FROM python:3.11-slim
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app
CMD ["python", "-m", "agent_os_kernel"]
```

### Kubernetes

```yaml
# ✅ 好: 资源限制
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

# ✅ 好: 健康检查
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

## 代码风格

```python
# ✅ 好: 类型注解
from typing import Dict, List, Optional

async def create_agent(
    name: str,
    task: str,
    priority: int = 50,
    metadata: Optional[Dict] = None
) -> str:
    """创建 Agent"""
    pass

# ✅ 好: Docstring
def process_data(data: Data) -> Result:
    """处理数据并返回结果
    
    Args:
        data: 输入数据
        
    Returns:
        处理结果
        
    Raises:
        ValueError: 数据格式错误
    """
    pass
```

## 性能优化清单

- [ ] 使用上下文缓存
- [ ] 批量操作
- [ ] 异步处理
- [ ] 资源限制
- [ ] 监控指标
- [ ] 日志记录
- [ ] 错误处理
- [ ] 超时控制
