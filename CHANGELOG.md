# Changelog

All notable changes to this project will be documented in this file.

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
