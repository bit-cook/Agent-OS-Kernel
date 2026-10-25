# -*- coding: utf-8 -*-
"""
REST API Server

提供 REST API 接口，支持：
1. Agent 管理（真实内核操作，无占位符）
2. 任务提交
3. 状态查询
4. 指标监控

安全默认值（审计 P0-04）：
- 默认绑定 127.0.0.1（loopback），公开监听必须显式指定 host
- 变更型端点（POST/DELETE）默认要求 API Key（环境变量 AOSK_API_KEY）；
  未配置 key 时仅允许 loopback 客户端访问，非 loopback 匿名变更请求一律 401
"""

import logging
import os
import hmac
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from agent_os_kernel import (
    AgentOSKernel,
    create_metrics_collector,
    __version__ as KERNEL_VERSION,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


# ========== Data Models ==========

class AgentCreateRequest(BaseModel):
    """创建 Agent 请求"""
    name: str = Field(..., description="Agent 名称")
    task: str = Field(..., description="任务描述")
    priority: int = Field(50, ge=0, le=100, description="优先级")


class TaskSubmitRequest(BaseModel):
    """提交任务请求"""
    agent_id: str = Field(..., description="Agent ID")
    task: str = Field(..., description="任务内容")


class ContextRequest(BaseModel):
    """上下文请求"""
    agent_id: str = Field(..., description="Agent ID")
    content: str = Field(..., description="上下文内容")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="重要性")


class AgentResponse(BaseModel):
    """Agent 响应"""
    agent_id: str
    name: str
    task: str
    priority: int
    state: str
    created_at: str


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    agent_id: str
    status: str
    result: Optional[str] = None


class StatusResponse(BaseModel):
    """状态响应"""
    running: bool
    agents_count: int
    uptime_seconds: float
    version: str
    metrics: Dict[str, Any]


# ========== API Server ==========

