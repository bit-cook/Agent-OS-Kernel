# -*- coding: utf-8 -*-
"""Tool Memory - 工具记忆

记录 Agent 的工具使用历史，支持规划和优化。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from uuid import uuid4
import json

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """工具调用状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolCall:
    """工具调用记录"""
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    status: ToolStatus
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    error: Optional[str] = None


class ToolMemory:
    """工具记忆系统"""
    
    def __init__(
        self,
        max_history: int = 1000,
        retention_days: int = 30
    ):
        """
        初始化工具记忆系统
        
        Args:
            max_history: 最大历史记录数
            retention_days: 保留天数
        """
        self.max_history = max_history
        self.retention_days = retention_days
        
        self._calls: List[ToolCall] = []
        self._tool_stats: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        
        logger.info(f"ToolMemory initialized: max_history={max_history}")
    
    async def record_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        status: ToolStatus,
        duration_ms: float,
        agent_id: str = None,
        task_id: str = None,
        error: str = None
    ) -> str:
        """
        记录工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 调用参数
            result: 调用结果
            status: 状态
            duration_ms: 耗时
            agent_id: Agent ID
            task_id: 任务 ID
            error: 错误信息
            
        Returns:
            调用 ID
        """
        call_id = str(uuid4())
        
        call = ToolCall(
            call_id=call_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
            duration_ms=duration_ms,
            agent_id=agent_id,
            task_id=task_id,
            error=error
        )
        
        async with self._lock:
            self._calls.append(call)
            
            # 更新统计
            if tool_name not in self._tool_stats:
                self._tool_stats[tool_name] = {
                    "total_calls": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "total_duration_ms": 0,
                    "avg_duration_ms": 0
                }
            
            stats = self._tool_stats[tool_name]
            stats["total_calls"] += 1
            if status == ToolStatus.SUCCESS:
                stats["success_count"] += 1
            else:
                stats["failed_count"] += 1
            stats["total_duration_ms"] += duration_ms
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
            
            # 清理旧记录
            if len(self._calls) > self.max_history:
                self._calls = self._calls[-self.max_history:]
        
        logger.debug(f"Tool call recorded: {tool_name} -> {call_id}")
        
        return call_id
    
    async def get_tool_history(
        self,
        tool_name: str = None,
        agent_id: str = None,
        limit: int = 100
    ) -> List[ToolCall]:
        """
        获取工具调用历史
        
        Args:
            tool_name: 工具名称过滤
            agent_id: Agent ID 过滤
            limit: 返回数量
            
        Returns:
            调用记录列表
        """
        async with self._lock:
            filtered = self._calls
            
            if tool_name:
                filtered = [c for c in filtered if c.tool_name == tool_name]
            
            if agent_id:
                filtered = [c for c in filtered if c.agent_id == agent_id]
            
            return filtered[-limit:]
    
    async def get_tool_statistics(self, tool_name: str = None) -> Dict:
        """
        获取工具统计
        
        Args:
            tool_name: 工具名称
            
        Returns:
            统计信息
        """
        async with self._lock:
            if tool_name:
                return self._tool_stats.get(tool_name, {})
            
            total_calls = sum(s["total_calls"] for s in self._tool_stats.values())
            total_success = sum(s["success_count"] for s in self._tool_stats.values())
            total_failed = sum(s["failed_count"] for s in self._tool_stats.values())
            
            return {
                "tools_count": len(self._tool_stats),
                "total_calls": total_calls,
                "success_rate": (total_success / total_calls * 100) if total_calls > 0 else 0,
                "tool_stats": self._tool_stats
            }
    
    async def get_frequently_used_tools(self, limit: int = 10) -> List[Dict]:
        """
        获取最常使用的工具
        
        Args:
            limit: 返回数量
            
        Returns:
            工具列表
        """
        async with self._lock:
            sorted_tools = sorted(
                self._tool_stats.items(),
                key=lambda x: x[1]["total_calls"],
                reverse=True
            )
            
            return [
                {"tool_name": name, **stats}
                for name, stats in sorted_tools[:limit]
            ]
    
    async def get_failed_tools(self, limit: int = 10) -> List[Dict]:
        """
        获取失败率高的工具
        
        Args:
            limit: 返回数量
            
        Returns:
            工具列表
        """
        async with self._lock:
            failed_tools = [
                {"tool_name": name, **stats}
                for name, stats in self._tool_stats.items()
                if stats["failed_count"] > 0
            ]
            
            return sorted(
                failed_tools,
                key=lambda x: x["failed_count"] / x["total_calls"] if x["total_calls"] > 0 else 0,
                reverse=True
            )[:limit]
    
    async def get_slow_tools(self, threshold_ms: float = 1000, limit: int = 10) -> List[Dict]:
        """
        获取慢速工具
        
        Args:
            threshold_ms: 耗时阈值
            limit: 返回数量
            
        Returns:
            工具列表
        """
        async with self._lock:
            slow_tools = [
                {"tool_name": name, **stats}
                for name, stats in self._tool_stats.items()
                if stats["avg_duration_ms"] > threshold_ms
            ]
            
            return sorted(
                slow_tools,
                key=lambda x: x["avg_duration_ms"],
                reverse=True
            )[:limit]
    
    async def suggest_tools_for_task(self, task_description: str) -> List[str]:
        """
        为任务推荐工具
        
        Args:
            task_description: 任务描述
            
        Returns:
            推荐的工具列表
        """
        # 简单的关键词匹配
        task_lower = task_description.lower()
        suggestions = []
        
        if "search" in task_lower or "查找" in task_lower:
            suggestions.append("search")
        
        if "read" in task_lower or "读取" in task_lower:
            suggestions.append("read_file")
        
        if "write" in task_lower or "写入" in task_lower:
            suggestions.append("write_file")
        
        if "calculate" in task_lower or "计算" in task_lower:
            suggestions.append("calculator")
        
        if "python" in task_lower or "代码" in task_lower:
            suggestions.append("execute_python")
        
        # 添加最常用的工具
        top_tools = await self.get_frequently_used_tools(3)
        for tool in top_tools:
            if tool["tool_name"] not in suggestions:
                suggestions.append(tool["tool_name"])
        
        return suggestions[:5]
    
    def clear_history(self):
        """清空历史"""
        self._calls.clear()
        self._tool_stats.clear()
        logger.info("Tool history cleared")
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_calls": len(self._calls),
            "tools_count": len(self._tool_stats),
            "retention_days": self.retention_days,
            "max_history": self.max_history
        }
