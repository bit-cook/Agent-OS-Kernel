// 缓存工具
use std::collections::HashMap;

pub trait Cache {
    fn get(&self, key: &str) -> Option<serde_json::Value>;
    fn set(&mut self, key: &str, value: serde_json::Value);
    fn remove(&mut self, key: &str);
}

pub struct SimpleCache {
    cache: HashMap<String, serde_json::Value>,
}

impl SimpleCache {
    pub fn new() -> Self {
        Self { cache: HashMap::new() }
    }
}

impl Cache for SimpleCache {
    fn get(&self, key: &str) -> Option<serde_json::Value> {
        self.cache.get(key).cloned()
    }

    fn set(&mut self, key: &str, value: serde_json::Value) {
        self.cache.insert(key.to_string(), value);
    }

    fn remove(&mut self, key: &str) {
        self.cache.remove(key);
    }
}
