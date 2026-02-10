# 更新日志

## v1.0.0 (2026-02-10)

### 新增核心模块

- **TaskQueue** - 任务队列，支持优先级、重试、延迟任务
- **ConfigManager** - 配置管理，支持热加载、多环境
- **WorkflowEngine** - DAG 工作流引擎
- **EventBus** - 事件驱动架构
- **CircuitBreaker** - 熔断器
- **MetricsCollector** - 指标收集器
- **AgentPool** - Agent 池
- **AgentRegistry** - Agent 注册中心
- **RateLimiter** - 速率限制器
- **ToolMarket** - 工具市场

### 新增 LLM Providers

- **Kimi** - Moonshot AI (kimi-k2.5)
- **DeepSeek** - DeepSeek Chat/Reasoner
- **MiniMax** - MiniMax Chat
- **Groq** - 高性能推理
- **Ollama** - 本地模型
- **vLLM** - 高性能推理引擎

### 新增文档

- [架构设计](architecture.md)
- [API 参考](api-reference.md)
- [部署指南](deployment.md)
- [配置管理](configuration.md)
- [任务队列](task-queue.md)
- [安全指南](security.md)

### 研究文档

- CrewAI, LangGraph, AutoGPT 研究
- AgentOps, SuperAGI 研究
- AIOS, OpenAgents 深度分析

### 性能优化

- Context 管理优化
- 批处理支持
- 多级缓存

### 重大变更

- AgentConfig 增加 role/goal/backstory
- 统一的事件系统
- 新的插件架构

## v0.9.0 (2026-02-01)

### 初始版本

- 基础 Agent 抽象
- 上下文管理
- PostgreSQL 存储
- MCP 工具支持
