# -*- coding: utf-8 -*-
"""Pipeline - 数据管道

支持多阶段处理、并行管道、条件分支。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone, timezone, timedelta, timezone
from enum import Enum
from uuid import uuid4
from collections import deque

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """管道阶段"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineItem:
    """管道项目"""
    item_id: str
    data: Any
    stage: PipelineStage = PipelineStage.PENDING
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


class Pipeline:
    """数据管道"""
    
    def __init__(
        self,
        name: str = "default",
        max_concurrent: int = 10,
        timeout: float = 300.0
    ):
        """
        初始化管道
        
        Args:
            name: 管道名称
            max_concurrent: 最大并发
            timeout: 超时时间
        """
        self.name = name
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        
        self._stages: Dict[str, Callable] = {}
        self._items: Dict[str, PipelineItem] = {}
        self._processing = 0
        self._lock = asyncio.Lock()
        self._callbacks: Dict[str, Callable] = {}
        self._running = False
        
        self._worker_task: Optional[asyncio.Task] = None
        
        logger.info(f"Pipeline initialized: {name}")
    
    def add_stage(self, stage_name: str, func: Callable):
        """
        添加阶段
        
        Args:
            stage_name: 阶段名称
            func: 处理函数
        """
        self._stages[stage_name] = func
        logger.info(f"Added stage: {stage_name}")
    
    def stage(self, stage_name: str):
        """装饰器添加阶段"""
        def decorator(func):
            self.add_stage(stage_name, func)
            return func
        return decorator
    
    async def process(self, data: Any, metadata: Dict = None) -> PipelineItem:
        """
        处理数据
        
        Args:
            data: 输入数据
            metadata: 元数据
            
        Returns:
            处理结果
        """
        item_id = str(uuid4())
        item = PipelineItem(
            item_id=item_id,
            data=data,
            metadata=metadata or {}
        )
        
        self._items[item_id] = item
        
        await self._run_pipeline(item)
        
        return item
    
    async def process_batch(self, items: List[Any], metadata: Dict = None) -> List[PipelineItem]:
        """
        批量处理
        
        Args:
            items: 数据列表
            metadata: 元数据
            
        Returns:
            处理结果列表
        """
        results = []
        
        for data in items:
            result = await self.process(data, metadata)
            results.append(result)
        
        return results
    
    async def _run_pipeline(self, item: PipelineItem):
        """运行管道"""
        item.stage = PipelineStage.RUNNING
        
        for stage_name, func in self._stages.items():
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(item.data, item.results)
                else:
                    result = func(item.data, item.results)
                
                item.results[stage_name] = result
                item.stage = PipelineStage.COMPLETED
                
            except Exception as e:
                item.errors[stage_name] = str(e)
                item.stage = PipelineStage.FAILED
                logger.error(f"Pipeline stage {stage_name} failed: {e}")
                break
        
        item.completed_at = datetime.now(timezone.utc)
        
        # 回调
        if "on_complete" in self._callbacks:
            try:
                await self._callbacks["on_complete"](item)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def on_complete(self, callback: Callable):
        """注册完成回调"""
        self._callbacks["on_complete"] = callback
    
    def on_error(self, callback: Callable):
        """注册错误回调"""
        self._callbacks["on_error"] = callback
    
    def get_item(self, item_id: str) -> Optional[PipelineItem]:
        """获取项目"""
        return self._items.get(item_id)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        completed = sum(1 for i in self._items.values() if i.stage == PipelineStage.COMPLETED)
        failed = sum(1 for i in self._items.values() if i.stage == PipelineStage.FAILED)
        
        return {
            "total_items": len(self._items),
            "completed": completed,
            "failed": failed,
            "processing": self._processing,
            "stages": len(self._stages)
        }
