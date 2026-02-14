//! 工作流 Agent 实现
//!
//! 基于工作流模式的 Agent，支持顺序和并行执行

use async_trait::async_trait;
use serde_json::Value;
use std::time::Duration;

use super::Agent;

/// 工作流类型
#[derive(Debug, Clone)]
pub enum WorkflowType {
    /// 线性工作流
    Linear,
    /// 并行工作流
    Parallel,
    /// 条件工作流
    Conditional,
}

/// 工作流步骤
#[derive(Debug, Clone)]
pub struct WorkflowStep {
    /// 步骤名称
    pub name: String,
    /// 步骤描述
    pub description: String,
    /// 是否启用
    pub enabled: bool,
}

impl Default for WorkflowStep {
    fn default() -> Self {
        Self {
            name: "step".to_string(),
            description: "".to_string(),
            enabled: true,
        }
    }
}

/// 工作流 Agent 配置
#[derive(Debug, Clone)]
pub struct WorkflowConfig {
    /// 工作流类型
    pub workflow_type: WorkflowType,
    /// 步骤列表
    pub steps: Vec<WorkflowStep>,
    /// 超时时间
    pub timeout: Duration,
}

impl Default for WorkflowConfig {
    fn default() -> Self {
        Self {
            workflow_type: WorkflowType::Linear,
            steps: Vec::new(),
            timeout: Duration::from_secs(600),
        }
    }
}

/// 工作流 Agent
#[derive(Debug)]
pub struct WorkflowAgent {
    config: WorkflowConfig,
}

impl WorkflowAgent {
    /// 创建新工作流 Agent
    pub fn new(config: WorkflowConfig) -> Self {
        Self { config }
    }
}

#[async_trait]
impl Agent for WorkflowAgent {
    fn name(&self) -> &str {
        "WorkflowAgent"
    }
    
    async fn run(&self, task: &str) -> Result<Value, String> {
        let step_count = self.config.steps.len();
        
        Ok(serde_json::json!({
            "agent": self.name(),
            "task": task,
            "workflow_type": format!("{:?}", self.config.workflow_type),
            "steps": step_count,
            "status": "workflow_defined",
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_workflow_agent_run() {
        let config = WorkflowConfig::default();
        let agent = WorkflowAgent::new(config);
        let result = agent.run("workflow task").await;
        assert!(result.is_ok());
        let value = result.unwrap();
        assert_eq!(value["agent"], "WorkflowAgent");
    }
}
