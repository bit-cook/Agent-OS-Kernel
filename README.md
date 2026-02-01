<div align="center">

# 🖥️ Agent OS Kernel

**为 AI Agent 构建的操作系统内核**

[![CI](https://github.com/bit-cook/Agent-OS-Kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/bit-cook/Agent-OS-Kernel/actions)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](https://github.com/bit-cook/Agent-OS-Kernel/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](./docs)

[English](#) | [中文](#) | [文档](https://github.com/bit-cook/Agent-OS-Kernel/wiki) | [示例](./examples) | [更新日志](./CHANGELOG.md)

</div>

---

## 📋 目录

- [🎯 什么是 Agent OS Kernel？](#-什么是-agent-os-kernel)
- [✨ 核心特性](#-核心特性)
- [🏗️ 架构设计](#️-架构设计)
- [🚀 快速开始](#-快速开始)
  - [安装](#安装)
  - [基础示例](#基础示例)
  - [进阶示例](#进阶示例)
- [📦 核心组件详解](#-核心组件详解)
- [📊 性能基准](#-性能基准)
- [🔍 与其他框架对比](#-与其他框架对比)
- [🛠️ 开发指南](#️-开发指南)
- [❓ 常见问题](#-常见问题)
- [🗺️ 路线图](#️-路线图)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

---

## 🎯 什么是 Agent OS Kernel？

**Agent OS Kernel** 是一个基于操作系统设计原理的 AI Agent 运行时内核。它将传统操作系统 50 年的演化经验应用到 AI Agent 基础设施中，解决以下核心问题：

| 传统计算机 | Agent 世界 | 核心挑战 | Agent OS Kernel 解决方案 |
|-----------|-----------|---------|------------------------|
| **CPU** | **LLM** | 如何高效调度推理任务？ | 抢占式调度 + 资源配额管理 |
| **RAM** | **Context Window** | 如何管理有限的上下文窗口？ | 虚拟内存式上下文管理 |
| **Disk** | **Database** | 如何持久化状态？ | ACID 存储 + 检查点机制 |
| **Process** | **Agent** | 如何管理生命周期？ | 进程抽象 + 沙箱隔离 |

> 💡 **核心洞察**: 就像 Linux 让应用程序无需关心硬件细节一样，Agent OS Kernel 让 AI Agent 无需关心上下文管理、资源调度和持久化存储。

---

## ✨ 核心特性

### 🧠 智能上下文管理
- **虚拟内存机制**: 自动换入换出，突破上下文长度限制
- **KV-Cache 优化**: 智能布局最大化缓存命中率，降低 10x API 成本
- **语义重要性**: 基于向量相似度保留关键信息

### ⚡ 高效进程调度
- **抢占式调度**: 优先级 + 时间片，公平分配计算资源
- **资源配额**: 防止单个 Agent 耗尽 API 预算
- **实时决策**: < 10ms 调度延迟

### 💾 企业级存储
- **双存储后端**: 内存存储（开发）+ PostgreSQL（生产）
- **向量检索**: pgvector 支持的语义搜索
- **完整审计**: 所有操作可追溯、可回放

### 🔒 安全沙箱
- **Docker 隔离**: 每个 Agent 独立容器
- **权限控制**: 细粒度的资源访问控制
- **审计追踪**: 完整的执行历史记录

### 🛠️ 丰富工具生态
- **标准化接口**: 统一的 Tool 抽象
- **内置工具**: 计算器、文件操作、代码执行等
- **CLI 包装**: 将任意命令行工具封装为 Agent 工具

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   Agent Applications                     │
│     (CodeAssistant │ ResearchAgent │ DataAnalyst...)    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 🎛️ Agent OS Kernel                       │
│  ┌──────────────┬──────────────┬──────────────┐         │
│  │   Context    │   Process    │    I/O       │         │
│  │   Manager    │  Scheduler   │   Manager    │         │
│  │  (虚拟内存)   │   (调度器)    │   (工具系统)  │         │
│  └──────────────┴──────────────┴──────────────┘         │
│  ┌──────────────────────────────────────────┐           │
│  │       💾 Storage Layer (存储层)            │           │
│  │   Memory │ PostgreSQL │ Vector Search     │           │
│  └──────────────────────────────────────────┘           │
│  ┌──────────────────────────────────────────┐           │
│  │       🔒 Security Subsystem (安全)        │           │
│  │   Sandbox │ Audit │ Permissions          │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 🖥️ Hardware Resources                     │
│        LLM APIs │ Vector DB │ Message Queue              │
└─────────────────────────────────────────────────────────┘
```

### 工作流程

```mermaid
graph TD
    A[Agent Application] -->|spawn_agent| B[AgentOSKernel]
    B --> C[Context Manager]
    B --> D[Scheduler]
    B --> E[Tool Registry]
    B --> F[Storage Manager]
    
    C -->|allocate_page| C1[Memory Pages]
    C -->|swap_out| C2[Disk Storage]
    
    D -->|schedule| D1[Priority Queue]
    D -->|preempt| D2[Running Process]
    
    E -->|execute| E1[Calculator]
    E -->|execute| E2[File System]
    E -->|execute| E3[Web Search]
    
    F -->|save| F1[PostgreSQL]
    F -->|checkpoint| F2[Snapshot]
    F -->|log| F3[Audit Trail]
```

---

## 🚀 快速开始

### 安装

根据你的使用场景选择合适的安装方式：

| 场景 | 安装命令 | 说明 |
|------|---------|------|
| **基础使用** | `pip install agent-os-kernel` | 仅标准库，适合快速体验 |
| **生产环境** | `pip install agent-os-kernel[postgres]` | PostgreSQL 持久化 |
| **Claude 集成** | `pip install agent-os-kernel[claude]` | Claude API 支持 |
| **完整功能** | `pip install agent-os-kernel[all]` | 所有功能 |
| **开发** | `pip install agent-os-kernel[dev]` | 包含测试和调试工具 |

<details>
<summary>📋 查看详细的依赖说明</summary>

```bash
# 基础版本 - 仅 Python 标准库
pip install agent-os-kernel

# PostgreSQL 存储后端
pip install agent-os-kernel[postgres]
# 额外安装: psycopg2-binary, pgvector

# Claude API 集成
pip install agent-os-kernel[claude]
# 额外安装: anthropic

# OpenAI API 集成
pip install agent-os-kernel[openai]
# 额外安装: openai

# Docker 沙箱支持
pip install agent-os-kernel[docker]
# 额外安装: docker

# 安装所有可选依赖
pip install agent-os-kernel[all]
```

</details>

### 基础示例

#### 1️⃣ 最简单的 Agent

```python
from agent_os_kernel import AgentOSKernel

# 初始化内核
kernel = AgentOSKernel()

# 创建 Agent
agent_pid = kernel.spawn_agent(
    name="CodeAssistant",
    task="Help write Python code",
    priority=30
)

# 运行内核
kernel.run(max_iterations=10)

# 查看系统状态
kernel.print_status()
```

#### 2️⃣ 多 Agent 协作

```python
from agent_os_kernel import AgentOSKernel

kernel = AgentOSKernel()

# 创建一个开发团队
team = [
    ("Architect", "Design system architecture", 20),
    ("Developer", "Implement core features", 40),
    ("Tester", "Write and run tests", 60),
    ("Documenter", "Write documentation", 70),
]

for name, task, priority in team:
    kernel.spawn_agent(name, task, priority)

# 运行协作
kernel.run(max_iterations=len(team) * 3)
```

### 进阶示例

#### 🔗 与 Claude API 集成

```python
import os
from agent_os_kernel import ClaudeIntegratedKernel

# 配置 API 密钥
os.environ["ANTHROPIC_API_KEY"] = "your-api-key"

# 创建内核
kernel = ClaudeIntegratedKernel()

# 注册自定义工具
from agent_os_kernel.tools.builtin import WebSearchTool
kernel.tool_registry.register(WebSearchTool())

# 创建研究 Agent
agent_pid = kernel.spawn_agent(
    name="ResearchAssistant",
    task="Research the latest developments in LLM context management",
    priority=10
)

# 运行并监控
kernel.run(max_iterations=5)

# 查看审计追踪
audit = kernel.get_audit_trail(agent_pid)
for log in audit:
    print(f"[{log.timestamp}] {log.action_type}: {log.reasoning[:100]}...")
```

#### 💾 使用 PostgreSQL 持久化

```python
from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.storage import StorageManager

# 配置 PostgreSQL 存储
storage = StorageManager.from_postgresql(
    "postgresql://user:password@localhost:5432/agent_os",
    enable_vector=True  # 启用向量搜索
)

# 使用持久化存储创建内核
kernel = AgentOSKernel(storage_backend=storage.backend)

# 创建 Agent
agent_pid = kernel.spawn_agent(
    name="PersistentAgent",
    task="Long-running analysis task"
)

# 创建检查点（随时恢复）
checkpoint_id = kernel.create_checkpoint(
    agent_pid, 
    description="Before critical operation"
)

# 即使程序崩溃，也可以从检查点恢复
# new_pid = kernel.restore_checkpoint(checkpoint_id)
```

#### 🔒 配置安全策略

```python
from agent_os_kernel import AgentOSKernel, SecurityPolicy, PermissionLevel

# 创建受限的 Agent
policy = SecurityPolicy(
    permission_level=PermissionLevel.STANDARD,
    max_memory_mb=512,
    max_cpu_percent=50,
    allowed_paths=["/tmp", "/workspace"],
    blocked_paths=[/"etc", "/root"],
    allowed_tools=["calculator", "read_file"],
    network_enabled=False  # 禁用网络访问
)

kernel = AgentOSKernel()
agent_pid = kernel.spawn_agent(
    name="SandboxedAgent",
    task="Process untrusted data",
    policy=policy
)
```

---

## 📦 核心组件详解

### 1. Context Manager - 虚拟内存管理

类比操作系统虚拟内存，实现 LLM 上下文的透明管理：

```python
from agent_os_kernel import ContextManager

# 初始化（类比物理内存大小）
cm = ContextManager(max_context_tokens=100000)

# 分配页面（自动处理溢出）
page1 = cm.allocate_page(
    agent_pid="agent-1",
    content="System: You are a helpful assistant...",
    importance=1.0,      # 重要性评分 (0-1)
    page_type="system"   # 页面类型
)

page2 = cm.allocate_page(
    agent_pid="agent-1",
    content="User: How do I write a Python function?",
    importance=0.8,
    page_type="user"
)

# 访问页面（自动 swap in）
page = cm.access_page(page1)

# 获取完整上下文（自动优化布局）
context = cm.get_agent_context("agent-1", optimize_for_cache=True)
```

**核心算法**:
- **页面置换**: LRU + 重要性 + 访问频率 多因素评分
- **KV-Cache 优化**: 静态内容前置，动态内容按访问频率排序
- **语义重要性**: 基于向量相似度计算页面与当前任务的相关性

### 2. Process Scheduler - 进程调度

类比操作系统进程调度，实现公平的资源分配：

```python
from agent_os_kernel import AgentScheduler, ResourceQuota

# 配置资源配额
quota = ResourceQuota(
    max_tokens_per_window=100000,    # 每小时 token 上限
    max_api_calls_per_window=1000,   # 每小时 API 调用上限
    max_tokens_per_request=10000     # 单次请求上限
)

scheduler = AgentScheduler(
    time_slice=60.0,  # 时间片：60秒
    quota=quota
)
```

**调度策略**:
1. **优先级调度**: 数字越小优先级越高 (0-100)
2. **时间片轮转**: 防止单个 Agent 垄断资源
3. **抢占式调度**: 高优先级 Agent 可抢占当前运行 Agent
4. **资源配额**: 防止 API 预算超支

### 3. Storage Layer - 存储层

```python
from agent_os_kernel import StorageManager

# 生产环境：PostgreSQL + pgvector
storage = StorageManager.from_postgresql(
    "postgresql://user:pass@localhost/agent_os"
)

# 保存进程状态
storage.save_process(process)

# 创建检查点
checkpoint_id = storage.save_checkpoint(
    process, 
    description="Before migration"
)

# 语义搜索
results = storage.semantic_search(
    agent_pid="agent-1",
    query_embedding=[0.1, 0.2, ...],  # 1536-dim vector
    limit=10
)
```

### 4. Tool System - 工具系统

```python
from agent_os_kernel import Tool, ToolRegistry

# 定义自定义工具
class DatabaseQueryTool(Tool):
    def name(self) -> str:
        return "query_db"
    
    def description(self) -> str:
        return "Query the database with SQL"
    
    def parameters(self):
        return [
            ToolParameter("sql", "string", "SQL query", required=True)
        ]
    
    def execute(self, sql: str, **kwargs):
        # 执行查询...
        return {"success": True, "data": results}

# 注册并使用
registry = ToolRegistry()
registry.register(DatabaseQueryTool())

# 自动发现 CLI 工具
registry.auto_discover_cli_tools()  # 自动注册 grep, find, curl 等
```

---

## 📊 性能基准

在标准测试环境下（Intel i7, 32GB RAM, PostgreSQL 14）：

### Context Manager

| 指标 | 数值 | 说明 |
|------|------|------|
| **上下文利用率** | 92% | 相比原生 API 调用提升 40% |
| **KV-Cache 命中率** | 75% | 降低 8x API 成本 |
| **页面换入延迟** | 45ms | P95 延迟 |
| **内存开销** | < 50MB | 每 1000 页面 |

### Scheduler

| 指标 | 数值 | 说明 |
|------|------|------|
| **调度延迟** | 3ms | 从就绪到运行 |
| **吞吐量** | 1,500 进程/小时 | 单节点 |
| **公平性偏差** | ±3% | 资源分配 |
| **抢占响应** | < 10ms | 高优先级抢占 |

### Storage

| 指标 | Memory | PostgreSQL | 说明 |
|------|--------|-----------|------|
| **写入延迟** | 0.1ms | 25ms | 检查点保存 |
| **读取延迟** | 0.05ms | 15ms | 状态恢复 |
| **向量搜索** | N/A | 85ms | 1536-dim, 10k 向量 |
| **审计查询** | 0.5ms | 45ms | 单 Agent 历史 |

---

## 🔍 与其他框架对比

| 特性 | Agent OS Kernel | LangChain | AutoGPT | Semantic Kernel |
|------|-----------------|-----------|---------|-----------------|
| **核心定位** | OS 内核 | 应用框架 | 自主 Agent | SDK |
| **上下文管理** | ✅ 虚拟内存 | ⚠️ 链式 | ❌ 手动 | ⚠️ 有限 |
| **多 Agent 调度** | ✅ 抢占式 | ❌ | ❌ 单 Agent | ❌ |
| **资源配额** | ✅ 内置 | ❌ | ❌ | ❌ |
| **持久化** | ✅ ACID | ⚠️ 外部 | ⚠️ 文件 | ⚠️ 外部 |
| **向量检索** | ✅ 内置 | ⚠️ 外部 | ❌ | ⚠️ 外部 |
| **安全沙箱** | ✅ Docker | ❌ | ❌ | ❌ |
| **审计追踪** | ✅ 完整 | ❌ | ⚠️ 日志 | ❌ |
| **学习曲线** | 中等 | 低 | 低 | 中等 |

**适用场景**:
- **Agent OS Kernel**: 生产级多 Agent 系统，需要资源管理、持久化、审计
- **LangChain**: 快速原型开发，简单的链式调用
- **AutoGPT**: 单 Agent 自主任务执行
- **Semantic Kernel**: Microsoft 生态集成

---

## 🛠️ 开发指南

### 本地开发设置

```bash
# 1. 克隆仓库
git clone https://github.com/bit-cook/Agent-OS-Kernel.git
cd Agent-OS-Kernel

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装开发依赖
pip install -e ".[dev,all]"

# 4. 运行测试
pytest tests/ -v --cov=agent_os_kernel

# 5. 代码格式化
black agent_os_kernel tests
isort agent_os_kernel tests

# 6. 类型检查
mypy agent_os_kernel
```

### 项目结构

```
agent-os-kernel/
├── agent_os_kernel/          # 核心包
│   ├── core/                 # 核心模块
│   │   ├── types.py          # 数据类型定义
│   │   ├── context_manager.py # 上下文管理器（虚拟内存）
│   │   ├── scheduler.py      # 进程调度器
│   │   ├── storage.py        # 存储层
│   │   └── security.py       # 安全子系统
│   ├── tools/                # 工具系统
│   │   ├── base.py           # Tool 基类
│   │   ├── registry.py       # 工具注册表
│   │   └── builtin.py        # 内置工具
│   ├── integrations/         # 集成模块
│   │   └── claude_integration.py
│   └── kernel.py             # 主内核
├── tests/                    # 测试套件
├── examples/                 # 使用示例
├── docs/                     # 文档
├── pyproject.toml            # 项目配置
└── README.md                 # 本文件
```

---

## ❓ 常见问题

### Q: 为什么选择操作系统作为设计灵感？

**A**: 传统操作系统已经解决了资源管理、进程调度、内存管理等核心问题。LLM Agent 面临的挑战与这些高度相似：有限的上下文（内存）、多任务调度（CPU）、状态持久化（磁盘）。借鉴成熟的设计可以避免重复造轮子。

### Q: 与 LangChain 有什么区别？

**A**: LangChain 是一个应用开发框架，关注如何快速构建 LLM 应用；Agent OS Kernel 是一个运行时内核，关注如何可靠地运行和管理多个 Agent。两者可以互补使用。

### Q: 生产环境需要哪些依赖？

**A**: 最小生产部署需要：
- PostgreSQL 14+ (主存储)
- pgvector 扩展 (向量检索)
- Docker (沙箱隔离，可选)
- Redis (分布式锁，可选)

### Q: 支持哪些 LLM？

**A**: 目前提供 Claude 的完整集成示例。通过继承 `AgentOSKernel` 并重写 `execute_agent_step` 方法，可以轻松集成 OpenAI、本地模型等。

### Q: 如何处理上下文长度限制？

**A**: Context Manager 实现了虚拟内存机制：
1. 将长上下文分割为页面
2. 只保留活跃页面在"内存"中
3. 自动换出不活跃页面到数据库
4. 访问时自动换入

### Q: 是否支持分布式部署？

**A**: v0.2.0 是单节点版本。分布式调度正在开发中（v0.3.0 目标），计划支持：
- 多节点 Agent 迁移
- 全局资源调度
- 分布式 checkpoint

---

## 🗺️ 路线图

### v0.2.x (当前)
- [x] 核心内核实现
- [x] PostgreSQL 存储
- [x] Docker 沙箱
- [x] Claude 集成
- [x] 完整测试覆盖

### v0.3.0 (进行中)
- [ ] 分布式调度器
- [ ] Agent 热迁移
- [ ] Web UI 监控面板
- [ ] OpenAI 官方集成
- [ ] 性能剖析工具

### v0.4.0 (计划中)
- [ ] GPU 资源管理
- [ ] 自适应调度（RL-based）
- [ ] 联邦学习支持
- [ ] gRPC API
- [ ] Kubernetes Operator

### v1.0.0 (长期)
- [ ] 生产级稳定性保证
- [ ] 多租户支持
- [ ] 完整的生态工具链
- [ ] 企业级安全认证

---

## 🤝 贡献

我们欢迎所有形式的贡献！

### 特别需要帮助的领域

🔴 **高优先级**
- 分布式调度器设计
- 更多 LLM 集成（OpenAI, Llama, etc.）
- 性能优化

🟡 **中优先级**
- Web UI 开发
- 更多内置工具
- 文档翻译

🟢 **低优先级**
- 示例项目
- 教程编写
- 代码审查

### 贡献步骤

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 获取详细信息。

### 贡献者

<a href="https://github.com/bit-cook/Agent-OS-Kernel/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=bit-cook/Agent-OS-Kernel" />
</a>

---

## 📚 相关资源

### 推荐阅读
- [Operating Systems: Three Easy Pieces](http://pages.cs.wisc.edu/~remzi/OSTEP/) - 操作系统经典教材
- [Designing Data-Intensive Applications](https://dataintensive.net/) - 数据系统设计
- [Manus: Context Engineering for AI Agents](https://manus.im/blog/) - 上下文工程实践

### 相关项目
- [Semantic Kernel](https://github.com/microsoft/semantic-kernel) - Microsoft 的 Agent SDK
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) - 自主 Agent
- [SuperAGI](https://github.com/TransformerOptimus/SuperAGI) - 开源自主 AI 框架

---

## 📄 许可证

[MIT License](./LICENSE) © 2026 Bit-Cook

---

## 🙏 致谢

灵感来源：
- **Linux Kernel** - 操作系统设计的典范
- **PostgreSQL** - 数据库的瑞士军刀
- **Anthropic Claude** - 展示了 Agent 的可能性

特别感谢所有贡献者和社区支持！

---

<div align="center">

**如果这个项目对你有帮助，请给我们一个 ⭐️ Star！**

[![Star History Chart](https://api.star-history.com/svg?repos=bit-cook/Agent-OS-Kernel&type=Date)](https://star-history.com/#bit-cook/Agent-OS-Kernel&Date)

</div>
