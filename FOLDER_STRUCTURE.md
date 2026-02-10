# 文件夹结构规范

> 本规范定义了项目的标准文件夹结构，所有新增文件都应按照此规范归置。

## 项目根结构

```
Agent-OS-Kernel/
├── agent_os_kernel/    # 核心代码
├── tests/              # 测试文件
├── examples/           # 示例代码
├── docs/              # 文档
├── research/          # 研究文档
├── config/            # 配置文件
├── scripts/           # 脚本工具
└── development-docs/  # 开发文档
```

---

## 1. 研究文档 (research/)

### 文件夹结构

```
research/
├── README.md              # 索引
├── framework/             # 框架研究
├── analysis/             # 深度分析
└── summary/              # 研究总结
```

### 分类规则

| 文件类型 | 文件夹 | 命名规则 |
|----------|--------|----------|
| 框架研究 | `framework/` | `research_{框架名}.md` |
| 深度分析 | `analysis/` | `{分析主题}_ANALYSIS.md` |
| 研究总结 | `summary/` | `research_summary.md` 或 `research_{主题}.md` |

### 示例

```
research/
├── framework/
│   ├── research_crewai.md
│   ├── research_langgraph.md
│   └── research_autogpt.md
├── analysis/
│   ├── AIOS_ANALYSIS.md
│   └── ANALYSIS.md
└── summary/
    ├── research_summary.md
    └── research_projects.md
```

---

## 2. 示例代码 (examples/)

### 文件夹结构

```
examples/
├── README.md          # 索引
├── quickstart/        # 快速开始
├── advanced/          # 高级功能
├── multi_agent/       # 多 Agent
├── api/              # API
├── workflow/         # 工作流
├── llm/              # LLM 集成
├── storage/          # 存储
├── tools/            # 工具
├── distributed/     # 分布式
├── optimization/     # 优化
├── plugins/         # 插件
└── learning/         # 自学习
```

### 分类规则

| 类别 | 文件夹 | 说明 |
|------|--------|------|
| 快速开始 | `quickstart/` | 基础教程、入门示例 |
| 高级功能 | `advanced/` | 复杂功能、高级用法 |
| 多 Agent | `multi_agent/` | Agent 协作、协调 |
| API | `api/` | REST/WebSocket API |
| 工作流 | `workflow/` | 工作流编排 |
| LLM | `llm/` | LLM Provider 集成 |
| 存储 | `storage/` | 数据库存储 |
| 工具 | `tools/` | MCP/Tools 集成 |
| 分布式 | `distributed/` | 分布式部署 |
| 优化 | `optimization/` | 性能优化 |
| 插件 | `plugins/` | 插件开发 |
| 学习 | `learning/` | 自学习/记忆 |

### 命名规则

- 使用snake_case: `multi_agent_demo.py`
- 演示文件后缀: `_demo.py` 或 `_example.py`
- 完整工作流: `complete_workflow.py`, `production_workflow.py`

---

## 3. 配置文件 (config/)

### 文件夹结构

```
config/
├── README.md              # 说明文档
├── config.example.yaml    # 完整配置模板
└── config-example.yaml    # 简配示例
```

### 命名规则

- 主配置文件示例: `config.example.yaml`
- 额外示例: `config-{场景}.yaml`

---

## 4. 文档 (docs/)

### 文件夹结构

```
docs/
├── README.md              # 文档索引
├── *.md                   # 主要文档
```

### 命名规则

| 文档类型 | 文件名 |
|----------|--------|
| 快速开始 | `quickstart.md` |
| 架构设计 | `architecture.md` |
| API 参考 | `api-reference.md` |
| 最佳实践 | `best-practices.md` |
| 故障排除 | `troubleshooting.md` |
| 部署指南 | `distributed-deployment.md` |
| 本地模型 | `local-models.md` |
| 对比分析 | `comparison.md` |

---

## 5. 核心代码 (agent_os_kernel/)

### 文件夹结构

```
agent_os_kernel/
├── core/              # 核心模块
├── llm/               # LLM Provider
├── tools/             # 工具系统
├── agents/            # Agent 抽象
├── api/               # Web API
├── cli/               # CLI
├── distributed/       # 分布式
├── integrations/      # 集成
└── resources/         # 资源
```

---

## 6. 测试 (tests/)

### 文件夹结构

```
tests/
├── README.md          # 测试说明
├── test_*.py          # 单元测试
└── conftest.py        # pytest 配置
```

### 命名规则

- 测试文件: `test_{模块名}.py`
- 测试类: `Test{ClassName}`

---

## 7. 开发文档 (development-docs/)

### 文件夹结构

```
development-docs/
├── 3DAY_PLAN.md       # 三日计划
├── ITERATION_PLAN.md  # 迭代计划
└── *.md              # 其他文档
```

---

## 新增文件流程

### 研究文档

```bash
# 1. 确定分类
research/framework/      # 框架研究
research/analysis/       # 深度分析
research/summary/       # 总结

# 2. 创建文件
touch research/framework/research_{框架名}.md

# 3. 更新索引
# 编辑 research/README.md 添加新文件
```

### 示例代码

```bash
# 1. 确定分类
examples/quickstart/    # 快速开始
examples/advanced/     # 高级功能
examples/api/          # API 示例

# 2. 创建文件
touch examples/{分类}/{描述}.py

# 3. 更新索引
# 编辑 examples/README.md 添加新文件
```

---

## 维护检查清单

- [ ] 新文件在正确文件夹
- [ ] 命名符合规范
- [ ] README 索引已更新
- [ ] 分类合理

---

*最后更新: 2026-02-10*
