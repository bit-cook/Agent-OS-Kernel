<div align="center">

# 🖥️ Agent OS Kernel

**Operating System Kernel for AI Agents**

> Inspired by [Ruohang Feng's "The Operating System Moment for AI Agents"](https://vonng.com/db/agent-os/), attempting to fill the "missing kernel" in the Agent ecosystem

**Chinese Models Supported**: DeepSeek | Kimi | MiniMax | Qwen

[![CI](https://github.com/bit-cook/Agent-OS-Kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/bit-cook/Agent-OS-Kernel/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/bit-cook/Agent-OS-Kernel/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](./README_EN.md) | [中文](./README.md) | [Manifesto](./MANIFESTO.md) | [Docs](docs/) | [Examples](./examples)

</div>

---

## 📋 Table of Contents

- [📖 Project Origin](#-project-origin)
- [🎯 Core Insight](#-core-insight)
- [📚 Project Documentation](#-project-documentation)
- [🚀 Quick Start](#-quick-start)
- [🏗️ Architecture](#-architecture)
- [📁 Project Structure](#-project-structure)
- [✨ Core Features](#-core-features)
- [🇨🇳 Chinese Model Support](#-chinese-model-support)
- [🔧 Common MCP Servers](#-common-mcp-servers)
- [🏗️ AIOS Reference Architecture](#-aios-reference-architecture)
- [🔗 Related Resources](#-related-resources)
- [📊 Project Statistics](#-project-statistics)
- [📄 License](#-license)

---

## 📖 Project Origin

In 2025, coding Agents exploded. Products like Claude Code and Manus demonstrated the amazing capabilities of AI Agents. But look closely, and you'll discover a startling fact: **their underlying operations are extremely "primitive".**

Agents directly manipulate the file system and terminal, relying on a "trust model" rather than an "isolation model". This is just like **1980s DOS** — no memory protection, no multitasking, no standardized device interfaces.

**Agent OS Kernel was born to fill this "missing kernel."**

---

## 🎯 Core Insight

| Traditional Computer | Agent World | Core Challenge | Agent OS Kernel Solution |
|---------------------|-------------|----------------|------------------------|
| **CPU** | **LLM** | How to efficiently schedule inference tasks? | Preemptive scheduling + resource quota management |
| **RAM** | **Context Window** | How to manage limited context windows? | Virtual memory-style context management |
| **Disk** | **Database** | How to persist state? | PostgreSQL five roles |
| **Process** | **Agent** | How to manage lifecycle? | True process management |
| **Device Driver** | **Tools** | How to standardize tool invocation? | MCP + Agent-Native CLI |
| **Security** | **Sandbox** | How to ensure security? | Sandbox + observability + audit |

---

## 📚 Project Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Best Practices](docs/best-practices.md)
- [Distributed Deployment](docs/distributed-deployment.md)
- [Development Plans](development-docs/3DAY_PLAN.md)
- [AIOS_ANALYSIS.md](./AIOS_ANALYSIS.md) - AIOS deep analysis
- [INSPIRATION.md](./INSPIRATION.md) - GitHub project inspiration collection

---

## 🚀 Quick Start

### Installation

```bash
pip install agent-os-kernel
```

### Basic Example

```python
from agent_os_kernel import AgentOSKernel

kernel = AgentOSKernel()

# Create Agent
agent_pid = kernel.spawn_agent(
    name="CodeAssistant",
    task="Help me write a Python web scraper",
    priority=30
)

# Run kernel
kernel.run(max_iterations=10)

# View system status
kernel.print_status()
```

---

## 🏗️ Architecture

```
+----------------------------------------------------------------+
|                        Agent Applications                        |
| (CodeAssistant | ResearchAgent | DataAnalyst...)                 |
+----------------------------------------------------------------+
                                |
                                v
+----------------------------------------------------------------+
|                      [ Agent OS Kernel ]                        |
+----------------------------------------------------------------+
|  +------------------+------------------+------------------+     |
|  |     Context      |     Process     |       I/O        |     |
|  |     Manager      |    Scheduler    |     Manager     |     |
|  +------------------+------------------+------------------+     |
|  +------------------+------------------+------------------+     |
|  | Storage Layer (PostgreSQL) | Learning Layer (Self-Learning)| |
|  +------------------+------------------+------------------+     |
+----------------------------------------------------------------+
                                |
                                v
+----------------------------------------------------------------+
|                     [ Hardware Resources ]                        |
|             LLM APIs | Vector DB | MCP Servers                  |
+----------------------------------------------------------------+
```

---

## 📁 Project Structure

```
Agent-OS-Kernel/
├── agent_os_kernel/          # Core code
│   ├── kernel.py            # Main kernel
│   ├── core/                # Core subsystems
│   │   ├── context_manager.py  # Virtual memory management
│   │   ├── scheduler.py        # Process scheduling
│   │   ├── storage.py          # Persistent storage
│   │   ├── security.py         # Security subsystem
│   │   ├── metrics.py          # Performance metrics
│   │   ├── plugin_system.py    # Plugin system
│   │   └── learning/          # Self-learning system
│   │       ├── trajectory.py   # Trajectory recording
│   │       └── optimizer.py     # Strategy optimization
│   ├── llm/                 # LLM Provider
│   │   ├── provider.py       # Abstract layer
│   │   ├── factory.py        # Factory pattern
│   │   ├── openai.py         # OpenAI
│   │   ├── anthropic.py      # Anthropic Claude
│   │   ├── deepseek.py       # DeepSeek
│   │   ├── kimi.py          # Kimi
│   │   ├── minimax.py       # MiniMax
│   │   ├── qwen.py          # Qwen
│   │   ├── ollama.py         # Ollama (local)
│   │   └── vllm.py          # vLLM (local)
│   ├── tools/               # Tool system
│   │   ├── registry.py      # Tool registry
│   │   ├── base.py          # Tool base class
│   │   └── mcp/             # MCP protocol
│   │       ├── client.py
│   │       └── registry.py
│   └── api/                  # Web API
│       ├── server.py         # FastAPI service
│       └── static/           # Vue.js admin interface
├── tests/                   # Test cases
├── examples/                # Example code
│   ├── basic_usage.py
│   ├── agent_spawning.py
│   ├── mcp_integration.py
│   ├── advanced_workflow.py
│   └── agent_learning.py
├── docs/                    # Documentation
│   ├── architecture.md
│   ├── api-reference.md
│   ├── distributed-deployment.md
│   └── best-practices.md
├── scripts/                 # CLI tools
│   └── kernel-cli
├── development-docs/       # Development plans
│   ├── 3DAY_PLAN.md
│   └── ITERATION_PLAN.md
├── config.example.yaml
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

---

## ✨ Core Features

### 🧠 Memory Management: Virtual Memory-Style Context

- **Context Pages**: Split long contexts into fixed-size pages
- **Page Fault**: Automatically load pages from database when accessed but not in memory
- **Page Replacement**: LRU + importance + semantic similarity multi-factor scoring
- **KV-Cache Optimization**: Static content first, dynamic content sorted by access frequency

```python
from agent_os_kernel import ContextManager

cm = ContextManager(max_context_tokens=128000)

# Allocate page
page_id = cm.allocate_page(
    agent_pid="agent-1",
    content="Large amount of context content...",
    importance=0.8
)

# Get optimized context
context = cm.get_agent_context(agent_pid="agent-1")
```

### 💾 Storage: PostgreSQL Five Roles

| Role | Function | Analogy |
|-----|------|------|
| **Long-term Memory** | Conversation history, learned knowledge | Hippocampus |
| **State Persistence** | Checkpoint/snapshot, task state | Hard Disk |
| **Vector Index** | Semantic retrieval, pgvector | Page Table |
| **Coordination** | Distributed locks, task queues | IPC Mechanism |
| **Audit Log** | Immutable records of all operations | Black Box |

```python
from agent_os_kernel import StorageManager

storage = StorageManager.from_postgresql(
    "postgresql://user:pass@localhost/agent_os",
    enable_vector=True
)

# Vector semantic search
results = storage.semantic_search(
    query="Requirements user mentioned earlier",
    limit=5
)
```

### ⚡ Process Management

- **Concurrent Scheduling**: Priority + time slice + preemptive scheduling
- **State Persistence**: Recover from checkpoint after Agent crash
- **Inter-Process Communication**: State synchronization between Agents
- **Graceful Termination**: Safe exit rather than kill -9

```python
from agent_os_kernel import AgentOSKernel

kernel = AgentOSKernel()

# Create Agent
agent_pid = kernel.spawn_agent(
    name="DBA_Agent",
    task="Monitor database health status",
    priority=10
)

# Recover from checkpoint
new_pid = kernel.restore_checkpoint(checkpoint_id)
```

### 🔧 Multi LLM Provider Support

```python
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig

factory = LLMProviderFactory()

providers = [
    ("OpenAI", "gpt-4o"),
    ("DeepSeek", "deepseek-chat"),
    ("Kimi", "moonshot-v1-32k"),
    ("Qwen", "qwen-turbo"),
    ("Ollama", "qwen2.5:7b"),  # Local
    ("vLLM", "Llama-3.1-8B"),  # Local
]

for name, model in providers:
    provider = factory.create(LLMConfig(
        provider=name.lower(),
        model=model
    ))
```

### 🧠 Self-Learning System

```python
from agent_os_kernel.core.learning import TrajectoryRecorder, AgentOptimizer

# Trajectory recording
recorder = TrajectoryRecorder()
traj_id = recorder.start_recording("Agent1", pid, "task")
recorder.add_step(phase="thinking", thought="Analyze problem")
recorder.finish_recoding("success", success=True)

# Strategy optimization
optimizer = AgentOptimizer(recorder)
analysis = optimizer.analyze("Agent1")

print(f"Success rate: {analysis.success_rate:.1%}")
print(f"Suggestions: {len(analysis.suggestions)}")
```

### 🔒 Security and Observability

- **Sandbox Isolation**: Docker + resource limits
- **Complete Audit**: Immutable records of all operations
- **Security Policies**: Permission levels, path limits, network control

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

## 🇨🇳 Chinese Model Support

Agent OS Kernel fully supports major Chinese AI model providers:

| Provider | Models | Features | Config Example |
|----------|--------|----------|---------------|
| **DeepSeek** | deepseek-chat, deepseek-reasoner | Cost-effective, strong reasoning | `{"provider": "deepseek", "model": "deepseek-chat"}` |
| **Kimi (Moonshot)** | kimi-vl, kimi-k1 | Ultra-long context, Multimodal | `{"provider": "kimi", "model": "kimi-vl"}` |
| **MiniMax** | abab6.5s-chat, abab6.5-chat | Fast response, Low latency | `{"provider": "minimax", "model": "abab6.5s-chat"}` |
| **Qwen (Alibaba)** | qwen-turbo, qwen-plus, qwen-max, qwen-long | Stable API, Complete ecosystem | `{"provider": "qwen", "model": "qwen-turbo"}` |

### Configuration

```yaml
# config.yaml
llms:
  models:
    - name: "deepseek-chat"
      provider: "deepseek"
      
    - name: "kimi-vl"
      provider: "kimi"
      
    - name: "abab6.5s-chat"
      provider: "minimax"
      
    - name: "qwen-plus"
      provider: "qwen"
```

```python
from agent_os_kernel.llm import LLMProviderFactory, LLMConfig

factory = LLMProviderFactory()

# Use DeepSeek
provider = factory.create(LLMConfig(
    provider="deepseek",
    model="deepseek-chat"
))

# Use Kimi
provider = factory.create(LLMConfig(
    provider="kimi",
    model="kimi-vl"
))

# Use Qwen
provider = factory.create(LLMConfig(
    provider="qwen",
    model="qwen-plus"
))
```

---

## 🔧 Common MCP Servers

Full support for Model Context Protocol, connecting to 400+ MCP servers.

```bash
# File system
npx @modelcontextprotocol/server-filesystem /path

# Git
npx @modelcontextprotocol/server-git

# Database
npx @modelcontextprotocol/server-postgres

# Web browsing
npx @playwright/mcp@latest --headless
```

---

## 🏗️ AIOS Reference Architecture

Agent OS Kernel is deeply inspired by [AIOS](https://github.com/agiresearch/AIOS) (COLM 2025) architecture:

### AIOS Core Reference

```
+----------------------------------------------------------------+
|            [ Agent-OS-Kernel (AIOS-Inspired) ]                   |
+----------------------------------------------------------------+
|  Kernel Layer                                                  |
|  + LLM Core (Multi-Provider)                                    |
|  + Context Manager (Virtual Memory)                             |
|  + Memory Manager (Memory)                                      |
|  + Storage Manager (Persistent)                                 |
|  + Tool Manager (Tools)                                         |
|  + Scheduler (Process)                                         |
+----------------------------------------------------------------+
|  SDK Layer (Cerebrum-Style)                                     |
|  + Agent Builder (Builder)                                       |
|  + Tool Registry (Registry)                                      |
|  + Plugin System (Plugins)                                      |
+----------------------------------------------------------------+
```

### AIOS Key Feature Implementation

| AIOS Feature | Agent-OS-Kernel Support |
|--------------|------------------------|
| Multi LLM Provider | ✅ 9+ Providers |
| Agent Scheduling | ✅ Preemptive scheduling |
| Memory Management | ✅ Virtual memory-style context |
| Tool Management | ✅ MCP + Native CLI |
| Deployment Mode | ✅ Local/Remote |
| CLI Tools | ✅ kernel-cli |

---

## 🔗 Related Resources

### 📖 Inspiration Sources
- [AIOS (COLM 2025)](https://github.com/agiresearch/AIOS) - Agent OS architecture, published at Conference on Language Modeling
- ["The Operating System Moment for AI Agents"](https://vonng.com/db/agent-os/) - Ruohang Feng
- [Manus - Context Engineering](https://manus.im/blog/context-engineering) - Context engineering practices
- [DeepSeek Engram](https://arxiv.org/abs/2502.01623) - Memory-enhanced LLM reasoning

### 🌟 Reference Projects

#### Agent Frameworks
- [AutoGen](https://microsoft.github.io/autogen/) - Microsoft multi-agent framework
- [AutoGen Studio](https://microsoft.github.io/autogen-studio/) - No-code multi-agent development GUI
- [MetaGPT](https://github.com/geekan/MetaGPT) - Software development multi-agent framework

#### Agent Infrastructure
- [E2B](https://e2b.dev/) - Agent sandbox environment
- [AIWaves Agents](https://github.com/aiwaves-cn/agents) - Self-learning language agents

#### Workflow and Tools
- [ActivePieces](https://github.com/activepieces/activepieces) - AI workflow automation
- [Cerebrum](https://github.com/agiresearch/Cerebrum) - AIOS SDK
- [CowAgent](https://github.com/CowAI-Lab/CowAgent) - Multi-platform agent

#### Protocols and Standards
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol by Anthropic
- [OSWorld](https://github.com/xlang-ai/OSWorld) - Computer use agent benchmark

### 📚 Project Documentation

> **Tip**: Add new documentation links here

---

## 📊 Project Statistics

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Python Files** | 87 |
| **Core Modules** | 24+ |
| **LLM Providers** | 9 |
| **Test Files** | 10 |
| **Examples** | 18 |
| **Documentation** | 6 |
| **Agent Communication** | 5 |

## 📄 License

MIT License © 2026 OpenClaw

---

<div align="center">

**Give us a ⭐ Star if this project helps you!**

[![Star History](https://api.star-history.com/svg?repos=bit-cook/Agent-OS-Kernel&type=Date)](https://star-history.com/#bit-cook/Agent-OS-Kernel&Date)

</div>
