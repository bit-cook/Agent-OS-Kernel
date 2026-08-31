# Agent OS Kernel 全面审查与极限优化计划

> 审查日期：2026-08-31<br>
> 审查对象：`bit-cook/Agent-OS-Kernel`<br>
> Python 主线快照：`97b25eab8617adaad6f204e98f4d248b5f107b08`（2026-02-24）<br>
> Rust 分支参考：`origin/rust-refactor-v3` / `97aab0c3651ff1e2ac610bf6fe51b2574e3e7cd1`（2026-03-08）<br>
> 当前状态：**审查与计划已完成；任何源码修改、提交、发布均待用户明确批准。**

## 0. 决策摘要

Agent OS Kernel 有一个值得继续投入的核心命题：把 Agent 当作可调度、可恢复、可隔离、可审计的进程，而不是把它继续包装成另一套 graph DSL。当前仓库已经积累了广泛的概念原型，但尚未形成一个可证明正确、可安全暴露、可稳定发布的运行时内核。

最重要的判断不是“缺少功能”，而是：

1. **公开承诺与真实交付面不一致。** README、包版本、API/CLI、Release、Python/Rust 分支与 CI 对“当前产品是什么”给出不同答案。
2. **核心黄金路径尚未闭环。** README 快速开始依赖未导出的顶层符号；主内核的默认 agent step 是模拟实现；API 调用了不存在或不匹配的方法；checkpoint 的调用契约在 Kernel、Scheduler、Storage 三层不一致。
3. **安全边界目前不能承载不可信 Agent。** 内置文件工具没有 workspace 根约束，Python 工具直接在宿主执行，Docker 不可用时的“进程隔离”使用 `shell=True` 在宿主执行；API 默认绑定 `0.0.0.0` 且没有认证授权。
4. **仓库宽度远大于验证深度。** Python 实现约 42,779 行、133 个模块、58 个 test 文件、130 个示例；`core/__init__.py` 单文件 1,161 行并发生名称覆盖。可见的最近 20 次 GitHub CI 均失败，最新主线的 test/docs/docker job 全部失败。
5. **行业基线已经前移。** LangGraph、Microsoft Agent Framework、OpenAI Agents SDK、Google ADK 已覆盖 durable/checkpoint、HITL、resume、sandbox、streaming、tracing 等能力；Temporal 提供更严格的 event history / replay / effect isolation 参照。差异化应落在更底层的 Agent Process ABI、capability isolation、quota/fairness/backpressure、deterministic replay 与逐 effect 审计。

因此，建议采用“**先止血、再收敛、后证明、最后扩展**”的路线。首个目标不是宣布 1.0，而是交付一个范围清楚、默认安全、故障语义可测试的 `0.x` 内核基线。

## 1. 审查范围与方法

### 1.1 已审查

- 产品定位、README、架构文档、变更记录与仓库治理
- Python 顶层入口、Kernel、Scheduler、Storage、Checkpoint、Context、Tools、Security
- API、CLI、配置、LLM Provider、metrics/observability
- 测试、CI、依赖、容器、打包、Release/Tag
- Python 主线与 Rust 重构分支的产品关系
- LangGraph、Microsoft Agent Framework、OpenAI Agents SDK、Google ADK、Temporal、OpenTelemetry GenAI 官方资料

### 1.2 执行过的只读验证

- 固定提交、分支、Tag、Release、GitHub Actions 与分支保护状态
- 文件/模块/测试/示例/行数统计
- 全 Python 模块 `compileall`：通过
- 本地 import/test 尝试：运行环境有 Python 3.14.4，但未预装 `psutil`、`pytest`，因此未将本地依赖缺失误判为项目测试结果
- GitHub CI 一手状态：最新主线 test 3.12、docs、docker 失败，3.10/3.11 被取消；失败注释包含 exit 127/1

### 1.3 证据边界

- 本报告没有声称完整测试套件本地通过或失败。
- 性能文档中的吞吐/延迟数据没有可复现实验环境与原始结果，未作为性能结论。
- Rust 分支做了结构与制品审查，没有把尚未执行的跨语言 parity 测试当作事实。
- 风险等级按“生产级、多租户、会执行不可信工具”的目标评估；若项目明确降级为单机教学原型，部分等级可下调，但文档与发布声明也必须同步下调。

## 2. 当前事实基线

