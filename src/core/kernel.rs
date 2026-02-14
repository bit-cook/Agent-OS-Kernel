use super::types::*;
use super::context::ContextManager;
use super::scheduler::AgentScheduler;
use super::storage::StorageManager;
use super::security::{SecurityPolicy, SandboxManager};
use std::sync::Arc;
use tokio::sync::RwLock;
use log::info;
use tokio::time::Duration;
use chrono::Utc;

#[derive(Debug, Clone, PartialEq)]
pub enum KernelState {
    Initializing,
    Running,
    Paused,
    ShuttingDown,
    Shutdown,
}

#[derive(Debug, Clone)]
pub struct KernelConfig {
    pub max_context_tokens: usize,
    pub time_slice: u64,
    pub enable_sandbox: bool,
}

impl Default for KernelConfig {
    fn default() -> Self {
        Self {
            max_context_tokens: 128_000,
            time_slice: 60_000,
            enable_sandbox: false,
        }
    }
}

#[derive(Debug, Clone)]
pub struct KernelStats {
    pub version: String,
    pub start_time: f64,
    pub total_agents: u32,
    pub active_agents: u32,
    pub total_iterations: u64,
    pub total_tokens: u64,
    pub total_api_calls: u64,
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

#[derive(Debug)]
pub struct AgentOSKernel {
    state: Arc<RwLock<KernelState>>,
    config: KernelConfig,
    context_manager: Arc<ContextManager>,
    scheduler: Arc<AgentScheduler>,
    storage_manager: Arc<StorageManager>,
    security: Option<Arc<SandboxManager>>,
    stats: Arc<RwLock<KernelStats>>,
    running: Arc<RwLock<bool>>,
}

impl AgentOSKernel {
    pub async fn new(config: KernelConfig) -> Result<Self, Box<dyn std::error::Error>> {
        info!("Initializing Agent OS Kernel v0.2.0");
        info!("==================================");
        info!("Configuration:");
        info!("  Max Context: {} tokens", config.max_context_tokens);
        info!("  Time Slice: {}ms", config.time_slice);
        info!("  Sandbox: {}", if config.enable_sandbox { "Enabled" } else { "Disabled" });
        info!("");

        let state = Arc::new(RwLock::new(KernelState::Initializing));
        let context_manager = Arc::new(ContextManager::new(super::context::ContextConfig {
            max_context_tokens: config.max_context_tokens,
            working_memory_limit: 20_000,
            session_context_limit: 80_000,
            page_replacement_policy: super::context::PageReplacementPolicy::LruImportance,
            page_size: 1000,
        }));

        let storage_manager = Arc::new(StorageManager::from_postgres_url(
            "postgresql://postgres:password@localhost/agent_os"
        ).await?);

        let scheduler = Arc::new(AgentScheduler::new(super::scheduler::SchedulerConfig {
            policy: super::scheduler::SchedulingPolicy::Priority,
            default_time_slice: config.time_slice,
            max_pending_tasks: 100,
            scheduling_interval: 100,
            preemption_threshold: 10_000,
        }, context_manager.clone(), storage_manager.clone()));

        let security = if config.enable_sandbox {
            info!("Initializing sandbox manager...");
            Some(Arc::new(SandboxManager::new()))
        } else {
            None
        };

        let stats = Arc::new(RwLock::new(KernelStats::default()));
        let running = Arc::new(RwLock::new(false));

        {
            let mut inner_stats = stats.write().await;
            inner_stats.start_time = Utc::now().timestamp() as f64;
        }

        let kernel = Self {
            state,
            config,
            context_manager,
            scheduler,
            storage_manager,
            security,
            stats,
            running,
        };

        info!("Agent OS Kernel initialized successfully!");
        info!("");

        Ok(kernel)
    }

    pub async fn spawn_agent(
        &self,
        name: &str,
        task: &str,
        priority: Priority,
        policy: Option<SecurityPolicy>,
    ) -> Result<AgentPid, Box<dyn std::error::Error>> {
        let mut state = self.state.write().await;
        if *state != KernelState::Initializing && *state != KernelState::Running {
            return Err("Kernel not in valid state".into());
        }
        *state = KernelState::Running;
        drop(state);

        let pid = format!("agent-{}", uuid::Uuid::new_v4());

        info!("Spawning agent: {}", name);
        info!("PID: {}", pid);
        info!("Priority: {}", priority);

        let process = AgentProcess::new(pid.clone(), name.to_string(), priority);

        self.scheduler.add_process(process).await;

        if let Some(policy) = policy {
            if let Some(ref security) = self.security {
                security.create_sandbox(&pid, policy.clone()).await;
            }
        }

        let system_prompt = format!("You are {}. Your task: {}", name, task);
        self.context_manager.allocate_page(
            pid.clone(),
            system_prompt,
            1.0,
            PageType::System
        ).await;

        let task_page = format!("Current task: {}", task);
        self.context_manager.allocate_page(
            pid.clone(),
            task_page,
            0.9,
            PageType::Task
        ).await;

        let mut stats = self.stats.write().await;
        stats.total_agents += 1;

        info!("Agent successfully spawned");
        info!("");

        Ok(pid)
    }

    pub async fn create_checkpoint(&self, pid: &str, description: &str) -> Result<CheckpointId, Box<dyn std::error::Error>> {
        info!("Creating checkpoint for {}...", pid);

        let state = self.state.read().await;
        if *state != KernelState::Running {
            return Err("Kernel not in running state".into());
        }
        drop(state);

        let checkpoint_id = self.scheduler.suspend_process(pid, true).await;

        if let Some(checkpoint_id) = checkpoint_id {
            let state_data = serde_json::json!({
                "description": description,
                "created_at": Utc::now(),
            });

            self.storage_manager.create_checkpoint(pid, &state_data).await?;

            info!("Checkpoint created: {}", checkpoint_id);
            Ok(checkpoint_id)
        } else {
            Err("Failed to create checkpoint".into())
        }
    }

