//! MiniMax Provider（真实实现，OpenAI 兼容端点）
//!
//! 环境变量：MINIMAX_API_KEY（必需）、MINIMAX_BASE_URL（可选，默认官方）、
//! MINIMAX_MODEL（可选，默认 abab6.5s-chat）。
//! MiniMax 国际站走 OpenAI 兼容 /v1/chat/completions 形状。

use super::{extract_openai_text, openai_chat_body};

const DEFAULT_BASE_URL: &str = "https://api.minimax.chat/v1";
const DEFAULT_MODEL: &str = "abab6.5s-chat";

pub struct MiniMaxProvider {
    api_key: String,
    base_url: String,
    model: String,
    temperature: f32,
    client: reqwest::Client,
}

impl MiniMaxProvider {
    pub fn from_env() -> Result<Self, String> {
        let api_key = std::env::var("MINIMAX_API_KEY")
            .map_err(|_| "MINIMAX_API_KEY not set".to_string())?;
        if api_key.trim().is_empty() {
            return Err("MINIMAX_API_KEY is empty".to_string());
        }
        Ok(Self {
            api_key,
            base_url: std::env::var("MINIMAX_BASE_URL")
                .unwrap_or_else(|_| DEFAULT_BASE_URL.to_string()),
            model: std::env::var("MINIMAX_MODEL")
                .unwrap_or_else(|_| DEFAULT_MODEL.to_string()),
            temperature: 0.7,
            client: reqwest::Client::new(),
        })
    }

    pub fn new(api_key: impl Into<String>) -> Self {
        Self {
            api_key: api_key.into(),
            base_url: DEFAULT_BASE_URL.to_string(),
            model: DEFAULT_MODEL.to_string(),
            temperature: 0.7,
            client: reqwest::Client::new(),
        }
    }

    pub fn with_base_url(mut self, url: &str) -> Self {
        self.base_url = url.trim_end_matches('/').to_string();
        self
    }

    pub fn with_model(mut self, model: &str) -> Self {
        self.model = model.to_string();
        self
    }

    pub async fn query(&self, prompt: &str) -> Result<String, String> {
        let body = openai_chat_body(&self.model, prompt, self.temperature);
        let resp = self
            .client
            .post(format!("{}/chat/completions", self.base_url))
            .bearer_auth(&self.api_key)
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("request failed: {}", e))?;

        let status = resp.status();
        let payload: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("invalid JSON response ({}): {}", status, e))?;

        if !status.is_success() {
            return Err(extract_openai_text(&payload).unwrap_err());
        }
        extract_openai_text(&payload)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_query_surfaces_error() {
        let p = MiniMaxProvider::new("k").with_base_url("http://127.0.0.1:1/v1");
        assert!(p.query("hi").await.is_err());
    }
}