| 维度 | 观察 | 结论 |
|---|---:|---|
| Python 实现 | 133 个 `.py`，约 42,779 行 | 功能面已非常宽，不适合继续横向扩张 |
| 测试 | 58 个 `test_*.py`，约 10,015 行 | 数量不等于可信度，需要按黄金路径和故障语义重构 |
| 示例 | 130 个 Python 示例 | 大量直接导入内部模块，形成事实上的公共 API 膨胀 |
| 提交 | 162 commits，项目始于 2026-01-29 | 短期高速生成，结构债务显著 |
| GitHub | 3 stars、1 fork、1 个当前 open issue、0 PR | 尚处早期，适合做不兼容收敛 |
| CI | 最近 20 个可见 run 全部 failure | 当前不具备可信发布门禁 |
| 治理 | main 无 branch protection | 失败 CI 不能阻止直接进入主线 |
| 版本 | README 1.0.0；包/顶层 0.2.0；API/CLI 1.0.0 | 单一版本真相缺失 |
| 语言 | main 为 Python；latest Release 宣称 Rust；v0.2.0 tag 同时含 Python 与 Rust | 产品边界、制品与兼容策略未定义 |

## 3. 严重度模型

- **P0 / 阻断：** 可能导致宿主代码执行、数据越权、公开 API 不可用、状态恢复失真，或使任何“生产可用”声明不成立。
- **P1 / 高：** 核心语义不确定、可造成数据丢失/重复执行/资源失控，或长期阻断维护与发布。
- **P2 / 中：** 降低性能、可观测性、扩展体验或文档可信度，但有明确绕行路径。
- **P3 / 改进：** 体验、治理与生态完善项，不应挤占正确性和安全工作。

## 4. 关键发现

### P0-01：宿主执行边界不安全，sandbox 失败时会静默降级为非隔离执行

**证据**

- `AgentOSKernel.__init__` 默认 `enable_sandbox=False`，且只有同时传入 policy 才创建 sandbox：`agent_os_kernel/kernel.py:99-149`、`:243-249`。
- `FileReadTool` / `FileWriteTool` 仅做 `abspath`，没有把路径限制在授权根目录，可读写宿主任意可访问路径：`agent_os_kernel/tools/builtin.py:171-206`、`:258-280`。
- `PythonExecuteTool` 将任意代码写入临时文件并调用宿主 `python`：`:318-347`。
- Docker 不可用或创建失败时，`SandboxManager` 回退为仅创建目录的“process isolation”；实际通过 `shell=True` 在宿主执行命令：`agent_os_kernel/core/security.py:123-191`、`:253-299`。
- policy 的 `allowed_paths`、`network_enabled`、资源限制没有被内置工具统一强制执行。

**影响**

不可信 prompt、tool call、API caller 或插件可以在宿主权限范围内读取密钥、改写文件、启动进程与访问网络。当前 fallback 名称会制造错误安全感。

**方案**

1. 立即把所有 effect 收敛到唯一 `EffectExecutor` / `ToolRuntime`；工具定义不能直接执行宿主 I/O。
2. 默认 deny：未提供可用 sandbox runtime 时，危险工具注册失败，不能降级执行。
3. capability token 显式声明 `fs.read roots`、`fs.write roots`、`network hosts`、`process.exec`、`secrets refs`、CPU/内存/时长/输出限制。
4. 路径使用 `Path.resolve()` + `relative_to(allowed_root)`，防 symlink escape；网络做 DNS/IP 重绑定与私网/metadata endpoint 阻断。
5. shell 命令采用 argv，不允许 `shell=True`；Python 执行必须在隔离进程/容器/微 VM 内。
6. sandbox 不可用时返回结构化 `IsolationUnavailable`，写审计事件并 fail closed。

**退出标准**

- 读取 `/etc/passwd`、`../`、symlink escape、写 root 外路径、访问 `169.254.169.254`、shell metacharacter、fork bomb 等红队用例全部被拒绝。
- 每次 effect 有 policy decision、principal、capability、input digest、result digest、资源用量与 trace id。
- 任何危险工具都不能在“无 sandbox”状态下运行。

### P0-02：Checkpoint/Restore 契约断裂，当前“可恢复”承诺不可成立

**证据**

