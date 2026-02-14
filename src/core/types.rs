//! 核心数据类型

use serde::Serialize;
use serde::Deserialize;
use uuid::Uuid;
use chrono::{DateTime, Utc};

/// Agent PID
pub type AgentPid = String;

/// 页面 ID
pub type PageId = Uuid;

/// 检查点 ID
pub type CheckpointId = Uuid;

/// 工具名称
pub type ToolName = String;

/// Agent 优先级
pub type Priority = u8;

/// 资源配额配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceQuota {
    /// 每时间窗口的最大 Token 数
    pub max_tokens_per_window: u64,
    /// 每时间窗口的最大 API 调用数
    pub max_api_calls_per_window: u32,
    /// 最大内存使用 (MB)
    pub max_memory_mb: u32,
    /// 最大 CPU 使用率 (%)
    pub max_cpu_percent: u8,
}

impl Default for ResourceQuota {
    fn default() -> Self {
        Self {
            max_tokens_per_window: 100_000,
            max_api_calls_per_window: 1000,
            max_memory_mb: 512,
            max_cpu_percent: 50,
        }
    }
}

/// 安全策略级别
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum PermissionLevel {
    /// 受限沙箱模式
    Restricted,
    /// 标准模式
    Standard,
    /// 完全访问模式
    Unrestricted,
}

impl Default for PermissionLevel {
    fn default() -> Self {
        Self::Standard
    }
}

/// 安全策略
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityPolicy {
    /// 权限级别
    pub permission_level: PermissionLevel,
    /// 最大内存使用 (MB)
    pub max_memory_mb: u32,
    /// 最大 CPU 使用率 (%)
    pub max_cpu_percent: u8,
    /// 允许访问的路径
    pub allowed_paths: Vec<String>,
    /// 阻止访问的路径
    pub blocked_paths: Vec<String>,
    /// 是否允许网络访问
    pub network_enabled: bool,
}

impl Default for SecurityPolicy {
    fn default() -> Self {
        Self {
            permission_level: PermissionLevel::Standard,
            max_memory_mb: 512,
            max_cpu_percent: 50,
            allowed_paths: vec!["/workspace".to_string()],
            blocked_paths: vec!["/etc".to_string(), "/root".to_string()],
            network_enabled: false,
        }
    }
}

/// 页面状态
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum PageStatus {
    /// 在内存中
    InMemory,
    /// 已交换到存储
    Swapped,
    /// 待加载
    Loading,
}

/// 上下文页面类型
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum PageType {
    /// 系统提示
    System,
    /// 用户输入
    User,
    /// 工作记忆
    Working,
    /// 长期记忆
    LongTerm,
    /// 工具结果
    ToolResult,
    /// 任务描述
    Task,
    /// 工具定义
    Tools,
}

/// 上下文页面
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextPage {
    /// 页面 ID
    pub id: PageId,
    /// Agent PID
    pub agent_pid: AgentPid,
    /// 内容
    pub content: String,
    /// 重要性评分 (0.0 - 1.0)
    pub importance: f32,
    /// 页面类型
    pub page_type: PageType,
    /// 访问时间
    pub last_accessed: DateTime<Utc>,
    /// 创建时间
    pub created_at: DateTime<Utc>,
    /// Token 数量
    pub token_count: u32,
    /// 状态
    pub status: PageStatus,
}

impl ContextPage {
    pub fn new(
        agent_pid: AgentPid,
        content: String,
        importance: f32,
        page_type: PageType,
        token_count: u32,
    ) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            agent_pid,
            content,
            importance: importance.clamp(0.0, 1.0),
            page_type,
            last_accessed: now,
            created_at: now,
            token_count,
            status: PageStatus::InMemory,
        }
    }
}

/// LLM 消息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmMessage {
    /// 角色
    pub role: String,
    /// 内容
    pub content: String,
    /// 时间戳
    pub timestamp: DateTime<Utc>,
}

impl LlmMessage {
    pub fn new(role: &str, content: String) -> Self {
        Self {
            role: role.to_string(),
            content,
            timestamp: Utc::now(),
        }
    }
}

/// 审计日志条目
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditLogEntry {
    /// 时间戳
    pub timestamp: DateTime<Utc>,
    /// Agent PID
    pub agent_pid: AgentPid,
    /// 操作类型
    pub action_type: String,
    /// 输入数据
    pub input_data: serde_json::Value,
    /// 输出数据
    pub output_data: serde_json::Value,
    /// 推理过程
    pub reasoning: Option<String>,
    /// 持续时间 (毫秒)
    pub duration_ms: u64,
}

