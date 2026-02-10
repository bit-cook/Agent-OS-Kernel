# 部署指南

## 概述

本文档介绍如何在不同环境中部署 Agent OS Kernel。

## Docker 部署

### 基础镜像

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "-m", "agent_os_kernel"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  agent-os:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/agent_os
      - REDIS_URL=redis://cache:6379
    depends_on:
      - db
      - cache
    volumes:
      - ./config:/app/config

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: agent_os

  cache:
    image: redis:7-alpine
```

## Kubernetes 部署

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-os
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-os
  template:
    metadata:
      labels:
        app: agent-os
    spec:
      containers:
      - name: agent-os
        image: agent-os:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### HPA 自动伸缩

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-os-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent-os
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 生产环境配置

### 1. 数据库

```python
# 高可用配置
from agent_os_kernel import StorageManager

storage = StorageManager.from_postgresql(
    connection_string=POSTGRES_URL,
    pool_size=20,
    max_overflow=10
)
```

### 2. 缓存

```python
from agent_os_kernel.core.enhanced_memory import EnhancedMemory

memory = EnhancedMemory(
    short_term_ttl=3600,
    long_term_enabled=True
)
```

### 3. 监控

```python
from agent_os_kernel.core.metrics_collector import MetricsCollector

metrics = MetricsCollector(
    flush_interval=60,
    enable_console=True
)
```

## 安全配置

### 1. 网络隔离

```python
from agent_os_kernel import SecurityPolicy

policy = SecurityPolicy(
    permission_level=PermissionLevel.STANDARD,
    allowed_paths=["/workspace"],
    blocked_paths=["/etc", "/root"],
    network_access=True
)
```

### 2. API 密钥

```bash
# 使用环境变量
export AGENT_OS_API_KEY="your-api-key"
export AGENT_OS_SECRET_KEY="your-secret-key"
```

## 性能优化

### 1. 连接池

```python
# PostgreSQL 连接池
await storage.initialize(pool_size=20)
```

### 2. 批处理

```python
# 批量处理任务
from agent_os_kernel.core.optimization import BatchProcessor

processor = BatchProcessor(batch_size=100, timeout_ms=1000)
```

### 3. 缓存策略

```python
from agent_os_kernel.core.optimization import TieredCache

cache = TieredCache(
    memory_size=1000,
    disk_size=10000
)
```

## 日志配置

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent-os.log'),
        logging.StreamHandler()
    ]
)
```

## 故障恢复

### 1. 检查点恢复

```python
# 从检查点恢复
new_pid = kernel.restore_checkpoint(checkpoint_id)
```

### 2. 熔断器

```python
from agent_os_kernel.core import CircuitBreaker

breaker = CircuitBreaker("api", CircuitConfig(failure_threshold=5))
```

## 监控告警

### Prometheus 指标

```python
from agent_os_kernel.core import MetricsCollector

collector = MetricsCollector()
collector.gauge("agent_running", count)
collector.counter("task_completed", 1)
```

### 告警规则

```yaml
groups:
- name: agent-os
  rules:
  - alert: AgentDown
    expr: agent_os_running == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Agent down"
```
