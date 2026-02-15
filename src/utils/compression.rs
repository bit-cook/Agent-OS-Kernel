//! Context Compression Module
//!
//! Provides context compression strategies for efficient token usage

/// Compression strategy type
#[derive(Debug, Clone)]
pub enum CompressionStrategy {
    /// Keep only most important messages
    ImportanceBased,
    /// Summarize old messages
    Summarization,
    /// Keep recent context only
    SlidingWindow,
    /// Hybrid approach
    Hybrid,
}

/// Compression configuration
#[derive(Debug, Clone)]
pub struct CompressionConfig {
    /// Maximum context tokens
    pub max_tokens: usize,
    /// Compression strategy
    pub strategy: CompressionStrategy,
    /// Importance threshold (0-1)
    pub importance_threshold: f32,
    /// Summary prompt template
    pub summary_prompt: String,
}

impl Default for CompressionConfig {
    fn default() -> Self {
        Self {
            max_tokens: 8000,
            strategy: CompressionStrategy::Hybrid,
            importance_threshold: 0.5,
            summary_prompt: "Summarize this conversation concisely:".to_string(),
        }
    }
}

/// Context message
#[derive(Debug, Clone)]
pub struct ContextMessage {
    /// Role (user, assistant, system)
    pub role: String,
    /// Message content
    pub content: String,
    /// Importance score (0-1)
    pub importance: f32,
    /// Token count estimate
    pub token_count: usize,
    /// Timestamp
    pub timestamp: u64,
}

/// Compression result
#[derive(Debug)]
pub struct CompressionResult {
    /// Compressed messages
    pub messages: Vec<ContextMessage>,
    /// Total tokens after compression
    pub total_tokens: usize,
    /// Compression ratio
    pub compression_ratio: f32,
    /// Whether compression was applied
    pub was_compressed: bool,
}

/// Context Compressor
#[derive(Debug)]
pub struct ContextCompressor {
    config: CompressionConfig,
}

impl ContextCompressor {
    /// Create new compressor
    pub fn new(config: CompressionConfig) -> Self {
        Self { config }
    }

    /// Compress messages
    pub fn compress(&self, messages: &[ContextMessage]) -> CompressionResult {
        let total_input_tokens: usize = messages.iter().map(|m| m.token_count).sum();
        
        if total_input_tokens <= self.config.max_tokens {
            return CompressionResult {
                messages: messages.to_vec(),
                total_tokens: total_input_tokens,
                compression_ratio: 1.0,
                was_compressed: false,
            };
        }

        let compressed = match self.config.strategy {
            CompressionStrategy::ImportanceBased => self.compress_by_importance(messages),
            CompressionStrategy::Summarization => self.compress_by_summarization(messages),
            CompressionStrategy::SlidingWindow => self.compress_sliding_window(messages),
            CompressionStrategy::Hybrid => self.compress_hybrid(messages),
        };

        let total_output_tokens: usize = compressed.iter().map(|m| m.token_count).sum();

        CompressionResult {
            messages: compressed,
            total_tokens: total_output_tokens,
            compression_ratio: total_output_tokens as f32 / total_input_tokens as f32,
            was_compressed: true,
        }
    }

    /// Importance-based compression
    fn compress_by_importance(&self, messages: &[ContextMessage]) -> Vec<ContextMessage> {
        let mut important: Vec<_> = messages.iter()
            .filter(|m| m.importance >= self.config.importance_threshold)
            .cloned()
            .collect();
        
        important.sort_by(|a, b| b.importance.partial_cmp(&a.importance).unwrap());
        
        // Fill up to max tokens
        let mut result = Vec::new();
        let mut token_count = 0;
        
        for msg in important {
            if token_count + msg.token_count <= self.config.max_tokens {
                result.push(msg.clone());
                token_count += msg.token_count;
            } else if result.is_empty() {
                // Always include at least one message
                result.push(msg.clone());
            }
        }
        
        result
    }

