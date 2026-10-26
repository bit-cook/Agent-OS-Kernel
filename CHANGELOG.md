# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- 存储层 memory 后端：`StorageBackend` enum（Postgres | Memory），`in_memory()` 与
  `from_url_or_memory()`；内核读 `AOSK_DATABASE_URL`，无值/连不通自动回退内存，
  不再强依赖 PostgreSQL 才能启动
- 内置工具真实实现：calculator（递归下降表达式解析器，无 eval 语义）、
  read_file/write_file（workspace 根约束）、execute_shell（默认 fail-closed，
  显式 opt-in 后 argv 无 shell 执行）、json_tool、search；
  `register_builtin_tools()` + 内核 `tool_registry` / `tools()`
- `llm-providers` feature：OpenAI/MiniMax/Anthropic 真实 reqwest 客户端
  （替代禁用的 async-openai），请求构造与响应解析为纯函数离线单测

### Fixed
- Cargo.toml 无效的 `[target.'cfg(feature="python")'.dependencies]` 配置
  （Cargo 报警，feature 选择不生效）；pyo3 改 optional 接入 python feature
- reqwest 改 default-features=false + rustls-tls，避免拖入 openssl-sys

### Removed
- 供应链噪音：vendor/、async-trait.crate、rustup-init.sh（无任何引用）

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
