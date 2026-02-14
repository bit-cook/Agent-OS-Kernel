// OpenAI API 集成
pub struct OpenAIProvider;

impl OpenAIProvider {
    pub async fn query(&self, _prompt: String) -> Result<serde_json::Value, String> {
        Err("Not implemented".to_string())
    }
}
