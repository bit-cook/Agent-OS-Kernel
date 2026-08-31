# F7: Industry benchmark and target architecture

## Findings

### [1] LangGraph 的定位不是高层 agent harness，而是面向 long-running、stateful agent 的 low-level orchestration runtime；其基线能力已包括 deterministic/agentic 混合图、persistence、durable execution、streaming 与 human-in-the-loop，因此这些能力对 Agent OS Kernel 只能算 table stakes。
- quote: "LangGraph is focused on the underlying capabilities important for agent orchestration: durable execution, streaming, human-in-the-loop, and more."
- url: https://docs.langchain.com/oss/python/langgraph/overview
- source_type: primary
- published: unknown
- confidence: high

### [2] Microsoft Agent Framework（MAF）把 production workflow 的官方能力面扩展到 sequential、concurrent、handoff、group collaboration、checkpointing、streaming、human-in-the-loop、time-travel、middleware 与内建 OpenTelemetry，并以 Python、C#/.NET、Go 三种语言覆盖企业异构栈。
- quote: "includes checkpointing, streaming, human-in-the-loop, and time-travel"
- url: https://github.com/microsoft/agent-framework
- source_type: primary
- published: unknown
- confidence: high

### [3] MAF 官方仓库同时提供从 Semantic Kernel 与 AutoGen 的 migration guide，表明 Microsoft 的演进方向是以统一 agent/workflow foundation 承接两条既有产品线，而 production runtime 必须把兼容迁移与 versioned state evolution 当作正式架构能力。
- quote: "Migration from Semantic Kernel ... Migration from AutoGen"
- url: https://github.com/microsoft/agent-framework
- source_type: primary
- published: unknown
- confidence: high

### [4] OpenAI Agents SDK 明确选择“少量 primitives + Python-first orchestration”：核心是 Agent、Agents-as-tools/Handoffs、Guardrails，再由 runtime 管理 turns、tool execution、handoffs、sessions 与 tracing；这更像可嵌入 application SDK，而非通用 durable scheduler。
- quote: "The Agents SDK has a very small set of primitives"
- url: https://openai.github.io/openai-agents-python/
- source_type: primary
- published: unknown
- confidence: high

### [5] OpenAI Agents SDK 已把 isolated workspace、manifest-defined files、sandbox client selection 与 resumable sandbox sessions 纳入 Sandbox agents，因此“有 sandbox”本身已不足以形成 OS-inspired runtime 的差异化。
- quote: "Sandbox agents support manifest-defined files, sandbox client selection, and resumable sandbox sessions."
- url: https://openai.github.io/openai-agents-python/
- source_type: primary
- published: unknown
- confidence: high

### [6] Google ADK 的 runtime 采用 event-loop/event-stream 模型并显式暴露 yield/pause/resume、resume、cancel 与 RunConfig，同时提供 Dev UI、CLI、REST API Server、Ambient Agents；该页面标注此运行层自 Python v0.1.0、TypeScript v0.2.0、Go v0.1.0、Java v0.1.0、Kotlin v0.1.0 起受支持。
- quote: "including the yield/pause/resume cycle"
- url: https://google.github.io/adk-docs/runtime/
- source_type: primary
- published: unknown
- confidence: high

### [7] Temporal 给 durable execution 的生产语义是“无强制时限”，Workflow code 可运行数秒到数年且 effectively-once to completion，失败后平台持久化 state 并从 latest state 恢复；Agent OS Kernel 若声称 durable，应至少达到这一可测试语义而非仅保存聊天记录。
- quote: "whether your code executes for seconds or years"
- url: https://docs.temporal.io/workflow-execution
- source_type: primary
- published: unknown
- confidence: high

### [8] Temporal 通过 Event History 检查 replay 时重新生成的 Commands，并把外部交互隔离为 Activities、workflow 间交互隔离为 Signals；其官方规模表述为一个 application 可含 millions to billions 个并发 Workflow Executions，这为 deterministic control plane 与 nondeterministic effect plane 的分界提供了成熟参照。
- quote: "During a Replay the Commands that are generated are checked against an existing Event History."
- url: https://docs.temporal.io/workflow-execution
- source_type: primary
- published: unknown
- confidence: high

### [9] OpenTelemetry 已把 GenAI semantic conventions 迁至独立官方仓库，覆盖 GenAI clients、MCP、provider-specific（含 OpenAI）的 spans、metrics、events；Agent OS Kernel 应把该 schema 作为 vendor-neutral telemetry ABI，而不是自造不可互操作的 trace vocabulary。
- quote: "including spans, metrics, and events for GenAI clients, MCP (Model Context Protocol), and provider-specific conventions"
- url: https://github.com/open-telemetry/semantic-conventions-genai
- source_type: primary
- published: unknown
- confidence: high

### [10] 综合上述基线，一个可辩护的 target architecture 是六层：event-sourced durable kernel（run identity、lifecycle、scheduler、checkpoint/replay）、idempotent effect boundary（LLM/tool/I/O）、capability-secured sandbox data plane、可插拔 graph/handoff/agent-loop frontends、MCP/A2A interoperability、OTel-native control plane，并以 deterministic replay 边界约束所有 nondeterministic side effects。
- quote: "The action that the Temporal Service takes is recorded in the Workflow Execution's Event History as an Event."
- url: https://docs.temporal.io/workflow-execution
- source_type: primary
- published: unknown
- confidence: medium

### [11] OS-inspired 的可守差异化不应是再造 graph DSL，而应是 graph 之下的 agent-process semantics：强 capability isolation、CPU/token/time/network quotas、fair scheduling/backpressure/admission control、signals/cancellation、versioned live upgrade 与逐 effect 审计，并允许 LangGraph、MAF、OpenAI SDK、ADK 作为兼容 frontend 运行其上。
- quote: "LangGraph is very low-level, and focused entirely on agent orchestration."
- url: https://docs.langchain.com/oss/python/langgraph/overview
- source_type: primary
- published: unknown
- confidence: medium

## Dead ends
- Google Search 的 3 个首轮查询均返回 HTTP 429，未提供可用结果。
- Bing 对 LangGraph、OpenAI Agents SDK、Google ADK 与 OpenTelemetry 的 site-restricted 查询出现明显日文词典噪声，未据此引用任何结果摘要。
- OpenTelemetry 旧 gen-ai-agent-spans 页面仅返回迁移通知，实际内容已转移到 semantic-conventions-genai 官方仓库。

## Suggested follow-ups
- 对六个 runtime 做同一故障注入矩阵：worker crash、duplicate delivery、checkpoint corruption、human pause、code upgrade，各自保证的 recovery semantics 到底是什么？
- 核验 MCP、A2A 与 OpenTelemetry GenAI conventions 在 Agent OS Kernel 中可稳定化的最小 Agent Process ABI 字段与版本策略。
- 对 capability sandbox、multi-tenant quota/fair scheduling、secret egress policy 做竞品逐项 source-code audit，确认真正未被覆盖的 moat。
