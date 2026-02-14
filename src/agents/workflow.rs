// 工作流 Agent 实现
pub struct WorkflowAgent;

impl WorkflowAgent {
    pub async fn run(&self, _task: &str) -> Result<serde_json::Value, String> {
        Err("Not implemented".to_string())
    }
}
