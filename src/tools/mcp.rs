//! MCP (Model Context Protocol) Client Module
//!
//! Provides MCP client functionality for tool registration and execution

use serde::{Serialize, Deserialize};
use serde_json::Value;
use std::collections::HashMap;
use std::path::PathBuf;
use log::info;

/// MCP Tool definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpTool {
    /// Tool name
    pub name: String,
    /// Tool description
    pub description: String,
    /// Input schema (JSON Schema)
    pub input_schema: Value,
}

/// MCP Client configuration
#[derive(Debug, Clone)]
pub struct McpClientConfig {
    /// MCP server command
    pub command: String,
    /// Command arguments
    pub args: Vec<String>,
    /// Working directory
    pub cwd: Option<PathBuf>,
    /// Environment variables
    pub env: HashMap<String, String>,
    /// Timeout for requests (seconds)
    pub timeout_seconds: u64,
}

impl Default for McpClientConfig {
    fn default() -> Self {
        Self {
            command: "uvx".to_string(),
            args: vec!["mcp-server-fetch".to_string()],
            cwd: None,
            env: HashMap::new(),
            timeout_seconds: 30,
        }
    }
}

/// MCP Server information
#[derive(Debug, Clone)]
pub struct McpServer {
    /// Server name
    pub name: String,
    /// Command being run
    pub command: String,
    /// Process ID (if running)
    pub pid: Option<u32>,
    /// Whether it's connected
    pub connected: bool,
}

/// MCP Client
#[derive(Debug)]
pub struct McpClient {
    /// Server configurations
    pub servers: HashMap<String, McpServer>,
    /// Available tools
    pub tools: HashMap<String, McpTool>,
}

impl McpClient {
    /// Create new MCP client
    pub fn new() -> Self {
        Self {
            servers: HashMap::new(),
            tools: HashMap::new(),
        }
    }

    /// Add a server
    pub fn add_server(&mut self, name: &str, command: &str) {
        self.servers.insert(
            name.to_string(),
            McpServer {
                name: name.to_string(),
                command: command.to_string(),
                pid: None,
                connected: false,
            },
        );
        info!("Added MCP server: {}", name);
    }

    /// Register a tool
    pub fn register_tool(&mut self, tool: McpTool) {
        self.tools.insert(tool.name.clone(), tool.clone());
        info!("Registered MCP tool: {}", tool.name);
    }

    /// List available tools
    pub fn list_tools(&self) -> Vec<&McpTool> {
        self.tools.values().collect()
    }
}

impl crate::tools::Tool for McpClient {
    fn name(&self) -> &'static str {
        "mcp_client"
    }
    
    fn description(&self) -> &'static str {
        "MCP (Model Context Protocol) client for tool registration"
    }
    
    fn run(&self, _params: Value) -> Result<Value, String> {
        let tools: Vec<Value> = self.tools.values()
            .map(|t| serde_json::json!({
                "name": t.name,
                "description": t.description
            }))
            .collect();
        
        Ok(serde_json::json!({
            "status": "ok",
            "server_count": self.servers.len(),
            "tool_count": self.tools.len(),
            "tools": tools
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tools::Tool;

    #[test]
    fn test_mcp_client_creation() {
        let client = McpClient::new();
        assert_eq!(client.tools.len(), 0);
        assert_eq!(client.servers.len(), 0);
    }

    #[test]
    fn test_register_tool() {
        let mut client = McpClient::new();
        
        let tool = McpTool {
            name: "test_tool".to_string(),
            description: "A test tool".to_string(),
            input_schema: serde_json::json!({
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }),
        };
        
        client.register_tool(tool);
        assert_eq!(client.tools.len(), 1);
        assert!(client.tools.contains_key("test_tool"));
    }

    #[test]
    fn test_run() {
        let mut client = McpClient::new();
        client.add_server("test_server", "uvx mcp-server-fetch");
        
        let result = client.run(serde_json::json!({}));
        assert!(result.is_ok());
        let value = result.unwrap();
        assert_eq!(value["server_count"], 1);
        assert_eq!(value["tool_count"], 0);
    }
}
