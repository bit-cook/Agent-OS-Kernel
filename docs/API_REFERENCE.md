# API 参考文档

## 核心模块概览

Agent-OS-Kernel 提供以下核心模块：

### agent_definition

Agent Definition - 完整的 Agent 定义

参考 CrewAI 设计，添加 role/goal/backstory

**主要类**: AgentStatus, AgentConstraints, AgentDefinition, TaskDefinition, CrewDefinition

### agent_migration

Agent Migration - Agent热迁移

支持Agent状态保存、跨节点迁移、状态恢复

**主要类**: AgentState, MigrationInfo, AgentMigration

### agent_pool

Agent Pool - Agent 对象池

管理 Agent 实例的复用，提高性能。

**主要类**: PooledAgent, AgentPool

### agent_pool_enhanced

Enhanced Agent Pool for Agent-OS-Kernel

This module provides an enhanced agent pool with:
- Priorit

**主要类**: AgentState, AgentPriority, AgentTask, AgentHealthChecker, DefaultHealthChecker

### agent_registry

Agent Registry - Agent 注册中心

**主要类**: AgentMetadata, AgentRegistry

### api_gateway

API Gateway Module - Agent-OS-Kernel API网关模块

提供请求路由、速率限制、认证中间件和请求/响应转换功能。

**主要类**: HTTPMethod, GatewayError, RouteNotFoundError, RateLimitExceededError, UnauthorizedError

### async_queue

Async Queue - 异步队列

高性能异步消息队列，支持发布/订阅模式。

**主要类**: QueueType, MessageStatus, Message, AsyncQueue

### batch_processor

批处理器

**主要类**: AggregationType, Batch, SlidingWindowProcessor, BatchProcessor

### benchmark

Performance Benchmark Tools - Agent-OS-Kernel 性能基准测试工具

提供延迟测量、吞吐量测量、资源监控和性能报告生成功能。

**主要类**: LatencyResult, ThroughputResult, ResourceUsage, LatencyBenchmark, ThroughputBenchmark

### bulkhead

Bulkhead Pattern Implementation for Agent-OS-Kernel

The bulkhead pattern isolates failures and limi

**主要类**: BulkheadConfig, BulkheadState, BulkheadError, BulkheadFullError, BulkheadTimeoutError

### cache_system

Cache System - 缓存系统

支持多级缓存、TTL、缓存失效、分布式缓存。

**主要类**: CacheLevel, EvictionPolicy, CacheEntry, CacheSystem

### cache_system_enhanced

Advanced Cache System for Agent-OS-Kernel

This module provides a multi-tier, distributed caching sy

**主要类**: EvictionPolicy, CacheLevel, CacheEntry, CachePolicy, LRUCachePolicy

### cache_utils

缓存工具模块 - 提供常用缓存策略

**主要类**: LRUCache, TTLCache

### checkpointer

Checkpointer - 检查点管理器

支持状态保存/恢复/时间旅行。

**主要类**: CheckpointStatus, Checkpoint, Checkpointer

### circuit_breaker

Circuit Breaker Module

A robust implementation of the Circuit Breaker pattern for preventing
cascad

**主要类**: CircuitState, CircuitError, CircuitMetrics, CircuitConfig, CircuitBreaker

### command_pattern

Command Pattern Implementation

This module provides a generic command pattern implementation for en

**主要类**: CommandStatus, CommandContext, Command, SimpleCommand, ValueCommand

### config_hot_reload

Config Hot Reload Module

Configuration hot reload functionality with file watching, auto-reload,
co

**主要类**: ConfigChangeType, ConfigChange, ConfigSchema, ConfigValidator, ConfigFileHandler

### config_manager

Config Manager - 配置管理器

支持多环境配置、动态更新、配置热加载。

**主要类**: ConfigSection, ConfigManager

### config_manager_enhanced

Enhanced Config Manager - 配置管理增强版

支持配置热重载、环境变量、配置文件模板

**主要类**: ConfigSection, EnhancedConfigManager

### connection_pool

Connection Pool Module - 提供连接池功能

