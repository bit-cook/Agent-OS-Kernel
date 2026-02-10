# Agent-OS-Kernel 项目结构

```
Agent-OS-Kernel/
├── agent_os_kernel/         # 核心代码 (40+ 模块)
│   ├── core/               # 核心模块
│   │   ├── learning/       # 自学习系统
│   │   │   ├── trajectory.py   # 轨迹记录
│   │   │   └── optimizer.py    # 策略优化
│   │   │
│   │   ├── optimization/   # 性能优化
│   │   │   ├── batch.py        # 批处理
│   │   │   ├── cache.py        # 缓存
│   │   │   └── compressor.py   # 压缩
│   │   │
│   │   ├── kernel.py           # 主内核
│   │   ├── context_manager.py  # 上下文管理
│   │   ├── scheduler.py        # 调度器
│   │   ├── storage.py          # 存储
│   │   ├── security.py         # 安全
│   │   ├── metrics.py          # 指标
│   │   ├── events.py           # 事件
│   │   ├── state.py            # 状态
│   │   ├── types.py            # 类型定义
│   │   ├── exceptions.py       # 异常
│   │   ├── plugin_system.py    # 插件系统
│   │   │
│   │   ├── agent_definition.py # Agent 定义
│   │   ├── task_manager.py     # 任务管理
│   │   ├── checkpointer.py     # 检查点
│   │   ├── enhanced_memory.py  # 增强记忆
│   │   ├── cost_tracker.py     # 成本追踪
│   │   ├── observability.py    # 可观测性
│   │   ├── agent_pool.py      # Agent 池
│   │   ├── rate_limiter.py    # 速率限制
│   │   ├── workflow_engine.py # 工作流引擎
│   │   ├── event_bus.py       # 事件总线
│   │   ├── tool_market.py     # 工具市场
│   │   ├── metrics_collector.py # 指标收集
│   │   ├── circuit_breaker.py  # 熔断器
│   │   └── agent_registry.py  # Agent 注册
│   │
│   ├── agents/              # Agent 模块
│   │   ├── base.py           # 基类
│   │   ├── react.py         # ReAct Agent
│   │   ├── autogen_bridge.py # AutoGen 桥接
│   │   ├── workflow_agent.py # 工作流 Agent
│   │   └── communication/   # 通信模块
│   │       ├── messenger.py
│   │       ├── knowledge_share.py
│   │       ├── group_chat.py
│   │       └── collaboration.py
│   │
│   ├── llm/                 # LLM Providers
│   │   ├── provider.py      # 抽象层
│   │   ├── factory.py       # 工厂
│   │   ├── openai.py        # OpenAI
│   │   ├── anthropic.py     # Anthropic
│   │   ├── deepseek.py      # DeepSeek
│   │   ├── kimi.py         # Kimi
│   │   ├── minimax.py      # MiniMax
│   │   ├── qwen.py         # Qwen
│   │   ├── ollama.py       # Ollama
│   │   ├── vllm.py         # vLLM
│   │   └── mock_provider.py # Mock
│   │
│   ├── tools/              # 工具系统
│   │   ├── base.py         # 基类
│   │   ├── registry.py      # 注册表
│   │   ├── builtin.py       # 内置工具
│   │   └── mcp/            # MCP 协议
│   │       ├── client.py
│   │       └── registry.py
│   │
│   ├── api/               # Web API
│   │   ├── server.py       # FastAPI 服务
│   │   └── static/         # 管理界面
│   │
│   ├── cli/               # CLI
│   │   └── main.py        # CLI 主程序
│   │
│   ├── distributed/        # 分布式
│   ├── integrations/       # 集成
│   └── resources/         # 资源
│
├── examples/              # 示例代码 (27)
│   ├── quickstart/        # 快速开始 (3)
│   ├── advanced/          # 高级功能 (7)
│   ├── workflow/          # 工作流 (2)
│   ├── api/               # API (4)
│   └── integration/       # 集成 (17)
│
├── research/             # 研究文档 (15)
│   ├── framework/         # 框架研究 (10)
│   ├── analysis/          # 深度分析 (2)
│   └── summary/           # 总结 (2)
│
├── docs/                 # 文档 (14)
├── config/               # 配置 (2)
├── tests/                # 测试 (20+)
├── scripts/              # 脚本
└── development-docs/     # 开发文档
```

## 统计

| 类别 | 数量 |
|------|------|
| 核心模块 | 40+ |
| 示例文件 | 27 |
| 研究文档 | 15 |
| 测试文件 | 20+ |
| 文档 | 14 |

## 设计原则

1. **模块化** - 每个目录职责单一
2. **分层** - core → agents → llm → tools
3. **可扩展** - 插件系统、工具市场
4. **可观测** - 指标、事件、日志
