//! Agent 进程调度器

use super::types::*;
use super::context::ContextManager;
use super::storage::StorageManager;
use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use tokio::sync::Mutex;
use log::{info, warn};
use chrono::{DateTime, Utc};
use uuid::Uuid;

/// 调度策略
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchedulingPolicy {
    /// 优先级调度
    Priority,
    /// 时间片调度
    RoundRobin,
    /// 公平调度
    Fair,
    /// 截止时间调度
    Deadline,
}

/// 调度器配置
#[derive(Debug, Clone)]
pub struct SchedulerConfig {
    /// 调度策略
    pub policy: SchedulingPolicy,
    /// 默认时间片（毫秒）
    pub default_time_slice: u64,
    /// 最大待处理任务数
    pub max_pending_tasks: usize,
    /// 调度间隔（毫秒）
    pub scheduling_interval: u64,
    /// 抢占阈值（Token 数）
    pub preemption_threshold: u32,
}

impl Default for SchedulerConfig {
    fn default() -> Self {
        Self {
            policy: SchedulingPolicy::Priority,
            default_time_slice: 5000,
            max_pending_tasks: 100,
            scheduling_interval: 100,
            preemption_threshold: 10000,
        }
    }
}

/// 调度器状态
#[derive(Debug, Clone)]
pub struct SchedulerState {
    /// 就绪队列
    pub ready_queue: VecDeque<AgentPid>,
    /// 运行队列
    pub running_queue: Vec<AgentPid>,
    /// 等待队列
    pub waiting_queue: VecDeque<AgentPid>,
    /// 进程映射
    pub processes: HashMap<AgentPid, AgentProcess>,
    /// 资源使用统计
    pub resource_usage: HashMap<AgentPid, ResourceUsage>,
}

impl Default for SchedulerState {
    fn default() -> Self {
        Self {
            ready_queue: VecDeque::new(),
            running_queue: Vec::new(),
            waiting_queue: VecDeque::new(),
            processes: HashMap::new(),
            resource_usage: HashMap::new(),
        }
    }
}

/// 资源使用情况
#[derive(Debug, Clone)]
pub struct ResourceUsage {
    /// 累计 Token 数
    pub total_tokens: u64,
    /// 本次窗口 Token 数
    pub window_tokens: u64,
    /// API 调用次数
    pub api_calls: u64,
    /// 运行时间（毫秒）
    pub runtime_ms: u64,
    /// 最后活动时间
    pub last_active: DateTime<Utc>,
}

impl Default for ResourceUsage {
    fn default() -> Self {
        Self {
            total_tokens: 0,
            window_tokens: 0,
            api_calls: 0,
            runtime_ms: 0,
            last_active: Utc::now(),
        }
    }
}

/// 调度器
#[derive(Debug)]
pub struct AgentScheduler {
    /// 配置
    config: SchedulerConfig,
    /// 内部状态
    state: Arc<Mutex<SchedulerState>>,
    /// 上下文管理器
    context_manager: Arc<ContextManager>,
    /// 存储管理器
    storage_manager: Arc<StorageManager>,
}

impl AgentScheduler {
    /// 创建新调度器
    pub fn new(
        config: SchedulerConfig,
        context_manager: Arc<ContextManager>,
        storage_manager: Arc<StorageManager>,
    ) -> Self {
        Self {
            config,
            state: Arc::new(Mutex::new(SchedulerState::default())),
            context_manager,
            storage_manager,
        }
    }

    /// 添加进程
    pub async fn add_process(&self, process: AgentProcess) {
        let pid = process.pid.clone();
        let mut state = self.state.lock().await;
        state.processes.insert(pid.clone(), process);
        state.ready_queue.push_back(pid.clone());
        state.resource_usage.insert(pid.clone(), ResourceUsage::default());
        info!("Process added to ready queue: {}", pid);
    }

    /// 调度下一个进程
    pub async fn schedule(&self) -> Option<AgentProcess> {
        let mut state = self.state.lock().await;

        // 检查运行中的任务是否需要暂停
        self.check_preemption(&mut state).await;

        // 从就绪队列调度新任务
        if let Some(pid) = self.select_next_task(&mut state).await {
            let process = state.processes.get_mut(&pid).cloned();
            if let Some(mut process) = process {
                process.state = AgentState::Running;
                state.running_queue.push(pid.clone());
                return Some(process);
            }
        }

        None
    }

