# -*- coding: utf-8 -*-
"""FastAPI Web Server

提供 RESTful API 接口：
- Agent 管理
- 状态监控
- 检查点操作
- 系统配置
"""

import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_os_kernel import AgentOSKernel
from agent_os_kernel.core.types import AgentState, Checkpoint


# ========== Pydantic Models ==========

class AgentCreateRequest(BaseModel):
    """创建 Agent 请求"""
    name: str = Field(..., min_length=1, max_length=128, description="Agent 名称")
    task: str = Field(..., description="任务描述")
    priority: int = Field(default=30, ge=0, le=100, description="优先级")


class AgentResponse(BaseModel):
    """Agent 响应"""
    pid: str
    name: str
    state: str
    priority: int
    created_at: Optional[str] = None
    active: Optional[str] = None


class StatusResponse(BaseModel):
    """系统状态响应"""
    status: str
    overall_health: str
    version: str
    active_agents: int
    total_agents: int
    cpu_usage: float
    memory_usage: float
    gateway_latency: Optional[int] = None


class CheckpointResponse(BaseModel):
    """检查点响应"""
    checkpoint_id: str
    agent_pid: str
    agent_name: str
    description: str
    timestamp: str


class CheckpointCreateRequest(BaseModel):
    """创建检查点请求"""
    description: str = Field(default="", description="检查点描述")


class MetricsResponse(BaseModel):
    """指标响应"""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    context_hit_rate: float
    swap_count: int
    active_agents: int
    queued_agents: int


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """工具调用响应"""
    success: bool
    result: Any
    error: Optional[str] = None


# ========== 全局内核实例 ==========

_kernel: Optional[AgentOSKernel] = None


def get_kernel() -> AgentOSKernel:
    """获取内核实例"""
    global _kernel
    if _kernel is None:
        _kernel = AgentOSKernel()
    return _kernel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    global _kernel
    _kernel = AgentOSKernel()
    print("🚀 Agent-OS-Kernel API Server started")
    yield
    print("👋 Agent-OS-Kernel API Server stopped")


# ========== 创建 FastAPI App ==========

