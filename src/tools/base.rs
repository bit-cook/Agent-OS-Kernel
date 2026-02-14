// 基础工具定义
pub trait Tool {
    fn name(&self) -> &'static str;
    fn description(&self) -> &'static str;
    fn run(&self, params: serde_json::Value) -> Result<serde_json::Value, String>;
}

// 工具错误
#[derive(Debug)]
pub struct ToolError {
    pub code: String,
    pub message: String,
}

impl From<String> for ToolError {
    fn from(s: String) -> Self {
        Self {
            code: "UNKNOWN".to_string(),
            message: s,
        }
    }
}
