//! 安全与可观测性系统

use super::types::*;
use std::collections::{HashSet, HashMap};
use std::path::Path;
use std::sync::Arc;
use tokio::sync::{RwLock, Mutex};
use async_trait::async_trait;
use log::{info, warn};
use serde_json::json;
use chrono::Utc;

/// 安全策略
#[derive(Debug, Clone)]
pub struct SecurityPolicy {
    /// 权限级别
    pub level: PermissionLevel,
    /// 是否允许网络访问
    pub allow_network: bool,
    /// 是否允许文件系统访问
    pub allow_filesystem: bool,
    /// 是否允许系统调用
    pub allow_syscalls: bool,
    /// 文件系统权限
    pub filesystem_permissions: Vec<(String, FilePermission)>,
    /// 允许的网络地址
    pub allowed_network_addresses: Vec<String>,
}

impl Default for SecurityPolicy {
    fn default() -> Self {
        Self {
            level: PermissionLevel::Standard,
            allow_network: true,
            allow_filesystem: true,
            allow_syscalls: false,
            filesystem_permissions: vec![
                ("/workspace".to_string(), FilePermission::ReadWrite),
                ("/tmp".to_string(), FilePermission::ReadWrite),
            ],
            allowed_network_addresses: Vec::new(),
        }
    }
}

impl SecurityPolicy {
    pub fn builder() -> SecurityPolicyBuilder {
        SecurityPolicyBuilder::new()
    }

    pub async fn check_permission(&self, operation: SecurityOperation) -> Result<(), SecurityViolation> {
        match self.level {
            PermissionLevel::Unrestricted => Ok(()),
            PermissionLevel::Standard => self.check_standard_permission(operation).await,
            PermissionLevel::Restricted => self.check_restricted_permission(operation).await,
        }
    }

    async fn check_standard_permission(&self, operation: SecurityOperation) -> Result<(), SecurityViolation> {
        match operation {
            SecurityOperation::NetworkAccess(address) => {
                if self.allow_network {
                    Ok(())
                } else {
                    Err(SecurityViolation {
                        violation_type: SecurityViolationType::NetworkAccess,
                        message: format!("Network access to '{}' is not allowed in standard mode", address),
                        severity: SecuritySeverity::Medium,
                    })
                }
            }
            SecurityOperation::FileAccess(path) => {
                if self.allow_filesystem {
                    self.check_path_permission(&path).await
                } else {
                    Err(SecurityViolation {
                        violation_type: SecurityViolationType::PathAccess,
                        message: format!("File system access to '{}' is not allowed in standard mode", path),
                        severity: SecuritySeverity::High,
                    })
                }
            }
            SecurityOperation::SystemCall(syscall) => {
                if self.allow_syscalls {
                    Ok(())
                } else {
                    Err(SecurityViolation {
                        violation_type: SecurityViolationType::SystemCall,
                        message: format!("System call '{}' is not allowed in standard mode", syscall),
                        severity: SecuritySeverity::High,
                    })
                }
            }
        }
    }

    async fn check_restricted_permission(&self, operation: SecurityOperation) -> Result<(), SecurityViolation> {
        Err(SecurityViolation {
            violation_type: match operation {
                SecurityOperation::NetworkAccess(_) => SecurityViolationType::NetworkAccess,
                SecurityOperation::FileAccess(_) => SecurityViolationType::PathAccess,
                SecurityOperation::SystemCall(_) => SecurityViolationType::SystemCall,
            },
            message: format!("All operations are blocked in restricted mode"),
            severity: SecuritySeverity::Critical,
        })
    }

    async fn check_path_permission(&self, path: &str) -> Result<(), SecurityViolation> {
        let normalized_path = Path::new(path).to_str().unwrap_or(path);
        
        for (pattern, permission) in &self.filesystem_permissions {
            if normalized_path.starts_with(pattern) {
                if permission.can_read() {
                    return Ok(());
                }
            }
        }

        warn!("Path access violation: {}", normalized_path);
        Err(SecurityViolation {
            violation_type: SecurityViolationType::PathAccess,
            message: format!("Path '{}' is not allowed", normalized_path),
            severity: SecuritySeverity::Medium,
        })
    }

    pub fn get_info(&self) -> String {
        format!(
            "SecurityPolicy(level={:?}, net={}, fs={}, syscalls={})",
            self.level,
            self.allow_network,
            self.allow_filesystem,
            self.allow_syscalls
        )
    }
}

/// 安全策略构建器
pub struct SecurityPolicyBuilder {
    policy: SecurityPolicy,
}

impl SecurityPolicyBuilder {
    pub fn new() -> Self {
        Self {
            policy: SecurityPolicy::default(),
        }
    }

    pub fn permission_level(mut self, level: PermissionLevel) -> Self {
        self.policy.level = level;
        self
    }

    pub fn allow_network(mut self, allow: bool) -> Self {
        self.policy.allow_network = allow;
        self
    }

    pub fn allow_filesystem(mut self, allow: bool) -> Self {
        self.policy.allow_filesystem = allow;
        self
    }

    pub fn allow_syscalls(mut self, allow: bool) -> Self {
        self.policy.allow_syscalls = allow;
        self
    }

    pub fn build(mut self) -> SecurityPolicy {
        match self.policy.level {
            PermissionLevel::Unrestricted => {
                self.policy.allow_network = true;
                self.policy.allow_filesystem = true;
                self.policy.allow_syscalls = true;
            }
            PermissionLevel::Restricted => {
                self.policy.allow_network = false;
                self.policy.allow_filesystem = false;
                self.policy.allow_syscalls = false;
            }
            _ => (),
        }

        self.policy
    }
}

