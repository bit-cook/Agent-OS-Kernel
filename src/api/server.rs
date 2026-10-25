//! Axum Web API Server for Agent OS Kernel
//!
//! Provides REST API endpoints and a built-in dashboard.

use axum::{
    Router,
    routing::get,
    extract::{Path, State, Json, ConnectInfo},
    response::{Html, IntoResponse},
    http::{StatusCode, Method, HeaderMap, header},
};
use tower_http::cors::CorsLayer;
use serde::{Serialize, Deserialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use std::collections::HashMap;
use std::net::SocketAddr;
use chrono::Utc;
use uuid::Uuid;
use log::info;

// ─── Shared State ───────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
pub struct AgentInfo {
    pub pid: String,
    pub name: String,
    pub task: String,
    pub priority: u32,
    pub status: String,
    pub created_at: String,
    pub tokens_used: u64,
    pub iterations: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct KernelStatus {
    pub version: String,
    pub state: String,
    pub uptime_secs: f64,
    pub start_time: String,
    pub total_agents: u32,
    pub active_agents: u32,
    pub total_tokens: u64,
    pub total_iterations: u64,
    pub total_api_calls: u64,
    pub max_context_tokens: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct SchedulerStatus {
    pub policy: String,
    pub ready_queue: usize,
    pub running_queue: usize,
    pub waiting_queue: usize,
    pub time_slice_ms: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct MetricsData {
    pub cpu_usage_percent: f32,
    pub memory_mb: f32,
    pub agents_per_second: f32,
    pub avg_latency_ms: f32,
    pub cache_hit_rate: f32,
    pub context_utilization: f32,
    pub timestamp: String,
}

#[derive(Debug)]
pub struct AppState {
    pub agents: RwLock<HashMap<String, AgentInfo>>,
    pub start_time: chrono::DateTime<Utc>,
    pub total_api_calls: RwLock<u64>,
    pub total_tokens: RwLock<u64>,
    pub total_iterations: RwLock<u64>,
    /// 变更型端点的 API Key（None = 未配置，仅 loopback 可变更）
    pub api_key: Option<String>,
}

impl AppState {
    pub fn new() -> Self {
        Self::with_api_key(None)
    }

    pub fn with_api_key(api_key: Option<String>) -> Self {
        Self {
            agents: RwLock::new(HashMap::new()),
            start_time: Utc::now(),
            total_api_calls: RwLock::new(0),
            total_tokens: RwLock::new(0),
            total_iterations: RwLock::new(0),
            api_key,
        }
    }
}

/// 变更型端点（POST/DELETE）认证（审计 P0-04）：
/// - 配置了 key：必须提供正确的 X-API-Key
/// - 未配置 key：仅放行 loopback 客户端，其余 401
fn check_write_auth(
    state: &AppState,
    headers: &HeaderMap,
    client_addr: SocketAddr,
) -> Result<(), axum::response::Response> {
    let is_loopback = client_addr.ip().is_loopback();

    if let Some(expected) = &state.api_key {
        let provided = headers
            .get("X-API-Key")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");
        if provided != expected {
            return Err((
                StatusCode::UNAUTHORIZED,
                Json(ErrorResponse {
                    ok: false,
                    error: "Invalid or missing API key".to_string(),
                }),
            )
                .into_response());
        }
        return Ok(());
    }

    if !is_loopback {
        return Err((
            StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                ok: false,
                error: "Anonymous mutations are only allowed from loopback; \
                        set AOSK_API_KEY to authorize remote clients"
                    .to_string(),
            }),
        )
            .into_response());
    }
    Ok(())
}

#[derive(Deserialize)]
pub struct CreateAgentRequest {
    pub name: String,
    pub task: String,
    #[serde(default = "default_priority")]
    pub priority: u32,
}

fn default_priority() -> u32 { 50 }

#[derive(Serialize)]
pub struct ApiResponse<T: Serialize> {
    pub ok: bool,
    pub data: T,
}

#[derive(Serialize)]
pub struct ErrorResponse {
    pub ok: bool,
    pub error: String,
}

// ─── Handlers ───────────────────────────────────────────────

async fn get_status(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let mut calls = state.total_api_calls.write().await;
    *calls += 1;
    let agents = state.agents.read().await;
    let active = agents.values().filter(|a| a.status == "running").count() as u32;
    let tokens = *state.total_tokens.read().await;
    let iterations = *state.total_iterations.read().await;
    let uptime = (Utc::now() - state.start_time).num_seconds() as f64;

    Json(ApiResponse {
        ok: true,
        data: KernelStatus {
            version: "0.3.0".to_string(),
            state: "Running".to_string(),
            uptime_secs: uptime,
            start_time: state.start_time.to_rfc3339(),
            total_agents: agents.len() as u32,
            active_agents: active,
            total_tokens: tokens,
            total_iterations: iterations,
            total_api_calls: *calls,
            max_context_tokens: 128_000,
        },
    })
}

async fn list_agents(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let mut calls = state.total_api_calls.write().await;
    *calls += 1;
    let agents = state.agents.read().await;
    let list: Vec<AgentInfo> = agents.values().cloned().collect();
    Json(ApiResponse { ok: true, data: list })
}

async fn create_agent(
    State(state): State<Arc<AppState>>,
    ConnectInfo(client_addr): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    Json(req): Json<CreateAgentRequest>,
) -> axum::response::Response {
    if let Err(resp) = check_write_auth(&state, &headers, client_addr) {
        return resp;
    }
    let mut calls = state.total_api_calls.write().await;
    *calls += 1;
    let pid = format!("agent-{}", Uuid::new_v4());
    let agent = AgentInfo {
        pid: pid.clone(),
        name: req.name,
        task: req.task,
        priority: req.priority,
        status: "running".to_string(),
        created_at: Utc::now().to_rfc3339(),
        tokens_used: 0,
        iterations: 0,
    };
    let mut agents = state.agents.write().await;
    agents.insert(pid.clone(), agent.clone());
    info!("Agent created: {} ({})", agent.name, pid);
    (StatusCode::CREATED, Json(ApiResponse { ok: true, data: agent })).into_response()
}

async fn get_agent(
    State(state): State<Arc<AppState>>,
    Path(pid): Path<String>,
) -> impl IntoResponse {
    let agents = state.agents.read().await;
    match agents.get(&pid) {
        Some(agent) => Ok(Json(ApiResponse { ok: true, data: agent.clone() })),
        None => Err((StatusCode::NOT_FOUND, Json(ErrorResponse {
            ok: false,
            error: format!("Agent {} not found", pid),
        }))),
    }
}

async fn delete_agent(
    State(state): State<Arc<AppState>>,
    ConnectInfo(client_addr): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    Path(pid): Path<String>,
) -> axum::response::Response {
    if let Err(resp) = check_write_auth(&state, &headers, client_addr) {
        return resp;
    }
    let mut agents = state.agents.write().await;
    match agents.remove(&pid) {
        Some(agent) => {
            info!("Agent terminated: {} ({})", agent.name, pid);
            (StatusCode::OK, Json(ApiResponse { ok: true, data: serde_json::json!({"terminated": pid}) }))
                .into_response()
        }
        None => (
            StatusCode::NOT_FOUND,
            Json(ErrorResponse {
                ok: false,
                error: format!("Agent {} not found", pid),
            }),
        )
            .into_response(),
    }
}

async fn get_metrics(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let mut calls = state.total_api_calls.write().await;
    *calls += 1;
    let agents = state.agents.read().await;
    let uptime = (Utc::now() - state.start_time).num_seconds().max(1) as f32;
    Json(ApiResponse {
        ok: true,
        data: MetricsData {
            cpu_usage_percent: 12.5,
            memory_mb: 48.2,
            agents_per_second: agents.len() as f32 / uptime,
            avg_latency_ms: 2.3,
            cache_hit_rate: 0.85,
            context_utilization: if agents.is_empty() { 0.0 } else { 0.42 },
            timestamp: Utc::now().to_rfc3339(),
        },
    })
}

async fn get_scheduler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let agents = state.agents.read().await;
    let running = agents.values().filter(|a| a.status == "running").count();
    let waiting = agents.values().filter(|a| a.status == "waiting").count();
    let ready = agents.values().filter(|a| a.status == "ready").count();
    Json(ApiResponse {
        ok: true,
        data: SchedulerStatus {
            policy: "Priority".to_string(),
            ready_queue: ready,
            running_queue: running,
            waiting_queue: waiting,
            time_slice_ms: 60000,
        },
    })
}

async fn dashboard() -> Html<&'static str> {
    Html(include_str!("../../static/dashboard.html"))
}

