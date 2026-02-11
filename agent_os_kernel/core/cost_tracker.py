# -*- coding: utf-8 -*-
"""Cost Tracker - 成本追踪

参考 AgentOps 的成本追踪功能
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import logging
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class CostEntry:
    """成本条目"""
    
    id: str
    provider: str  # openai, anthropic, deepseek, etc.
    model: str
    input_tokens: int
    output_tokens: int
    
    # 成本信息
    input_cost: float  # USD
    output_cost: float  # USD
    total_cost: float
    
    # 元数据
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": self.total_cost,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CostLimit:
    """成本限制"""
    
    max_cost_usd: float = 10.0  # 最大成本
    max_tokens: int = 100000  # 最大 token
    period_hours: Optional[int] = None  # 周期 (小时)
    
    def to_dict(self) -> Dict:
        return {
            "max_cost_usd": self.max_cost_usd,
            "max_tokens": self.max_tokens,
            "period_hours": self.period_hours,
        }


class CostTracker:
    """成本追踪器
    
    功能:
    - 追踪 API 调用成本
    - 设置成本限制
    - 生成成本报告
    """
    
    # 定价表 (USD per 1M tokens)
    PRICING = {
        "openai": {
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            "o1": {"input": 15.0, "output": 60.0},
            "o3-mini": {"input": 1.0, "output": 10.0},
        },
        "anthropic": {
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-opus-4": {"input": 15.0, "output": 75.0},
            "claude-haiku": {"input": 0.25, "output": 1.25},
        },
        "deepseek": {
            "deepseek-chat": {"input": 0.14, "output": 0.28},  # V3
            "deepseek-reasoner": {"input": 0.55, "output": 2.19},  # R1
        },
        "google": {
            "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
            "gemini-1.5-flash": {"input": 0.075, "output": 0.3},
        },
        "groq": {
            "llama-3.3-70b": {"input": 0.59, "output": 0.79},
            "mixtral-8x7b": {"input": 0.24, "output": 0.24},
        },
        "ollama": {
            "qwen2.5": {"input": 0.0, "output": 0.0},  # 本地
            "llama3": {"input": 0.0, "output": 0.0},  # 本地
        },
        "minimax": {
            "abab6.5s-chat": {"input": 0.1, "output": 0.1},
            "abab6.5-chat": {"input": 0.2, "output": 0.2},
        },
        "kimi": {
            "kimi-vl": {"input": 0.1, "output": 0.1},
            "kimi-k1": {"input": 0.1, "output": 0.1},
        },
        "qwen": {
            "qwen-turbo": {"input": 0.1, "output": 0.3},
            "qwen-plus": {"input": 0.2, "output": 0.6},
            "qwen-max": {"input": 0.4, "output": 1.2},
        },
    }
    
    def __init__(
        self,
        limits: Optional[CostLimit] = None,
        default_provider: str = "openai"
    ):
        """初始化成本追踪器"""
        self.limits = limits or CostLimit()
        self.default_provider = default_provider
        
        self._entries: List[CostEntry] = []
        self._session_totals: Dict[str, Dict[str, Any]] = {}
        self._agent_totals: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        
        logger.info(
            f"CostTracker initialized "
            f"(max_cost=${self.limits.max_cost_usd}, max_tokens={self.limits.max_tokens})"
        )
    
    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, float]:
        """计算成本"""
        # 获取定价
        provider_pricing = self.PRICING.get(provider, {})
        model_pricing = provider_pricing.get(model, {"input": 1.0, "output": 3.0})
        
        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        total = input_cost + output_cost
        
        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total,
        }
    
    def record(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> CostEntry:
        """记录成本"""
        with self._lock:
            # 计算成本
            costs = self.calculate_cost(
                provider, model, input_tokens, output_tokens
            )
            
            entry = CostEntry(
                id=str(uuid4())[:8],
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost=costs["input_cost"],
                output_cost=costs["output_cost"],
                total_cost=costs["total_cost"],
                agent_id=agent_id,
                task_id=task_id,
                session_id=session_id,
            )
            
            self._entries.append(entry)
            
            # 更新会话总计
            if session_id:
                if session_id not in self._session_totals:
                    self._session_totals[session_id] = {
                        "cost": 0.0,
                        "tokens": 0,
                        "requests": 0
                    }
                self._session_totals[session_id]["cost"] += entry.total_cost
                self._session_totals[session_id]["tokens"] += (
                    input_tokens + output_tokens
                )
                self._session_totals[session_id]["requests"] += 1
            
            # 更新 Agent 总计
            if agent_id:
                if agent_id not in self._agent_totals:
                    self._agent_totals[agent_id] = {
                        "cost": 0.0,
                        "tokens": 0,
                        "requests": 0
                    }
                self._agent_totals[agent_id]["cost"] += entry.total_cost
                self._agent_totals[agent_id]["tokens"] += (
                    input_tokens + output_tokens
                )
                self._agent_totals[agent_id]["requests"] += 1
            
            # 检查限制
            self._check_limits(session_id, agent_id)
            
            logger.debug(f"Cost recorded: {entry.total_cost:.4f} ({provider}/{model})")
            return entry
    
    def _check_limits(
        self,
        session_id: Optional[str],
        agent_id: Optional[str]
    ):
        """检查成本限制"""
        # 检查全局限制
        total_cost = sum(e.total_cost for e in self._entries)
        total_tokens = sum(
            e.input_tokens + e.output_tokens 
            for e in self._entries
        )
        
        if total_cost > self.limits.max_cost_usd:
            logger.warning(
                f"⚠️ Cost limit exceeded: ${total_cost:.2f} > ${self.limits.max_cost_usd}"
            )
        
        if total_tokens > self.limits.max_tokens:
            logger.warning(
                f"⚠️ Token limit exceeded: {total_tokens} > {self.limits.max_tokens}"
            )
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话统计"""
        return self._session_totals.get(session_id)
    
    def get_agent_stats(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 统计"""
        return self._agent_totals.get(agent_id)
    
    def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计"""
        total_cost = sum(e.total_cost for e in self._entries)
        total_tokens = sum(
            e.input_tokens + e.output_tokens 
            for e in self._entries
        )
        
        # 按 Provider 统计
        by_provider: Dict[str, Dict[str, Any]] = {}
        for entry in self._entries:
            if entry.provider not in by_provider:
                by_provider[entry.provider] = {
                    "cost": 0.0,
                    "tokens": 0,
                    "requests": 0
                }
            by_provider[entry.provider]["cost"] += entry.total_cost
            by_provider[entry.provider]["tokens"] += (
                entry.input_tokens + entry.output_tokens
            )
            by_provider[entry.provider]["requests"] += 1
        
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_requests": len(self._entries),
            "total_sessions": len(self._session_totals),
            "total_agents": len(self._agent_totals),
            "by_provider": by_provider,
            "limits": self.limits.to_dict(),
        }
    
    def get_report(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> str:
        """生成成本报告"""
        if session_id:
            stats = self._session_totals.get(session_id)
            if stats:
                return f"""## Session Report: {session_id}

- **Total Cost**: ${stats["cost"]:.4f}
- **Total Tokens**: {stats["tokens"]:,}
- **Total Requests**: {stats["requests"]}
"""
        
        if agent_id:
            stats = self._agent_totals.get(agent_id)
            if stats:
                return f"""## Agent Report: {agent_id}

- **Total Cost**: ${stats["cost"]:.4f}
- **Total Tokens**: {stats["tokens"]:,}
- **Total Requests**: {stats["requests"]}
"""
        return "No data available"
    
    def export_csv(self, filepath: str):
        """导出为 CSV"""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "id", "provider", "model", "input_tokens", "output_tokens",
                "input_cost", "output_cost", "total_cost",
                "agent_id", "task_id", "session_id", "created_at"
            ])
            writer.writeheader()
            for entry in self._entries:
                writer.writerow(entry.to_dict())
        
        logger.info(f"Cost data exported to {filepath}")
    
    def reset(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ):
        """重置统计"""
        with self._lock:
            if session_id:
                if session_id in self._session_totals:
                    del self._session_totals[session_id]
                self._entries = [
                    e for e in self._entries 
                    if e.session_id != session_id
                ]
            
            if agent_id:
                if agent_id in self._agent_totals:
                    del self._agent_totals[agent_id]
                self._entries = [
                    e for e in self._entries 
                    if e.agent_id != agent_id
                ]
            
            logger.info(f"CostTracker reset for session={session_id}, agent={agent_id}")