impl AuditLogEntry {
    pub fn new(
        agent_pid: AgentPid,
        action_type: String,
        input_data: serde_json::Value,
        output_data: serde_json::Value,
        reasoning: Option<String>,
        duration_ms: u64,
    ) -> Self {
        Self {
            timestamp: Utc::now(),
            agent_pid,
            action_type,
            input_data,
            output_data,
            reasoning,
            duration_ms,
        }
    }
}

/// 任务状态
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    /// 待处理
    Pending,
    /// 运行中
    Running,
    /// 暂停
    Suspended,
    /// 完成
    Completed,
    /// 失败
    Failed,
    /// 被取消
    Canceled,
}

/// 进程状态
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum AgentState {
    /// 就绪状态
    Ready,
    /// 运行中
    Running,
    /// 等待资源
    Waiting,
    /// 已暂停
    Suspended,
    /// 已完成
    Completed,
    /// 已终止
    Terminated,
}

/// 任务信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskInfo {
    /// Agent PID
    pub agent_pid: AgentPid,
    /// 任务名称
    pub name: String,
    /// 任务描述
    pub task: String,
    /// 状态
    pub status: TaskStatus,
    /// 优先级
    pub priority: Priority,
    /// 创建时间
    pub created_at: DateTime<Utc>,
    /// 最后运行时间
    pub last_run_at: Option<DateTime<Utc>>,
    /// 完成时间
    pub completed_at: Option<DateTime<Utc>>,
}

/// Agent 进程
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentProcess {
    /// PID
    pub pid: AgentPid,
    /// 名称
    pub name: String,
    /// 优先级
    pub priority: Priority,
    /// 状态
    pub state: AgentState,
    /// 上下文
    pub context: serde_json::Value,
    /// 错误计数
    pub error_count: u32,
    /// 最后错误
    pub last_error: Option<String>,
    /// 最大错误数
    pub max_errors: u32,
    /// 检查点 ID
    pub checkpoint_id: Option<CheckpointId>,
}

impl AgentProcess {
    pub fn new(pid: AgentPid, name: String, priority: Priority) -> Self {
        Self {
            pid,
            name,
            priority,
            state: AgentState::Ready,
            context: serde_json::json!({}),
            error_count: 0,
            last_error: None,
            max_errors: 3,
            checkpoint_id: None,
        }
    }

    pub fn is_active(&self) -> bool {
        matches!(self.state, AgentState::Ready | AgentState::Running | AgentState::Waiting)
    }
}

/// 内核统计信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KernelStats {
    /// 版本
    pub version: String,
    /// 启动时间
    pub start_time: f64,
    /// 总 Agent 数
    pub total_agents: u32,
    /// 活跃 Agent 数
    pub active_agents: u32,
    /// 总迭代次数
    pub total_iterations: u64,
    /// 总 Token 消耗
    pub total_tokens: u64,
    /// 总 API 调用数
    pub total_api_calls: u64,
    /// 平均缓存命中率
    pub avg_cache_hit_rate: f32,
}

impl Default for KernelStats {
    fn default() -> Self {
        Self {
            version: "0.2.0".to_string(),
            start_time: 0.0,
            total_agents: 0,
            active_agents: 0,
            total_iterations: 0,
            total_tokens: 0,
            total_api_calls: 0,
            avg_cache_hit_rate: 0.0,
        }
    }
}

/// 系统状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemStatus {
    /// 活跃 Agent 数量
    pub active_agents: usize,
    /// 总内存使用
    pub total_memory_usage: u64,
    /// 总 Token 消耗
    pub total_token_consumption: u64,
    /// 系统负载
    pub system_load: f32,
    /// 任务队列长度
    pub task_queue_length: usize,
}

/// 检查点信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckpointInfo {
    /// 检查点 ID
    pub id: CheckpointId,
    /// Agent PID
    pub agent_pid: AgentPid,
    /// 描述
    pub description: String,
    /// 创建时间
    pub created_at: DateTime<Utc>,
    /// 包含的页面数
    pub page_count: u32,
    /// 进程状态
    pub process_state: serde_json::Value,
}
