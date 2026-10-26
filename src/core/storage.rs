use super::types::*;
use sqlx::postgres::PgPoolOptions;
use sqlx::{Pool, Postgres, Error, Row};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;
use log::{info, warn};
use uuid::Uuid;
use chrono::Utc;

/// 内存存储后端：无数据库时内核仍可启动（开发/测试默认）
#[derive(Debug, Default)]
pub struct MemoryStore {
    pages: HashMap<PageId, ContextPage>,
    tasks: HashMap<String, TaskInfo>,
    checkpoints: HashMap<CheckpointId, (String, serde_json::Value)>,
    audit: Vec<AuditLogEntry>,
}

/// 存储后端二选一
#[derive(Debug)]
enum StorageBackend {
    Postgres(Pool<Postgres>),
    Memory(tokio::sync::Mutex<MemoryStore>),
}

#[derive(Debug, Clone)]
pub struct PostgresConfig {
    pub url: String,
    pub pool_size: u32,
    pub enable_vector: bool,
    pub vector_dimensions: u32,
    pub enable_audit_log: bool,
}

impl Default for PostgresConfig {
    fn default() -> Self {
        Self {
            url: "postgresql://postgres:password@localhost/agent_os".to_string(),
            pool_size: 10,
            enable_vector: true,
            vector_dimensions: 1536,
            enable_audit_log: true,
        }
    }
}

#[derive(Debug)]
pub struct StorageManager {
    backend: StorageBackend,
    config: PostgresConfig,
    initialized: Arc<Mutex<bool>>,
}

impl StorageManager {
    pub async fn from_config(config: PostgresConfig) -> Result<Self, Box<dyn std::error::Error>> {
        info!("Connecting to PostgreSQL: {}", config.url);
        
        let pool = PgPoolOptions::new()
            .max_connections(config.pool_size)
            .connect(&config.url)
            .await?;

        let manager = Self {
            backend: StorageBackend::Postgres(pool),
            config,
            initialized: Arc::new(Mutex::new(false)),
        };

        manager.ensure_schema().await?;

        info!("PostgreSQL storage manager initialized successfully");
        Ok(manager)
    }

    pub async fn from_postgres_url(url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let config = PostgresConfig {
            url: url.to_string(),
            ..Default::default()
        };

        Self::from_config(config).await
    }

    /// PG 后端连接池访问器（仅 PG 方法体内部使用）
    fn pg_pool(&self) -> &Pool<Postgres> {
        match &self.backend {
            StorageBackend::Postgres(pool) => pool,
            StorageBackend::Memory(_) => {
                unreachable!("pg_pool called on memory backend — dispatch bug")
            }
        }
    }

    /// 内存后端：无数据库依赖，进程退出即失（明确 warning）
    pub fn in_memory() -> Self {
        warn!("Storage backend: in-memory (data is NOT persisted; set AOSK_DATABASE_URL for PostgreSQL)");
        Self {
            backend: StorageBackend::Memory(tokio::sync::Mutex::new(MemoryStore::default())),
            config: PostgresConfig {
                enable_vector: false,
                ..Default::default()
            },
            initialized: Arc::new(Mutex::new(true)),
        }
    }

    /// 尝试 PostgreSQL，失败或无 URL 时回退内存后端
    pub async fn from_url_or_memory(url: Option<&str>) -> Self {
        match url.filter(|u| !u.trim().is_empty()) {
            Some(u) => match Self::from_postgres_url(u).await {
                Ok(m) => m,
                Err(e) => {
                    warn!("PostgreSQL connection failed ({}); falling back to in-memory storage", e);
                    Self::in_memory()
                }
            },
            None => Self::in_memory(),
        }
    }

