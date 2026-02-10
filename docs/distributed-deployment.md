# 分布式部署指南

本文档介绍如何将 Agent-OS-Kernel 部署为分布式系统。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     负载均衡器 (Nginx)                       │
│                    lb.agent-os-kernel.io                     │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Worker 1   │    │   Worker 2   │    │   Worker N   │
│  node-1      │    │  node-2      │    │  node-n      │
├──────────────┤    ├──────────────┤    ├──────────────┤
│ API Server   │    │ API Server   │    │ API Server   │
│ Agent Core   │    │ Agent Core   │    │ Agent Core   │
│ Memory Store │    │ Memory Store │    │ Memory Store │
└──────────────┘    └──────────────┘    └──────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
        ┌─────────────────────────────────────────┐
        │         共享存储 (PostgreSQL)           │
        │  - 检查点存储    - 审计日志              │
        │  - 状态持久化   - 向量索引              │
        └─────────────────────────────────────────┘
```

## 前置要求

### 基础设施
- **负载均衡器**: Nginx / HAProxy / Cloud Load Balancer
- **消息队列** (可选): Redis / RabbitMQ / Kafka
- **共享存储**: PostgreSQL 15+
- **向量数据库** (可选): pgvector / Milvus / Qdrant
- **监控**: Prometheus + Grafana

### 服务器要求
- CPU: 4 核+
- 内存: 8GB+
- 存储: 50GB+
- 网络: 1Gbps+

## 部署步骤

### 1. 准备共享存储

```bash
# 安装 PostgreSQL
sudo apt install postgresql-15 postgresql-15-pgvector

# 创建数据库
sudo -u postgres psql
CREATE DATABASE aosk;
CREATE USER aosk_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aosk TO aosk_user;
\c aosk
GRANT ALL ON SCHEMA public TO aosk_user;
```

### 2. 配置共享存储

```yaml
# config.yaml
storage:
  backend: "postgresql"
  postgresql:
    host: "postgres.example.com"
    port: 5432
    database: "aosk"
    user: "aosk_user"
    password: "your_password"
    pool_size: 20
    max_overflow: 40
```

### 3. 配置 Redis 缓存 (可选)

```yaml
# config.yaml
cache:
  backend: "redis"
  redis:
    host: "redis.example.com"
    port: 6379
    password: "your_password"
    db: 0
    pool_size: 50
```

### 4. 配置消息队列 (可选)

```yaml
# config.yaml
message_queue:
  backend: "redis"  # 或 "rabbitmq", "kafka"
  redis:
    host: "redis.example.com"
    port: 6379
    queue_prefix: "aosk:"
```

### 5. Nginx 负载均衡配置

```nginx
# /etc/nginx/sites-available/agent-os-kernel

upstream agent_os_backend {
    least_conn;
    server node1.example.com:8080 weight=5;
    server node2.example.com:8080 weight=5;
    server node3.example.com:8080 weight=3;
    
    keepalive 32;
}

server {
    listen 80;
    server_name lb.agent-os-kernel.io;
    
    location / {
        proxy_pass http://agent_os_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # WebSocket 支持
        proxy_buffering off;
        proxy_cache off;
    }
    
    # 健康检查端点
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### 6. Docker Compose 集群配置

```yaml
# docker-compose.cluster.yml

version: '3.8'

services:
  # 负载均衡器
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - worker1
      - worker2
      - worker3
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Worker 节点 1
  worker1:
    image: agent-os-kernel:latest
    environment:
      - AOSK_STORAGE_BACKEND=postgresql
      - AOSK_POSTGRESQL_HOST=postgres
      - AOSK_NODE_ID=node-1
      - AOSK_REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  # Worker 节点 2
  worker2:
    image: agent-os-kernel:latest
    environment:
      - AOSK_STORAGE_BACKEND=postgresql
      - AOSK_POSTGRESQL_HOST=postgres
      - AOSK_NODE_ID=node-2
      - AOSK_REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  # Worker 节点 3
  worker3:
    image: agent-os-kernel:latest
    environment:
      - AOSK_STORAGE_BACKEND=postgresql
      - AOSK_POSTGRESQL_HOST=postgres
      - AOSK_NODE_ID=node-3
      - AOSK_REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: aosk
      POSTGRES_USER: aosk_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aosk_user -d aosk"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis 缓存
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    driver: overlay
    attachable: true
```

### 7. Kubernetes 部署 (可选)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-os-kernel
  namespace: aosk
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-os-kernel
  template:
    metadata:
      labels:
        app: agent-os-kernel
    spec:
      containers:
      - name: agent-os-kernel
        image: agent-os-kernel:latest
        ports:
        - containerPort: 8080
        env:
        - name: AOSK_STORAGE_BACKEND
          value: "postgresql"
        - name: AOSK_POSTGRESQL_HOST
          valueFrom:
            configMapKeyRef:
              name: aosk-config
              key: postgres_host
        - name: AOSK_POSTGRESQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aosk-secrets
              key: postgres_password
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: agent-os-kernel
  namespace: aosk
spec:
  selector:
    app: agent-os-kernel
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

## 高可用配置

### PostgreSQL 主从复制

```bash
# 主库配置
sudo tee /etc/postgresql/15/main/conf.d/replication.conf << EOF
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
wal_keep_size = 1GB
EOF

# 从库配置
pg_basebackup -h master.example.com -D /var/lib/postgresql/15/main -U replication -Fp -Xs -P -R
```

### 健康检查

```python
# health_check.py
import requests

def check_health(url: str) -> bool:
    try:
        r = requests.get(f"{url}/api/health", timeout=5)
        return r.json().get('status') == 'healthy'
    except:
        return False
```

## 监控配置

### Prometheus 配置

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agent-os-kernel'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: /metrics
```

### Grafana 仪表板

导入以下指标：
- Agent 数量
- CPU/内存使用率
- 请求延迟
- 错误率
- 吞吐量

## 故障排查

### 问题: Agent 无法连接到 PostgreSQL

```bash
# 检查连接
pg_isready -h postgres.example.com -p 5432 -U aosk_user

# 检查防火墙
sudo ufw status
```

### 问题: 负载不均衡

```bash
# 检查 Nginx 日志
tail -f /var/log/nginx/error.log

# 检查后端健康
for i in 1 2 3; do curl -s http://node$i.example.com:8080/health; done
```

### 问题: 内存不足

```bash
# 查看内存使用
free -h

# 查看进程
ps aux | grep python
```

## 扩缩容

### 水平扩容

```bash
# 增加 Worker 节点
docker-compose -f docker-compose.cluster.yml scale worker=5

# 或修改 K8s Deployment
kubectl scale deployment agent-os-kernel --replicas=5
```

### 垂直扩容

```yaml
# 增加资源限制
resources:
  limits:
    memory: "8Gi"
    cpu: "4"
```

## 备份恢复

### PostgreSQL 备份

```bash
# 备份
pg_dump -h postgres.example.com -U aosk_user aosk > aosk_backup_$(date +%Y%m%d).sql

# 恢复
psql -h postgres.example.com -U aosk_user aosk < aosk_backup_20240101.sql
```

### 增量备份

```bash
# 配置 WAL 归档
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'
```