    /// 检查是否需要抢占
    async fn check_preemption(&self, state: &mut SchedulerState) {
        let mut to_suspend = Vec::new();

        for pid in &state.running_queue {
            if let Some(usage) = state.resource_usage.get(pid) {
                if usage.window_tokens > self.config.preemption_threshold as u64 {
                    to_suspend.push(pid.clone());
                }
            }
        }

        for pid in to_suspend {
            state.running_queue.retain(|p| p != &pid);
            state.ready_queue.push_back(pid.clone());
            if let Some(process) = state.processes.get_mut(&pid) {
                process.state = AgentState::Ready;
            }
            info!("Process preempted: {}", pid);
        }
    }

    /// 选择下一个任务
    async fn select_next_task(&self, state: &mut SchedulerState) -> Option<AgentPid> {
        match self.config.policy {
            SchedulingPolicy::Priority => self.select_priority_task(state),
            SchedulingPolicy::RoundRobin => self.select_round_robin_task(state),
            SchedulingPolicy::Fair => self.select_fair_task(state),
            SchedulingPolicy::Deadline => self.select_deadline_task(state),
        }
    }

    /// 优先级调度
    fn select_priority_task(&self, state: &mut SchedulerState) -> Option<AgentPid> {
        let mut selected_index = None;
        let mut max_priority = 0;

        for (i, pid) in state.ready_queue.iter().enumerate() {
            if let Some(process) = state.processes.get(pid) {
                if process.priority > max_priority {
                    max_priority = process.priority;
                    selected_index = Some(i);
                }
            }
        }

        selected_index.map(|i| state.ready_queue.remove(i).unwrap())
    }

    /// 时间片调度
    fn select_round_robin_task(&self, state: &mut SchedulerState) -> Option<AgentPid> {
        state.ready_queue.pop_front()
    }

    /// 公平调度
    fn select_fair_task(&self, state: &mut SchedulerState) -> Option<AgentPid> {
        let mut selected_index = None;
        let mut min_usage = u64::MAX;

        for (i, pid) in state.ready_queue.iter().enumerate() {
            if let Some(usage) = state.resource_usage.get(pid) {
                if usage.total_tokens < min_usage {
                    min_usage = usage.total_tokens;
                    selected_index = Some(i);
                }
            }
        }

        selected_index.map(|i| state.ready_queue.remove(i).unwrap())
    }

    /// 截止时间调度（简单实现）
    fn select_deadline_task(&self, state: &mut SchedulerState) -> Option<AgentPid> {
        let mut selected_index = None;
        let earliest_time: DateTime<Utc> = Utc::now();

        for (i, pid) in state.ready_queue.iter().enumerate() {
            if let Some(_process) = state.processes.get(pid) {
                let created = Utc::now().timestamp() - 60;
                let task_time = chrono::DateTime::from_timestamp(created, 0).unwrap_or(Utc::now());

                if task_time < earliest_time {
                    selected_index = Some(i);
                }
            }
        }

        selected_index.map(|i| state.ready_queue.remove(i).unwrap())
    }

    /// 请求资源
    pub async fn request_resources(&self, pid: &str, tokens_needed: usize) -> bool {
        let mut state = self.state.lock().await;

        if let Some(usage) = state.resource_usage.get_mut(pid) {
            let new_usage = usage.window_tokens + tokens_needed as u64;

            if new_usage <= self.config.preemption_threshold as u64 {
                usage.window_tokens += tokens_needed as u64;
                usage.total_tokens += tokens_needed as u64;
                usage.api_calls += 1;
                usage.last_active = Utc::now();
                return true;
            }
        }

        warn!("Resource request rejected for {} - quota exceeded", pid);
        false
    }

    /// 暂停进程（创建检查点）
    pub async fn suspend_process(&self, pid: &str, create_checkpoint: bool) -> Option<CheckpointId> {
        let mut state = self.state.lock().await;

        // First, check if the process exists and is in a valid state
        let can_suspend = if let Some(process) = state.processes.get(pid) {
            process.state == AgentState::Running || process.state == AgentState::Ready
        } else {
            false
        };

        if can_suspend {
            // Now update the process state
            if let Some(process) = state.processes.get_mut(pid) {
                process.state = AgentState::Suspended;
            }

            state.running_queue.retain(|p| p != pid);
            state.ready_queue.retain(|p| p != pid);

            if let Some(pos) = state.waiting_queue.iter().position(|p| p == pid) {
                state.waiting_queue.remove(pos);
            }

            state.waiting_queue.push_back(pid.to_string());

            if create_checkpoint {
                let checkpoint_id = Uuid::new_v4();
                if let Some(process) = state.processes.get_mut(pid) {
                    process.checkpoint_id = Some(checkpoint_id);
                }
                info!("Created checkpoint for {}: {}", pid, checkpoint_id);
                return Some(checkpoint_id);
            }
        }

        None
    }