// ─── Server ─────────────────────────────────────────────────

/// 启动 Web API 服务器（审计 P0-04 默认值）：
/// - 默认绑定 127.0.0.1（loopback）；显式公开须设 AOSK_BIND_ADDR
/// - 变更型端点认证：AOSK_API_KEY（X-API-Key header）；
///   未配置时仅 loopback 客户端可变更
pub async fn start_server(port: u16) -> Result<(), Box<dyn std::error::Error>> {
    start_server_with_bind(port, None, None).await
}

pub async fn start_server_with_bind(
    port: u16,
    bind_addr: Option<String>,
    api_key: Option<String>,
) -> Result<(), Box<dyn std::error::Error>> {
    let bind_addr = bind_addr
        .or_else(|| std::env::var("AOSK_BIND_ADDR").ok())
        .unwrap_or_else(|| "127.0.0.1".to_string());
    let api_key = api_key.or_else(|| std::env::var("AOSK_API_KEY").ok());
    let is_public = bind_addr != "127.0.0.1" && bind_addr != "localhost" && bind_addr != "::1";

    let state = Arc::new(AppState::with_api_key(api_key));

    // CORS：默认不放行跨站；显式公开监听时才允许 Any
    let cors = if is_public {
        info!("⚠️  Public bind {} — 显式公开暴露，必须配置 AOSK_API_KEY", bind_addr);
        CorsLayer::new()
            .allow_origin(tower_http::cors::Any)
            .allow_methods([Method::GET, Method::POST, Method::DELETE])
            .allow_headers(tower_http::cors::Any)
    } else {
        CorsLayer::new()
            .allow_methods([Method::GET, Method::POST, Method::DELETE])
            .allow_headers(vec![header::CONTENT_TYPE, header::AUTHORIZATION])
    };

    let app = Router::new()
        .route("/", get(dashboard))
        .route("/api/status", get(get_status))
        .route("/api/agents", get(list_agents).post(create_agent))
        .route("/api/agents/{pid}", get(get_agent).delete(delete_agent))
        .route("/api/metrics", get(get_metrics))
        .route("/api/scheduler", get(get_scheduler))
        .layer(cors)
        .with_state(state);

    let ip: std::net::IpAddr = bind_addr.parse()?;
    let addr = SocketAddr::new(ip, port);
    info!("🚀 Agent OS Kernel Web API starting on http://{}", addr);
    info!("📊 Dashboard: http://{}/", addr);
    info!("📡 API: http://{}/api/status", addr);

    let server = axum::Server::bind(&addr).serve(app.into_make_service_with_connect_info::<SocketAddr>());
    server.await?;
    Ok(())
}
