<div align="center">

# 🖥️ Agent OS Kernel

**AI Agent 的操作系统内核**

> 深受 [冯若航《AI Agent 的操作系统时刻》](https://vonng.com/db/agent-os/) 启发，试图填补 Agent 生态中"缺失的内核"

**支持中国模型**: DeepSeek | Kimi | MiniMax | Qwen

[![CI](https://github.com/bit-cook/Agent-OS-Kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/bit-cook/Agent-OS-Kernel/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/bit-cook/Agent-OS-Kernel/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](./README_EN.md) | [中文](./README.md) | [宣言](./MANIFESTO.md) | [文档](docs/) | [示例](./examples)

</div>

---

## 🇨🇳 中国模型支持

Agent OS Kernel 完整支持主流中国 AI 模型提供商：

| Provider | 模型 | 特点 | 示例 |
|----------|------|------|------|
| **DeepSeek** | deepseek-chat, deepseek-reasoner | 性价比高、推理强 | `"deepseek-chat"` |
| **Kimi (Moonshot)** | moonshot-v1-8k, moonshot-v1-32k | 超长上下文 | `"moonshot-v1-32k"` |
| **MiniMax** | abab6.5s-chat | 快速响应 | `"abab6.5s-chat"` |
| **Qwen (阿里)** | qwen-turbo, qwen-plus, qwen-max | 生态完善 | `"qwen-turbo"` |

### 快速配置

```yaml
# config.yaml
api_keys:
  deepseek: "${DEEPSEEK_API_KEY}"
  kimi: "${KIMI_API_KEY}"
  minimax: "${MINIMAX_API_KEY}"
  qwen: "${DASHSCOPE_API_KEY}"

llms:
  models:
    - name: "deepseek-chat"
      provider: "deepseek"
    - name: "moonshot-v1-32k"
      provider: "kimi"
    - name: "qwen-turbo"
      provider: "qwen"

default_model: "deepseek-chat"
```

```python
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig

# 创建中国模型 Provider
factory = LLMProviderFactory()
provider = factory.create(LLMConfig(
    provider="deepseek",
    model="deepseek-chat"
))
```

---

## 🏗️ AIOS 参考架构

Agent OS Kernel 深度参考 [AIOS](https://github.com/agiresearch/AIOS) (COLM 2025) 架构设计：

### AIOS 核心借鉴

```
┌─────────────────────────────────────────────────┐
│         Agent-OS-Kernel (基于 AIOS 架构)          │
├─────────────────────────────────────────────────┤
│  🎛️ Kernel Layer                                │
│  ├── LLM Core (多模型抽象层)                       │
│  ├── Context Manager (虚拟内存式上下文)            │
│  ├── Memory Manager (记忆管理)                    │
│  ├── Storage Manager (持久化存储)                 │
│  ├── Tool Manager (工具管理)                      │
│  └── Scheduler (进程调度)                        │
├─────────────────────────────────────────────────┤
│  🛠️ SDK Layer (Cerebrum 风格)                   │
│  ├── Agent Builder (Agent 构建器)                 │
│  ├── Tool Registry (工具注册表)                   │
│  └── Plugin System (插件系统)                    │
└─────────────────────────────────────────────────┘
```

### AIOS 关键特性实现

| AIOS 特性 | Agent-OS-Kernel 支持 |
|-----------|---------------------|
| 多 LLM Provider | ✅ 9+ Providers |
| Agent 调度 | ✅ 抢占式调度 |
| 内存管理 | ✅ 虚拟内存式上下文 |
| 工具管理 | ✅ MCP + Native CLI |
| 部署模式 | ✅ 本地/远程 |
| CLI 工具 | ✅ kernel-cli |

---

## 🔧 MCP 协议支持

完整支持 Model Context Protocol，连接 400+ MCP 服务器：

### MCP 集成

```python
from agent_os_kernel.tools.mcp import init_mcp_registry

# 初始化 MCP 注册表
mcp_registry = init_mcp_registry(kernel.tool_registry)

# 添加 MCP 服务器
mcp_registry.add_server(
    name="filesystem",
    command="npx",
    args=["@modelcontextprotocol/server-filesystem", "/tmp"]
)

# 发现并注册工具
await mcp_registry.discover_tools()

# Agent 自动使用 MCP 工具
agent_pid = kernel.spawn_agent(
    name="FileWorker",
    task="使用 MCP 工具管理文件"
)
```

### 常用 MCP 服务器

```bash
# 文件系统
npx @modelcontextprotocol/server-filesystem /path

# Git
npx @modelcontextprotocol/server-git

# 数据库
npx @modelcontextprotocol/server-postgres

# 网页浏览
npx @playwright/mcp@latest --headless
```

---

## 📖 项目起源

2025 年，编程 Agent 大爆发。Claude Code、Manus 等产品展示了 AI Agent 的惊人能力。但仔细观察，你会发现一个惊人的事实：**它们的底层操作极其 "原始"**。

Agent 直接操作文件系统和终端，依赖"信任模型"而非"隔离模型"。这就像 **1980 年代的 DOS** ——没有内存保护，没有多任务，没有标准化的设备接口。

**Agent OS Kernel 正是为了填补这个"缺失的内核"而生。**

---

## 🎯 核心洞察：用操作系统理解 Agent 基础设施

| 传统计算机 | Agent 世界 | 核心挑战 | Agent OS Kernel 解决方案 |
|-----------|-----------|---------|------------------------|
| **CPU** | **LLM** | 如何高效调度推理任务？ | 抢占式调度 + 资源配额管理 |
| **RAM** | **Context Window** | 如何管理有限的上下文窗口？ | 虚拟内存式上下文管理 |
| **Disk** | **Database** | 如何持久化状态？ | PostgreSQL 五重角色 |
| **Process** | **Agent** | 如何管理生命周期？ | 真正的进程管理 |
| **Device Driver** | **Tools** | 如何标准化工具调用？ | MCP + Agent-Native CLI |
| **Security** | **Sandbox** | 如何保障安全？ | 沙箱 + 可观测性 + 审计 |

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
│  │  (虚拟内存)   │   (调度器)    │   (MCP+CLI)  │         │
│  └──────────────┴──────────────┴──────────────┘         │
│  ┌──────────────────────────────────────────┐           │
│  │       💾 Storage Layer (PostgreSQL)       │           │
│  │   记忆存储 │ 状态持久化 │ 向量索引 │ 审计日志  │           │
│  └──────────────────────────────────────────┘           │
│  ┌──────────────────────────────────────────┐           │
│  │       🧠 Learning Layer (自学习系统)        │           │
│  │   轨迹记录 │ 策略优化 │ 经验积累           │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 🖥️ Hardware Resources                     │
│        LLM APIs │ Vector DB │ MCP Servers                │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ 核心特性

### 🧠 内存管理：虚拟内存式上下文

- **上下文页面（Page）**：将长上下文分割为固定大小的页面
- **缺页中断（Page Fault）**：访问不在内存中的页面时自动从数据库加载
- **页面置换（Page Replacement）**：LRU + 重要性 + 语义相似度多因素评分
- **KV-Cache 优化**：静态内容前置，动态内容按访问频率排序

```python
from agent_os_kernel import ContextManager

cm = ContextManager(max_context_tokens=128000)

# 分配页面
page_id = cm.allocate_page(
    agent_pid="agent-1",
    content="大量上下文内容...",
    importance=0.8
)

# 获取优化后的上下文
context = cm.get_agent_context(agent_pid="agent-1")
```

### 💾 外存：PostgreSQL 五重角色

| 角色 | 功能 | 类比 |
|-----|------|------|
| **长期记忆存储** | 对话历史、学到的知识 | 海马体 |
| **状态持久化** | Checkpoint/快照、任务状态 | 硬盘 |
| **向量索引** | 语义检索、pgvector | 页表 |
| **协调服务** | 分布式锁、任务队列 | IPC 机制 |
| **审计日志** | 所有操作的不可篡改记录 | 黑匣子 |

```python
from agent_os_kernel import StorageManager

storage = StorageManager.from_postgresql(
    "postgresql://user:pass@localhost/agent_os",
    enable_vector=True
)

# 向量语义搜索
results = storage.semantic_search(
    query="用户之前提到的需求",
    limit=5
)
```

### ⚡ 进程管理

- **并发调度**：优先级 + 时间片 + 抢占式调度
- **状态持久化**：Agent 崩溃后从断点恢复
- **进程间通信**：Agent 之间的状态同步
- **优雅终止**：安全退出而非 kill -9

```python
from agent_os_kernel import AgentOSKernel

kernel = AgentOSKernel()

# 创建 Agent
agent_pid = kernel.spawn_agent(
    name="DBA_Agent",
    task="监控数据库健康状态",
    priority=10
)

# 从检查点恢复
new_pid = kernel.restore_checkpoint(checkpoint_id)
```

### 🔧 多 LLM Provider 支持

```python
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig

factory = LLMProviderFactory()

# 创建不同 Provider
providers = [
    ("OpenAI", "gpt-4o"),
    ("DeepSeek", "deepseek-chat"),
    ("Kimi", "moonshot-v1-32k"),
    ("Qwen", "qwen-turbo"),
    ("Ollama", "qwen2.5:7b"),  # 本地
    ("vLLM", "Llama-3.1-8B"),  # 本地
]

for name, model in providers:
    provider = factory.create(LLMConfig(
        provider=name.lower(),
        model=model
    ))
```

### 🧠 自学习系统

```python
from agent_os_kernel.core.learning import TrajectoryRecorder, AgentOptimizer

# 轨迹记录
recorder = TrajectoryRecorder()
traj_id = recorder.start_recording("Agent1", pid, "任务")
recorder.add_step(phase="thinking", thought="分析问题")
recorder.finish_recoding("成功", success=True)

# 策略优化
optimizer = AgentOptimizer(recorder)
analysis = optimizer.analyze("Agent1")

print(f"成功率: {analysis.success_rate:.1%}")
print(f"优化建议: {len(analysis.suggestions)} 条")
```

### 🔒 安全与可观测性

- **沙箱隔离**：Docker + 资源限制
- **完整审计**：所有操作的不可篡改记录
- **安全策略**：权限级别、路径限制、网络控制

```python
from agent_os_kernel import SecurityPolicy

policy = SecurityPolicy(
    permission_level=PermissionLevel.STANDARD,
    max_memory_mb=512,
    allowed_paths=["/workspace"],
    blocked_paths=["/etc", "/root"]
)
```

---

## 🚀 快速开始

### 安装

```bash
pip install agent-os-kernel
```

### 基础示例

```python
from agent_os_kernel import AgentOSKernel

kernel = AgentOSKernel()

# 创建 Agent
agent_pid = kernel.spawn_agent(
    name="CodeAssistant",
    task="帮我写一个 Python 爬虫",
    priority=30
)

# 运行内核
kernel.run(max_iterations=10)

# 查看系统状态
kernel.print_status()
```

### 中国模型示例

```python
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig

factory = LLMProviderFactory()

# 使用 DeepSeek
provider = factory.create(LLMConfig(
    provider="deepseek",
    model="deepseek-chat",
    api_key="your-api-key"
))

# 或使用 Kimi
provider = factory.create(LLMConfig(
    provider="kimi",
    model="moonshot-v1-32k",
    api_key="your-api-key"
))
```

---

## 📁 项目结构

```
Agent-OS-Kernel/
├── agent_os_kernel/          # 核心代码
│   ├── kernel.py            # 主内核
│   ├── core/                # 核心子系统
│   │   ├── context_manager.py  # 虚拟内存管理
│   │   ├── scheduler.py        # 进程调度
│   │   ├── storage.py          # 持久化存储
│   │   ├── security.py         # 安全子系统
│   │   ├── metrics.py          # 性能指标
│   │   ├── plugin_system.py    # 插件系统
│   │   └── learning/          # 自学习系统
│   │       ├── trajectory.py   # 轨迹记录
│   │       └── optimizer.py     # 策略优化
│   ├── llm/                 # LLM Provider (新增!)
│   │   ├── provider.py       # 抽象层
│   │   ├── factory.py        # 工厂模式
│   │   ├── openai.py         # OpenAI
│   │   ├── anthropic.py      # Anthropic Claude
│   │   ├── deepseek.py       # DeepSeek 🇨🇳
│   │   ├── kimi.py          # Kimi 🇨🇳
│   │   ├── minimax.py       # MiniMax 🇨🇳
│   │   ├── qwen.py          # Qwen 🇨🇳
│   │   ├── ollama.py         # Ollama (本地)
│   │   └── vllm.py          # vLLM (本地)
│   ├── tools/               # 工具系统
│   │   ├── registry.py      # 工具注册表
│   │   ├── base.py          # 工具基类
│   │   └── mcp/             # MCP 协议 (新增!)
│   │       ├── client.py
│   │       └── registry.py
│   └── api/                  # Web API
│       ├── server.py         # FastAPI 服务
│       └── static/           # Vue.js 管理界面
├── tests/                   # 测试用例 (9+ 文件)
├── examples/                # 示例代码 (13+ 文件)
│   ├── basic_usage.py
│   ├── agent_spawning.py
│   ├── mcp_integration.py   # MCP 示例
│   ├── advanced_workflow.py # 工作流示例
│   └── agent_learning.py    # 自学习示例
├── docs/                    # 文档 (14+ 份)
│   ├── architecture.md
│   ├── api-reference.md
│   ├── distributed-deployment.md
│   └── best-practices.md
├── scripts/                 # CLI 工具
│   └── kernel-cli          # 交互式 CLI
├── config.example.yaml      # 配置模板
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

---

## 📊 项目统计

| 指标 | 数值 |
|------|------|
| **总文件数** | 78+ |
| **核心代码** | 24+ Python 文件 |
| **LLM Providers** | 9 个 |
| **测试文件** | 9 个 |
| **文档** | 14+ 份 |
| **示例代码** | 13+ 个 |
| **API 端点** | 20+ |

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行类型检查
mypy agent_os_kernel/

# 代码格式化
black agent_os_kernel/ tests/
```

---

## 📚 文档

- [架构设计](docs/architecture.md)
- [API 参考](docs/api-reference.md)
- [最佳实践](docs/best-practices.md)
- [分布式部署](docs/distributed-deployment.md)
- [三日完善计划](3DAY_PLAN.md)

---

## 🔗 相关资源

### 📖 灵感来源
- [AIOS (COLM 2025)](https://github.com/agiresearch/AIOS) - Agent OS 架构，论文发表于 Conference on Language Modeling
- [《AI Agent 的操作系统时刻》](https://vonng.com/db/agent-os/) - 冯若航，最初的灵感来源
- [Manus - Context Engineering](https://manus.im/blog/context-engineering) - 上下文工程实践经验
- [DeepSeek Engram](https://arxiv.org/abs/2502.01623) - 记忆增强的 LLM 推理

### 🌟 参考项目

#### Agent 框架
- [AutoGen](https://microsoft.github.io/autogen/) - Microsoft 多 Agent 框架，支持 AgentChat 和 Core API
- [AutoGen Studio](https://microsoft.github.io/autogen-studio/) - No-code 多 Agent 开发 GUI
- [MetaGPT](https://github.com/geekan/MetaGPT) - 软件开发多 Agent 框架

#### Agent 基础设施
- [E2B](https://e2b.dev/) - Agent 安全沙箱环境，10.8k+ stars
- [AIWaves Agents](https://github.com/aiwaves-cn/agents) - 自学习语言 Agent，支持符号学习

#### 工作流与工具
- [ActivePieces](https://github.com/activepieces/activepieces) - AI 工作流自动化，15k+ stars
- [Cerebrum](https://github.com/agiresearch/Cerebrum) - AIOS SDK，Agent 开发部署平台
- [CowAgent](https://github.com/CowAI-Lab/CowAgent) - 多平台接入 Agent，支持飞书/钉钉/企业微信

#### 协议与标准
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol，Anthropic 提出
- [OSWorld](https://github.com/xlang-ai/OSWorld) - 电脑使用 Agent 基准测试

### 📚 项目文档

- [AIOS_ANALYSIS.md](./AIOS_ANALYSIS.md) - AIOS 深度分析文档
- [INSPIRATION.md](./INSPIRATION.md) - GitHub 项目灵感收集
- [三日完善计划](3DAY_PLAN.md) - 项目开发计划

---

## 📄 许可证

MIT License © 2026 OpenClaw

---

<div align="center">

**给项目一个 ⭐ Star 支持我们！**

[![Star History](https://api.star-history.com/svg?repos=bit-cook/Agent-OS-Kernel&type=Date)](https://star-history.com/#bit-cook/Agent-OS-Kernel&Date)

</div>