- Scheduler 调用 `storage.save_checkpoint(agent_pid=..., process_state=..., context_pages=...)`，但 StorageManager 的签名只接受一个 `checkpoint_data: dict`：`scheduler.py:467-503` vs `storage.py:719-725`。
- StorageManager 提供 `get_checkpoint`，Kernel/Scheduler 调用 `load_checkpoint`：`storage.py:727-733` vs `kernel.py:319-320`、`scheduler.py:520-523`。
- Scheduler 在第一次保存时明确把 `context_pages=[]`，Kernel 随后只把页面单独保存，未更新已保存 checkpoint 的 context_pages：`scheduler.py:492-496`、`kernel.py:289-305`。
- 默认 StorageManager 即使主 backend 是 PostgreSQL，也把 checkpoint/audit 初始化为 Memory：`storage.py:653-669`；这与崩溃恢复目标相冲突。
- 另有独立 `Checkpointer`，仅保存在实例字典中，形成第三套 checkpoint 语义。

**影响**

创建 checkpoint 可能直接 TypeError；即使绕过，也可能得到不含上下文的空恢复、进程重启后丢失 checkpoint，或在 effect 已执行后重复执行。

**方案**

建立唯一的版本化 `RunSnapshot` + append-only `EventHistory`：

```text
RunIdentity -> Event(seq, type, payload_schema, input_digest, effect_id)
            -> Snapshot(at_seq, state_schema_version, state_digest)
            -> Effect(effect_id, idempotency_key, attempt, status, result_ref)
```

- deterministic control plane 只根据 EventHistory 推导下一 command；LLM、tool、clock、random、network 全部走 effect boundary。
- snapshot 只是加速，不是真相来源；恢复先校验 checksum/schema/version，再 replay 到最新 event。
- effect 至少一次投递 + 幂等键；对于不可幂等 effect 要有 prepare/commit 或人工确认语义。
- 状态迁移必须 versioned，支持旧 checkpoint fixture 升级测试。

**退出标准**

- 在每个生命周期边界 kill worker，重启后结果与无故障基线一致。
- 重放不会重复 tool side effect；corrupt snapshot 能被识别并从较早 snapshot + history 恢复。
- 100 次随机 crash/retry property test 无状态倒退、无重复完成事件。

### P0-03：README、包入口、CLI、API 的黄金路径均存在硬断点

**证据**

- README 使用 `from agent_os_kernel import AgentOSKernel`，但顶层 `__init__.py` 只导出 `core`、`llm` 与元数据：`README.md:64-78`，`agent_os_kernel/__init__.py:8-22`。
- CLI `_cmd_create/_cmd_list` 使用 `from ..core import AgentOSKernel`；`core/__init__.py` 没有这个类，它位于 `agent_os_kernel/kernel.py`：`cli/main.py:128-140`。
- API lifespan 调用 `self.kernel.stop()`，Kernel 公开的是 `shutdown()`；API 还调用 `get_agent/list_agents`，主 Kernel 未实现这些方法：`api/server.py:93-100`、`:131-191`。
- context API 每次创建新的 ContextManager，因此 add/get 不共享状态：`:222-244`。
- delete/task endpoints 明确是占位逻辑但返回成功/待处理：`:186-218`。
- 包 entry point 指向 `agent_os_kernel.__main__:main`，该入口默认运行 repo 外 `examples.*`，且版本写死 1.0.0：`pyproject.toml:42-43`，`__main__.py:13-44`。

**影响**

用户从安装、quickstart、CLI 到 API 的第一条路径都可能失败或产生虚假成功。这比缺少高级能力更严重。

**方案与退出标准**

- 定义唯一黄金路径：`pip install` → `agent-os-kernel doctor` → `agent-os-kernel run quickstart.yaml` → 可观察到一次真实 mock/deterministic run。
- 只保留一个 CLI 实现与一个 API service facade；API 不直接拼装核心对象。
- 安装 wheel 后在空临时目录运行 smoke test，不允许依赖 repo 的 examples。
- README 的每段代码作为 doctest/smoke test 进入 CI。
- OpenAPI contract、CLI snapshot、Python public import snapshot 全部版本化。

### P0-04：无认证 API 默认监听所有网卡，并暴露变更型能力

**证据**

- API 与 CLI serve 默认 host 为 `0.0.0.0`：`api/server.py:82`、`:278-283`，`cli/main.py:80-83`。
- create/delete agent、submit task、写 context、读取 metrics/status 均没有认证或授权依赖：`api/server.py:114-275`。

