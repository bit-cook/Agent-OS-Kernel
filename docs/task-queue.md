# 任务队列

## 概述

Agent OS Kernel 提供强大的任务队列系统，支持优先级队列、延迟任务、任务重试。

## 快速开始

### 创建队列

```python
from agent_os_kernel.core.task_queue import TaskQueue, TaskPriority

queue = TaskQueue(
    max_concurrent=10,  # 最大并发数
    max_size=10000,      # 最大队列大小
    default_timeout=300  # 默认超时
)
```

### 提交任务

```python
async def process_data(data):
    return data * 2

task_id = await queue.submit(
    "process_task",
    process_data,
    100,
    priority=TaskPriority.HIGH,
    max_retries=3
)
```

## 任务优先级

| 优先级 | 值 | 用途 |
|--------|-----|------|
| `CRITICAL` | 0 | 系统关键任务 |
| `HIGH` | 1 | 重要用户请求 |
| `NORMAL` | 2 | 普通任务 |
| `LOW` | 3 | 后台任务 |
| `BACKGROUND` | 4 | 非常低优先级 |

## 核心功能

### 1. 延迟任务

```python
# 延迟 5 秒执行
await queue.submit_delay(
    "delayed_task",
    send_notification,
    delay_seconds=5
)
```

### 2. 任务重试

```python
await queue.submit(
    "unreliable_task",
    unstable_api_call,
    max_retries=3,
    retry_delay=1.0  # 重试间隔
)
```

### 3. 获取结果

```python
result = await queue.get_result(task_id, timeout=10)
```

## API 参考

### TaskQueue

| 方法 | 说明 |
|------|------|
| `submit()` | 提交任务 |
| `submit_delay()` | 提交延迟任务 |
| `get_result()` | 获取结果 |
| `cancel()` | 取消任务 |
| `get_status()` | 获取状态 |
| `get_stats()` | 获取统计 |

### 任务状态

| 状态 | 说明 |
|------|------|
| `PENDING` | 等待中 |
| `RUNNING` | 运行中 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |
| `RETRYING` | 重试中 |

## 最佳实践

1. **合理设置优先级**
2. **设置超时时间**
3. **限制并发数**
4. **监控队列深度**
