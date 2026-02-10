# API 使用指南

## 概述

Agent OS Kernel 提供 RESTful API 用于管理和操作 Agent 系统。

## 基础 URL

```
http://localhost:8000/api/v1
```

## 认证

所有 API 请求需要携带 API Key：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/agents
```

## Agent 管理

### 列出所有 Agent

```bash
GET /api/v1/agents
```

**响应示例：**
```json
{
  "agents": [
    {
      "id": "agent-001",
      "name": "Assistant",
      "status": "running",
      "created_at": "2026-02-10T10:00:00Z"
    }
  ],
  "total": 1
}
```

### 创建 Agent

```bash
POST /api/v1/agents
```

**请求体：**
```json
{
  "name": "MyAgent",
  "role": "general",
  "goal": "帮助用户完成任务",
  "model": "gpt-4o",
  "max_iterations": 100
}
```

### 获取 Agent 信息

```bash
GET /api/v1/agents/{agent_id}
```

### 删除 Agent

```bash
DELETE /api/v1/agents/{agent_id}
```

### 发送消息

```bash
POST /api/v1/agents/{agent_id}/messages
```

**请求体：**
```json
{
  "content": "请帮我写一个 Python 脚本",
  "stream": true
}
```

## 任务管理

### 列出任务

```bash
GET /api/v1/tasks
```

### 创建任务

```bash
POST /api/v1/tasks
```

**请求体：**
```json
{
  "name": "research_task",
  "description": "研究 AI 发展趋势",
  "agent_id": "agent-001",
  "priority": 80
}
```

### 获取任务状态

```bash
GET /api/v1/tasks/{task_id}
```

### 取消任务

```bash
DELETE /api/v1/tasks/{task_id}
```

## 内存管理

### 获取上下文

```bash
GET /api/v1/agents/{agent_id}/memory
```

### 保存记忆

```bash
POST /api/v1/agents/{agent_id}/memory
```

### 清空内存

```bash
DELETE /api/v1/agents/{agent_id}/memory
```

## 系统状态

### 健康检查

```bash
GET /health
```

### 系统统计

```bash
GET /api/v1/stats
```

**响应示例：**
```json
{
  "running_agents": 3,
  "queued_tasks": 5,
  "memory_usage_mb": 512,
  "cpu_percent": 45.2
}
```

## WebSocket 连接

支持实时通信：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request parameters",
    "details": {}
  }
}
```

### 常见错误码

| 代码 | 描述 |
|------|------|
| `INVALID_REQUEST` | 请求参数无效 |
| `NOT_FOUND` | 资源不存在 |
| `RATE_LIMITED` | 请求频率超限 |
| `INTERNAL_ERROR` | 服务器内部错误 |

## 速率限制

| 级别 | 请求数/分钟 |
|------|-------------|
| 免费 | 60 |
| Pro | 600 |
| Enterprise | 6000 |

## Python SDK 示例

```python
from agent_os_kernel.api import Client

client = Client(base_url="http://localhost:8000", api_key="your-key")

# 创建 Agent
agent = client.create_agent(
    name="Assistant",
    role="general",
    goal="帮助用户"
)

# 发送消息
response = agent.send_message("请帮我写代码")
print(response)
```