**影响**

一旦服务被启动在云主机、容器或共享网络，任意可达用户可创建任务、探测状态，并在未来工具执行闭环后放大为远程代码执行面。

**方案与退出标准**

- 默认 bind `127.0.0.1`；非 loopback 必须显式 `--public` 并配置认证。
- principal + tenant + role + scoped capability；管理、运行、查看 trace、查看 secret 元数据分离。
- request size、并发、速率、run quota、超时与审计默认开启。
- OpenAPI security scheme 与 401/403/429 contract tests；匿名变更请求全部拒绝。

### P1-01：公共命名空间被重复实现覆盖，系统没有清晰内核边界

`core/__init__.py` 超过 1,100 行，把 74+ 模块的几乎所有类型重导出；`AgentState`、`AgentPool`、`CacheLevel`、`CacheEntry`、`ConfigSection` 等先从基础模块导入，又被 enhanced 版本覆盖。仓库同时存在 scheduler/task_scheduler/optimized_scheduler/distributed_scheduler，event_bus/enhanced/advanced，storage/enhanced，metrics/metrics_collector/monitoring/observability/trace_manager 等平行实现。

**建议目标边界**

```text
agent_os_kernel/
  api/             # stable public Python API, versioned
  runtime/         # Run, Process, Scheduler, Signal, Cancellation
  durability/      # EventHistory, Snapshot, EffectJournal, migrations
  effects/         # LLM, Tool, Network, Filesystem ports
  policy/          # capability + quota + admission decisions
  telemetry/       # OTel semantic ABI + audit
  adapters/        # providers, MCP, storage, sandbox
  experimental/    # 尚未承诺兼容的功能
```

禁止 `core/__init__` 星型聚合；稳定 API 只从 `agent_os_kernel.api` 与顶层精选符号导出。旧实现先标记 owner/status/consumer，再通过 ADR 选择 canonical；没有消费者且没有独特测试的实现删除或移入 history，不做“永久兼容层”。

### P1-02：主 Kernel 不是实际 LLM runtime，调度与执行模型仍是同步模拟循环

- `execute_agent_step` 使用粗略 word×2 估算 token、`time.sleep(0.1)` 与固定 reasoning；`done` 永远 False：`kernel.py:348-399`。
- 主循环是单线程同步 polling，空闲时 sleep；错误重试没有 backoff/jitter/dead-letter，取消/超时/信号语义未成为统一 contract：`:401-468`。
- LLM 层同时存在 `LLMProvider`、`BaseLLMProvider`、两个 OpenAIProvider，主 Kernel 没有依赖其中任何一套。

**建议**

Kernel 不应自行实现 agent reasoning。它应该运行 `ProcessProgram`，由 frontend adapter（ReAct、graph、OpenAI SDK 等）产生 Commands。Scheduler 只关心 admission、priority、deadline、quota、fairness、cancellation；effect workers 执行 LLM/tool I/O。

### P1-03：CI、依赖与 Release 不是可用的质量门禁

- CI 安装 `.[dev]`，但 `pyproject.toml` dev 只含 pytest/pytest-cov；随后调用 black、flake8、mypy，docs job 安装不存在的 `.[docs]`，与 exit 127 注释一致：`pyproject.toml:31-36`，`.github/workflows/ci.yml:27-38,52-59`。
- CI 构建 Dockerfile，但 main 的 Dockerfile/requirements/包元数据依赖面不一致；Python 支持声明分别为 3.8+、3.10+、CI 3.10–3.12。
- mypy 配置包含全局 `ignore_errors=True`。
- main 无 branch protection；失败 CI 没有合并阻断效果。
- README/API/CLI/Changelog/Release 对 0.2.0/1.0.0 不一致。

**建议**

- 选定 Python 3.11+ 或 3.10+ 的明确窗口；用 lock/constraints 保证可复现。
- 统一 `quality`、`test`、`docs`、`release` extras；CI 从 `pyproject.toml` 单一来源安装。
- 必须通过：format/lint、strict type（分阶段 ratchet）、unit、contract、integration、security、wheel install、docs links/code、container smoke。
- main branch protection + required checks；Release 只由 tag workflow 产生并带 SBOM、provenance、checksum、签名。

### P1-04：Python 与 Rust 是两个产品还是一个产品，当前没有决策