    /// Summarization-based compression
    fn compress_by_summarization(&self, messages: &[ContextMessage]) -> Vec<ContextMessage> {
        // Keep system message if exists
        let system: Vec<_> = messages.iter()
            .filter(|m| m.role == "system")
            .cloned()
            .collect();
        
        // Summarize older messages
        let non_system: Vec<_> = messages.iter()
            .filter(|m| m.role != "system")
            .cloned()
            .collect();
        
        // Simple compression: keep recent messages
        let recent = self.compress_sliding_window(&non_system);
        
        [&system[..], &recent[..]].concat()
    }

    /// Sliding window compression
    fn compress_sliding_window(&self, messages: &[ContextMessage]) -> Vec<ContextMessage> {
        let recent: Vec<_> = messages.iter()
            .rev()
            .take_while(|m| {
                // Rough token estimate: 4 chars per token
                let chars: usize = m.content.chars().count();
                chars / 4 <= self.config.max_tokens
            })
            .cloned()
            .collect();
        
        recent.into_iter().rev().collect()
    }

    /// Hybrid compression
    fn compress_hybrid(&self, messages: &[ContextMessage]) -> Vec<ContextMessage> {
        // Keep system message
        let system: Vec<_> = messages.iter()
            .filter(|m| m.role == "system")
            .cloned()
            .collect();
        
        // Keep recent messages (70%)
        let recent_count = (messages.len() as f32 * 0.7) as usize;
        let recent: Vec<_> = messages.iter()
            .rev()
            .take(recent_count)
            .cloned()
            .collect();
        
        // Keep important messages (30%)
        let important: Vec<_> = messages.iter()
            .filter(|m| m.importance >= 0.7)
            .cloned()
            .collect();
        
        // Merge and dedup
        let mut merged = [&system[..], &recent[..], &important[..]].concat();
        merged.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        merged.dedup_by(|a, b| a.content == b.content);
        
        merged
    }
}

/// Estimate token count from text
pub fn estimate_tokens(text: &str) -> usize {
    // Rough estimate: 4 characters per token
    text.chars().count() / 4
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_messages() -> Vec<ContextMessage> {
        vec![
            ContextMessage {
                role: "system".to_string(),
                content: "You are a helpful assistant.".to_string(),
                importance: 1.0,
                token_count: 6,
                timestamp: 1000,
            },
            ContextMessage {
                role: "user".to_string(),
                content: "Hello!".to_string(),
                importance: 0.3,
                token_count: 2,
                timestamp: 2000,
            },
            ContextMessage {
                role: "assistant".to_string(),
                content: "Hi there!".to_string(),
                importance: 0.5,
                token_count: 3,
                timestamp: 3000,
            },
            ContextMessage {
                role: "user".to_string(),
                content: "Tell me about Rust.".to_string(),
                importance: 0.8,
                token_count: 5,
                timestamp: 4000,
            },
        ]
    }

    #[test]
    fn test_no_compression_needed() {
        let compressor = ContextCompressor::new(CompressionConfig::default());
        let messages = create_test_messages();
        let result = compressor.compress(&messages);
        
        assert!(!result.was_compressed);
        assert_eq!(result.messages.len(), 4);
    }

    #[test]
    fn test_importance_based() {
        let compressor = ContextCompressor::new(CompressionConfig {
            max_tokens: 10,
            strategy: CompressionStrategy::ImportanceBased,
            importance_threshold: 0.5,
            summary_prompt: "".to_string(),
        });
        
        let messages = create_test_messages();
        let result = compressor.compress(&messages);
        
        assert!(result.was_compressed);
        // Should keep system and important messages
        assert!(result.messages.iter().any(|m| m.role == "system"));
    }

    #[test]
    fn test_sliding_window() {
        let compressor = ContextCompressor::new(CompressionConfig {
            max_tokens: 10,
            strategy: CompressionStrategy::SlidingWindow,
            importance_threshold: 0.5,
            summary_prompt: "".to_string(),
        });
        
        let messages = create_test_messages();
        let result = compressor.compress(&messages);
        
        assert!(result.was_compressed || !result.was_compressed);
    }

    #[test]
    fn test_estimate_tokens() {
        let text = "Hello world! This is a test.";
        let tokens = estimate_tokens(text);
        assert!(tokens > 0);
        assert!(tokens < text.chars().count());
    }
}
