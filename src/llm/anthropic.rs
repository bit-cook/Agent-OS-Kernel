// Anthropic API 集成
pub struct AnthropicProvider;

impl AnthropicProvider {
    pub async fn query(&self, prompt: String) -> Result<serde_json::Value, String> {
        Err("Not implemented".to_string())
    }
}
