# -*- coding: utf-8 -*-
"""
任务去重器模块 - Agent-OS-Kernel

提供任务去重功能，防止重复执行相同的任务。
适用于并发场景、事件处理和API调用去重。
"""

from typing import Dict, Any, Optional, Callable, Set, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
import hashlib
import json
import time
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class DeduplicationPolicy(Enum):
    """去重策略"""
    EXACT_MATCH = "exact_match"  # 完全匹配
    PARTIAL_MATCH = "partial_match"  # 部分匹配（忽略某些字段）
    TIME_WINDOW = "time_window"  # 时间窗口内去重
    CUSTOM = "custom"  # 自定义


@dataclass
class DeduplicationConfig:
    """去重配置"""
    policy: DeduplicationPolicy = DeduplicationPolicy.EXACT_MATCH
    ignore_fields: List[str] = field(default_factory=list)  # 部分匹配时忽略的字段
    time_window_seconds: float = 60.0  # 时间窗口（秒）
    max_entries: int = 10000  # 最大缓存条目数
    cleanup_interval_seconds: float = 300.0  # 清理间隔（秒）
    custom_key_generator: Optional[Callable] = None  # 自定义key生成器


@dataclass
class DedupeEntry:
    """去重条目"""
    entry_id: str
    key: str
    created_at: datetime
    expires_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    execution_count: int = 1
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expires_at


class TaskDeduplicator:
    """任务去重器"""
    
    def __init__(self, config: Optional[DeduplicationConfig] = None):
        self.config = config or DeduplicationConfig()
        self._entries: Dict[str, DedupeEntry] = {}
        self._processing: Set[str] = set()  # 正在处理的任务
        self._lock = asyncio.Lock()
        self._last_cleanup = datetime.now()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def _generate_key(self, task_data: Dict[str, Any]) -> str:
        """生成任务key"""
        if self.config.custom_key_generator:
            return self.config.custom_key_generator(task_data)
        
        if self.config.policy == DeduplicationPolicy.EXACT_MATCH:
            # 完全匹配：序列化整个字典
            serialized = json.dumps(task_data, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode()).hexdigest()
        
        elif self.config.policy == DeduplicationPolicy.PARTIAL_MATCH:
            # 部分匹配：忽略指定字段
            filtered = {k: v for k, v in task_data.items() 
                       if k not in self.config.ignore_fields}
            serialized = json.dumps(filtered, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode()).hexdigest()
        
        elif self.config.policy == DeduplicationPolicy.TIME_WINDOW:
            # 时间窗口：基于任务类型+关键字段生成key
            key_parts = []
            for field in self.config.ignore_fields:
                if field in task_data:
                    key_parts.append(f"{field}:{task_data[field]}")
            key_str = "|".join(key_parts)
            return hashlib.md5(key_str.encode()).hexdigest()
        
        else:
            # 默认使用完整序列化
            serialized = json.dumps(task_data, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode()).hexdigest()
    
    def _create_entry(self, key: str, data: Dict[str, Any]) -> DedupeEntry:
        """创建去重条目"""
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.config.time_window_seconds)
        return DedupeEntry(
            entry_id=str(uuid.uuid4())[:8],
            key=key,
            created_at=now,
            expires_at=expires_at,
            data=data
        )
    
    async def acquire(self, task_data: Dict[str, Any]) -> bool:
        """
        尝试获取执行许可
        
        Args:
            task_data: 任务数据
            
        Returns:
            True if can execute, False if duplicate
        """
        key = self._generate_key(task_data)
        
        async with self._lock:
            # 检查是否正在处理
            if key in self._processing:
                logger.debug(f"Task {key} is already being processed")
                return False
            
            # 检查是否存在有效条目
            if key in self._entries:
                entry = self._entries[key]
                if not entry.is_expired():
                    entry.execution_count += 1
                    logger.debug(f"Task {key} duplicated (count: {entry.execution_count})")
                    return False
                else:
                    # 过期，移除旧条目
                    del self._entries[key]
            
            # 清理过期条目
            await self._cleanup_if_needed()
            
            # 限制最大条目数
            if len(self._entries) >= self.config.max_entries:
                # 移除最旧的条目
                oldest_key = min(self._entries.keys(), 
                               key=lambda k: self._entries[k].created_at)
                del self._entries[oldest_key]
            
            # 标记为正在处理
            self._processing.add(key)
            self._entries[key] = self._create_entry(key, task_data)
            return True
    
    async def release(self, task_data: Dict[str, Any], 
                     success: bool = True) -> None:
        """释放执行许可"""
        key = self._generate_key(task_data)
        
        async with self._lock:
            self._processing.discard(key)
            if not success:
                # 失败时移除条目，允许重试
                self._entries.pop(key, None)
    
    async def execute(self, task_data: Dict[str, Any],
                     executor: Callable,
                     *args, **kwargs) -> Any:
        """
        安全执行任务（自动处理去重）
        
        Args:
            task_data: 任务数据
            executor: 执行函数
            *args, **kwargs: 执行参数
            
        Returns:
            执行结果
            
        Raises:
            DuplicateTaskError: 如果是重复任务
        """
        if not await self.acquire(task_data):
            raise DuplicateTaskError(
                f"Duplicate task detected: {self._generate_key(task_data)}"
            )
        
        try:
            if asyncio.iscoroutinefunction(executor):
                result = await executor(*args, **kwargs)
            else:
                result = executor(*args, **kwargs)
            await self.release(task_data, success=True)
            return result
        except Exception as e:
            await self.release(task_data, success=False)
            raise
    
    async def is_duplicate(self, task_data: Dict[str, Any]) -> bool:
        """检查是否是重复任务"""
        key = self._generate_key(task_data)
        async with self._lock:
            if key in self._processing:
                return True
            if key in self._entries:
                entry = self._entries[key]
                if not entry.is_expired():
                    return True
            return False
    
    async def get_duplicate_count(self, task_data: Dict[str, Any]) -> int:
        """获取任务重复次数"""
        key = self._generate_key(task_data)
        async with self._lock:
            if key in self._entries:
                return self._entries[key].execution_count
            return 0
    
    async def get_status(self) -> Dict[str, Any]:
        """获取去重器状态"""
        async with self._lock:
            active_count = len(self._processing)
            cached_count = len(self._entries)
            
            # 统计过期条目
            expired_count = sum(1 for e in self._entries.values() 
                              if e.is_expired())
            
            return {
                "active_processing": active_count,
                "cached_entries": cached_count,
                "expired_entries": expired_count,
                "max_entries": self.config.max_entries,
                "policy": self.config.policy.value,
                "time_window_seconds": self.config.time_window_seconds
            }
    
    async def clear(self, older_than_seconds: Optional[float] = None) -> int:
        """清理缓存条目"""
        async with self._lock:
            if older_than_seconds is None:
                count = len(self._entries)
                self._entries.clear()
                return count
            
            cutoff = datetime.now() - timedelta(seconds=older_than_seconds)
            keys_to_remove = [k for k, v in self._entries.items() 
                            if v.created_at < cutoff]
            count = len(keys_to_remove)
            for k in keys_to_remove:
                del self._entries[k]
            return count
    
    async def _cleanup_if_needed(self) -> None:
        """必要时清理过期条目"""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() >= \
           self.config.cleanup_interval_seconds:
            await self._cleanup_expired()
            self._last_cleanup = now
    
    async def _cleanup_expired(self) -> None:
        """清理所有过期条目"""
        expired_keys = [k for k, v in self._entries.items() if v.is_expired()]
        for k in expired_keys:
            del self._entries[k]
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired entries")
    
    def start_auto_cleanup(self) -> None:
        """启动自动清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
    
    async def _auto_cleanup_loop(self) -> None:
        """自动清理循环"""
        while True:
            await asyncio.sleep(self.config.cleanup_interval_seconds)
            await self._cleanup_expired()
    
    def stop_auto_cleanup(self) -> None:
        """停止自动清理任务"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class DuplicateTaskError(Exception):
    """重复任务错误"""
    pass