最新 Release 名称是“Rust 重构版本”，但 v0.2.0 tag 同时保留 Python 包与 Rust crate；main 不含 Rust `src/`，Rust 分支继续独立更新。Cargo 默认 feature 打开 postgres/web/cli，但 `llm-providers` 被显式禁用；Python binding 仍是 feasibility 层。Rust 分支还提交了 vendored crates、`rustup-init.sh` 等大量供应链文件。

**推荐决策：先采用 Python control plane + 可选 Rust acceleration，而不是立即全量重写。**

理由：当前最大风险是语义、边界与验证，而不是 Python 性能；在语义未稳定前重写只会复制不确定性。Rust 只承接经过 profile 证明的热路径（例如高吞吐 journal/queue/codec），通过稳定 FFI/IPC contract 接入。若团队坚持 Rust-first，则必须先通过 parity gate：同一 conformance suite、同一 state schema、同一 effect journal、同一 CLI/OpenAPI contract，之后明确 Python 的 deprecation 时间线。

### P1-05：配置、密钥与默认值缺乏单一 schema

配置存在多个 example 文件、CLI 自行写 `config.yaml`、provider 自行读环境变量、Storage 内置 PostgreSQL 默认密码 `secret`。没有明确 precedence、unknown-key policy、redaction、secret reference 与动态配置安全边界。

建议使用强类型 `KernelConfig`，顺序固定为 defaults < file < env < CLI，启动时输出 redacted effective config 与 schema version；未知字段默认报错。secret 只保存引用，不写入 checkpoint/event/log。

### P2-01：可观测性是多套本地记录器，不是可互操作的运行时 ABI

Observability、MetricsCollector、MetricsRegistry、monitoring、trace_manager 等重复；主要输出 JSONL、自造 Prometheus 文本与内存事件。尚未以 OpenTelemetry GenAI semantic conventions 建模 run/agent/LLM/tool/MCP spans、metrics、events，也缺少统一 correlation IDs 与 cardinality budget。

建议所有 runtime entity 统一 `tenant_id/run_id/process_id/step_id/effect_id/attempt`；OTel 是 telemetry ABI，审计 journal 是不可变事实，两者分离但可关联。指标至少覆盖 queue wait、admission reject、run/effect latency、retry、checkpoint/replay、token/cost、sandbox violation、worker saturation。

### P2-02：性能优化尚未建立可信基线

仓库已经有 cache/batch/pool/optimized scheduler/benchmark 等大量优化模块，但在核心语义与 benchmark harness 稳定前，这些优化难以证明收益，并增加状态空间。

建议先定义 6 类 workload：短 ReAct、长会话、并发多租户、tool-heavy、checkpoint-heavy、streaming；固定数据与 mock latency，测 p50/p95/p99 queue wait、step/effect latency、throughput、memory/run、replay time、fairness Jain index、recovery RTO/RPO。任何优化必须记录 baseline、假设、结果、噪声、保留/回退决策。

### P2-03：文档与示例过多，反而稀释了黄金路径

130 个示例大量导入 `agent_os_kernel.core.*`；文档存在大小写/同义重复（API/API_REFERENCE/api-reference、DEPLOYMENT/deployment 等）。应收敛为 5 条经过 CI 的黄金路径：quickstart、durable run、safe tool、custom provider、distributed worker；其余迁入 cookbook/experimental 并标注版本。

## 5. 值得保留和强化的基础

- OS 映射对 scheduler/context/effect/security 的讨论有启发性，适合形成明确的 Agent Process ABI。
- 已经存在 scheduler、context pages、storage、checkpoint、tool registry、MCP、metrics 等概念部件，能作为需求与 conformance case 的素材。
- 代码普遍有类型标注、dataclass、抽象接口与测试文件，重构时比完全无结构的脚本更容易提炼 contract。
- 项目愿意覆盖中国模型、本地模型与 MCP，具备 provider-neutral / deployment-neutral 的潜在定位。
- MIT 许可、公开研究材料与大量示例有利于社区参与；现在正处早期，做不兼容收敛成本相对低。

## 6. 目标产品定义

### 6.1 一句话

**Agent OS Kernel 是可嵌入、provider-neutral 的 Agent Process Runtime：它为上层 agent/graph SDK 提供持久执行、effect 隔离、资源治理、信号与审计，而不与上层 reasoning framework 竞争。**

