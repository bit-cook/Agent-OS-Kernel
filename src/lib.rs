// Agent OS Kernel - Rust Version
//
// 基于最新 GitHub 架构的高性能实现
// https://github.com/bit-cook/Agent-OS-Kernel

#![cfg_attr(docsrs, feature(doc_cfg))]
#![warn(missing_docs)]

//! Agent OS Kernel 是 AI Agent 的操作系统内核，提供：
//! - 虚拟内存式上下文管理（Context Manager）
//! - 进程调度器（Agent Scheduler）
//! - 存储管理器（Storage Manager - PostgreSQL 五重角色）
//! - 工具注册表（Tool Registry - Agent-Native CLI）
//! - 安全沙箱（Security Subsystem - Sandbox + Observability）

pub mod core;
pub mod tools;
pub mod llm;
pub mod agents;
pub mod api;
pub mod cli;
pub mod utils;

pub use core::*;
pub use tools::*;
pub use llm::*;
pub use agents::*;
pub use api::*;
pub use cli::*;
pub use utils::*;

// 主入口点
pub use core::kernel::AgentOSKernel;
pub use core::context::ContextManager;
pub use core::scheduler::AgentScheduler;
pub use core::storage::StorageManager;
pub use core::security::SecurityPolicy;
