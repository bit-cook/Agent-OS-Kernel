# 文件夹结构规范

## 项目根结构

```
Agent-OS-Kernel/
├── agent_os_kernel/    # 核心代码
├── tests/              # 测试文件
├── examples/           # 示例代码
├── docs/              # 文档
├── research/          # 研究文档
├── config/            # 配置文件
└── scripts/           # 脚本工具
```

---

## 1. 示例代码 (examples/)

### 文件夹结构

```
examples/
├── README.md          # 索引
├── quickstart/        # 快速开始
├── advanced/          # 高级功能
├── workflow/         # 工作流编排
├── api/              # API 示例
└── integration/      # 集成示例
```

### 分类规则

| 类别 | 文件夹 | 说明 |
|------|--------|------|
| 快速开始 | `quickstart/` | 基础教程、入门示例 |
| 高级功能 | `advanced/` | 复杂功能、高级用法 |
| 工作流 | `workflow/` | 工作流编排 |
| API | `api/` | REST/WebSocket API |
| 集成 | `integration/` | LLM/Storage/Tools/Distributed 等 |

### 命名规则

- 使用 snake_case: `multi_agent_demo.py`
- 演示文件后缀: `_demo.py` 或 `_example.py`

---

## 2. 研究文档 (research/)

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
| 研究总结 | `summary/` | `research_summary.md` |

---

## 3. 配置文件 (config/)

```
config/
├── README.md              # 说明文档
├── config.example.yaml    # 完整配置模板
└── config-example.yaml    # 简配示例
```

---

## 4. 核心代码 (agent_os_kernel/)

```
agent_os_kernel/
├── core/              # 核心模块
├── agents/            # Agent 模块
├── llm/               # LLM Provider
├── tools/             # 工具系统
├── api/               # Web API
├── cli/               # CLI
├── distributed/       # 分布式
├── integrations/      # 集成
└── resources/         # 资源
```

---

## 新增文件流程

### 研究文档

```bash
# 1. 确定分类
research/framework/      # 框架研究
research/analysis/       # 深度分析
research/summary/        # 总结

# 2. 创建文件
touch research/framework/research_{框架名}.md

# 3. 更新索引
# 编辑 research/README.md 添加新文件
```

### 示例代码

```bash
# 1. 确定分类
examples/quickstart/    # 快速开始
examples/advanced/      # 高级功能
examples/api/          # API 示例
examples/integration/  # 集成

# 2. 创建文件
touch examples/{分类}/{描述}.py

# 3. 更新索引
# 编辑 examples/README.md 添加新文件
```

---

## 当前统计

| 类别 | 数量 |
|------|------|
| 示例代码 | 27 |
| 研究文档 | 15 |
| 核心模块 | 40+ |
| 测试文件 | 20+ |

---

*最后更新: 2026-02-10*
