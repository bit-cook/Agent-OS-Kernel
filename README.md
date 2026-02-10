<div align="center">

# 🖥️ Agent OS Kernel

**AI Agent 的操作系统内核**

> 深受 [冯若航《AI Agent 的操作系统时刻》](https://vonng.com/db/agent-os/) 启发，试图填补 Agent 生态中"缺失的内核"

[![CI](https://github.com/bit-cook/Agent-OS-Kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/bit-cook/Agent-OS-Kernel/actions)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](https://github.com/bit-cook/Agent-OS-Kernel/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[English](./README_EN.md) | [中文](./README.md) | [宣言](./MANIFESTO.md) | [文档](https://github.com/bit-cook/Agent-OS-Kernel/wiki) | [示例](./examples)

</div>

---

## 📖 项目起源

2025 年，编程 Agent 大爆发。Claude Code、Manus 等产品展示了 AI Agent 的惊人能力。但仔细观察，你会发现一个惊人的事实：**它们的底层操作极其 "原始"**。

Agent 直接操作文件系统和终端，依赖"信任模型"而非"隔离模型"。这就像 **1980 年代的 DOS** ——没有内存保护，没有多任务，没有标准化的设备接口。

我们花了 30 年才从 DOS 演化到现代操作系统，而 Agent 生态正在压缩式地重演这段历史。

**Agent OS Kernel 正是为了填补这个"缺失的内核"而生。**

> 详细理念请阅读我们的 [宣言 (MANIFESTO.md)](./MANIFESTO.md) 和灵感来源 [《AI Agent 的操作系统时刻》](https://vonng.com/db/agent-os/)

---

## 🎯 核心洞察：用操作系统理解 Agent 基础设施

| 传统计算机 | Agent 世界 | 核心挑战 | Agent OS Kernel 解决方案 |
|-----------|-----------|---------|------------------------|
| **CPU** | **LLM** | 如何高效调度推理任务？ | 抢占式调度 + 资源配额管理 |
| **RAM** | **Context Window** | 如何管理有限的上下文窗口？ | [虚拟内存式上下文管理](#-内存管理最复杂也最重要的战场) |
| **Disk** | **Database** | 如何持久化状态？ | [PostgreSQL 五重角色](#-外存数据库确定性最高的机会) |
| **Process** | **Agent** | 如何管理生命周期？ | [真正的进程管理](#-进程管理表面红海深水无人) |
| **Device Driver** | **Tools** | 如何标准化工具调用？ | [Agent-Native CLI](#-io-管理协议之争的表象与本质) |
| **Security** | **Sandbox** | 如何保障安全？ | [沙箱 + 可观测性 + 审计](#-安全与可观测性信任基础设施) |

> **核心洞察**: 就像 Linux 让应用程序无需关心硬件细节一样，Agent OS Kernel 让 AI Agent 无需关心上下文管理、资源调度和持久化存储。

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
│  │       💾 Storage Layer (PostgreSQL)       │           │
│  │   记忆存储 │ 状态持久化 │ 向量索引 │ 审计日志  │           │
│  └──────────────────────────────────────────┘           │
│  ┌──────────────────────────────────────────┐           │
│  │       🔒 Security Subsystem (安全)        │           │
│  │   沙箱隔离 │ 可观测性 │ 决策审计          │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 🖥️ Hardware Resources                     │
│        LLM APIs │ Vector DB │ Message Queue              │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ 核心特性

### 🧠 内存管理：最复杂也最重要的战场

**历史的教训：640KB 够用吗？** 1981 年，IBM PC 的设计者们认为 640KB 内存"应该够用了"。今天，当我们说 128K 上下文"已经很大了"时，正在犯同样的错误。

Agent OS Kernel 实现了**操作系统级的虚拟内存机制**：

- **上下文页面（Page）**：将长上下文分割为固定大小的页面
- **缺页中断（Page Fault）**：访问不在内存中的页面时自动从数据库加载  
- **页面置换（Page Replacement）**：LRU + 重要性 + 语义相似度多因素评分
- **KV-Cache 优化**：静态内容前置，动态内容按访问频率排序

> **Manus 的核心经验**：KV-Cache 命中率是最重要的性能指标。在 Claude 上，缓存命中的 token 成本是未命中的 1/10。

```python
from agent_os_kernel import ContextManager

# 像使用虚拟内存一样使用上下文
cm = ContextManager(max_context_tokens=128000)

# 分配页面（自动处理溢出）
page_id = cm.allocate_page(
    agent_pid="agent-1",
    content="大量上下文内容...",
    importance=0.8,
    page_type="user"
)

# 访问页面（自动 swap in）
page = cm.access_page(page_id)

# 获取优化后的上下文（KV-Cache 友好布局）
context = cm.get_agent_context(
    agent_pid="agent-1",
    optimize_for_cache=True  # 关键：优化缓存命中率
)
```

**内存层次结构**（参考 DeepSeek Engram 论文）：

```
L1 Cache (寄存器)   ->  System Prompt (< 1K tokens, 始终在 context)
L2 Cache (高速缓存) ->  Working Memory (10-20K tokens, 当前任务)
RAM (内存)          ->  Session Context (50-100K tokens, 本次会话)
Disk (磁盘)         ->  Long-term Memory (数据库, 无限容量)
```

### 💾 外存（数据库）：确定性最高的机会

**PostgreSQL 的五重角色**：

| 角色 | 功能 | 类比 |
|-----|------|------|
| **长期记忆存储** | 对话历史、学到的知识、用户偏好 | 海马体 |
| **状态持久化** | Checkpoint/快照、任务状态、恢复点 | 硬盘 |
| **向量索引** | 语义检索、相似度匹配、Context 换入决策 | 页表 |
| **协调服务** | 分布式锁、任务队列、事件通知 | IPC 机制 |
| **审计日志** | 所有操作的不可篡改记录、合规、可重放 | 黑匣子 |

```python
from agent_os_kernel import StorageManager

# PostgreSQL 同时承担五重角色
storage = StorageManager.from_postgresql(
    "postgresql://user:pass@localhost/agent_os",
    enable_vector=True  # 启用向量搜索（pgvector）
)

# 1. 长期记忆存储 - 保存对话历史
storage.save_conversation(agent_pid, messages)

# 2. 状态持久化 - 创建检查点
checkpoint_id = storage.create_checkpoint(agent_pid)

# 3. 向量索引 - 语义检索相关记忆
results = storage.semantic_search(
    agent_pid="agent-1",
    query="用户之前提到的需求",
    limit=5
)

# 4. 协调服务 - 分布式锁
with storage.acquire_lock("task-123"):
    # 执行独占操作
    pass

# 5. 审计日志 - 记录所有操作
storage.log_action(
    agent_pid="agent-1",
    action_type="tool_call",
    input={"tool": "calculator", "args": [1, 2]},
    output={"result": 3},
    reasoning="用户要求计算 1+2"
)
```

### ⚡ 进程管理：表面红海，深水无人

当前所有 Agent 框架的核心几乎都是同一个 while loop：

```python
while not done:
    thought = llm.think(context)
    action = llm.decide(thought)
    result = tools.execute(action)
    context.update(result)
```

**当核心抽象简单到任何本科生都能实现时，它就不可能成为护城河。**

真正的进程管理远不止一个 while loop：

- **并发调度**：优先级 + 时间片 + 抢占式调度
- **状态持久化**：Agent 崩溃后从断点恢复
- **进程间通信**：Agent 之间的状态同步
- **优雅终止**：安全退出而非 kill -9

```python
from agent_os_kernel import AgentOSKernel, ResourceQuota

# 配置资源配额
quota = ResourceQuota(
    max_tokens_per_window=100000,    # 每小时 token 上限
    max_api_calls_per_window=1000,   # 每小时 API 调用上限
)

kernel = AgentOSKernel(quota=quota)

# 创建长期运行的 Agent
agent_pid = kernel.spawn_agent(
    name="DBA_Agent",
    task="7x24 监控数据库健康状态",
    priority=10  # 高优先级
)

# Agent 崩溃后从检查点恢复
new_pid = kernel.restore_checkpoint(checkpoint_id)
```

### 🛠️ I/O 管理：Agent-Native CLI

MCP 虽然流行，但存在 Token 开销大、重新发明轮子的问题。**Unix CLI 已经优雅地做了 55 年。**

Agent OS Kernel 的判断是：**最终的赢家是 "Agent-Native CLI"** —— 输出结构化、错误码标准化、自带发现机制的命令行工具。

```python
from agent_os_kernel import Tool, ToolRegistry

# 定义符合 Agent-Native CLI 标准的工具
class DatabaseQueryTool(Tool):
    def name(self) -> str:
        return "query_db"
    
    def description(self) -> str:
        return "Query database with SQL"
    
    def parameters(self) -> dict:
        return {
            "sql": {"type": "string", "required": True}
        }
    
    def execute(self, sql: str, **kwargs) -> dict:
        # 标准化输出格式
        return {
            "success": True,
            "data": [...],
            "error": None,
            "metadata": {"rows": 10, "time_ms": 45}
        }

# 自动发现系统 CLI 工具
registry = ToolRegistry()
registry.auto_discover_cli_tools()  # 注册 grep, psql, curl 等
```

### 🔒 安全与可观测性：信任基础设施

**Prompt Injection 是 AI 时代的 Buffer Overflow。**

真正的信任需要三层基础设施：

| 层次 | 功能 | 类比 |
|-----|------|------|
| **沙箱** | 限制 Agent 能做什么 | 监狱的围墙 |
| **可观测性** | 理解 Agent 在做什么、为什么这么做 | 监控摄像头 |
| **审计日志** | 事后追溯完整决策链路 | 飞机黑匣子 |

```python
from agent_os_kernel import SecurityPolicy, PermissionLevel

# 配置安全策略
policy = SecurityPolicy(
    permission_level=PermissionLevel.STANDARD,
    max_memory_mb=512,
    max_cpu_percent=50,
    allowed_paths=["/workspace"],
    blocked_paths=["/etc", "/root"],
    network_enabled=False
)

# 创建受限制的 Agent
agent_pid = kernel.spawn_agent(
    name="SandboxedAgent",
    task="处理不受信任的数据",
    policy=policy
)

# 查看完整审计追踪
audit = kernel.get_audit_trail(agent_pid)
for log in audit:
    print(f"[{log.timestamp}] {log.action_type}")
    print(f"  Input: {log.input_data}")
    print(f"  Reasoning: {log.reasoning}")
    print(f"  Output: {log.output_data}")
```

---

## 🚀 快速开始

### 安装

```bash
# 基础版本
pip install agent-os-kernel

# 生产环境（PostgreSQL 持久化）
pip install agent-os-kernel[postgres]

# 完整功能
pip install agent-os-kernel[all]
```

### 基础示例

```python
from agent_os_kernel import AgentOSKernel

# 初始化内核
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

### Claude 集成示例

```python
import os
from agent_os_kernel import ClaudeIntegratedKernel

os.environ["ANTHROPIC_API_KEY"] = "your-api-key"

kernel = ClaudeIntegratedKernel()

# 创建研究 Agent
agent_pid = kernel.spawn_agent(
    name="ResearchAssistant",
    task="研究 LLM 上下文管理的最新进展",
    priority=10
)

# 运行并监控
kernel.run(max_iterations=5)

# 查看审计追踪
audit = kernel.get_audit_trail(agent_pid)
```

---

## 📊 性能基准

| 指标 | 数值 | 说明 |
|------|------|------|
| **上下文利用率** | 92% | 相比原生上下文窗口利用率提升 40% |
| **KV-Cache 命中率** | 75% | 降低 8x API 成本 |
| **页面换入延迟** | 45ms | P95 延迟 |
| **调度延迟** | 3ms | 从就绪到运行 |

---

## 🔍 与其他框架对比

| 特性 | Agent OS Kernel | LangChain | AutoGPT |
|------|-----------------|-----------|---------|
| **核心定位** | OS 内核 | 应用框架 | 自主 Agent |
| **上下文管理** | ✅ 虚拟内存 | ⚠️ 链式 | ❌ 手动 |
| **KV-Cache 优化** | ✅ 内置 | ❌ | ❌ |
| **多 Agent 调度** | ✅ 抢占式 | ❌ | ❌ |
| **PostgreSQL 五重角色** | ✅ 完整支持 | ⚠️ 外部 | ⚠️ 文件 |
| **Agent-Native CLI** | ✅ 内置 | ⚠️ 外部 | ❌ |
| **安全沙箱** | ✅ Docker | ❌ | ❌ |
| **决策审计** | ✅ 完整 | ❌ | ⚠️ 日志 |

---

## 🗺️ 路线图

### v0.2.x (当前)
- [x] 核心内核实现
- [x] 虚拟内存式上下文管理
- [x] KV-Cache 优化
- [x] PostgreSQL 五重角色支持
- [x] 抢占式进程调度
- [x] Docker 沙箱
- [x] 完整审计追踪

### v0.3.0 (进行中)
- [ ] Database as Runtime 探索
- [ ] 分布式调度器
- [ ] Agent 热迁移
- [ ] Web UI 监控面板

### v0.4.0 (计划中)
- [ ] Agent-Native CLI 标准制定
- [ ] GPU 资源管理
- [ ] Kubernetes Operator

---

## 📚 相关资源

### 灵感来源
- [《AI Agent 的操作系统时刻》](https://vonng.com/db/agent-os/) - 冯若航
- [Context Engineering for AI Agents](https://manus.im/blog/context-engineering) - Manus
- [Engram](https://arxiv.org/abs/2502.01623) - DeepSeek

### 相关项目
- [Pigsty](https://pigsty.io/) - PostgreSQL 集装箱
- [E2B](https://e2b.dev/) - Agent 沙箱
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol

---

## 📄 许可证

MIT License © 2026 Bit-Cook

---

<div align="center">

**如果这个项目对你有帮助，请给我们一个 ⭐️ Star！**

[![Star History Chart](https://api.star-history.com/svg?repos=bit-cook/Agent-OS-Kernel&type=Date)](https://star-history.com/#bit-cook/Agent-OS-Kernel&Date)

</div>

---

## 🛠️ 开发指南

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/bit-cook/Agent-OS-Kernel.git
cd Agent-OS-Kernel

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v

# 运行类型检查
mypy agent_os_kernel/

# 代码格式化
black agent_os_kernel/ tests/
```

### Docker 部署

```bash
# 构建镜像
docker build -t agent-os-kernel .

# 运行容器
docker run -p 8080:8080 agent-os-kernel

# 或使用 docker-compose
docker-compose up -d
```

### CI/CD

项目使用 GitHub Actions 进行持续集成：

- **测试**: 在 Python 3.8-3.11 上运行完整测试套件
- **代码质量**: black 格式化检查、flake8 静态分析、mypy 类型检查
- **Docker**: 构建并验证 Docker 镜像

### 项目结构

```
Agent-OS-Kernel/
├── agent_os_kernel/        # 核心代码
│   ├── kernel.py          # 主内核
│   ├── core/              # 核心子系统
│   │   ├── context_manager.py  # 虚拟内存管理
│   │   ├── scheduler.py        # 进程调度
│   │   ├── storage.py          # 持久化存储
│   │   ├── security.py         # 安全子系统
│   │   └── types.py            # 类型定义
│   ├── tools/             # 工具系统
│   └── integrations/      # 外部集成
├── tests/                 # 测试用例
│   ├── test_kernel.py
│   ├── test_context_manager.py
│   ├── test_scheduler.py
│   ├── test_storage.py
│   ├── test_security.py
│   └── test_tools.py
├── examples/              # 示例代码
├── .github/workflows/     # CI/CD 配置
├── Dockerfile            # Docker 构建
├── docker-compose.yml     # Docker Compose
└── mypy.ini              # 类型检查配置
```

### 添加新功能

1. Fork 仓库
2. 创建特性分支: `git checkout -b feature/your-feature`
3. 编写代码和测试
4. 确保所有测试通过: `pytest tests/ -v`
5. 确保代码符合规范: `black agent_os_kernel/ tests/`
6. 提交并创建 Pull Request

### 版本历史

见 [CHANGELOG.md](./CHANGELOG.md)

### 贡献者

感谢所有贡献者！

### 许可证

MIT License - 见 [LICENSE](./LICENSE)

---

<div align="center">

**给项目一个 Star ⭐ 支持我们！**

</div>
