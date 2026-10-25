# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - 2026-10-24

### Python Mainline Remediation (P0 security & golden-path closure)

按仓库自带审查报告（site/audit/report.md）的 P0 退出标准逐项修复，全部有执行验证：

#### Fixed — P0-03 黄金路径断裂
- 顶层 `__init__.py` 导出 `AgentOSKernel` / `KernelStats` / `create_metrics_collector`
  等稳定公共 API（README 与 test_kernel 的导入此前直接 ImportError）
- CLI 重写：`doctor`（环境自检）/ `create` / `list` / `delete` / `status` /
  `demo --type checkpoint` 全部真实执行，状态持久化到 `.agent-os-kernel-state.json`
- API server 重写：`kernel.stop()` → `shutdown()`；补齐 `get_agent` /
  `list_agents` / `terminate_agent`；context 端点改用内核共享的 ContextManager
  （此前每请求新建导致状态丢失）；delete/task 占位假成功改为真实实现
- `__main__` 入口不再依赖 repo 外 examples；版本号与包一致（0.2.0）
- 删除第二套重复 CLI 实现（`cli/commands.py`，525 行），统一到 `cli/main.py`
- 修复两个隐藏崩溃：`StorageManager.log_action`（主循环每步 AttributeError，
  实为 `log_audit`）、`StorageManager.save_context_page`（不存在）

#### Fixed — P0-02 Checkpoint 契约断裂
- Scheduler / Kernel / Storage 三层统一为单一 dict 契约
  （checkpoint_id / agent_pid / agent_name / process_state / context_pages /
  description / created_at）
- 上下文页面真正进入检查点并随恢复回到新进程（此前恒为空列表）
- `StorageManager` 新增 `load_checkpoint`（别名）、`get_checkpoint`、
  `save_context_page` / `load_context_page`；FILE/PG backend 的 checkpoint 与
  主 backend 一致（此前恒为内存）
- 修复 FileStorage `list_keys` 返回不可反推的哈希名（信封格式保存原始 key）

#### Fixed — P0-01 宿主执行边界
- FileRead/FileWrite 工具：workspace 根约束（`Path.resolve()` + `relative_to`），
  `../`、绝对路径穿越、symlink escape 一律拒绝（结构化 denied 错误）
- PythonExecuteTool：默认 fail closed（`isolation_unavailable`），显式
  `allow_host_execution=True` 才走宿主；argv 无 shell、`sys.executable`、
  工作区 cwd、超时后清理临时文件
- SandboxManager：无 Docker 时不再伪装 "process isolation" ——
  `create_sandbox` 返回 None；`execute_in_sandbox` 默认 fail closed，
  显式 `allow_host_fallback=True` 才宿主执行（且移除 shell=True，改 argv）
- WebFetchTool：SSRF 防护（阻断私网/环回/链路本地/云元数据 169.254.169.254/
  非 http(s) scheme，DNS 解析后逐 IP 校验）
- `validate_file_access` 修复 startswith 前缀误匹配（`/etc` 曾匹配 `/etcXXX`）

#### Fixed — P0-04 API 暴露面
- 默认绑定 `127.0.0.1`（API 与 CLI serve）
- 变更型端点（POST/DELETE）API Key 认证（`AOSK_API_KEY` / `X-API-Key`）；
  未配置 key 时仅 loopback 可变更，非 loopback 匿名变更一律 401

#### Fixed — 测试套件缺陷
- 修复 `EventPersister.persist_lock` 死锁（`Lock` → `RLock`）：`save_events`
  持锁调用 `save_event` 同锁重入，导致全量套件永久挂起
- 修复事件时间戳 naive/aware 混用（`utcnow` vs `now(timezone.utc)`）导致的
  TypeError；`from_dict` 兼容旧 naive 时间戳
- 修复 `AgentPool.remove_agent` 在运行中的事件循环里做
  `run_until_complete`/`asyncio.run` 杂技（RuntimeError）
- 修正 `can_handle_priority` 语义：CRITICAL 任务仅 CRITICAL/HIGH 级 Agent
  可处理（与显式契约测试一致）；修正一处与该契约矛盾的负载均衡测试
- 优先级队列测试改用真正的 PriorityQueue（asyncio.Queue 是 FIFO，
  优先级顺序断言对它无效）

#### Changed — 质量门禁与版本一致性
- pyproject：dev extra 补齐 CI 实际调用的工具（ruff/black/mypy/
  pytest-asyncio/pytest-timeout/fastapi/uvicorn），消除 CI exit 127；
  `requires-python` 统一为 >=3.10；pytest 增加 60s 单测试超时防挂死
- CI 重写：ruff + black + mypy(ratchet) + 全量测试 + wheel 干净目录冒烟
  （import + `agent-os-kernel doctor`）+ 文档链接检查（替代不存在的
  sphinx conf）；docs job 不再安装不存在的 `.[docs]`
- README/README_EN 版本徽章统一为 0.2.0-alpha；Dockerfile CMD 改为
  `doctor`（真实自检）；Makefile 更新；48 个 markdown 链接检查全过

#### Added
- `tests/test_security_hardening.py`：P0-01/P0-04 红队测试 15 项
  （/etc/passwd、../、symlink escape、元数据端点、shell 场景、认证矩阵）
- `tests/test_api_server.py`：API 契约测试 11 项（黄金路径 + 认证 + 404）
- `scripts/check_docs_links.py`：文档内链检查

## [Unreleased] - 2026-02-24

### Rust Refactor (rust-refactor-v3)

#### Added
- CLI binary target (`agent-os-kernel`)
- PyO3 Python binding feasibility research
- MCP (Model Context Protocol) client integration
- Context compression module with 4 strategies:
  - Sliding Window
  - Importance-based
  - Summary
  - Hybrid
- Agent Trait with 3 types:
  - ReActAgent
  - ExecutorAgent  
  - WorkflowAgent

#### Changed
- Upgraded sqlx from 0.6.3 to 0.7.4
- Cleaned up all compiler warnings (174 → 0)
- Refactored codebase for better performance

#### Fixed
- Removed unused import warnings
- Fixed test compilation errors
- All 16/16 tests passing ✅

#### Stats
- Total lines: ~3,000+
- Source files: 30
- Test coverage: 16/16 passing
- Compiler warnings: 0
- Release size: 2.0 MB

## [1.0.0] - 2026-02-15

### Python Version

#### Added
- Initial release with 74+ core modules
- 11+ LLM Provider support (OpenAI, DeepSeek, Qwen, Kimi, MiniMax, Ollama, vLLM)
- 59 test files
- 48 example demos
- 41 documentation files
- 158+ total commits

---

**Contributors**: OpenClaw, XieClaw
**License**: MIT
