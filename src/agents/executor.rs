//! 执行器 Agent 实现
//!
//! 提供任务执行功能的 Agent

use async_trait::async_trait;
use serde_json::Value;

use super::Agent;

/// 执行器 Agent 配置
#[derive(Debug, Clone)]
pub struct ExecutorConfig {
    /// 超时时间（秒）
    pub timeout_seconds: u64,
    /// 重试次数
    pub max_retries: u32,
    /// 是否并行执行
    pub parallel_execution: bool,
}

impl Default for ExecutorConfig {
    fn default() -> Self {
        Self {
            timeout_seconds: 300,
            max_retries: 3,
            parallel_execution: false,
        }
    }
}

/// 执行器 Agent
#[derive(Debug)]
pub struct ExecutorAgent {
    config: ExecutorConfig,
}

impl ExecutorAgent {
    /// 创建新执行器
    pub fn new(config: ExecutorConfig) -> Self {
        Self { config }
    }
}

#[async_trait]
impl Agent for ExecutorAgent {
    fn name(&self) -> &str {
        "ExecutorAgent"
    }
    
    async fn run(&self, task: &str) -> Result<Value, String> {
        Ok(serde_json::json!({
            "agent": self.name(),
            "task": task,
            "status": "executed",
            "config": {
                "timeout": self.config.timeout_seconds,
                "retries": self.config.max_retries,
            }
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_executor_agent_run() {
        let agent = ExecutorAgent::new(ExecutorConfig::default());
        let result = agent.run("execute task").await;
        assert!(result.is_ok());
        let value = result.unwrap();
        assert_eq!(value["agent"], "ExecutorAgent");
        assert_eq!(value["status"], "executed");
    }
}
