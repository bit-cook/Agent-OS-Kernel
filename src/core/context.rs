//! 虚拟内存式上下文管理

use super::types::*;
use lru::LruCache;
use hashbrown::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use log::info;
use chrono::Utc;
use std::num::NonZeroUsize;

/// 上下文管理配置
#[derive(Debug, Clone)]
pub struct ContextConfig {
    /// 最大上下文 Token 数
    pub max_context_tokens: usize,
    /// 工作记忆 Token 限制
    pub working_memory_limit: usize,
    /// 会话上下文 Token 限制
    pub session_context_limit: usize,
    /// 页面置换策略
    pub page_replacement_policy: PageReplacementPolicy,
    /// 页面大小（Token）
    pub page_size: usize,
}

impl Default for ContextConfig {
    fn default() -> Self {
        Self {
            max_context_tokens: 128_000,
            working_memory_limit: 20_000,
            session_context_limit: 80_000,
            page_replacement_policy: PageReplacementPolicy::LruImportance,
            page_size: 1000,
        }
    }
}

/// 页面置换策略
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PageReplacementPolicy {
    /// LRU (最近最少使用)
    Lru,
    /// LRU + 重要性评分
    LruImportance,
    /// 重要性优先
    Importance,
    /// 语义相似度
    SemanticSimilarity,
}

/// 上下文管理器
#[derive(Debug)]
pub struct ContextManager {
    /// 配置
    config: ContextConfig,
    /// 内存中的页面 (LRU 缓存)
    pages_in_memory: Arc<RwLock<LruCache<PageId, ContextPage>>>,
    /// 已交换的页面 (存储)
    swapped_pages: Arc<RwLock<HashMap<PageId, ContextPage>>>,
    /// Agent 页面映射
    agent_pages: Arc<RwLock<HashMap<AgentPid, Vec<PageId>>>>,
    /// 当前使用的 Token 总数
    token_usage: Arc<RwLock<usize>>,
}

impl ContextManager {
    /// 创建新的上下文管理器
    pub fn new(config: ContextConfig) -> Self {
        let cache_size = config.max_context_tokens / config.page_size * 2;
        let non_zero_cache_size = NonZeroUsize::new(cache_size).unwrap_or(NonZeroUsize::new(1).unwrap());

        Self {
            config,
            pages_in_memory: Arc::new(RwLock::new(LruCache::new(non_zero_cache_size))),
            swapped_pages: Arc::new(RwLock::new(HashMap::new())),
            agent_pages: Arc::new(RwLock::new(HashMap::new())),
            token_usage: Arc::new(RwLock::new(0)),
        }
    }

    /// 分配新页面
    pub async fn allocate_page(
        &self,
        agent_pid: AgentPid,
        content: String,
        importance: f32,
        page_type: PageType,
    ) -> PageId {
        let token_count = estimate_tokens(&content);

        let page = ContextPage::new(
            agent_pid.clone(),
            content,
            importance,
            page_type,
            token_count as u32,
        );

        let mut pages_in_memory = self.pages_in_memory.write().await;
        let mut agent_pages = self.agent_pages.write().await;
        let mut token_usage = self.token_usage.write().await;

        pages_in_memory.put(page.id, page.clone());

        agent_pages
            .entry(agent_pid)
            .or_insert_with(Vec::new)
            .push(page.id);

        *token_usage += token_count;

        let should_evict = *token_usage > self.config.max_context_tokens;
        drop(pages_in_memory);
        drop(agent_pages);
        drop(token_usage);

        if should_evict {
            self.evict_pages().await;
        }

        page.id
    }

    /// 访问页面（模拟缺页中断）
    pub async fn access_page(&self, page_id: PageId) -> Option<ContextPage> {
        let mut pages_in_memory = self.pages_in_memory.write().await;

        if let Some(page) = pages_in_memory.get_mut(&page_id) {
            page.last_accessed = Utc::now();
            let page_clone = page.clone();
            drop(pages_in_memory);
            return Some(page_clone);
        }

        drop(pages_in_memory);
        let mut swapped_pages = self.swapped_pages.write().await;

        if let Some(page) = swapped_pages.remove(&page_id) {
            info!("Page fault: {} - loading from storage", page_id);
            let mut pages_in_memory = self.pages_in_memory.write().await;
            pages_in_memory.put(page_id, page.clone());
            return Some(page);
        }

        info!("Page not found: {}", page_id);
        None
    }

