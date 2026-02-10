# -*- coding: utf-8 -*-
"""Batch Processor - 批量操作处理器

优化多个操作的批量执行，减少 API 调用开销。

参考：
- AutoGen 的批量工具调用
- 批量 LLM 推理优化
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)


class BatchStrategy(Enum):
    """批量策略"""
    SEQUENTIAL = "sequential"     # 顺序执行
    PARALLEL = "parallel"        # 并行执行
    THROTTLED = "throttled"      # 限流并行
    ADAPTIVE = "adaptive"         # 自适应选择


@dataclass
class BatchConfig:
    """批量配置"""
    max_batch_size: int = 10          # 最大批量大小
    max_wait_time_ms: int = 100       # 最大等待时间 (毫秒)
    min_batch_size: int = 1           # 最小批量大小
    max_concurrent: int = 5           # 最大并发数
    retry_count: int = 3             # 重试次数
    retry_delay_ms: int = 1000        # 重试延迟
    preserve_order: bool = True       # 保持顺序


@dataclass
class BatchItem:
    """批量项目"""
    item_id: str
    data: Any
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class BatchResult:
    """批量结果"""
    item_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict = field(default_factory=dict)


class BatchProcessor:
    """
    批量操作处理器
    
    优化多个相似操作的批量执行。
    """
    
    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self._queue: List[BatchItem] = []
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent)
        self._results: Dict[str, BatchResult] = {}
        self._processing = False
    
    async def add(
        self,
        item_id: str,
        data: Any,
        priority: int = 0,
        metadata: Dict = None
    ) -> str:
        """添加项目到批次"""
        item = BatchItem(
            item_id=item_id,
            data=data,
            priority=priority,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self._queue.append(item)
            self._queue.sort(key=lambda x: (-x.priority, x.created_at))
        
        return item_id
    
    async def add_batch(
        self,
        items: List[Dict[str, Any]],
        key_fn: Callable = None
    ) -> List[str]:
        """批量添加项目"""
        item_ids = []
        
        for i, item_data in enumerate(items):
            key = key_fn(item_data) if key_fn else f"batch_{i}"
            
            item_id = await self.add(
                item_id=key,
                data=item_data.get("data", item_data),
                priority=item_data.get("priority", 0),
                metadata=item_data.get("metadata", {})
            )
            item_ids.append(item_id)
        
        return item_ids
    
    async def process(
        self,
        processor_fn: Callable[[Any], Awaitable[Any]],
        strategy: BatchStrategy = BatchStrategy.ADAPTIVE
    ) -> List[BatchResult]:
        """
        处理批次
        
        Args:
            processor_fn: 处理函数
            strategy: 处理策略
            
        Returns:
            处理结果列表
        """
        async with self._lock:
            if not self._queue:
                return []
            
            items = self._queue[:self.config.max_batch_size]
            self._queue = self._queue[self.config.max_batch_size:]
        
        # 根据策略选择处理方式
        if strategy == BatchStrategy.SEQUENTIAL:
            return await self._process_sequential(items, processor_fn)
        elif strategy == BatchStrategy.PARALLEL:
            return await self._process_parallel(items, processor_fn)
        elif strategy == BatchStrategy.THROTTLED:
            return await self._process_throttled(items, processor_fn)
        else:  # ADAPTIVE
            return await self._process_adaptive(items, processor_fn)
    
    async def _process_sequential(
        self,
        items: List[BatchItem],
        processor_fn: Callable[[Any], Awaitable[Any]]
    ) -> List[BatchResult]:
        """顺序处理"""
        results = []
        
        for item in items:
            result = await self._execute_with_retry(item, processor_fn)
            results.append(result)
        
        return results
    
    async def _process_parallel(
        self,
        items: List[BatchItem],
        processor_fn: Callable[[Any], Awaitable[Any]]
    ) -> List[BatchResult]:
        """并行处理"""
        tasks = [
            self._execute_with_retry(item, processor_fn)
            for item in items
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 转换异常为结果
        final_results = []
        for item, result in zip(items, results):
            if isinstance(result, Exception):
                final_results.append(BatchResult(
                    item_id=item.item_id,
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _process_throttled(
        self,
        items: List[BatchItem],
        processor_fn: Callable[[Any], Awaitable[Any]]
    ) -> List[BatchResult]:
        """限流并行处理"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def limited_task(item):
            async with semaphore:
                return await self._execute_with_retry(item, processor_fn)
        
        tasks = [limited_task(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for item, result in zip(items, results):
            if isinstance(result, Exception):
                final_results.append(BatchResult(
                    item_id=item.item_id,
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _process_adaptive(
        self,
        items: List[BatchItem],
        processor_fn: Callable[[Any], Awaitable[Any]]
    ) -> List[BatchResult]:
        """自适应处理 - 根据项目数量选择策略"""
        if len(items) <= 2:
            return await self._process_sequential(items, processor_fn)
        elif len(items) <= 10:
            return await self._process_throttled(items, processor_fn)
        else:
            # 大批量分批处理
            all_results = []
            batch_size = self.config.max_concurrent
            
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                results = await self._process_throttled(batch, processor_fn)
                all_results.extend(results)
            
            return all_results
    
    async def _execute_with_retry(
        self,
        item: BatchItem,
        processor_fn: Callable[[Any], Awaitable[Any]]
    ) -> BatchResult:
        """带重试的执行"""
        start_time = datetime.now()
        
        for attempt in range(self.config.retry_count):
            try:
                result = await processor_fn(item.data)
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return BatchResult(
                    item_id=item.item_id,
                    success=True,
                    result=result,
                    execution_time_ms=execution_time,
                    metadata={
                        **item.metadata,
                        "attempts": attempt + 1
                    }
                )
            except Exception as e:
                item.retry_count += 1
                
                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(self.config.retry_delay_ms / 1000)
                else:
                    return BatchResult(
                        item_id=item.item_id,
                        success=False,
                        error=str(e),
                        execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                        metadata={
                            **item.metadata,
                            "attempts": attempt + 1
                        }
                    )
        
        return BatchResult(item_id=item.item_id, success=False)
    
    def get_results(self, item_ids: List[str]) -> List[BatchResult]:
        """获取结果"""
        return [
            self._results.get(item_id)
            for item_id in item_ids
            if item_id in self._results
        ]
    
    def clear_results(self, completed_before: datetime = None):
        """清理旧结果"""
        cutoff = completed_before or datetime.now() - timedelta(hours=1)
        
        to_remove = [
            item_id for item_id, result in self._results.items()
            if hasattr(result, 'execution_time_ms') and datetime.now() - datetime.now() > timedelta(hours=1)
        ]
        
        for item_id in to_remove:
            del self._results[item_id]
    
    def stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "queue_size": len(self._queue),
            "pending_results": len(self._results),
            "max_batch_size": self.config.max_batch_size,
            "max_concurrent": self.config.max_concurrent,
            "retry_count": self.config.retry_count
        }


class LLMBatchProcessor:
    """
    LLM 批量处理器
    
    专门优化 LLM API 调用的批量处理。
    """
    
    def __init__(self, batch_config: BatchConfig = None):
        self.batch_processor = BatchProcessor(batch_config or BatchConfig())
        self._model = None
    
    def set_model(self, model):
        """设置 LLM 模型"""
        self._model = model
    
    async def complete_batch(
        self,
        prompts: List[Dict[str, Any]],
        model: str = None,
        strategy: BatchStrategy = BatchStrategy.ADAPTIVE
    ) -> List[BatchResult]:
        """
        批量完成 LLM 调用
        
        Args:
            prompts: 提示列表 [{"role": "user", "content": "..."}]
            model: 模型名称
            strategy: 处理策略
            
        Returns:
            结果列表
        """
        async def call_llm(prompt_data):
            if self._model:
                return await self._model.complete(prompt_data)
            else:
                # 模拟 LLM 调用
                return {"response": f"Response to: {prompt_data.get('content', '')[:50]}"}
        
        # 包装为批量项目
        items = [
            {
                "data": prompt,
                "priority": 0,
                "metadata": {"model": model}
            }
            for prompt in prompts
        ]
        
        await self.batch_processor.add_batch(items)
        
        return await self.batch_processor.process(call_llm, strategy)
    
    async def complete_batch_streaming(
        self,
        prompts: List[Dict[str, Any]],
        model: str = None
    ):
        """批量流式完成 (简化版)"""
        for prompt in prompts:
            yield await self._model.complete(prompt)


# 便捷函数
def create_batch_processor(
    max_batch_size: int = 10,
    max_concurrent: int = 5
) -> BatchProcessor:
    """创建批量处理器"""
    config = BatchConfig(
        max_batch_size=max_batch_size,
        max_concurrent=max_concurrent
    )
    return BatchProcessor(config)


def create_llm_batch_processor(
    model=None,
    max_batch_size: int = 10
) -> LLMBatchProcessor:
    """创建 LLM 批量处理器"""
    processor = LLMBatchProcessor()
    processor.set_model(model)
    return processor
