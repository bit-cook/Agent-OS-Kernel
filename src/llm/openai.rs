//! OpenAI 兼容 Provider（真实实现）
//!
//! 环境变量：OPENAI_API_KEY（必需）、OPENAI_BASE_URL（可选，默认官方）、
//! OPENAI_MODEL（可选，默认 gpt-4o-mini）。

use super::{extract_openai_text, openai_chat_body};
use serde_json::Value;

const DEFAULT_BASE_URL: &str = "https://api.openai.com/v1";
const DEFAULT_MODEL: &str = "gpt-4o-mini";

pub struct OpenAIProvider {
    api_key: String,
    base_url: String,
    model: String,
    temperature: f32,
    client: reqwest::Client,
}

impl OpenAIProvider {
    /// 从环境变量构造；缺少 API key 时返回 Err（绝不静默无 key 调用）
    pub fn from_env() -> Result<Self, String> {
        let api_key = std::env::var("OPENAI_API_KEY")
            .map_err(|_| "OPENAI_API_KEY not set".to_string())?;
        if api_key.trim().is_empty() {
            return Err("OPENAI_API_KEY is empty".to_string());
        }
        Ok(Self {
            api_key,
            base_url: std::env::var("OPENAI_BASE_URL")
                .unwrap_or_else(|_| DEFAULT_BASE_URL.to_string()),
            model: std::env::var("OPENAI_MODEL").unwrap_or_else(|_| DEFAULT_MODEL.to_string()),
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

    /// 单轮对话：POST {base}/chat/completions，返回第一条文本
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
        let payload: Value = resp
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

    #[test]
    fn test_builders() {
        let p = OpenAIProvider::new("k")
            .with_base_url("http://localhost:9999/v1/")
            .with_model("test-model");
        assert_eq!(p.base_url, "http://localhost:9999/v1"); // 尾斜杠被剥掉
        assert_eq!(p.model, "test-model");
    }

    #[tokio::test]
    async fn test_query_surfaces_api_error() {
        // 本地无服务：请求失败应以 Err 返回，绝不 panic
        let p = OpenAIProvider::new("k").with_base_url("http://127.0.0.1:1/v1");
        assert!(p.query("hi").await.is_err());
    }
}