/// 文件系统权限
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FilePermission {
    None,
    Read,
    ReadWrite,
    All,
}

impl FilePermission {
    pub fn can_read(self) -> bool {
        matches!(self, FilePermission::Read | FilePermission::ReadWrite | FilePermission::All)
    }

    pub fn can_write(self) -> bool {
        matches!(self, FilePermission::ReadWrite | FilePermission::All)
    }

    pub fn can_execute(self) -> bool {
        self == FilePermission::All
    }
}

/// 安全操作
#[derive(Debug, Clone)]
pub enum SecurityOperation {
    NetworkAccess(String),
    FileAccess(String),
    SystemCall(String),
}

/// 安全违规
#[derive(Debug, Clone)]
pub struct SecurityViolation {
    pub violation_type: SecurityViolationType,
    pub message: String,
    pub severity: SecuritySeverity,
}

impl std::fmt::Display for SecurityViolation {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "[{}] {}", self.violation_type, self.message)
    }
}

impl std::error::Error for SecurityViolation {}

/// 安全违规类型
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SecurityViolationType {
    PathAccess,
    NetworkAccess,
    SystemCall,
    ResourceLimit,
    SandboxEscape,
}

impl std::fmt::Display for SecurityViolationType {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{:?}", self)
    }
}

/// 安全严重程度
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum SecuritySeverity {
    Low,
    Medium,
    High,
    Critical,
}

impl SecuritySeverity {
    pub fn to_color(&self) -> &'static str {
        match self {
            SecuritySeverity::Low => "blue",
            SecuritySeverity::Medium => "yellow",
            SecuritySeverity::High => "orange",
            SecuritySeverity::Critical => "red",
        }
    }
}

/// 安全沙箱管理器
#[derive(Debug)]
pub struct SandboxManager {
    sandboxes: Arc<RwLock<HashMap<AgentPid, SandboxConfig>>>,
    audit_log: Arc<Mutex<Vec<AuditLogEntry>>>,
}

impl SandboxManager {
    pub fn new() -> Self {
        Self {
            sandboxes: Arc::new(RwLock::new(HashMap::new())),
            audit_log: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub async fn create_sandbox(&self, pid: &str, policy: SecurityPolicy) {
        let mut sandboxes = self.sandboxes.write().await;
        sandboxes.insert(pid.to_string(), SandboxConfig { policy });
        info!("Created sandbox for {}", pid);
    }

    pub async fn get_sandbox(&self, pid: &str) -> Option<SandboxConfig> {
        let sandboxes = self.sandboxes.read().await;
        sandboxes.get(pid).cloned()
    }

    pub async fn check_operation(&self, pid: &str, operation: SecurityOperation) -> Result<(), SecurityViolation> {
        let sandboxes = self.sandboxes.read().await;

        if let Some(sandbox) = sandboxes.get(pid) {
            let result = sandbox.policy.check_permission(operation.clone()).await;
            
            if let Err(violation) = &result {
                self.log_audit(pid, operation, violation).await;
            }

            result
        } else {
            Ok(())
        }
    }

    async fn log_audit(&self, pid: &str, operation: SecurityOperation, violation: &SecurityViolation) {
        let mut audit_log = self.audit_log.lock().await;
        let action_type = match operation {
            SecurityOperation::NetworkAccess(_) => "network_access",
            SecurityOperation::FileAccess(_) => "file_access",
            SecurityOperation::SystemCall(_) => "system_call",
        };

        let log = AuditLogEntry {
            timestamp: Utc::now(),
            agent_pid: pid.to_string(),
            action_type: format!("security_violation:{}", action_type),
            input_data: json!({"operation": format!("{:?}", operation)}),
            output_data: json!({"violation": violation.message}),
            reasoning: None,
            duration_ms: 0,
        };

        audit_log.push(log);
        warn!("Security violation by {}: {}", pid, violation.message);
    }

    pub async fn get_audit_log(&self, pid: &str, limit: usize) -> Vec<AuditLogEntry> {
        let audit_log = self.audit_log.lock().await;
        audit_log.iter()
            .filter(|log| log.agent_pid == pid)
            .rev()
            .take(limit)
            .cloned()
            .collect()
    }
}

#[derive(Debug, Clone)]
pub struct SandboxConfig {
    pub policy: SecurityPolicy,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_security_policy_basic() {
        let policy = SecurityPolicy::builder()
            .permission_level(PermissionLevel::Standard)
            .allow_network(false)
            .allow_syscalls(false)
            .build();

        let result = policy.check_permission(SecurityOperation::NetworkAccess("api.example.com".to_string())).await;
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().severity, SecuritySeverity::Medium);
    }

    #[tokio::test]
    async fn test_unrestricted_policy() {
        let policy = SecurityPolicy::builder()
            .permission_level(PermissionLevel::Unrestricted)
            .build();

        let result = policy.check_permission(SecurityOperation::FileAccess("/etc/passwd".to_string())).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_restricted_policy() {
        let policy = SecurityPolicy::builder()
            .permission_level(PermissionLevel::Restricted)
            .build();

        let result = policy.check_permission(SecurityOperation::SystemCall("execve".to_string())).await;
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().severity, SecuritySeverity::Critical);
    }

    #[tokio::test]
    async fn test_sandbox_creation() {
        let manager = SandboxManager::new();
        let policy = SecurityPolicy::builder()
            .permission_level(PermissionLevel::Restricted)
            .build();

        let pid = "test-sandbox-1";
        manager.create_sandbox(pid, policy).await;

        let sandbox = manager.get_sandbox(pid).await;
        assert!(sandbox.is_some());
    }
}