### 6.2 明确不做

- 不再造通用 prompt/graph DSL
- 不在 Kernel 内绑定某一家模型 SDK
- 不把“目录 + subprocess”称作 sandbox
- 不把 in-memory snapshot 称作 durable recovery
- 不以模块数、provider 数、示例数作为成熟度指标
- 不同时承诺 Python-first 与 Rust rewrite，除非有一套跨语言 conformance contract

### 6.3 六层目标架构

1. **Frontend adapters**：ReAct、graph、handoff、OpenAI Agents SDK/ADK/LangGraph 适配，输出统一 Commands。
2. **Durable kernel**：Run identity、lifecycle、scheduler、signals、cancellation、event history、snapshot/replay。
3. **Effect boundary**：LLM/tool/file/network/clock/random；幂等、retry、timeout、circuit breaker。
4. **Capability data plane**：sandbox、filesystem/network/secrets policies、quota、admission、multi-tenancy。
5. **Interoperability**：MCP 工具、A2A/agent messaging（待成熟）、storage/provider adapters。
6. **Control plane**：OTel-native telemetry、audit、API/CLI/operator、schema/version migrations。

## 7. 分阶段极限优化路线图

> 工期是相对规模估算，不是承诺日期。建议 2–4 名核心工程师；所有阶段必须独立可回滚。

### Phase 0 — 冻结承诺与建立基线（3–5 天）

**目标：** 让所有人对“当前是什么”达成一致。

- 暂停新增 subsystem/provider/example。
- 标记 alpha，统一版本真相，撤下未经验证的 production-ready/1.0 声明。
- 建 capability inventory：模块 owner、状态（canonical/duplicate/experimental/dead）、消费者、测试。
- 写 ADR-001 产品边界、ADR-002 Python/Rust 策略、ADR-003 durability semantics、ADR-004 sandbox threat model。
- 建已知问题与风险登记簿。

**DoD：** README/package/API/CLI/Release 版本一致；架构图只画实际存在的路径；每个核心模块有状态标签；执行仍未开始新增功能。

### Phase 1 — 恢复可信构建与单一黄金路径（1–2 周）

**目标：** 任意贡献者能从干净环境复现同一结果。

- 重写 pyproject extras 与 lock/constraints；明确 Python 支持窗口。
- 修复 CI，加入 wheel install、README smoke、CLI/OpenAPI contract、docs link/code check。
- 开启 branch protection、required checks、CODEOWNERS、Dependabot/Renovate、security policy。
- 统一顶层 exports、CLI entry point、API facade；删除虚假成功 endpoint。
- 将示例收敛为 5 条黄金路径。

**DoD：** 三个连续主线 run 全绿；wheel 在空目录可安装运行；README 代码全部自动执行；CI 失败可阻止合并。

### Phase 2 — P0 安全重构（2–3 周）

**目标：** 不可信 effect 默认无法逃逸宿主边界。

- 实现 EffectExecutor + capability policy engine。
- 危险工具 fail closed；sandbox 无降级；rooted fs、egress policy、secret refs。
- API loopback default + authn/authz/rate/quota/audit。
- threat model + abuse cases + red-team suite + dependency/SBOM scanning。

**DoD：** P0-01/P0-04 攻击矩阵全过；安全决策覆盖率 100%；无裸 `shell=True`、无工具直接宿主 I/O；公开监听必须显式授权。

### Phase 3 — Durable Kernel v1（3–5 周）

**目标：** 用可测试语义兑现恢复承诺。

- 定义 Run/Process/Command/Event/Effect/Snapshot schema 与迁移。
- append-only event journal、幂等 effect、deterministic replay。
- 统一 scheduler/checkpointer/storage，删除平行 checkpoint 实现。
- signals/cancellation/deadline/retry/backoff/dead-letter/compensation。
- Postgres reference backend + in-memory deterministic test backend。

**DoD：** crash matrix、replay property tests、duplicate delivery、corruption、schema upgrade 全过；RPO=0（已提交 event），恢复后无重复 effect；状态机模型检查无非法转换。

### Phase 4 — 调度、背压与多租户资源治理（2–4 周）

**目标：** 从“有优先级队列”升级为可度量的运行时治理。

- admission control、bounded queues、worker lease/heartbeat。
- weighted fair scheduling + priority aging + deadline/cancellation。
- token/request/cost/CPU/memory/concurrency quotas；tenant isolation。
- overload policy、backpressure propagation、graceful shutdown/drain。