支持:
- 连接管理
- 连接复用
- 连接健康检查
- 连接超时

**主要类**: ConnectionState, ConnectionConfig, ConnectionInfo, ConnectionCreateError, ConnectionAcquireError

### context_manager

Context Manager - 上下文管理器

实现操作系统级的虚拟内存机制：
- 将 LLM 上下文窗口视为 RAM（有限、快速、昂贵）
- 将数据库存储视为 Disk（无限、慢速、便宜）
- 

**主要类**: PageStatus, ContextPage, MemoryHierarchy, KVCacheOptimizer, SemanticImportanceCalculator

### cost_tracker

Cost Tracker - 成本追踪

参考 AgentOps 的成本追踪功能

**主要类**: CostEntry, CostLimit, CostTracker

### countdown_timer

倒计时计时器模块 - Agent-OS-Kernel

提供倒计时功能、定时提醒、多次提醒和异步支持。
适用于需要时间管理的各种场景。

**主要类**: TimerState, TimerAlert, CountdownTimer, CountdownTimerManager

### distributed_lock

Distributed Lock Module - 提供分布式锁功能

支持:
- 互斥锁 (Mutex Lock)
- 读写锁 (Read-Write Lock)
- 超时机制
- 锁续期 (Loc

**主要类**: LockType, LockState, LockOwner, LockAcquireError, LockRenewalError

### distributed_scheduler

Distributed Scheduler - 分布式调度器

跨节点任务调度、负载均衡、故障转移

**主要类**: SchedulerState, NodeInfo, TaskInfo, DistributedScheduler

### enhanced_memory

Enhanced Memory - 增强的记忆系统

参考 CrewAI 和 AutoGPT 的记忆设计

**主要类**: MemoryType, MemoryItem, ShortTermMemory, LongTermMemory, EntityMemory

### error_handler

错误处理器模块 - Agent OS Kernel

提供完整的错误处理功能:
- 错误捕获
- 错误分类
- 错误恢复
- 错误报告

**主要类**: ErrorSeverity, ErrorCategory, ErrorInfo, ErrorHandler

### event_bus

Event Bus - 事件总线

发布/订阅模式的事件驱动架构。

**主要类**: EventPriority, Event, Subscription, EventBus

### event_bus_enhanced

Enhanced Event Bus - 增强型事件总线

完整的发布/订阅事件系统，支持优先级、通配符、持久化。

**主要类**: EventPriority, EventType, Event, Subscription, EnhancedEventBus

### event_system_advanced

Advanced Event System for Agent-OS-Kernel

This module provides advanced event handling capabilities

**主要类**: EventPriority, EventType, Event, EventFilter, EventFilterChain

### events

Event System - 事件系统

支持：
1. 事件发布/订阅
2. 事件类型过滤
3. 异步事件处理
4. 事件优先级
5. 事件历史

**主要类**: EventType, Event, EventHandler, EventBus

### exceptions

Exceptions - 异常定义

标准化的异常层次结构，便于错误处理和调试

**主要类**: AgentOSKernelError, AgentError, AgentNotFoundError, AgentCreationError, AgentExecutionError

### gpu_manager

GPU Resource Manager - GPU资源管理器

支持NVIDIA GPU监控、内存管理、计算分配

**主要类**: GPUInfo, GPUAllocation, GPUManager

### health_checker

Health Checker Module - Agent-OS-Kernel 健康检查器模块

提供全面的系统和服务健康检查功能：
1. 服务健康检查 - 检查本地和远程服务的运行状态
2. 依赖检

**主要类**: HealthStatus, CheckType, HealthCheckResult, ServiceCheckConfig, DependencyCheckConfig

### lock_manager

Lock Manager - 锁管理器

支持分布式锁、读写锁、信号量、限时锁。

**主要类**: LockType, LockStatus, Lock, LockManager, async_lock

### logging_system

Logging System - 日志系统

结构化日志、级别控制、输出格式

**主要类**: LogLevel, LogRecord, StructuredLogger

### memory_feedback

Memory Feedback - 记忆反馈系统

支持自然语言纠正、补充、替换记忆内容。

**主要类**: FeedbackType, MemoryFeedback, MemoryFeedbackSystem

### message_queue

Message Queue Module for Agent-OS-Kernel

This module provides message queue capabilities including:

**主要类**: MessagePriority, MessageStatus, Message, Subscription, PriorityMessageQueue

### metrics

Metrics - 性能指标

支持：
1. 收集性能指标
2. 计算统计信息
3. 导出指标
4. 设置告警阈值

**主要类**: MetricType, Metric, MetricsCollector

### metrics_collector

Metrics Collector - Agent-OS-Kernel 指标收集器

提供完整的指标收集系统,包括:
- Counter (计数器): 只增不减的指标
- Gauge (仪表盘): 可

**主要类**: MetricType, ExportFormat, MetricLabel, MetricSample, Counter

### monitoring

Monitoring - 监控系统

支持健康检查、性能监控、告警系统。

**主要类**: HealthStatus, HealthCheck, MetricPoint, Monitor

### monitoring_system

Monitoring System - 监控告警系统

健康检查、性能指标、告警规则

**主要类**: AlertSeverity, AlertStatus, Alert, HealthCheck, MonitoringSystem

### observability

Observability - 可观测性

参考 AgentOps 设计，提供完整的可观测性功能

**主要类**: EventType, Event, Session, CallbackHandler, FileCallbackHandler

### observer_pattern

Observer Pattern Implementation

This module provides a generic observer pattern implementation for 

**主要类**: EventPriority, Event, Observer, Subject, ObserverRegistry

### optimized_scheduler

Optimized Scheduler - MemScheduler 理念借鉴

借鉴 MemOS 的 MemScheduler 思路，优化任务调度。

**主要类**: Priority, TaskStatus, ScheduledTask, OptimizedScheduler

### optimizer

Performance Optimization Tools - Agent-OS-Kernel 性能优化工具

提供连接池优化、缓存优化、并发优化和内存优化功能。

**主要类**: PoolConfig, CacheConfig, ConcurrencyConfig, ConnectionPool, LRUCache

### pipeline

Pipeline - 数据管道

支持多阶段处理、并行管道、条件分支。

**主要类**: PipelineStage, PipelineItem, Pipeline

### plugin_system

Plugin System for Agent-OS-Kernel

提供完整的插件系统，包括：
- 插件加载 (Plugin Loading)
- 插件注册 (Plugin Registration

**主要类**: PluginState, PluginEventType, PluginInfo, BasePlugin, PluginMessage

### rate_bucket

Token Bucket Rate Limiter

A dedicated token bucket implementation for rate limiting with:
- Token g

**主要类**: TokenBucketConfig, TokenBucket, AsyncTokenBucket

### rate_limiter

Rate Limiter - 速率限制器

用于控制 API 调用频率。

**主要类**: RateLimitConfig, RateLimiter, MultiLimiter

### rate_limiter_enhanced

Advanced Rate Limiter for Agent-OS-Kernel

Provides multiple rate limiting algorithms:
- Sliding Win

**主要类**: RateLimitConfig, RateLimitResult, RateLimiter, SlidingWindowLimiter, TokenBucketLimiter

### retry_mechanism

重试机制模块 - Retry Mechanism

提供指数退避、最大重试次数、重试条件和重试超时等功能。

功能:
- 指数退避 (Exponential Backoff)
- 最大重试次数 (Ma

**主要类**: RetryExhaustedError, RetryCondition, RetryPolicy, RetryMechanism

### scheduler

Agent Scheduler - 进程调度器

实现真正的操作系统级进程管理：
- 抢占式调度（优先级 + 时间片）
- 状态持久化（Checkpoint/恢复）
- 进程间通信（IPC）
- 优雅

**主要类**: AgentState, ResourceQuota, AgentProcess, SchedulableProcess, IPCChannel

### security

Security Subsystem - 安全子系统

类比操作系统的权限管理 + 沙箱：
- Docker 容器隔离
- 完整的审计追踪
- 决策过程可视化
- 执行回放功能

**主要类**: PermissionLevel, SecurityPolicy, SandboxManager, PermissionManager

### service_mesh

Service Mesh Module - Agent-OS-Kernel 服务网格模块

提供服务发现、负载均衡、熔断器和服务间通信功能。

**主要类**: CircuitState, LoadBalancingStrategy, ServiceInstance, ServiceInfo, CircuitBreaker

### state

State Management - 状态管理

支持：
1. Agent 状态追踪
2. 状态持久化
3. 状态恢复
4. 状态转换历史

**主要类**: AgentState, StateTransition, AgentStateRecord, StateManager

### state_machine

状态机模块 - State Machine Module

提供完整的状态机功能，包括：
- 状态定义
- 状态转换
- 事件处理
- 状态回调

**主要类**: TransitionType, Transition, StateCallbacks, StateMachine, HierarchicalStateMachine

### storage

存储管理器

支持多种存储后端：
- Memory (内存)
- File (文件系统)
- PostgreSQL (关系数据库)
- Vector (向量数据库)

五重角色：
1. 记忆存储 (E

**主要类**: StorageStats, StorageInterface, MemoryStorage, FileStorage, PostgreSQLStorage

### storage_enhanced

Enhanced Storage Manager - 增强存储管理器

完整实现五种存储角色。

**主要类**: StorageRole, StorageStats, EnhancedStorageManager

### strategy_pattern

Strategy Pattern Module

Provides a flexible implementation of the Strategy pattern for algorithm
se

**主要类**: StrategyType, StrategyError, StrategyNotFoundError, StrategyRegistrationError, Strategy

### stream_handler

Stream Handler - 流处理器

支持流式数据处理、文本/Token 流、实时数据管道。

**主要类**: StreamType, StreamStatus, StreamChunk, StreamHandler, StreamManager

### task_manager

任务管理器

**主要类**: ExecutionStatus, TaskStatus, Execution, TaskManager

### task_queue

任务队列

**主要类**: TaskStatus, TaskPriority, Task, TaskQueue

### task_scheduler

任务调度器模块 - Agent-OS-Kernel

提供定时任务、周期性任务、任务优先级和任务依赖管理功能。
支持cron表达式调度、间隔执行和任务链执行。

**主要类**: TaskPriority, SchedulerState, ScheduledTask, TaskExecution, TaskScheduler

### time_window

Time Window Module

Provides time window functionality including:
- Sliding window: A moving window 

**主要类**: TimeWindow, SlidingWindow, FixedWindow, WindowMerger, WindowStats

### tool_market

Tool Market - 工具市场

动态工具发现、加载和管理系统。

**主要类**: ToolInfo, ToolMarket

### tool_memory

Tool Memory - 工具记忆

记录 Agent 的工具使用历史，支持规划和优化。

**主要类**: ToolStatus, ToolCall, ToolMemory

### toolkit

工具模块集合 - Agent-OS-Kernel 核心工具包

提供常用的工具类和函数。

**主要类**: Timer, Singleton

### trace_manager

Trace Manager Module

Distributed tracing module for the Agent-OS-Kernel. This module provides:
- Sp

**主要类**: SpanStatus, SpanKind, Span, TraceContext, SpanExporter

### types

核心类型定义

**主要类**: AgentState, PageType, StorageBackend, ToolCategory, ResourceQuota

### validation_utils

验证工具模块 - 提供数据验证功能

**主要类**: ValidationResult, Validator, SchemaValidator

### worker

Worker - 工作池

支持工作进程池、任务分发、负载均衡。

**主要类**: WorkerStatus, Worker, WorkerPool, NoAvailableWorkerError

### workflow_engine

工作流引擎模块 - Agent-OS-Kernel

提供工作流定义、任务调度、依赖管理和错误处理功能。
支持DAG结构的工作流定义，自动处理任务依赖和执行顺序。

**主要类**: TaskStatus, WorkflowStatus, TaskResult, TaskConfig, Task