    async fn ensure_schema(&self) -> Result<(), Error> {
        let mut initialized = self.initialized.lock().await;
        if *initialized {
            return Ok(());
        }

        if matches!(self.backend, StorageBackend::Memory(_)) {
            *initialized = true;
            return Ok(());
        }

        sqlx::query(r#"
            CREATE TABLE IF NOT EXISTS context_pages (
                id UUID PRIMARY KEY,
                agent_pid TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL NOT NULL,
                page_type TEXT NOT NULL,
                last_accessed TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                token_count INTEGER NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS task_info (
                agent_pid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                task TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                last_run_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                timestamp TIMESTAMPTZ NOT NULL,
                agent_pid TEXT NOT NULL,
                action_type TEXT NOT NULL,
                input_data JSONB,
                output_data JSONB,
                reasoning TEXT,
                duration_ms BIGINT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                id UUID PRIMARY KEY,
                agent_pid TEXT NOT NULL,
                state JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                previous_checkpoint UUID
            );

            CREATE INDEX IF NOT EXISTS idx_context_pages_agent_pid 
                ON context_pages(agent_pid);
            
            CREATE INDEX IF NOT EXISTS idx_audit_logs_agent_pid 
                ON audit_logs(agent_pid, timestamp DESC);
            
            CREATE INDEX IF NOT EXISTS idx_task_info_status 
                ON task_info(status);

            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE TABLE IF NOT EXISTS vector_index (
                id UUID PRIMARY KEY,
                agent_pid TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            );
        "#).execute(self.pg_pool()).await?;

        *initialized = true;
        Ok(())
    }

    pub async fn save_context_page(&self, page: &ContextPage) -> Result<(), Error> {
        if let StorageBackend::Memory(store) = &self.backend {
            store.lock().await.pages.insert(page.id.clone(), page.clone());
            return Ok(());
        }
        sqlx::query(r#"
            INSERT INTO context_pages (
                id, agent_pid, content, importance, page_type,
                last_accessed, created_at, token_count, status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                importance = EXCLUDED.importance,
                page_type = EXCLUDED.page_type,
                last_accessed = EXCLUDED.last_accessed,
                created_at = EXCLUDED.created_at,
                token_count = EXCLUDED.token_count,
                status = EXCLUDED.status
        "#)
        .bind(page.id.to_string())
        .bind(&page.agent_pid)
        .bind(&page.content)
        .bind(page.importance)
        .bind(format!("{:?}", page.page_type))
        .bind(page.last_accessed)
        .bind(page.created_at)
        .bind(page.token_count as i32)
        .bind(format!("{:?}", page.status))
        .execute(self.pg_pool())
        .await?;

        Ok(())
    }

    pub async fn load_context_page(&self, page_id: PageId) -> Result<Option<ContextPage>, Error> {
        if let StorageBackend::Memory(store) = &self.backend {
            return Ok(store.lock().await.pages.get(&page_id).cloned());
        }
        let row = sqlx::query(
            r#"
            SELECT id, agent_pid, content, importance, page_type,
                   last_accessed, created_at, token_count, status
            FROM context_pages WHERE id = $1
            "#
        )
        .bind(page_id.to_string())
        .fetch_optional(self.pg_pool()).await?;

        Ok(row.map(|r| ContextPage {
            id: r.get::<String, _>("id").parse().unwrap_or_else(|_| Uuid::new_v4()),
            agent_pid: r.get("agent_pid"),
            content: r.get("content"),
            importance: r.get("importance"),
            page_type: string_to_page_type(r.get::<String, _>("page_type").as_str()),
            last_accessed: r.get("last_accessed"),
            created_at: r.get("created_at"),
            token_count: r.get::<i32, _>("token_count") as u32,
            status: string_to_page_status(r.get::<String, _>("status").as_str()),
        }))
    }

    pub async fn save_task_info(&self, task: &TaskInfo) -> Result<(), Error> {
        if let StorageBackend::Memory(store) = &self.backend {
            store.lock().await.tasks.insert(task.agent_pid.clone(), task.clone());
            return Ok(());
        }
        sqlx::query(r#"
            INSERT INTO task_info (
                agent_pid, name, task, status, priority,
                created_at, last_run_at, completed_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (agent_pid) DO UPDATE SET
                name = EXCLUDED.name,
                task = EXCLUDED.task,
                status = EXCLUDED.status,
                priority = EXCLUDED.priority,
                last_run_at = EXCLUDED.last_run_at,
                completed_at = EXCLUDED.completed_at
        "#)
        .bind(&task.agent_pid)
        .bind(&task.name)
        .bind(&task.task)
        .bind(format!("{:?}", task.status))
        .bind(task.priority as i32)
        .bind(task.created_at)
        .bind(task.last_run_at)
        .bind(task.completed_at)
        .execute(self.pg_pool())
        .await?;

        Ok(())
    }

    pub async fn load_task_info(&self, agent_pid: &str) -> Result<Option<TaskInfo>, Error> {
        if let StorageBackend::Memory(store) = &self.backend {
            return Ok(store.lock().await.tasks.get(agent_pid).cloned());
        }
        let row = sqlx::query(
            r#"
            SELECT agent_pid, name, task, status, priority,
                   created_at, last_run_at, completed_at
            FROM task_info WHERE agent_pid = $1
            "#
        )
        .bind(agent_pid)
        .fetch_optional(self.pg_pool()).await?;

        Ok(row.map(|r| TaskInfo {
            agent_pid: r.get("agent_pid"),
            name: r.get("name"),
            task: r.get("task"),
            status: string_to_task_status(r.get::<String, _>("status").as_str()),
            priority: r.get::<i32, _>("priority") as u8,
            created_at: r.get("created_at"),
            last_run_at: r.get("last_run_at"),
            completed_at: r.get("completed_at"),
        }))
    }

    pub async fn create_checkpoint(&self, agent_pid: &str, state: &serde_json::Value) -> Result<CheckpointId, Error> {
        let checkpoint_id = Uuid::new_v4();

        if let StorageBackend::Memory(store) = &self.backend {
            store.lock().await.checkpoints.insert(checkpoint_id, (agent_pid.to_string(), state.clone()));
            return Ok(checkpoint_id);
        }

        sqlx::query(r#"
            INSERT INTO checkpoints (
                id, agent_pid, state, created_at
            )
            VALUES ($1, $2, $3, $4)
        "#)
        .bind(checkpoint_id.to_string())
        .bind(agent_pid)
        .bind(state)
        .bind(Utc::now())
        .execute(self.pg_pool())
        .await?;

        Ok(checkpoint_id)
    }

    pub async fn load_checkpoint(&self, checkpoint_id: CheckpointId) -> Result<Option<serde_json::Value>, Error> {
        if let StorageBackend::Memory(store) = &self.backend {
            return Ok(store.lock().await.checkpoints.get(&checkpoint_id).map(|(_, s)| s.clone()));
        }
        let row = sqlx::query(
            r#"
            SELECT state FROM checkpoints WHERE id = $1
            "#
        )
        .bind(checkpoint_id.to_string())
        .fetch_optional(self.pg_pool()).await?;

        Ok(row.map(|r| r.get("state")))
    }

    pub async fn log_action(&self, entry: &AuditLogEntry) -> Result<(), Error> {
        if !self.config.enable_audit_log {
            return Ok(());
        }

        if let StorageBackend::Memory(store) = &self.backend {
            store.lock().await.audit.push(entry.clone());
            return Ok(());
        }

        sqlx::query(r#"
            INSERT INTO audit_logs (
                timestamp, agent_pid, action_type,
                input_data, output_data, reasoning,
                duration_ms
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        "#)
        .bind(entry.timestamp)
        .bind(&entry.agent_pid)
        .bind(&entry.action_type)
        .bind(&entry.input_data)
        .bind(&entry.output_data)
        .bind(&entry.reasoning)
        .bind(entry.duration_ms as i64)
        .execute(self.pg_pool())
        .await?;

        Ok(())
    }

    pub async fn get_audit_trail(&self, agent_pid: &str, limit: usize) -> Result<Vec<AuditLogEntry>, Error> {
        if let StorageBackend::Memory(store) = &self.backend {
            let store = store.lock().await;
            let mut entries: Vec<AuditLogEntry> = store
                .audit
                .iter()
                .filter(|e| e.agent_pid == agent_pid)
                .cloned()
                .collect();
            entries.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
            entries.truncate(limit);
            return Ok(entries);
        }
        let rows = sqlx::query(
            r#"
            SELECT timestamp, agent_pid, action_type, input_data,
                   output_data, reasoning, duration_ms
            FROM audit_logs 
            WHERE agent_pid = $1
            ORDER BY timestamp DESC
            LIMIT $2
            "#
        )
        .bind(agent_pid)
        .bind(limit as i64)
        .fetch_all(self.pg_pool()).await?;

        Ok(rows.into_iter().map(|r| AuditLogEntry {
            timestamp: r.get("timestamp"),
            agent_pid: r.get("agent_pid"),
            action_type: r.get("action_type"),
            input_data: r.get("input_data"),
            output_data: r.get("output_data"),
            reasoning: r.get("reasoning"),
            duration_ms: r.get::<i64, _>("duration_ms") as u64,
        }).collect())
    }

    pub async fn semantic_search(
        &self,
        _agent_pid: &str,
        _query: &str,
        _limit: usize,
    ) -> Result<Vec<(String, f32)>, Error> {
        if !self.config.enable_vector {
            return Ok(Vec::new());
        }

        Ok(Vec::new())
    }

    pub async fn get_statistics(&self) -> Result<StorageStatistics, Error> {
        if let StorageBackend::Memory(store) = &self.backend {
            let store = store.lock().await;
            return Ok(StorageStatistics {
                total_pages: store.pages.len() as u64,
                total_tasks: store.tasks.len() as u64,
                total_checkpoints: store.checkpoints.len() as u64,
                audit_log_entries: store.audit.len() as u64,
                database_size: 0,
            });
        }
        let pages_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM context_pages"#
        ).fetch_one(self.pg_pool()).await?;

        let tasks_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM task_info"#
        ).fetch_one(self.pg_pool()).await?;

        let checkpoints_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM checkpoints"#
        ).fetch_one(self.pg_pool()).await?;

        let audit_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM audit_logs"#
        ).fetch_one(self.pg_pool()).await?;

        Ok(StorageStatistics {
            total_pages: pages_count as u64,
            total_tasks: tasks_count as u64,
            total_checkpoints: checkpoints_count as u64,
            audit_log_entries: audit_count as u64,
            database_size: 0,
        })
    }
}

impl Default for StorageManager {
    fn default() -> Self {
        panic!("StorageManager::default() not available - use from_config() or from_postgres_url()")
    }
}

#[derive(Debug, Clone)]
pub struct StorageStatistics {
    pub total_pages: u64,
    pub total_tasks: u64,
    pub total_checkpoints: u64,
    pub audit_log_entries: u64,
    pub database_size: u64,
}

fn string_to_page_type(s: &str) -> PageType {
    match s.to_lowercase().as_str() {
        "system" => PageType::System,
        "user" => PageType::User,
        "working" => PageType::Working,
        "longterm" | "long_term" => PageType::LongTerm,
        "toolresult" | "tool_result" => PageType::ToolResult,
        "task" => PageType::Task,
        "tools" => PageType::Tools,
        _ => PageType::User,
    }
}

fn string_to_page_status(s: &str) -> PageStatus {
    match s.to_lowercase().as_str() {
        "inmemory" | "in_memory" => PageStatus::InMemory,
        "swapped" => PageStatus::Swapped,
        "loading" => PageStatus::Loading,
        _ => PageStatus::Swapped,
    }
}

fn string_to_task_status(s: &str) -> TaskStatus {
    match s.to_lowercase().as_str() {
        "pending" => TaskStatus::Pending,
        "running" => TaskStatus::Running,
        "suspended" => TaskStatus::Suspended,
        "completed" => TaskStatus::Completed,
        "failed" => TaskStatus::Failed,
        "canceled" => TaskStatus::Canceled,
        _ => TaskStatus::Pending,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_page(pid: &str) -> ContextPage {
        ContextPage {
            id: Uuid::parse_str(pid).unwrap(),
            agent_pid: "agent-1".to_string(),
            content: "hello".to_string(),
            importance: 0.5,
            page_type: PageType::Working,
            last_accessed: Utc::now(),
            created_at: Utc::now(),
            token_count: 5,
            status: PageStatus::InMemory,
        }
    }

    #[tokio::test]
    async fn test_memory_storage_roundtrip() {
        let m = StorageManager::in_memory();

        // context page upsert/load
        let mut page = sample_page("123e4567-e89b-12d3-a456-426614174000");
        m.save_context_page(&page).await.unwrap();
        page.content = "updated".to_string();
        m.save_context_page(&page).await.unwrap();
        let loaded = m.load_context_page(page.id).await.unwrap().unwrap();
        assert_eq!(loaded.content, "updated");

        // task info
        let task = TaskInfo {
            agent_pid: "agent-1".to_string(),
            name: "t".to_string(),
            task: "do".to_string(),
            status: TaskStatus::Running,
            priority: 50,
            created_at: Utc::now(),
            last_run_at: None,
            completed_at: None,
        };
        m.save_task_info(&task).await.unwrap();
        let loaded_task = m.load_task_info("agent-1").await.unwrap().unwrap();
        assert_eq!(loaded_task.name, "t");

        // checkpoint
        let state = serde_json::json!({"k": "v"});
        let cid = m.create_checkpoint("agent-1", &state).await.unwrap();
        let loaded_ck = m.load_checkpoint(cid).await.unwrap().unwrap();
        assert_eq!(loaded_ck["k"], "v");

        // audit trail (倒序 + limit)
        for i in 0..3 {
            m.log_action(&AuditLogEntry {
                timestamp: Utc::now(),
                agent_pid: "agent-1".to_string(),
                action_type: format!("act-{}", i),
                input_data: serde_json::Value::Null,
                output_data: serde_json::Value::Null,
                reasoning: None,
                duration_ms: i as u64,
            })
            .await
            .unwrap();
        }
        let trail = m.get_audit_trail("agent-1", 2).await.unwrap();
        assert_eq!(trail.len(), 2);

        // statistics
        let stats = m.get_statistics().await.unwrap();
        assert_eq!(stats.total_pages, 1);
        assert_eq!(stats.total_tasks, 1);
        assert_eq!(stats.total_checkpoints, 1);
        assert_eq!(stats.audit_log_entries, 3);
    }

    #[tokio::test]
    async fn test_from_url_or_memory_falls_back() {
        // 空 URL -> 内存
        let m = StorageManager::from_url_or_memory(None).await;
        assert!(matches!(m.backend, StorageBackend::Memory(_)));
        // 不可达的 PostgreSQL -> 内存回退（而非 panic/Err）
        let m2 = StorageManager::from_url_or_memory(Some("postgresql://nobody:***@127.0.0.1:1/none")).await;
        assert!(matches!(m2.backend, StorageBackend::Memory(_)));
    }
}
