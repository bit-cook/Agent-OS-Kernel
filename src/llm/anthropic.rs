//! Anthropic (Claude) Provider（真实实现）
//!
//! 环境变量：ANTHROPIC_API_KEY（必需）、ANTHROPIC_BASE_URL（可选）、
//! ANTHROPIC_MODEL（可选，默认 claude-sonnet-4-5）。
//! Messages API：x-api-key 头 + anthropic-version，max_tokens 必填。

use super::extract_anthropic_text;
use serde_json::{json, Value};

const DEFAULT_BASE_URL: &str = "https://api.anthropic.com/v1";
const DEFAULT_MODEL: &str = "claude-sonnet-4-5";
const ANTHROPIC_VERSION: &str = "2023-06-01";

pub struct AnthropicProvider {
    api_key: String,
    base_url: String,
    model: String,
    max_tokens: u32,
    client: reqwest::Client,
}

impl AnthropicProvider {
    pub fn from_env() -> Result<Self, String> {
        let api_key = std::env::var("ANTHROPIC_API_KEY")
            .map_err(|_| "ANTHROPIC_API_KEY not set".to_string())?;
        if api_key.trim().is_empty() {
            return Err("ANTHROPIC_API_KEY is empty".to_string());
        }
        Ok(Self {
            api_key,
            base_url: std::env::var("ANTHROPIC_BASE_URL")
                .unwrap_or_else(|_| DEFAULT_BASE_URL.to_string()),
            model: std::env::var("ANTHROPIC_MODEL")
                .unwrap_or_else(|_| DEFAULT_MODEL.to_string()),
            max_tokens: 4096,
            client: reqwest::Client::new(),
        })
    }

    pub fn new(api_key: impl Into<String>) -> Self {
        Self {
            api_key: api_key.into(),
            base_url: DEFAULT_BASE_URL.to_string(),
            model: DEFAULT_MODEL.to_string(),
            max_tokens: 4096,
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

    /// Messages API 请求体（纯函数）
    pub fn body(model: &str, prompt: &str, max_tokens: u32) -> Value {
        json!({
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        })
    }

    pub async fn query(&self, prompt: &str) -> Result<String, String> {
        let resp = self
            .client
            .post(format!("{}/messages", self.base_url))
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", ANTHROPIC_VERSION)
            .json(&Self::body(&self.model, prompt, self.max_tokens))
            .send()
            .await
            .map_err(|e| format!("request failed: {}", e))?;

        let status = resp.status();
        let payload: Value = resp
            .json()
            .await
            .map_err(|e| format!("invalid JSON response ({}): {}", status, e))?;

        if !status.is_success() {
            return Err(extract_anthropic_text(&payload).unwrap_err());
        }
        extract_anthropic_text(&payload)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_body_shape() {
        let b = AnthropicProvider::body("claude-x", "hi", 1024);
        assert_eq!(b["model"], "claude-x");
        assert_eq!(b["max_tokens"], 1024);
        assert_eq!(b["messages"][0]["content"], "hi");
    }

    #[tokio::test]
    async fn test_query_surfaces_error() {
        let p = AnthropicProvider::new("k").with_base_url("http://127.0.0.1:1/v1");
        assert!(p.query("hi").await.is_err());
    }
}