def create_app(title: str = "Agent-OS-Kernel API",
               description: str = "AI Agent Operating System Kernel API",
               version: str = "2.0.0") -> FastAPI:
    
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ========== API 端点 ==========
    
    @app.get("/", include_in_schema=False)
    async def root():
        """API 根路径"""
        return {
            "name": "Agent-OS-Kernel API",
            "version": version,
            "docs": "/docs",
            "health": "/api/health"
        }
    
    @app.get("/api/health")
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": version
        }
    
    # ========== Agent Management ==========
    
    @app.get("/api/agents", response_model=List[AgentResponse])
    async def list_agents(kernel: AgentOSKernel = Depends(get_kernel)):
        """列出所有 Agent"""
        agents = kernel.scheduler.get_active_processes()
        return [
            AgentResponse(
                pid=p.pid,
                name=p.name,
                state=p.state.value,
                priority=p.priority,
                created_at=datetime.fromtimestamp(p.created_at).isoformat() if hasattr(p, 'created_at') else None,
                active=p.active if hasattr(p, 'active') else None
            )
            for p in agents
        ]
    
    @app.post("/api/agents", response_model=AgentResponse, status_code=201)
    async def create_agent(request: AgentCreateRequest, kernel: AgentOSKernel = Depends(get_kernel)):
        """创建 Agent"""
        pid = kernel.spawn_agent(
            name=request.name,
            task=request.task,
            priority=request.priority
        )
        
        if not pid:
            raise HTTPException(status_code=500, detail="Failed to create agent")
        
        process = kernel.scheduler.get_process(pid)
        return AgentResponse(
            pid=pid,
            name=process.name,
            state=process.state.value,
            priority=process.priority
        )
    
    @app.get("/api/agents/{agent_pid}", response_model=AgentResponse)
    async def get_agent(agent_pid: str, kernel: AgentOSKernel = Depends(get_kernel)):
        """获取 Agent 详情"""
        process = kernel.scheduler.get_process(agent_pid)
        if process is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return AgentResponse(
            pid=process.pid,
            name=process.name,
            state=process.state.value,
            priority=process.priority,
            created_at=datetime.fromtimestamp(process.created_at).isoformat() if hasattr(process, 'created_at') else None,
            active=process.active if hasattr(process, 'active') else None
        )
    
    @app.delete("/api/agents/{agent_pid}", status_code=204)
    async def terminate_agent(agent_pid: str, kernel: AgentOSKernel = Depends(get_kernel)):
        """终止 Agent"""
        success = kernel.terminate_agent(agent_pid)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found or already terminated")
    
    # ========== Checkpoints ==========
    
    @app.get("/api/checkpoints", response_model=List[CheckpointResponse])
    async def list_checkpoints(agent_pid: Optional[str] = Query(None, description="过滤特定 Agent"), kernel: AgentOSKernel = Depends(get_kernel)):
        """列出检查点"""
        checkpoints = kernel.storage.list_checkpoints(agent_pid)
        return [
            CheckpointResponse(
                checkpoint_id=cp.get('checkpoint_id', ''),
                agent_pid=cp.get('agent_pid', ''),
                agent_name=cp.get('agent_name', ''),
                description=cp.get('description', ''),
                timestamp=cp.get('timestamp', datetime.utcnow().isoformat())
            )
            for cp in checkpoints
        ]
    
    @app.post("/api/agents/{agent_pid}/checkpoints", response_model=CheckpointResponse, status_code=201)
    async def create_checkpoint(agent_pid: str, request: CheckpointCreateRequest, kernel: AgentOSKernel = Depends(get_kernel)):
        """创建检查点"""
        checkpoint_id = kernel.create_checkpoint(agent_pid, request.description)
        if not checkpoint_id:
            raise HTTPException(status_code=500, detail="Failed to create checkpoint")
        
        checkpoint = kernel.storage.get_checkpoint(checkpoint_id)
        return CheckpointResponse(
            checkpoint_id=checkpoint_id,
            agent_pid=agent_pid,
            agent_name=checkpoint.get('agent_name', '') if checkpoint else '',
            description=request.description,
            timestamp=datetime.utcnow().isoformat()
        )
    
    @app.post("/api/checkpoints/{checkpoint_id}/restore", response_model=AgentResponse, status_code=201)
    async def restore_checkpoint(checkpoint_id: str, kernel: AgentOSKernel = Depends(get_kernel)):
        """从检查点恢复"""
        new_pid = kernel.restore_checkpoint(checkpoint_id)
        if not new_pid:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        process = kernel.scheduler.get_process(new_pid)
        return AgentResponse(
            pid=new_pid,
            name=process.name,
            state=process.state.value,
            priority=process.priority
        )
    
    # ========== System Status ==========
    
    @app.get("/api/status", response_model=StatusResponse)
    async def get_status(kernel: AgentOSKernel = Depends(get_kernel)):
        """获取系统状态"""
        status = kernel.get_openclaw_status()
        return StatusResponse(
            status=status.get('status', 'unknown'),
            overall_health=status.get('overall_health', 'unknown'),
            version=status.get('version', ''),
            active_agents=len(kernel.scheduler.get_active_processes()),
            total_agents=len(kernel.scheduler.processes),
            cpu_usage=status.get('system', {}).get('cpu_percent', 0),
            memory_usage=status.get('system', {}).get('memory_percent', 0),
            gateway_latency=status.get('gateway_latency')
        )
    
    @app.get("/api/metrics", response_model=MetricsResponse)
    async def get_metrics(kernel: AgentOSKernel = Depends(get_kernel)):
        """获取性能指标"""
        metrics = kernel.metrics.get_metrics(
            active_agents=len(kernel.scheduler.get_active_processes())
        )
        return MetricsResponse(
            timestamp=metrics.timestamp.isoformat(),
            cpu_usage=metrics.cpu_usage,
            memory_usage=metrics.memory_usage,
            context_hit_rate=metrics.context_hit_rate,
            swap_count=metrics.swap_count,
            active_agents=metrics.active_agents,
            queued_agents=metrics.queued_agents
        )
    
    # ========== Tools ==========
    
    @app.get("/api/tools", response_model=List[Dict])
    async def list_tools(kernel: AgentOSKernel = Depends(get_kernel)):
        """列出可用工具"""
        return kernel.tool_registry.list_tools()
    
    @app.post("/api/tools/execute", response_model=ToolCallResponse)
    async def execute_tool(request: ToolCallRequest, kernel: AgentOSKernel = Depends(get_kernel)):
        """执行工具"""
        result = kernel.tool_registry.execute(request.tool_name, **request.parameters)
        if result.get('success'):
            return ToolCallResponse(success=True, result=result.get('data'))
        return ToolCallResponse(success=False, result=None, error=result.get('error'))
    
    # ========== Statistics ==========
    
    @app.get("/api/stats")
    async def get_statistics(kernel: AgentOSKernel = Depends(get_kernel)):
        """获取统计信息"""
        return kernel.get_statistics()
    
    @app.get("/api/storage/stats")
    async def get_storage_stats(kernel: AgentOSKernel = Depends(get_kernel)):
        """获取存储统计"""
        return kernel.storage.get_stats()
    
    @app.get("/api/audit-logs")
    async def get_audit_logs(agent_pid: Optional[str] = Query(None), limit: int = Query(100, le=1000), kernel: AgentOSKernel = Depends(get_kernel)):
        """获取审计日志"""
        return kernel.storage.get_audit_logs(agent_pid, limit)
    
    return app


# ========== 主入口 ==========

app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
