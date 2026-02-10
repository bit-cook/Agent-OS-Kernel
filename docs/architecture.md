# 架构设计文档

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent Applications                              │
│        (CodeAssistant │ ResearchAgent │ DataAnalyst...)              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      🎛️ Agent OS Kernel                               │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐          │
│  │   Context      │ │   Process      │ │     I/O        │          │
│  │   Manager      │ │   Scheduler    │ │   Manager      │          │
│  │  (虚拟内存)    │ │   (调度器)     │ │   (工具系统)   │          │
│  └────────────────┘ └────────────────┘ └────────────────┘          │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │         💾 Storage Layer (PostgreSQL 五重角色)             │       │
│  │  记忆存储 │ 状态持久化 │ 向量索引 │ 审计日志 │ 检查点存储 │       │
│  └────────────────────────────────────────────────────────────┘       │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │        🔒 Security Subsystem (安全与可观测性)               │       │
│  │      沙箱隔离 │ 可观测性 │ 决策审计 │ 权限控制              │       │
│  └────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    🖥️ Hardware Resources                               │
│              LLM APIs │ Vector DB │ Message Queue                    │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心子系统

### 1. Context Manager (上下文管理器)

**职责**: 虚拟内存式上下文管理

**核心特性**:
- 将 LLM 上下文窗口视为 RAM
- 将数据库存储视为 Disk
- 自动页面置换 (LRU + 重要性 + 语义相似度)
- KV-Cache 优化

**组件**:
- `ContextPage`: 上下文页面
- `PageManager`: 页面管理
- `SwapManager`: 页面置换
- `KVCacheOptimizer`: KV-Cache 优化

### 2. Process Scheduler (进程调度器)

**职责**: Agent 进程生命周期管理

**核心特性**:
- 抢占式调度
- 时间片轮转
- 优先级调度
- 公平共享

**组件**:
- `AgentProcess`: Agent 进程
- `Scheduler`: 主调度器
- `ResourceQuota`: 资源配额

### 3. I/O Manager (I/O 管理器)

**职责**: 工具/工具系统管理

**核心特性**:
- Agent-Native CLI
- 工具注册与发现
- 工具执行与安全检查

**组件**:
- `ToolRegistry`: 工具注册表
- `ToolExecutor`: 工具执行器
- `ToolSecurity`: 工具安全

### 4. Storage Layer (存储层)

**职责**: 持久化存储

**五重角色**:
1. 记忆存储 (Episodic Memory)
2. 状态持久化 (State Persistence)
3. 向量索引 (Vector Index)
4. 审计日志 (Audit Log)
5. 检查点存储 (Checkpoint Storage)

**支持后端**:
- Memory (内存)
- File (文件系统)
- PostgreSQL (关系数据库)
- Vector (向量数据库)

### 5. Security Subsystem (安全子系统)

**职责**: 安全与可观测性

**核心特性**:
- 沙箱隔离
- 权限控制
- 审计追踪
- 速率限制
- 熔断器

## 数据流

### Agent 创建流程

```
1. 接收创建请求
         │
         ▼
2. 验证参数 (名称、优先级等)
         │
         ▼
3. 创建 AgentProcess
         │
         ▼
4. 分配上下文页面 (System + Task + Tools)
         │
         ▼
5. 注册到调度器
         │
         ▼
6. 保存到存储层 (持久化)
         │
         ▼
7. 返回 PID
```

### 任务执行流程

```
1. 从调度器获取 Agent
         │
         ▼
2. 获取上下文 (从内存/磁盘)
         │
         ▼
3. 调用 LLM (生成工具调用)
         │
         ▼
4. 执行工具 (通过 I/O Manager)
         │
         ▼
5. 更新上下文
         │
         ▼
6. 检查是否需要页面置换
         │
         ▼
7. 返回结果
```

## 性能优化

### 上下文管理

- **页面预取**: 基于访问模式预测
- **批处理**: 合并多个小页面操作
- **压缩**: 对旧上下文进行压缩
- **索引**: 使用向量索引加速检索

### 调度优化

- **时间片自适应**: 根据工作负载调整
- **优先级继承**: 避免优先级反转
- **负载均衡**: 多核并行处理

### 存储优化

- **连接池**: 复用数据库连接
- **读写分离**: 主从复制
- **缓存**: 多级缓存策略

## 扩展性

### 插件系统

支持通过插件扩展功能：

```python
# 注册插件
manager.register_plugin("my_plugin.py")

# 注册钩子
manager.register_hook(Hooks.BEFORE_AGENT_SPAWN, callback)
manager.register_hook(Hooks.AFTER_TOOL_CALL, callback)
```

### 自定义工具

```python
class MyTool:
    name = "my_tool"
    description = "My custom tool"
    
    def execute(self, param1, param2):
        return {"result": "success"}
```

## 监控指标

### 核心指标

- `cpu_usage`: CPU 使用率
- `memory_usage`: 内存使用率
- `context_hit_rate`: 上下文命中率
- `swap_count`: 页面置换次数
- `active_agents`: 活跃 Agent 数
- `tool_calls_per_second`: 工具调用率

### 健康检查

- `gateway_latency`: Gateway 延迟
- `storage_health`: 存储健康状态
- `scheduler_load`: 调度器负载
