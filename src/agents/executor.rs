// 执行器 Agent 实现
pub struct ExecutorAgent;

impl ExecutorAgent {
    pub async fn run(&self, _task: &str) -> Result<serde_json::Value, String> {
        Err("Not implemented".to_string())
    }
}
