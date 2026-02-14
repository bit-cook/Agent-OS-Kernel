//! ReAct Agent 实现
//!
//! 基于 ReAct (Reasoning + Acting) 模式的 Agent

use async_trait::async_trait;
use serde_json::Value;

/// Agent Trait - 所有 Agent 类型的基 trait
#[async_trait]
pub trait Agent: Send + Sync {
    /// Agent 名称
    fn name(&self) -> &str;
    
    /// 运行 Agent
    async fn run(&self, task: &str) -> Result<Value, String>;
}

/// ReAct Agent 配置
#[derive(Debug, Clone)]
pub struct ReActConfig {
    /// 最大思考步数
    pub max_thought_steps: usize,
    /// 是否启用观察
    pub enable_observation: bool,
}

impl Default for ReActConfig {
    fn default() -> Self {
        Self {
            max_thought_steps: 5,
            enable_observation: true,
        }
    }
}

/// ReAct Agent 实现
#[derive(Debug)]
pub struct ReActAgent {
    config: ReActConfig,
}

impl ReActAgent {
    /// 创建新 ReAct Agent
    pub fn new(config: ReActConfig) -> Self {
        Self { config }
    }
}

#[async_trait]
impl Agent for ReActAgent {
    fn name(&self) -> &str {
        "ReActAgent"
    }
    
    async fn run(&self, task: &str) -> Result<Value, String> {
        // 简化的 ReAct 循环
        let thought = format!("Thinking about: {}", task);
        let action = format!("Action: analyze {}", task);
        let observation = format!("Observation: collected information about {}", task);
        
        Ok(serde_json::json!({
            "agent": self.name(),
            "task": task,
            "thought": thought,
            "action": action,
            "observation": observation,
            "steps": 1,
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_react_agent_run() {
        let agent = ReActAgent::new(ReActConfig::default());
        let result = agent.run("test task").await;
        assert!(result.is_ok());
        let value = result.unwrap();
        assert_eq!(value["agent"], "ReActAgent");
        assert_eq!(value["task"], "test task");
    }
}