    pub async fn restore_checkpoint(&self, checkpoint_id: CheckpointId) -> Result<AgentPid, Box<dyn std::error::Error>> {
        info!("Restoring from checkpoint {}", checkpoint_id);

        let state = self.state.read().await;
        if *state != KernelState::Initializing && *state != KernelState::Running {
            return Err("Kernel not in valid state".into());
        }
        drop(state);

        let state_data = self.storage_manager.load_checkpoint(checkpoint_id).await?;

        if state_data.is_some() {
            let pid = format!("agent-{}", uuid::Uuid::new_v4());
            let process = AgentProcess::new(pid.clone(), "Restored Agent".to_string(), 50);
            self.scheduler.add_process(process).await;
            info!("Process restored successfully: {}", pid);
            Ok(pid)
        } else {
            Err("Checkpoint not found".into())
        }
    }

    pub async fn run(&self, max_iterations: Option<usize>) -> Result<(), Box<dyn std::error::Error>> {
        let mut state = self.state.write().await;
        if *state == KernelState::Running {
            return Err("Kernel already running".into());
        }
        *state = KernelState::Running;
        drop(state);

        let mut running = self.running.write().await;
        *running = true;
        drop(running);

        info!("Starting kernel main loop");
        info!("========================");
        info!("Max iterations: {}", max_iterations.map(|x| x.to_string()).unwrap_or("Unlimited".to_string()));

        let mut iteration = 0;
        loop {
            let running = self.running.read().await;
            if !*running {
                break;
            }
            drop(running);

            if let Some(limit) = max_iterations {
                if iteration >= limit {
                    info!("Max iterations reached, stopping");
                    break;
                }
            }

            if let Some(process) = self.scheduler.schedule().await {
                self.execute_agent_step(process.pid).await;

                let mut stats = self.stats.write().await;
                stats.total_iterations += 1;
            }

            iteration += 1;

            tokio::time::sleep(Duration::from_millis(100)).await;
        }

        let mut state = self.state.write().await;
        *state = KernelState::Paused;

        info!("Kernel loop stopped after {} iterations", iteration);
        Ok(())
    }

    async fn execute_agent_step(&self, pid: AgentPid) {
        let context = self.context_manager.get_agent_context(&pid, true).await;
        let tokens_needed = context.iter().map(|msg| estimate_tokens(&msg.content)).sum::<usize>();

        if self.scheduler.request_resources(&pid, tokens_needed).await {
            info!("Executing step for {}", pid);

            let mut stats = self.stats.write().await;
            stats.total_tokens += tokens_needed as u64;
        }
    }

    pub async fn shutdown(&self) -> Result<(), Box<dyn std::error::Error>> {
        info!("Shutting down Agent OS Kernel");

        let mut running = self.running.write().await;
        *running = false;

        let mut state = self.state.write().await;
        *state = KernelState::ShuttingDown;

        let mut stats = self.stats.write().await;
        stats.active_agents = 0;

        let scheduler_state = self.scheduler.get_state().await;
        let processes: Vec<String> = scheduler_state.processes.keys().cloned().collect();

        for pid in processes {
            if let Some(checkpoint) = self.scheduler.suspend_process(&pid, true).await {
                info!("Created checkpoint for {}: {}", pid, checkpoint);
            }
        }

        info!("Shutdown complete");
        *state = KernelState::Shutdown;

        Ok(())
    }

    pub async fn print_status(&self) {
        info!("Agent OS Kernel Status");
        info!("======================");

        let state = self.state.read().await;
        info!("State: {:?}", *state);

        let stats = self.stats.read().await;
        info!("Uptime: {:.2}s", Utc::now().timestamp() as f64 - stats.start_time);
        info!("Total Agents: {}", stats.total_agents);
        info!("Active Agents: {}", stats.active_agents);
        info!("Iterations: {}", stats.total_iterations);
        info!("Tokens Processed: {}", stats.total_tokens);

        let scheduler_stats = self.scheduler.get_process_stats().await;
        info!("Ready Queue: {}", scheduler_stats["ready_queue_size"]);
        info!("Running Queue: {}", scheduler_stats["running_queue_size"]);
        info!("Waiting Queue: {}", scheduler_stats["waiting_queue_size"]);

        match self.storage_manager.get_statistics().await {
            Ok(storage_stats) => {
                info!("Total Pages: {}", storage_stats.total_pages);
                info!("Checkpoints: {}", storage_stats.total_checkpoints);
                info!("Audit Log Entries: {}", storage_stats.audit_log_entries);
            }
            Err(e) => {
                info!("Storage statistics unavailable: {}", e);
            }
        }

        info!("");
    }

    pub async fn get_stats(&self) -> KernelStats {
        self.stats.read().await.clone()
    }
}

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
    async fn test_kernel_initialization() {
        let config = KernelConfig::default();
        let result = AgentOSKernel::new(config).await;
        // Should fail due to no database
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_process_scheduling() {
        let context = Arc::new(ContextManager::default());
        let storage = Arc::new(StorageManager::default());
        let scheduler = Arc::new(AgentScheduler::default());

        scheduler.add_process(AgentProcess::new("test-pid-1".to_string(), "Test Process", 50)).await;
        let scheduled = scheduler.schedule().await;
        assert!(scheduled.is_some());
        assert_eq!(scheduled.unwrap().name, "Test Process");
    }
}
