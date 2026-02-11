# -*- coding: utf-8 -*-
"""Agent Definition - 完整的 Agent 定义

参考 CrewAI 设计，添加 role/goal/backstory
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from datetime import timezone, timezone, timedelta


class AgentStatus(Enum):
    """Agent 状态"""
    CREATED = "created"
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class AgentConstraints:
    """Agent 约束条件"""
    max_iterations: int = 100
    max_execution_time: float = 300.0  # 秒
    allowed_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)
    max_cost_usd: float = 10.0
    require_approval: bool = False
    output_format: Optional[str] = None
    memory_retention: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "max_iterations": self.max_iterations,
            "max_execution_time": self.max_execution_time,
            "allowed_tools": self.allowed_tools,
            "blocked_tools": self.blocked_tools,
            "max_cost_usd": self.max_cost_usd,
            "require_approval": self.require_approval,
            "output_format": self.output_format,
            "memory_retention": self.memory_retention,
        }


@dataclass
class AgentDefinition:
    """Agent 定义 - 完整的 Agent 配置
    
    参考 CrewAI 的 role/goal/backstory 设计
    """
    
    # 基础信息
    name: str
    role: str  # 角色，如 "Senior Researcher"
    goal: str  # 目标，如 "Discover breakthrough technologies"
    backstory: str  # 背景，如 "Expert researcher with 10 years experience"
    
    # 可选覆盖
    agent_id: Optional[str] = None
    description: Optional[str] = None
    
    # 工具
    tools: List[str] = field(default_factory=list)
    
    # 约束
    constraints: AgentConstraints = field(default_factory=AgentConstraints)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 创建时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "agent_id": self.agent_id or self.name.lower().replace(" ", "_"),
            "name": self.name,
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "description": self.description or f"{self.role}: {self.goal}",
            "tools": self.tools,
            "constraints": self.constraints.to_dict(),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentDefinition':
        """从字典创建"""
        constraints_data = data.get("constraints", {})
        if isinstance(constraints_data, dict):
            constraints = AgentConstraints(**constraints_data)
        else:
            constraints = constraints_data
        
        return cls(
            agent_id=data.get("agent_id"),
            name=data["name"],
            role=data["role"],
            goal=data["goal"],
            backstory=data["backstory"],
            description=data.get("description"),
            tools=data.get("tools", []),
            constraints=constraints,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
        )
    
    def __repr__(self) -> str:
        return f"AgentDefinition({self.name}, role={self.role})"


@dataclass
class TaskDefinition:
    """Task 定义 - 完整的 Task 配置
    
    参考 CrewAI 的 Task 设计
    """
    
    description: str  # 任务描述
    expected_output: str  # 预期输出
    agent_name: str  # 执行的 Agent 名称
    
    # 依赖
    depends_on: List[str] = field(default_factory=list)  # 依赖的 Task
    
    # 优先级和配置
    priority: int = 50
    timeout: float = 300.0  # 超时时间
    
    # 验证
    validation_criteria: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "description": self.description,
            "expected_output": self.expected_output,
            "agent_name": self.agent_name,
            "depends_on": self.depends_on,
            "priority": self.priority,
            "timeout": self.timeout,
            "validation_criteria": self.validation_criteria,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskDefinition':
        return cls(
            description=data["description"],
            expected_output=data["expected_output"],
            agent_name=data["agent_name"],
            depends_on=data.get("depends_on", []),
            priority=data.get("priority", 50),
            timeout=data.get("timeout", 300.0),
            validation_criteria=data.get("validation_criteria"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CrewDefinition:
    """Crew 定义 - Agent 团队配置
    
    参考 CrewAI 的 Crew 设计
    """
    
    name: str
    agents: List[AgentDefinition]
    tasks: List[TaskDefinition]
    
    # 编排模式
    process_mode: str = "sequential"  # sequential, hierarchical, consensual
    
    # 共享配置
    memory_enabled: bool = True
    embedder: Optional[Dict] = None
    max_iterations: int = 10
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "agents": [a.to_dict() for a in self.agents],
            "tasks": [t.to_dict() for t in self.tasks],
            "process_mode": self.process_mode,
            "memory_enabled": self.memory_enabled,
            "embedder": self.embedder,
            "max_iterations": self.max_iterations,
        }
