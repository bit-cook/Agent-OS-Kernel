# 监控与告警

## 概述

Agent OS Kernel 提供完整的监控和告警系统，支持健康检查、性能指标、告警触发。

## Monitor

### 基本使用

```python
from agent_os_kernel.core.monitoring import Monitor, HealthStatus

monitor = Monitor(
    name="agent-os",
    collect_interval=10.0
)
```

### 健康检查

```python
# 检查整体健康状态
status = monitor.get_overall_status()
print(status.value)  # healthy, degraded, unhealthy, critical

# 执行所有健康检查
results = await monitor.check_health()
for name, check in results.items():
    print(f"{name}: {check.status.value}")
```

### 自定义健康检查

```python
def check_database() -> HealthCheck:
    try:
        # 检查数据库连接
        db_status = check_db_connection()
        return HealthCheck(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database is healthy",
            latency_ms=10.0
        )
    except Exception as e:
        return HealthCheck(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=str(e),
            latency_ms=0
        )

monitor.register_health_check("database", check_database)
```

### 指标记录

```python
# 记录指标
monitor.record_metric("request_count", 100)
monitor.record_metric("response_time_ms", 150.5)
monitor.record_metric("error_rate", 0.05, labels={"type": "timeout"})

# 获取指标
metrics = monitor.get_metrics("request_count", limit=10)
```

### 告警系统

```python
# 注册告警回调
def handle_alert(alert):
    print(f"Alert: {alert['name']} - {alert['message']}")

monitor.on_alert(handle_alert)

# 触发告警
monitor.trigger_alert(
    name="high_cpu",
    message="CPU usage above 90%",
    severity="critical",
    details={"cpu_percent": 95}
)
```

### 系统信息

```python
# 获取系统信息
info = monitor.get_system_info()
print(f"Hostname: {info['hostname']}")
print(f"CPU: {info['cpu_count']}")
print(f"Memory: {info['memory_total'] / 1024 / 1024 / 1024:.2f} GB")
```

## WorkerPool

### 创建工作池

```python
from agent_os_kernel.core.worker import WorkerPool, WorkerStatus

pool = WorkerPool(
    name="processing",
    max_workers=10,
    strategy="least_busy"  # round_robin, least_busy, random
)
```

### 添加工作节点

```python
# 添加工作节点
pool.add_worker(
    worker_id="worker-1",
    name="Processor-1",
    metadata={"type": "cpu"}
)

pool.add_worker(
    worker_id="worker-2", 
    name="Processor-2",
    metadata={"type": "gpu"}
)
```

### 提交任务

```python
async def process_data(data):
    await asyncio.sleep(0.1)
    return {"result": data * 2}

# 提交任务
task_id = await pool.submit(
    task_id="task-1",
    func=process_data,
    data=100
)

# 获取结果
result = await pool.get_result(task_id)
print(result)  # {"result": 200}
```

### 管理工作节点

```python
# 列出工作节点
workers = pool.list_workers()
for w in workers:
    print(f"{w.name}: {w.status.value}")

# 获取可用节点
available = pool.get_available_workers()

# 移除节点
pool.remove_worker("worker-1")
```

## 统计信息

```python
# 监控统计
stats = monitor.get_stats()
print(f"状态: {stats['overall_status']}")
print(f"运行时间: {stats['uptime_seconds']:.0f}s")
print(f"指标数: {stats['metrics_count']}")
print(f"告警数: {stats['alerts_count']}")

# 工作池统计
pool_stats = pool.get_stats()
print(f"总节点: {pool_stats['total_workers']}")
print(f"可用节点: {pool_stats['available_workers']}")
print(f"总任务: {pool_stats['total_tasks']}")
```
