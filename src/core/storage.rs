use super::types::*;
use sqlx::postgres::PgPoolOptions;
use sqlx::{Pool, Postgres, Error, Row};
use std::sync::Arc;
use tokio::sync::Mutex;
use log::info;
use uuid::Uuid;
use chrono::Utc;

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
    pool: Arc<Pool<Postgres>>,
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
            pool: Arc::new(pool),
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

    async fn ensure_schema(&self) -> Result<(), Error> {
        let mut initialized = self.initialized.lock().await;
        if *initialized {
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
        "#).execute(&*self.pool).await?;

        *initialized = true;
        Ok(())
    }

    pub async fn save_context_page(&self, page: &ContextPage) -> Result<(), Error> {
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
        .execute(&*self.pool)
        .await?;

        Ok(())
    }

    pub async fn load_context_page(&self, page_id: PageId) -> Result<Option<ContextPage>, Error> {
        let row = sqlx::query(
            r#"
            SELECT id, agent_pid, content, importance, page_type,
                   last_accessed, created_at, token_count, status
            FROM context_pages WHERE id = $1
            "#
        )
        .bind(page_id.to_string())
        .fetch_optional(&*self.pool).await?;

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
        .execute(&*self.pool)
        .await?;

        Ok(())
    }

    pub async fn load_task_info(&self, agent_pid: &str) -> Result<Option<TaskInfo>, Error> {
        let row = sqlx::query(
            r#"
            SELECT agent_pid, name, task, status, priority,
                   created_at, last_run_at, completed_at
            FROM task_info WHERE agent_pid = $1
            "#
        )
        .bind(agent_pid)
        .fetch_optional(&*self.pool).await?;

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
        .execute(&*self.pool)
        .await?;

        Ok(checkpoint_id)
    }

    pub async fn load_checkpoint(&self, checkpoint_id: CheckpointId) -> Result<Option<serde_json::Value>, Error> {
        let row = sqlx::query(
            r#"
            SELECT state FROM checkpoints WHERE id = $1
            "#
        )
        .bind(checkpoint_id.to_string())
        .fetch_optional(&*self.pool).await?;

        Ok(row.map(|r| r.get("state")))
    }

    pub async fn log_action(&self, entry: &AuditLogEntry) -> Result<(), Error> {
        if !self.config.enable_audit_log {
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
        .execute(&*self.pool)
        .await?;

        Ok(())
    }

    pub async fn get_audit_trail(&self, agent_pid: &str, limit: usize) -> Result<Vec<AuditLogEntry>, Error> {
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
        .fetch_all(&*self.pool).await?;

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
        let pages_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM context_pages"#
        ).fetch_one(&*self.pool).await?;

        let tasks_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM task_info"#
        ).fetch_one(&*self.pool).await?;

        let checkpoints_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM checkpoints"#
        ).fetch_one(&*self.pool).await?;

        let audit_count: i64 = sqlx::query_scalar::<_, i64>(
            r#"SELECT COUNT(*) FROM audit_logs"#
        ).fetch_one(&*self.pool).await?;

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
