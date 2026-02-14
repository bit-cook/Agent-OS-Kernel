use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

use super::base::Tool;

pub struct ToolRegistry {
    tools: Arc<RwLock<HashMap<String, Arc<dyn Tool + Send + Sync>>>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn register(&self, tool: Arc<dyn Tool + Send + Sync>) {
        let mut tools = self.tools.write().await;
        tools.insert(tool.name().to_string(), tool);
    }

    pub async fn get(&self, name: &str) -> Option<Arc<dyn Tool + Send + Sync>> {
        let tools = self.tools.read().await;
        tools.get(name).cloned()
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Debug for ToolRegistry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ToolRegistry")
            .field("tools", &"<... >")
            .finish()
    }
}
