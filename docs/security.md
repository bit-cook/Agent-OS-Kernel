# 安全指南

## 概述

Agent OS Kernel 提供多层安全机制，确保 Agent 运行的安全性。

## 安全层级

### 1. 权限级别

| 级别 | 描述 | 能力 |
|------|------|------|
| `RESTRICTED` | 受限模式 | 仅允许基本操作 |
| `STANDARD` | 标准模式 | 允许大多数操作 |
| `ADVANCED` | 高级模式 | 允许敏感操作 |
| `FULL` | 完全模式 | 允许所有操作 |

### 2. 资源配额

```python
from agent_os_kernel import ResourceQuota

quota = ResourceQuota(
    max_tokens=128000,      # 最大 Token 数
    max_memory_mb=1024,     # 最大内存 (MB)
    max_cpu_percent=50,     # 最大 CPU 使用率
    max_disk_gb=10          # 最大磁盘使用 (GB)
)
```

### 3. 路径限制

```python
from agent_os_kernel import SecurityPolicy

policy = SecurityPolicy(
    permission_level=PermissionLevel.STANDARD,
    allowed_paths=["/workspace"],
    blocked_paths=["/etc", "/root", "/var/log"],
    max_file_size_mb=100,
    allowed_extensions=[".py", ".txt", ".md"]
)
```

## 安全策略配置

### 配置文件

```yaml
security:
  permission_level: "STANDARD"
  
  resources:
    max_tokens: 128000
    max_memory_mb: 512
    max_cpu_percent: 50
    max_disk_gb: 5
  
  paths:
    allowed:
      - "/workspace"
    blocked:
      - "/etc"
      - "/root"
      - "*.exe"
  
  network:
    allowed_domains:
      - "api.openai.com"
      - "api.deepseek.com"
    blocked_domains:
      - "malicious.com"
```

## 沙箱隔离

### 进程隔离

```python
kernel.spawn_agent(
    name="SandboxedAgent",
    sandbox=True,  # 启用沙箱
    policy=policy
)
```

### 文件系统限制

```python
# 只能访问 /workspace 目录
policy = SecurityPolicy(
    allowed_paths=["/workspace"],
    blocked_paths=["/etc", "/root", "/home"]
)
```

### 网络访问控制

```python
policy = SecurityPolicy(
    network_restrictions={
        "allowed_ips": ["8.8.8.8"],
        "blocked_ips": ["10.0.0.0/8"],
        "allowed_ports": [443, 80],
        "blocked_ports": [22, 3389]
    }
)
```

## API 安全

### API Key 管理

```bash
# 生成 API Key
python -m agent_os_kernel.cli key generate

# 设置环境变量
export AGENT_OS_API_KEY="your-api-key"
```

### 认证中间件

```python
from agent_os_kernel.api import AuthMiddleware

auth = AuthMiddleware(
    api_keys=["key1", "key2"],
    jwt_secret="your-secret"
)
```

## 审计日志

### 启用审计

```python
from agent_os_kernel.core import AuditLogger

logger = AuditLogger(
    enabled=True,
    storage="postgresql",
    retention_days=90
)
```

### 日志内容

```json
{
  "timestamp": "2026-02-10T15:00:00Z",
  "agent_id": "agent-001",
  "action": "file_write",
  "resource": "/workspace/test.py",
  "result": "success",
  "user": "admin"
}
```

## 最佳实践

1. **最小权限**：始终使用最低必要权限
2. **资源限制**：设置合理的资源配额
3. **网络隔离**：限制不必要的网络访问
4. **审计记录**：启用完整的审计日志
5. **定期审查**：定期检查安全日志

## 常见问题

### Q: 如何限制 Agent 的文件访问？

```python
policy = SecurityPolicy(
    allowed_paths=["/workspace"],
    blocked_paths=["/etc", "/root"]
)
```

### Q: 如何禁用网络访问？

```python
policy = SecurityPolicy(
    network_access=False
)
```

### Q: 如何查看审计日志？

```bash
agent-os-kernel audit logs --agent agent-001
```