**DoD：** 过载时内存有界；低优先级不永久饥饿；租户噪声隔离；shutdown 不丢已提交 work；benchmark 达到预先批准的 SLO。

### Phase 5 — Provider、MCP 与上层框架适配（2–3 周）

**目标：** 让生态通过稳定 port 接入，而不是进入内核。

- 一个 LLMProvider protocol、统一 request/response/stream/tool-call/error taxonomy。
- provider capability negotiation、timeouts、retry hints、usage/cost。
- MCP client 放在 effect boundary 后；连接、session、permission、schema 版本明确。
- 首选一个 frontend adapter（建议 LangGraph 或简洁 ReAct）证明可嵌入性。

**DoD：** provider conformance suite；mock + 2 个真实 provider contract；MCP 恶意 payload/断线/取消测试；上层 adapter 不修改内核即可替换。

### Phase 6 — OTel-native 可观测性与运维面（1–2 周）

**目标：** 每一次排队、决策、effect 与恢复都能关联。

- 采用 OpenTelemetry GenAI/MCP conventions；定义项目扩展命名空间。
- run/process/step/effect 全链路 trace；metrics cardinality budget；structured logs。
- SLO dashboards、health/readiness、audit query、诊断 bundle。

**DoD：** 一个 run 可从 API request 追到 LLM/tool effect 与 checkpoint；敏感字段默认 redacted；telemetry overhead 有预算并通过 benchmark。

### Phase 7 — 性能剖析与选择性 Rust 加速（2–4 周，条件触发）

**前置条件：** Phase 3–6 语义稳定且 profile 证明 Python 瓶颈。

- 固定 workload/数据/环境，建立可重复 benchmark。
- 优先做算法、批处理、连接复用与序列化优化。
- 只有超过批准阈值的热路径进入 Rust；同一 conformance suite 验证。
- Rust crate 不复制业务语义；不提交无必要的 toolchain installer/vendor blob。

**DoD：** 每项优化有置信区间与 keep/revert 记录；p95/p99、内存、fairness 无回归；FFI failure/cancellation/panic 安全。

### Phase 8 — Beta 发布与社区治理（1–2 周）

- SemVer、deprecation、state schema compatibility policy。
- signed artifacts、SBOM、provenance、checksum、release notes、upgrade/rollback guide。
- contribution guide、issue templates、RFC/ADR 流程、maintainer ownership。
- Beta reference deployment 与 72h soak/chaos test。

**DoD：** 可从上一 beta 升级并回滚；制品可验证；runbook 演练通过；文档不含未实现承诺。

## 8. 验证矩阵

| 层 | 必须验证 | 核心指标/断言 |
|---|---|---|
| Unit | 状态机、policy、quota、serialization | branch/condition + mutation tests |
| Contract | Python API、CLI、OpenAPI、Provider、MCP | schema snapshot + compatibility |
| Property | replay、queue、scheduler、idempotency | 随机序列下 invariant 不破坏 |
| Integration | Postgres、sandbox、2 providers、MCP | 真实依赖、确定性 fixtures |
| Fault injection | worker/db/network crash、timeout、duplicate | 无状态倒退/重复 effect |
| Security | fs/network/process/secrets/auth | deny-by-default，全审计 |
| Performance | 6 类 workload × 3 并发档 | p50/p95/p99、吞吐、内存、fairness |
| Soak | 24/72h 混合 workload | 无泄漏、queue 有界、恢复 SLO |
| Release | wheel/container/binary/SBOM | 空环境安装、签名和 provenance |

建议初始质量门槛：changed-code coverage ≥ 90%，核心状态机 mutation score ≥ 80%，全局 coverage 采用 ratchet 不倒退；这些数字需在 Phase 1 基线后最终批准，不能用低价值测试“刷数”。

## 9. 优先级与依赖

```text
Phase 0 事实一致性
   └── Phase 1 可信 CI / 黄金路径
        ├── Phase 2 安全边界 ─────┐
        └── Phase 3 Durable Kernel ├── Phase 4 调度治理
                                  └── Phase 5 生态适配
                                         └── Phase 6 可观测运维
                                                └── Phase 7 性能/Rust（条件触发）
                                                       └── Phase 8 Beta
```

