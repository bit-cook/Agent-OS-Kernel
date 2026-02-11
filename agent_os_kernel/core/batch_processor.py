"""批处理器"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio


class AggregationType(Enum):
    """聚合类型"""
    NONE = "none"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"


class Batch:
    """批次"""
    
    def __init__(
        self,
        batch_id: str,
        aggregation: AggregationType = AggregationType.NONE
    ):
        self.batch_id = batch_id
        self.items: List[Any] = []
        self.aggregation = aggregation
        self.created_at = datetime.now(timezone.utc)
        self.processed_at = None
        self.results: List[Any] = []
    
    def add(self, item):
        """添加项目"""
        self.items.append(item)
    
    def mark_processed(self):
        """标记已处理"""
        self.processed_at = datetime.now(timezone.utc)
    
    def get_aggregated_value(self) -> Any:
        """获取聚合值"""
        if not self.results:
            return None
        
        if self.aggregation == AggregationType.SUM:
            return sum(self.results)
        elif self.aggregation == AggregationType.AVG:
            return sum(self.results) / len(self.results)
        elif self.aggregation == AggregationType.MIN:
            return min(self.results)
        elif self.aggregation == AggregationType.MAX:
            return max(self.results)
        elif self.aggregation == AggregationType.COUNT:
            return len(self.results)
        
        return self.results


class SlidingWindowProcessor:
    """滑动窗口处理器"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._data: List[Any] = []
    
    def add(self, item: Any):
        """添加数据"""
        self._data.append(item)
        if len(self._data) > self.window_size:
            self._data.pop(0)
    
    def get_all(self) -> List[Any]:
        """获取所有数据"""
        return self._data.copy()


class BatchProcessor:
    """批处理器"""
    
    def __init__(
        self,
        batch_size: int = 100,
        timeout_ms: int = 5000,
        aggregation: AggregationType = AggregationType.NONE
    ):
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        self.aggregation = aggregation
        self._batches: Dict[str, Batch] = {}
        self._processing = False
        self._stats = {
            "batch_count": 0,
            "processed_count": 0,
            "failed_count": 0,
            "aggregated_value": None
        }
    
    async def add_task(self, task_data: Any, batch_id: str = "default") -> str:
        """添加任务"""
        if batch_id not in self._batches:
            self._batches[batch_id] = Batch(batch_id, self.aggregation)
        
        batch = self._batches[batch_id]
        batch.add(task_data)
        
        if len(batch.items) >= self.batch_size:
            await self._process_batch(batch)
        
        return batch_id
    
    async def _process_batch(self, batch: Batch):
        """处理批次"""
        batch.mark_processed()
        self._stats["batch_count"] += 1
        self._stats["processed_count"] += len(batch.items)
        self._stats["aggregated_value"] = batch.get_aggregated_value()
    
    async def flush(self):
        """刷新所有批次"""
        for batch_id, batch in list(self._batches.items()):
            if batch.items:
                await self._process_batch(batch)
    
    def get_statistics(self) -> Dict:
        """获取统计"""
        return {
            "batch_count": self._stats["batch_count"],
            "processed_count": self._stats["processed_count"],
            "failed_count": self._stats["failed_count"],
            "aggregated_value": self._stats["aggregated_value"],
            "active_batches": len(self._batches)
        }
