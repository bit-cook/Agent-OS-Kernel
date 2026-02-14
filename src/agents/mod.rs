//! Agent 模块
//!
//! 提供各种 Agent 类型实现

/// Agent Trait
pub use react::Agent;

/// ReAct Agent
pub mod react;
/// 执行器
pub mod executor;
/// 工作流
pub mod workflow;

pub use react::*;
pub use executor::*;
pub use workflow::*;