    /// 等待进程
    pub async fn wait_process(&self, pid: &str, reason: &str) {
        let mut state = self.state.lock().await;

        if let Some(process) = state.processes.get_mut(pid) {
            process.state = AgentState::Waiting;
            info!("Process {} waiting for: {}", pid, reason);
        }
    }

    /// 终止进程
    pub async fn terminate_process(&self, pid: &str, reason: &str) {
        let mut state = self.state.lock().await;

        if let Some(process) = state.processes.get_mut(pid) {
            process.state = AgentState::Terminated;
            state.running_queue.retain(|p| p != pid);
            state.ready_queue.retain(|p| p != pid);
            state.waiting_queue.retain(|p| p != pid);
            info!("Process terminated: {} ({})", pid, reason);
        }
    }

    /// 恢复进程
    pub async fn resume_process(&self, pid: &str) {
        let mut state = self.state.lock().await;

        if let Some(process) = state.processes.get_mut(pid) {
            if process.state == AgentState::Suspended || process.state == AgentState::Waiting {
                process.state = AgentState::Ready;

                if let Some(pos) = state.waiting_queue.iter().position(|p| p == pid) {
                    state.waiting_queue.remove(pos);
                }

                state.ready_queue.push_back(pid.to_string());
                info!("Process resumed: {}", pid);
            }
        }
    }

    /// 获取进程统计信息
    pub async fn get_process_stats(&self) -> serde_json::Value {
        let state = self.state.lock().await;

        serde_json::json!({
            "running": state.running_queue.first().map(|pid| state.processes.get(pid).map(|p| p.name.clone())),
            "ready_queue_size": state.ready_queue.len(),
            "waiting_queue_size": state.waiting_queue.len(),
            "total_processes": state.processes.len(),
            "active_processes": state.processes.values().filter(|p| p.is_active()).count(),
        })
    }

    /// 获取调度器状态（内部方法，供外部使用）
    pub async fn get_state(&self) -> SchedulerState {
        let state = self.state.lock().await;
        state.clone()
    }

    /// 清理超时的窗口统计
    pub async fn clear_window_usage(&self) {
        let mut state = self.state.lock().await;
        for usage in state.resource_usage.values_mut() {
            usage.window_tokens = 0;
        }
    }
}

impl Default for AgentScheduler {
    fn default() -> Self {
        let context = Arc::new(ContextManager::default());
        let storage = Arc::new(StorageManager::default());

        Self::new(SchedulerConfig::default(), context, storage)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_scheduler_basic() {
        let context = Arc::new(ContextManager::default());
        let storage = Arc::new(StorageManager::default());
        let scheduler = AgentScheduler::new(SchedulerConfig::default(), context, storage);

        let pid = "test-process-1".to_string();
        let process = AgentProcess::new(pid.clone(), "Test Process", 50);

        scheduler.add_process(process).await;

        let scheduled = scheduler.schedule().await;
        assert!(scheduled.is_some());
        assert_eq!(scheduled.unwrap().pid, pid);
    }

    #[tokio::test]
    async fn test_preemption() {
        let context = Arc::new(ContextManager::default());
        let storage = Arc::new(StorageManager::default());
        let config = SchedulerConfig {
            policy: SchedulingPolicy::Priority,
            default_time_slice: 5000,
            max_pending_tasks: 100,
            scheduling_interval: 100,
            preemption_threshold: 10_000,
        };

        let scheduler = AgentScheduler::new(config, context, storage);

        let pid1 = "test-preempt-1".to_string();
        scheduler.add_process(AgentProcess::new(pid1, "High Priority", 90)).await;

        let pid2 = "test-preempt-2".to_string();
        scheduler.add_process(AgentProcess::new(pid2, "Low Priority", 30)).await;

        let first_scheduled = scheduler.schedule().await;
        assert!(first_scheduled.is_some());
        assert_eq!(first_scheduled.unwrap().priority, 90);
    }
}