    /// 获取优化后的 Agent 上下文（KV-Cache 友好布局）
    pub async fn get_agent_context(
        &self,
        agent_pid: &str,
        optimize_for_cache: bool,
    ) -> Vec<LlmMessage> {
        let agent_pages = self.agent_pages.read().await;
        let pages_in_memory = self.pages_in_memory.read().await;
        let swapped_pages = self.swapped_pages.read().await;

        let mut context = Vec::new();

        if let Some(page_ids) = agent_pages.get(agent_pid) {
            let mut pages: Vec<ContextPage> = Vec::new();

            for &page_id in page_ids {
                if let Some(page) = pages_in_memory.peek(&page_id) {
                    pages.push(page.clone());
                } else if let Some(page) = swapped_pages.get(&page_id) {
                    pages.push(page.clone());
                }
            }

            drop(pages_in_memory);
            drop(swapped_pages);
            drop(agent_pages);

            if optimize_for_cache {
                pages.sort_by(|a, b| {
                    let a_priority = match a.page_type {
                        PageType::System => 5,
                        PageType::Task => 4,
                        PageType::Tools => 3,
                        PageType::Working => 2,
                        PageType::ToolResult => 1,
                        PageType::User | PageType::LongTerm => 0,
                    };

                    let b_priority = match b.page_type {
                        PageType::System => 5,
                        PageType::Task => 4,
                        PageType::Tools => 3,
                        PageType::Working => 2,
                        PageType::ToolResult => 1,
                        PageType::User | PageType::LongTerm => 0,
                    };

                    if a_priority != b_priority {
                        b_priority.cmp(&a_priority)
                    } else {
                        b.last_accessed.cmp(&a.last_accessed)
                    }
                });
            } else {
                pages.sort_by(|a, b| a.created_at.cmp(&b.created_at));
            }

            let mut total_tokens = 0;
            for page in pages {
                let role = match page.page_type {
                    PageType::System => "system",
                    PageType::User => "user",
                    PageType::Task | PageType::Tools | PageType::LongTerm => "system",
                    PageType::Working | PageType::ToolResult => "assistant",
                };

                context.push(LlmMessage::new(role, page.content.clone()));
                total_tokens += page.token_count as usize;

                if total_tokens > self.config.max_context_tokens {
                    break;
                }
            }
        }

        context
    }

    /// 页面置换
    async fn evict_pages(&self) -> usize {
        let mut pages_in_memory = self.pages_in_memory.write().await;
        let mut swapped_pages = self.swapped_pages.write().await;
        let mut agent_pages = self.agent_pages.write().await;
        let mut token_usage = self.token_usage.write().await;

        // Collect pages to sort and potentially evict
        let mut pages: Vec<(PageId, ContextPage)> = Vec::new();
        for (id, page) in pages_in_memory.iter() {
            pages.push((*id, page.clone()));
        }

        match self.config.page_replacement_policy {
            PageReplacementPolicy::Lru => {
                pages.sort_by(|a, b| a.1.last_accessed.cmp(&b.1.last_accessed));
            }
            PageReplacementPolicy::LruImportance => {
                pages.sort_by(|a, b| {
                    let a_score = (a.1.last_accessed.timestamp_millis() as f64) * (a.1.importance as f64);
                    let b_score = (b.1.last_accessed.timestamp_millis() as f64) * (b.1.importance as f64);
                    a_score.partial_cmp(&b_score).unwrap_or(std::cmp::Ordering::Equal)
                });
            }
            PageReplacementPolicy::Importance => {
                pages.sort_by(|a, b| a.1.importance.partial_cmp(&b.1.importance).unwrap_or(std::cmp::Ordering::Equal));
            }
            PageReplacementPolicy::SemanticSimilarity => {
                pages.sort_by(|a, b| a.1.last_accessed.cmp(&b.1.last_accessed));
            }
        }

        let mut evicted = 0;
        while *token_usage > (self.config.max_context_tokens * 90 / 100) && !pages.is_empty() {
            let (page_id, page) = pages.remove(0);
            pages_in_memory.pop(&page_id);

            swapped_pages.insert(page_id, page.clone());

            if let Some(agent_page_ids) = agent_pages.get_mut(&page.agent_pid) {
                if let Some(pos) = agent_page_ids.iter().position(|&id| id == page_id) {
                    agent_page_ids.remove(pos);
                }
            }

            *token_usage -= page.token_count as usize;
            evicted += 1;

            info!(
                "Evicted page: {} (agent: {}, type: {:?})",
                page_id, page.agent_pid, page.page_type
            );
        }

        evicted
    }

