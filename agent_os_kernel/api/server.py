# -*- coding: utf-8 -*-
"""
REST API Server

提供 REST API 接口，支持：
1. Agent 管理
2. 任务提交
3. 状态查询
4. 指标监控
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import uvicorn

from agent_os_kernel import AgentOSKernel, create_metrics_collector
from agent_os_kernel.core.events import EventBus, EventType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    metrics: Dict[str, Any]


# ========== API Server ==========

class AgentOSKernelAPI:
    """API 服务器"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.kernel = None
        self.metrics = create_metrics_collector()
        self.start_time = datetime.now()
        self._app = None
    
    def create_app(self) -> FastAPI:
        """创建 FastAPI 应用"""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 启动
            self.kernel = AgentOSKernel()
            logger.info("Kernel started")
            yield
            # 停止
            self.kernel.stop()
            logger.info("Kernel stopped")
        
        app = FastAPI(
            title="Agent OS Kernel API",
            description="AI Agent Operating System Kernel API",
            version="1.0.0",
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
                "version": "1.0.0",
                "docs": "/docs"
            }
        
        @app.get("/health", tags=["Health"])
        async def health():
            return {"status": "healthy"}
        
        # ========== Agent Management ==========
        
        @app.post("/api/v1/agents", response_model=AgentResponse, tags=["Agents"])
        async def create_agent(request: AgentCreateRequest):
            """创建 Agent"""
            agent_id = self.kernel.spawn_agent(
                name=request.name,
                task=request.task,
                priority=request.priority
            )
            
            self.metrics.counter("agents_created_total")
            
            agent = self.kernel.get_agent(agent_id)
            
            return AgentResponse(
                agent_id=agent_id,
                name=request.name,
                task=request.task,
                priority=request.priority,
                state="created",
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
                    task=a["task"],
                    priority=a["priority"],
                    state=a.get("state", "unknown"),
                    created_at=a.get("created_at", datetime.now().isoformat())
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
                created_at=agent.get("created_at", datetime.now().isoformat())
            )
        
        @app.delete("/api/v1/agents/{agent_id}", tags=["Agents"])
        async def delete_agent(agent_id: str):
            """删除 Agent"""
            # 实现删除逻辑
            self.metrics.counter("agents_deleted_total")
            return {"status": "deleted", "agent_id": agent_id}
        
        # ========== Tasks ==========
        
        @app.post("/api/v1/tasks", response_model=TaskResponse, tags=["Tasks"])
        async def submit_task(request: TaskSubmitRequest):
            """提交任务"""
            task_id = f"task-{datetime.now().timestamp()}"
            
            # 实现任务提交
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
            # 实现任务查询
            return TaskResponse(
                task_id=task_id,
                agent_id="",
                status="unknown"
            )
        
        # ========== Context ==========
        
        @app.post("/api/v1/context", tags=["Context"])
        async def add_context(request: ContextRequest):
            """添加上下文"""
            from agent_os_kernel import ContextManager
            cm = ContextManager()
            
            page_id = cm.allocate_page(
                agent_pid=request.agent_id,
                content=request.content,
                importance=0.5
            )
            
            return {"page_id": page_id, "status": "added"}
        
        @app.get("/api/v1/context/{agent_id}", tags=["Context"])
        async def get_context(agent_id: str):
            """获取上下文"""
            from agent_os_kernel import ContextManager
            cm = ContextManager()
            
            context = cm.get_agent_context(agent_id)
            
            return {"context": context}
        
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
        
        @app.get("/api/v1/status", response_model=StatusResponse, tags=["System"])
        async def get_status():
            """获取系统状态"""
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            return StatusResponse(
                running=True,
                agents_count=len(self.kernel.list_agents()),
                uptime_seconds=uptime,
                metrics=self.metrics.get_stats()
            )


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """运行服务器"""
    api = AgentOSKernelAPI(host=host, port=port)
    app = api.create_app()
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