class BatchDeduplicator:
    """批量任务去重器"""
    
    def __init__(self, config: Optional[DeduplicationConfig] = None,
                 batch_size: int = 100):
        self.deduplicator = TaskDeduplicator(config)
        self.batch_size = batch_size
    
    async def filter_duplicates(self, 
                               tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤重复任务
        
        Args:
            tasks: 任务列表
            
        Returns:
            去重后的任务列表
        """
        unique_tasks = []
        for task in tasks:
            if not await self.deduplicator.is_duplicate(task):
                unique_tasks.append(task)
        return unique_tasks
    
    async def process_batch(self,
                           tasks: List[Dict[str, Any]],
                           executor: Callable,
                           parallel: bool = False) -> List[Any]:
        """
        批量处理任务（自动去重）
        
        Args:
            tasks: 任务列表
            executor: 执行函数
            parallel: 是否并行执行
            
        Returns:
            结果列表
        """
        unique_tasks = await self.filter_duplicates(tasks)
        results = []
        
        if parallel:
            if asyncio.iscoroutinefunction(executor):
                tasks_coro = [executor(task) for task in unique_tasks]
                results = await asyncio.gather(*tasks_coro, return_exceptions=True)
            else:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None, lambda: [executor(task) for task in unique_tasks]
                )
        else:
            for task in unique_tasks:
                if asyncio.iscoroutinefunction(executor):
                    result = await executor(task)
                else:
                    result = executor(task)
                results.append(result)
        
        return results