class AgentOSKernelAPI:
    """API 服务器（门面：所有端点操作同一个内核实例，无每请求新建对象）"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000,
                 api_key: Optional[str] = None):
        self.host = host
        self.port = port
        # key 可显式传入或从环境变量读取；未配置时仅 loopback 可变更
        self.api_key = api_key or os.environ.get("AOSK_API_KEY")
        self.kernel: Optional[AgentOSKernel] = None
        self.metrics = create_metrics_collector()
        self.start_time = datetime.now()
        self._app = None
        self._tasks: Dict[str, Dict[str, Any]] = {}

    # ---------- 认证 ----------

    def _client_is_loopback(self, request: Request) -> bool:
        client = request.client.host if request.client else ""
        return client in LOOPBACK_HOSTS

    async def require_write_auth(self, request: Request):
        """变更型端点依赖：配置了 key 则必须提供正确 key；
        未配置 key 时仅放行 loopback 客户端，其余 401。"""
        if self.api_key:
            provided = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(provided, self.api_key):
                raise HTTPException(status_code=401, detail="Invalid or missing API key")
            return
        if not self._client_is_loopback(request):
            raise HTTPException(
                status_code=401,
                detail="Anonymous mutations are only allowed from loopback; "
                       "set AOSK_API_KEY to authorize remote clients"
            )

    def create_app(self) -> FastAPI:
        """创建 FastAPI 应用"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 启动：唯一内核实例，整个进程生命周期共享
            self.kernel = AgentOSKernel()
            logger.info("Kernel started")
            yield
            # 停止
            self.kernel.shutdown()
            logger.info("Kernel stopped")

        app = FastAPI(
            title="Agent OS Kernel API",
            description="AI Agent Operating System Kernel API",
            version=KERNEL_VERSION,
            lifespan=lifespan
        )

        self._register_routes(app)
        self._app = app

        return app

    def _register_routes(self, app: FastAPI):
        """注册路由"""

        @app.get("/", tags=["Root"])
        async def root():
            return {
                "name": "Agent OS Kernel API",
                "version": KERNEL_VERSION,
                "docs": "/docs"
            }

        @app.get("/health", tags=["Health"])
        async def health():
            return {"status": "healthy", "version": KERNEL_VERSION}

        # ========== Agent Management ==========

        @app.post("/api/v1/agents", response_model=AgentResponse, tags=["Agents"],
                  dependencies=[Depends(self.require_write_auth)])
        async def create_agent(request: AgentCreateRequest):
            """创建 Agent（真实 spawn 到内核）"""
            agent_id = self.kernel.spawn_agent(
                name=request.name,
                task=request.task,
                priority=request.priority
            )
            self.metrics.counter("agents_created_total")

            return AgentResponse(
                agent_id=agent_id,
                name=request.name,
                task=request.task,
                priority=request.priority,
                state="ready",
                created_at=datetime.now().isoformat()
            )

        @app.get("/api/v1/agents", response_model=List[AgentResponse], tags=["Agents"])
        async def list_agents():
            """列出所有 Agent"""
            agents = self.kernel.list_agents()

            return [
                AgentResponse(
                    agent_id=a["pid"],
                    name=a["name"],
                    task=a.get("task", ""),
                    priority=a.get("priority", 0),
                    state=a.get("state", "unknown"),
                    created_at=datetime.fromtimestamp(
                        a.get("created_at", 0)).isoformat() if a.get("created_at")
                    else datetime.now().isoformat()
                )
                for a in agents
            ]

        @app.get("/api/v1/agents/{agent_id}", response_model=AgentResponse, tags=["Agents"])
        async def get_agent(agent_id: str):
            """获取 Agent 信息"""
            agent = self.kernel.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            return AgentResponse(
                agent_id=agent_id,
                name=agent.get("name", ""),
                task=agent.get("task", ""),
                priority=agent.get("priority", 0),
                state=agent.get("state", "unknown"),
                created_at=datetime.fromtimestamp(
                    agent.get("created_at", 0)).isoformat() if agent.get("created_at")
                else datetime.now().isoformat()
            )

        @app.delete("/api/v1/agents/{agent_id}", tags=["Agents"],
                    dependencies=[Depends(self.require_write_auth)])
        async def delete_agent(agent_id: str):
            """删除 Agent（真实终止内核进程）"""
            ok = self.kernel.terminate_agent(agent_id, reason="deleted via API")
            if not ok:
                raise HTTPException(status_code=404, detail="Agent not found")

            self.metrics.counter("agents_deleted_total")
            return {"status": "deleted", "agent_id": agent_id}

        # ========== Tasks ==========

        @app.post("/api/v1/tasks", response_model=TaskResponse, tags=["Tasks"],
                  dependencies=[Depends(self.require_write_auth)])
        async def submit_task(request: TaskSubmitRequest):
            """提交任务（真实校验 Agent 存在并记录）"""
            agent = self.kernel.get_agent(request.agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            task_id = f"task-{datetime.now().timestamp()}"
            self._tasks[task_id] = {
                "task_id": task_id,
                "agent_id": request.agent_id,
                "task": request.task,
                "status": "pending",
                "result": None,
                "created_at": datetime.now().isoformat(),
            }
            self.metrics.counter("tasks_submitted_total")

            return TaskResponse(
                task_id=task_id,
                agent_id=request.agent_id,
                status="pending",
                result=None
            )

        @app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
        async def get_task(task_id: str):
            """获取任务状态"""
            task = self._tasks.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            return TaskResponse(
                task_id=task["task_id"],
                agent_id=task["agent_id"],
                status=task["status"],
                result=task.get("result")
            )

        # ========== Context ==========

        @app.post("/api/v1/context", tags=["Context"],
                  dependencies=[Depends(self.require_write_auth)])
        async def add_context(request: ContextRequest):
            """添加上下文（写入内核共享的 ContextManager）"""
            if not self.kernel.get_agent(request.agent_id):
                raise HTTPException(status_code=404, detail="Agent not found")

            page_id = self.kernel.context_manager.allocate_page(
                agent_pid=request.agent_id,
                content=request.content,
                importance=request.importance
            )

            return {"page_id": page_id, "status": "added"}

        @app.get("/api/v1/context/{agent_id}", tags=["Context"])
        async def get_context(agent_id: str):
            """获取上下文（从内核共享的 ContextManager 读取）"""
            if not self.kernel.get_agent(agent_id):
                raise HTTPException(status_code=404, detail="Agent not found")

            context = self.kernel.context_manager.get_agent_context(agent_id)

            return {"context": context}

        # ========== Checkpoints（真实内核 create_checkpoint/restore_checkpoint） ==========

        @app.post("/api/v1/agents/{agent_id}/checkpoints", tags=["Checkpoints"],
                  dependencies=[Depends(self.require_write_auth)])
        async def create_checkpoint(agent_id: str):
            """为 Agent 创建检查点（真实持久化进程状态+上下文页面）"""
            if not self.kernel.get_agent(agent_id):
                raise HTTPException(status_code=404, detail="Agent not found")
            checkpoint_id = self.kernel.create_checkpoint(agent_id, description="via API")
            if not checkpoint_id:
                raise HTTPException(status_code=500, detail="Checkpoint creation failed")
            self.metrics.counter("checkpoints_created_total")
            return {"checkpoint_id": checkpoint_id, "agent_id": agent_id, "status": "created"}

        @app.get("/api/v1/checkpoints", tags=["Checkpoints"])
        async def list_checkpoints(agent_id: Optional[str] = None):
            """列出检查点"""
            return {"checkpoints": self.kernel.storage.list_checkpoints(agent_pid=agent_id)}

        @app.post("/api/v1/checkpoints/{checkpoint_id}/restore", tags=["Checkpoints"],
                  dependencies=[Depends(self.require_write_auth)])
        async def restore_checkpoint(checkpoint_id: str):
            """从检查点恢复 Agent（真实恢复到新 PID）"""
            new_pid = self.kernel.restore_checkpoint(checkpoint_id)
            if not new_pid:
                raise HTTPException(status_code=404, detail="Checkpoint not found")
            self.metrics.counter("checkpoints_restored_total")
            return {"new_agent_id": new_pid, "checkpoint_id": checkpoint_id, "status": "restored"}

        # ========== Tools（真实工具注册表） ==========

        @app.get("/api/v1/tools", tags=["Tools"])
        async def list_tools():
            """列出已注册的内置工具（真实 schema）"""
            return {"tools": self.kernel.tool_registry.get_schemas()}

        # ========== Audit（真实审计日志） ==========

        @app.get("/api/v1/audit", tags=["Audit"])
        async def get_audit(agent_id: Optional[str] = None, limit: int = 50):
            """查询审计日志（真实记录）"""
            return {"logs": self.kernel.storage.get_audit_logs(agent_pid=agent_id, limit=limit)}

        # ========== Metrics ==========

        @app.get("/api/v1/metrics", tags=["Metrics"])
        async def get_metrics():
            """获取指标"""
            uptime = (datetime.now() - self.start_time).total_seconds()

            return {
                "uptime_seconds": uptime,
                "metrics": self.metrics.get_stats()
            }

        @app.get("/api/v1/metrics/prometheus", tags=["Metrics"])
        async def get_metrics_prometheus():
            """Prometheus 格式指标"""
            return self.metrics.export_prometheus()

        # ========== System ==========

        @app.get("/ui", response_class=HTMLResponse, tags=["System"],
                 include_in_schema=False)
        async def dashboard_ui():
            """控制面板（自包含单文件，无 CDN 依赖）"""
            index = Path(__file__).parent / "static" / "index.html"
            if not index.exists():
                raise HTTPException(status_code=404, detail="dashboard not installed")
            return HTMLResponse(index.read_text(encoding="utf-8"))

        @app.get("/api/v1/status", response_model=StatusResponse, tags=["System"])
        async def get_status():
            """获取系统状态"""
            uptime = (datetime.now() - self.start_time).total_seconds()

            return StatusResponse(
                running=True,
                agents_count=len(self.kernel.list_agents()),
                uptime_seconds=uptime,
                version=KERNEL_VERSION,
                metrics=self.metrics.get_stats()
            )


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """运行服务器（默认仅 loopback）"""
    api = AgentOSKernelAPI(host=host, port=port)
    app = api.create_app()

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