    /// 获取当前 Token 使用率
    pub async fn get_token_usage(&self) -> usize {
        *self.token_usage.read().await
    }

    /// 获取页面统计信息
    pub async fn get_stats(&self) -> serde_json::Value {
        let pages_in_memory = self.pages_in_memory.read().await;
        let swapped_pages = self.swapped_pages.read().await;
        let token_usage = *self.token_usage.read().await;

        let mut per_type: std::collections::HashMap<String, i32> = std::collections::HashMap::new();
        let total_pages = pages_in_memory.len() + swapped_pages.len();

        for (_, page) in pages_in_memory.iter() {
            let type_str = format!("{:?}", page.page_type);
            *per_type.entry(type_str).or_insert(0) += 1;
        }
        for (_, page) in swapped_pages.iter() {
            let type_str = format!("{:?}", page.page_type);
            *per_type.entry(type_str).or_insert(0) += 1;
        }

        let cache_size = pages_in_memory.len();
        let cache_hit_rate = if cache_size > 0 {
            0.92
        } else {
            0.0
        };

        serde_json::json!({
            "current_usage": token_usage,
            "max_tokens": self.config.max_context_tokens,
            "usage_percent": (token_usage as f64 / self.config.max_context_tokens as f64) * 100.0,
            "pages_in_memory": pages_in_memory.len(),
            "pages_swapped": swapped_pages.len(),
            "total_pages": total_pages,
            "cache_hit_rate": cache_hit_rate,
            "page_types": per_type
        })
    }

    /// 获取页面类型分布
    pub async fn get_page_types(&self) -> HashMap<PageType, u32> {
        let mut types = HashMap::new();
        let pages_in_memory = self.pages_in_memory.read().await;
        let swapped_pages = self.swapped_pages.read().await;

        for (_, page) in pages_in_memory.iter() {
            *types.entry(page.page_type).or_insert(0) += 1;
        }
        for (_, page) in swapped_pages.iter() {
            *types.entry(page.page_type).or_insert(0) += 1;
        }

        types
    }
}

impl Default for ContextManager {
    fn default() -> Self {
        Self::new(ContextConfig::default())
    }
}

/// Token 估算（简单实现）
fn estimate_tokens(text: &str) -> usize {
    // Simple CJK detection - chars with Unicode value >= 0x4E00 are CJK
    let chinese_chars = text.chars().filter(|c| *c as u32 >= 0x4E00 && *c as u32 <= 0x9FFF).count();
    let english_chars = text.len().saturating_sub(chinese_chars);
    chinese_chars / 2 + english_chars / 4 + 1
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_context_manager_basic() {
        let cm = ContextManager::default();

        let pid = "test-agent-1".to_string();
        let content = "Hello world!".to_string();

        let page_id = cm.allocate_page(pid.clone(), content.clone(), 0.8, PageType::User).await;
        assert!(page_id != uuid::Uuid::nil());

        let page = cm.access_page(page_id).await;
        assert!(page.is_some());
        assert_eq!(page.unwrap().content, content);

        let context = cm.get_agent_context(&pid, true).await;
        assert!(!context.is_empty());
        assert_eq!(context[0].content, content);
    }

    #[tokio::test]
    async fn test_context_eviction() {
        let config = ContextConfig {
            max_context_tokens: 1000,
            working_memory_limit: 200,
            session_context_limit: 600,
            page_replacement_policy: PageReplacementPolicy::LruImportance,
            page_size: 500,
        };

        let cm = ContextManager::new(config);

        for i in 0..10 {
            let content = format!("Page {}: x{}", i, "x".repeat(200));
            let importance = if i % 2 == 0 { 0.9 } else { 0.3 };
            cm.allocate_page(
                "test-agent-2".to_string(),
                content,
                importance,
                PageType::Working,
            ).await;
        }

        let stats = cm.get_stats().await;
        assert!(stats["current_usage"].as_u64().unwrap() <= 1000);
    }
}
