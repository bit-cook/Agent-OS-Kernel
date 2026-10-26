//! LLM Provider 模块 — 真实 HTTP 客户端（reqwest）
//!
//! 三个提供商共用一个 OpenAI 兼容 chat-completions 形状，差异集中在
//! URL / 认证头 / 负载字段。请求构造与响应解析是纯函数，可离线单测；
//! 网络调用只发生在 `query()`。

pub mod anthropic;
pub mod minimax;
pub mod openai;

pub use anthropic::AnthropicProvider;
pub use minimax::MiniMaxProvider;
pub use openai::OpenAIProvider;

use serde_json::{json, Value};

/// 从 OpenAI 兼容响应体中提取第一条文本内容（纯函数）
pub fn extract_openai_text(body: &Value) -> Result<String, String> {
    if let Some(err) = body.get("error") {
        let msg = err
            .get("message")
            .and_then(|m| m.as_str())
            .unwrap_or("unknown API error");
        return Err(format!("LLM API error: {}", msg));
    }
    body.get("choices")
        .and_then(|c| c.get(0))
        .and_then(|c| c.get("message"))
        .and_then(|m| m.get("content"))
        .and_then(|c| c.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| "Malformed LLM response: no choices[0].message.content".to_string())
}

/// 从 Anthropic messages 响应体中提取文本（纯函数）
pub fn extract_anthropic_text(body: &Value) -> Result<String, String> {
    if let Some(err) = body.get("error") {
        let msg = err
            .get("message")
            .and_then(|m| m.as_str())
            .unwrap_or("unknown API error");
        return Err(format!("Anthropic API error: {}", msg));
    }
    body.get("content")
        .and_then(|c| c.as_array())
        .and_then(|blocks| {
            blocks.iter().find_map(|b| {
                if b.get("type").and_then(|t| t.as_str()) == Some("text") {
                    b.get("text").and_then(|t| t.as_str()).map(String::from)
                } else {
                    None
                }
            })
        })
        .ok_or_else(|| "Malformed Anthropic response: no text block".to_string())
}

/// OpenAI 兼容请求体（纯函数）
pub fn openai_chat_body(model: &str, prompt: &str, temperature: f32) -> Value {
    json!({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_openai_text_ok() {
        let body = json!({
            "choices": [{"message": {"role": "assistant", "content": "hello"}}]
        });
        assert_eq!(extract_openai_text(&body).unwrap(), "hello");
    }

    #[test]
    fn test_extract_openai_text_error() {
        let body = json!({"error": {"message": "rate limited"}});
        let e = extract_openai_text(&body).unwrap_err();
        assert!(e.contains("rate limited"));
    }

    #[test]
    fn test_extract_openai_text_malformed() {
        assert!(extract_openai_text(&json!({"choices": []})).is_err());
    }

    #[test]
    fn test_extract_anthropic_text_ok() {
        let body = json!({
            "content": [
                {"type": "thinking", "thinking": "hmm"},
                {"type": "text", "text": "answer"}
            ]
        });
        assert_eq!(extract_anthropic_text(&body).unwrap(), "answer");
    }

    #[test]
    fn test_openai_chat_body_shape() {
        let b = openai_chat_body("gpt-4o-mini", "hi", 0.7);
        assert_eq!(b["model"], "gpt-4o-mini");
        assert_eq!(b["messages"][0]["role"], "user");
        assert_eq!(b["messages"][0]["content"], "hi");
        // f32 序列化有精度尾差，用容差比较
        let temp = b["temperature"].as_f64().unwrap();
        assert!((temp - 0.7).abs() < 1e-6, "temperature was {}", temp);
    }
}
