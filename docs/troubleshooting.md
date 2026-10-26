# 故障排查指南

## 常见问题

### 1. 安装问题

#### 问题：pip 安装失败

```bash
# 错误：Could not find a version that satisfies the requirement

# 解决方案
pip install --upgrade pip
pip install agent-os-kernel --no-cache-dir
```

#### 问题：依赖冲突

```bash
# 解决方案：使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate   # Windows
pip install -e .
```

---

### 2. API Key 问题

#### 问题：API Key 未设置

**错误信息**：
```
ValueError: API key is required
```

**解决方案**：
```python
# 检查环境变量
import os
print(os.getenv("DEEPSEEK_API_KEY"))

# 设置环境变量
# Linux/Mac:
export DEEPSEEK_API_KEY="your-key"

# Windows:
set DEEPSEEK_API_KEY=your-key

# 或在代码中设置
os.environ["DEEPSEEK_API_KEY"] = "your-key"
```

#### 问题：API Key 无效

**错误信息**：
```
AuthenticationError: Invalid API key
```

**解决方案**：
1. 检查 API Key 是否正确
2. 确认 Key 是否有对应权限
3. 检查 Key 是否过期

---

### 3. 模型调用问题

#### 问题：模型不存在

**错误信息**：
```
ModelNotFoundError: Model not found
```

**解决方案**：
```python
# 检查模型名称
providers = factory.list_providers()
print(providers)

# 使用正确的模型名称
config = LLMConfig(
    provider="deepseek",
    model="deepseek-chat"  # 正确的模型名称
)
```

#### 问题：API 调用超时

**错误信息**：
```
TimeoutError: Request timed out
```

**解决方案**：
```python
# 增加超时时间
config = LLMConfig(
    provider="deepseek",
    timeout=120.0  # 120秒
)

# 使用重试
config = LLMConfig(
    provider="deepseek",
    max_retries=5  # 最多重试5次
)
```

#### 问题：Rate limit

**错误信息**：
```
RateLimitError: Too many requests
```

**解决方案**：
```python
# 使用指数退避
import asyncio

async def call_with_backoff():
    for i in range(5):
        try:
            return await provider.complete(messages)
        except RateLimitError:
            await asyncio.sleep(2 ** i)  # 退避
```

---

### 4. 内存问题

#### 问题：上下文过长

**错误信息**：
```
ContextLengthExceeded: Context too long
```

**解决方案**：
```python
# 使用上下文压缩
from agent_os_kernel.core.optimization import compress_context

compressed = compress_context(
    messages,
    max_tokens=4000,
    strategy="hybrid"
)
```

#### 问题：内存泄漏

**症状**：
- 内存使用持续增长
- Agent 运行变慢

**解决方案**：
```python
# 定期清理
kernel.shutdown()

# 使用上下文压缩
compressor = ContextCompressor(max_tokens=4000)
```

---

### 5. Agent 问题

#### 问题：Agent 无响应

**症状**：Agent 一直运行但不返回结果

**解决方案**：
```python
# 设置超时
agent_pid = kernel.spawn_agent(
    name="Agent",
    task="Task",
    timeout=60
)

# 强制终止
kernel.terminate_agent(agent_pid)
```

#### 问题：Agent 崩溃

**错误信息**：
```
AgentCrashedError: Agent crashed
```

**解决方案**：
```python
# 启用错误恢复
from agent_os_kernel.distributed import AgentMigration

migration = AgentMigration()

# 创建检查点
checkpoint_id = await migration.create_checkpoint(
    agent_id=agent_pid,
    state=agent_state,
    context=context,
    memory=memory,
    tools_state=tools_state
)

# 从检查点恢复
restored = await migration.restore_from_checkpoint(checkpoint_id)
```

---

### 6. 分布式问题

#### 问题：节点不可达

**错误信息**：
```
ConnectionError: Node not reachable
```

**解决方案**：
```python
# 检查节点状态
status = await scheduler.get_cluster_status()

# 检查网络连接
import socket

socket.setdefaulttimeout(5)
try:
    socket.create_connection(("node-host", port))
    print("Node reachable")
except:
    print("Node not reachable")
```

#### 问题：任务分发失败

**错误信息**：
```
TaskDistributionError: Failed to distribute task
```

**解决方案**：
```python
# 检查任务配置
task_config = {
    "agent_id": "agent-1",
    "priority": 50,
    "preferred_nodes": ["node-1", "node-2"]
}

# 重新提交任务
await scheduler.submit_task(
    task_id="new-task-id",
    agent_config=task_config
)
```

---

### 7. GPU 问题

#### 问题：GPU 不可用

**错误信息**：
```
GPUNotFoundError: No GPU available
```

**解决方案**：
```python
# 检查 GPU 状态
from agent_os_kernel.resources import GPUMonitor

monitor = GPUMonitor()
devices = await monitor.detect_devices()

if not devices:
    print("No GPU available, using CPU")
```

#### 问题：显存不足

**错误信息**：
```
OutOfMemoryError: GPU out of memory
```

**解决方案**：
```python
# 减少内存分配
await gpu_manager.allocate_for_agent(
    agent_id=agent_pid,
    required_memory_mb=4096,  # 减少到 4GB
    preferred_devices=[0]
)

# 释放未使用的内存
await gpu_manager.release_agent_memory(agent_pid)
```

---

### 8. 监控问题

#### 问题：告警过多

**症状**：收到大量告警通知

**解决方案**：
```python
# 调整告警阈值
monitor.add_alert_rule(AlertRule(
    name="High CPU",
    metric="cpu_percent",
    threshold=95.0,  # 提高阈值
    operator=">",
    duration_seconds=300  # 延长持续时间
))
```

#### 问题：监控数据丢失

**症状**：历史数据不完整

**解决方案**：
```python
# 增大历史存储
monitor = SystemMonitor(history_size=7200)  # 2小时

# 定期导出
export = monitor.export_metrics(3600)
```

---

## 日志查看

### 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

### 查看日志文件

```bash
# 默认日志位置
tail -f agent_os_kernel.log

# Docker 日志
docker logs agent-os-kernel
```

---

## 调试技巧

### 1. 使用调试模式

```python
kernel = AgentOSKernel(debug=True)
```

### 2. 打印执行轨迹

```python
agent = kernel.get_agent(agent_pid)
trace = agent.get_trace()
print(trace)
```

### 3. 检查资源使用

```python
# CPU 使用
psutil.cpu_percent()

# 内存使用
psutil.virtual_memory()

# 磁盘使用
psutil.disk_usage('/')
```

---

## 联系支持

如果以上方案无法解决问题：

1. 查看[文档](../docs/)
2. 检查 [GitHub Issues](https://github.com/bit-cook/Agent-OS-Kernel/issues)
3. 创建 Issue 反馈问题

---

## 错误代码参考

| 错误代码 | 含义 | 解决方案 |
|---------|------|---------|
| E001 | API Key 缺失 | 设置环境变量 |
| E002 | API Key 无效 | 检查 Key |
| E003 | 模型不存在 | 检查模型名称 |
| E004 | 请求超时 | 增加超时时间 |
| E005 | 速率限制 | 使用退避 |
| E006 | 上下文过长 | 使用压缩 |
| E007 | Agent 崩溃 | 检查日志 |
| E008 | 节点离线 | 检查网络 |
| E009 | GPU 不可用 | 使用 CPU |
| E010 | 显存不足 | 减少分配 |
