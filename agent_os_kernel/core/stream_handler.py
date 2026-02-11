# -*- coding: utf-8 -*-
"""Stream Handler - 流处理器

支持流式数据处理、文本/Token 流、实时数据管道。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import deque
import json

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """流类型"""
    TEXT = "text"
    JSON = "json"
    BYTES = "bytes"
    EVENTS = "events"


class StreamStatus(Enum):
    """流状态"""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamChunk:
    """流数据块"""
    chunk_id: str
    stream_id: str
    data: Any
    chunk_index: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    is_last: bool = False


class StreamHandler:
    """流处理器"""
    
    def __init__(
        self,
        stream_id: str,
        stream_type: StreamType = StreamType.TEXT,
        buffer_size: int = 1000,
        auto_flush: bool = True,
        flush_interval: float = 0.1
    ):
        """
        初始化流处理器
        
        Args:
            stream_id: 流 ID
            stream_type: 流类型
            buffer_size: 缓冲区大小
            auto_flush: 自动刷新
            flush_interval: 刷新间隔
        """
        self.stream_id = stream_id
        self.stream_type = stream_type
        self.buffer_size = buffer_size
        self.auto_flush = auto_flush
        self.flush_interval = flush_interval
        
        self._buffer: deque = deque(maxlen=buffer_size)
        self._status = StreamStatus.IDLE
        self._chunk_index = 0
        self._callbacks: Dict[str, Callable] = {}
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._stats = {
            "chunks_sent": 0,
            "chunks_received": 0,
            "bytes_sent": 0,
            "errors": 0
        }
        
        logger.info(f"StreamHandler initialized: {stream_id}")
    
    async def start(self):
        """启动流"""
        self._running = True
        self._status = StreamStatus.ACTIVE
        
        if self.auto_flush:
            self._flush_task = asyncio.create_task(self._auto_flush_loop())
        
        logger.info(f"Stream started: {self.stream_id}")
    
    async def stop(self):
        """停止流"""
        self._running = False
        self._status = StreamStatus.COMPLETED
        
        if self._flush_task:
            self._flush_task.cancel()
        
        logger.info(f"Stream stopped: {self.stream_id}")
    
    async def write(self, data: Any, metadata: Dict = None) -> str:
        """
        写入数据
        
        Args:
            data: 数据
            metadata: 元数据
            
        Returns:
            块 ID
        """
        chunk_id = f"{self.stream_id}_{self._chunk_index}"
        
        chunk = StreamChunk(
            chunk_id=chunk_id,
            stream_id=self.stream_id,
            data=data,
            chunk_index=self._chunk_index,
            metadata=metadata or {}
        )
        
        self._buffer.append(chunk)
        self._chunk_index += 1
        self._stats["chunks_received"] += 1
        
        if self.stream_type == StreamType.TEXT:
            self._stats["bytes_sent"] += len(str(data))
        
        # 回调
        if "on_chunk" in self._callbacks:
            try:
                await self._callbacks["on_chunk"](chunk)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        return chunk_id
    
    async def write_json(self, data: Dict, metadata: Dict = None):
        """写入 JSON"""
        return await self.write(json.dumps(data), metadata)
    
    async def write_event(self, event_type: str, payload: Dict, metadata: Dict = None):
        """写入事件"""
        return await self.write({
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, metadata)
    
    async def _auto_flush_loop(self):
        """自动刷新循环"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush error: {e}")
    
    async def flush(self):
        """刷新缓冲区"""
        if self._buffer:
            chunks = list(self._buffer)
            self._buffer.clear()
            
            self._stats["chunks_sent"] += len(chunks)
            
            if "on_flush" in self._callbacks:
                try:
                    await self._callbacks["on_flush"](chunks)
                except Exception as e:
                    logger.error(f"Flush callback error: {e}")
    
    def on_chunk(self, callback: Callable):
        """注册块回调"""
        self._callbacks["on_chunk"] = callback
    
    def on_flush(self, callback: Callable):
        """注册刷新回调"""
        self._callbacks["on_flush"] = callback
    
    def iterator(self) -> AsyncIterator[StreamChunk]:
        """获取迭代器"""
        return self._iterator()
    
    async def _iterator(self) -> AsyncIterator[StreamChunk]:
        """异步迭代器"""
        while self._running or self._buffer:
            while self._buffer:
                yield self._buffer.popleft()
            await asyncio.sleep(0.01)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "status": self._status.value,
            "chunks_sent": self._stats["chunks_sent"],
            "chunks_received": self._stats["chunks_received"],
            "buffer_size": len(self._buffer),
            "bytes_sent": self._stats["bytes_sent"]
        }


class StreamManager:
    """流管理器"""
    
    def __init__(self):
        self._streams: Dict[str, StreamHandler] = {}
        self._stats = {"active_streams": 0, "total_chunks": 0}
    
    def create_stream(
        self,
        stream_id: str,
        stream_type: StreamType = StreamType.TEXT,
        buffer_size: int = 1000
    ) -> StreamHandler:
        """创建流"""
        if stream_id in self._streams:
            raise KeyError(f"Stream already exists: {stream_id}")
        
        stream = StreamHandler(stream_id, stream_type, buffer_size)
        self._streams[stream_id] = stream
        
        return stream
    
    async def delete_stream(self, stream_id: str):
        """删除流"""
        if stream_id in self._streams:
            await self._streams[stream_id].stop()
            del self._streams[stream_id]
    
    def get_stream(self, stream_id: str) -> Optional[StreamHandler]:
        """获取流"""
        return self._streams.get(stream_id)
    
    def list_streams(self) -> list:
        """列出所有流"""
        return list(self._streams.keys())
    
    def get_stats(self) -> Dict:
        """获取统计"""
        active = sum(1 for s in self._streams.values() if s._status == StreamStatus.ACTIVE)
        return {
            "total_streams": len(self._streams),
            "active_streams": active,
            "total_chunks": sum(s._stats["chunks_sent"] for s in self._streams.values())
        }