不能并行跳过的关系：安全和 durable semantics 必须先于公开多租户 API；contract 必须先于 provider 扩张；profile 必须先于 Rust 加速；绿色 CI 必须先于任何发布。

## 10. 暂缓清单

在 Phase 4 退出前暂缓：更多 provider、更多 cache/pool/strategy pattern、service mesh、自学习 optimizer、GPU manager、复杂 dashboard、A2A 扩展、全面 Rust rewrite。它们并非永远不做，而是目前会扩大未验证状态空间。

## 11. 关键风险与缓解

| 风险 | 缓解 |
|---|---|
| 大规模删除引发社区疑虑 | capability inventory + ADR + experimental namespace，不做无证据删除 |
| Durable redesign 复杂度失控 | 先单进程/Postgres reference，固定 event/effect contract，再扩分布式 |
| Sandbox 跨平台成本 | 定义 SandboxProvider；首个官方平台明确，其他平台 fail closed |
| Python/Rust争论拖慢交付 | 用 benchmark + conformance gate 决策，不用偏好决策 |
| 为追覆盖率写低价值测试 | mutation/property/fault tests 优先，changed-code ratchet |
| 文档再次超前 | docs-as-code；所有 code/claim 关联测试或 capability status |

## 12. 用户批准后的首个执行批次

如果用户批准，建议**只批准 Phase 0 + Phase 1**，不一次授权全路线：

1. 创建工作分支，不直接改 main。
2. 生成 capability inventory 和 4 份 ADR 草案。
3. 修复版本、pyproject、CI 与顶层导出。
4. 建 wheel/README/CLI smoke tests。
5. 收敛一个可运行的 deterministic mock golden path。
6. 独立代码审查与证据报告；用户再次批准后进入 P0 安全重构。

**当前没有执行以上任何一项。**

## 13. 开放问题（执行前必须定案）

1. 项目最终是 Python SDK、独立 runtime service，还是两者兼具？建议先 SDK + reference service。
2. 第一官方 sandbox 平台是 Linux container、gVisor、Firecracker 还是外部 sandbox provider？
3. 多租户是 beta 必需还是后续能力？若不是，API 仍需默认本地与认证能力。
4. Durable 语义目标是 at-least-once effect + idempotency，还是某些 effect 的更强事务语义？
5. Python 支持窗口与 Rust 的角色由谁拥有、维护容量是多少？
6. 首个 frontend adapter 选 LangGraph、OpenAI Agents SDK 还是项目自身最小 ReAct？
7. Beta 的量化 SLO：并发 run、p95 queue wait、RTO/RPO、最大 event history、成本预算。

## 14. 来源

### 仓库与一手项目证据

- Agent OS Kernel repository：<https://github.com/bit-cook/Agent-OS-Kernel>
- 审查提交：<https://github.com/bit-cook/Agent-OS-Kernel/commit/97b25eab8617adaad6f204e98f4d248b5f107b08>
- 最新审查 CI：<https://github.com/bit-cook/Agent-OS-Kernel/actions/runs/22356930858>
- v0.2.0 Release：<https://github.com/bit-cook/Agent-OS-Kernel/releases/tag/v0.2.0>

### 行业官方资料（访问日期均为 2026-08-31）

1. LangGraph Overview — <https://docs.langchain.com/oss/python/langgraph/overview>
2. Microsoft Agent Framework — <https://github.com/microsoft/agent-framework>
3. OpenAI Agents SDK — <https://openai.github.io/openai-agents-python/>
4. Google ADK Runtime — <https://google.github.io/adk-docs/runtime/>
5. Temporal Workflow Execution — <https://docs.temporal.io/workflow-execution>
6. OpenTelemetry GenAI Semantic Conventions — <https://github.com/open-telemetry/semantic-conventions-genai>

## 15. 最终建议

继续做，但改变成功标准：从“像操作系统一样拥有很多模块”转为“像内核一样拥有少量、稳定、可证明的语义”。

项目最有潜力的版本不是最大的版本，而是这样一个版本：上层任何 Agent framework 都可以把 run 交给它；worker 在任意时刻崩溃都可恢复；同一个 effect 不会被悄悄执行两次；不可信工具无法越过 capability；所有调度与策略决定都可审计；每个发布声明都能由 CI 和制品复现。达到这个标准后，再谈极限性能、Rust 与生态扩张，才会形成真正的复利。
