"""
追踪模块 - Agent OS Kernel

提供分布式追踪功能:
- 追踪上下文管理
- Span 创建和追踪
- 追踪数据收集
- 追踪导出
"""

import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Callable
from queue import Queue, Empty
import json


# 配置日志
logger = logging.getLogger(__name__)


class TraceStatus(Enum):
    """追踪状态"""
    STARTED = "started"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpanKind(Enum):
    """Span 类型"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class Span:
    """Span 数据类"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    status: TraceStatus = TraceStatus.STARTED
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.end_time is None:
            self.end_time = self.start_time
    
    def finish(self, status: TraceStatus = TraceStatus.FINISHED):
        """完成 span"""
        self.end_time = datetime.utcnow()
        self.status = status
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def add_attribute(self, key: str, value: Any):
        """添加属性"""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """添加事件"""
        event = {
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {}
        }
        self.events.append(event)
    
    def add_error(self, error: Exception, message: str = ""):
        """添加错误"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": self._get_traceback()
        }
        self.errors.append(error_info)
    
    def _get_traceback(self) -> str:
        """获取堆栈跟踪"""
        import traceback
        return ''.join(traceback.format_exc())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "errors": self.errors
        }
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class TraceContext:
    """追踪上下文"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._local = threading.local()
        self._spans: Dict[str, Span] = {}
        self._lock = threading.Lock()
    
    @property
    def current_trace_id(self) -> Optional[str]:
        """当前追踪 ID"""
        if hasattr(self._local, 'current_trace_id'):
            return self._local.current_trace_id
        return None
    
    @property
    def current_span_id(self) -> Optional[str]:
        """当前 span ID"""
        if hasattr(self._local, 'current_span_id'):
            return self._local.current_span_id
        return None
    
    @property
    def current_span(self) -> Optional[Span]:
        """当前 span"""
        span_id = self.current_span_id
        if span_id and span_id in self._spans:
            return self._spans[span_id]
        return None
    
    def get_or_create_trace_id(self) -> str:
        """获取或创建追踪 ID"""
        if self.current_trace_id:
            return self.current_trace_id
        return str(uuid.uuid4())
    
    def get_or_create_span_id(self) -> str:
        """获取或创建 span ID"""
        if self.current_span_id:
            return self.current_span_id
        return str(uuid.uuid4())
    
    def _set_context(self, trace_id: str, span_id: str):
        """设置上下文"""
        self._local.current_trace_id = trace_id
        self._local.current_span_id = span_id
    
    def _clear_context(self):
        """清除上下文"""
        self._local.current_trace_id = None
        self._local.current_span_id = None


class Tracing:
    """追踪器主类"""
    
    def __init__(self, service_name: str = "agent-os-kernel"):
        self.service_name = service_name
        self.context = TraceContext()
        self._exporters: List[Callable] = []
        self._span_processor = Queue(maxsize=10000)
        self._processor_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
    
    def start(self):
        """启动追踪器"""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._processor_thread = threading.Thread(
                target=self._process_spans,
                daemon=True
            )
            self._processor_thread.start()
            logger.info(f"Tracing started for service: {self.service_name}")
    
    def stop(self):
        """停止追踪器"""
        with self._lock:
            self._running = False
        
        # 处理剩余的 spans
        self._flush_spans()
        
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
            self._processor_thread = None
        
        logger.info("Tracing stopped")
    
    def create_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None
    ) -> Span:
        """创建 span"""
        trace_id = self.context.get_or_create_trace_id()
        span_id = str(uuid.uuid4())
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id or self.context.current_span_id,
            name=name,
            kind=kind,
            attributes=attributes or {}
        )
        
        with self._lock:
            self._spans[span_id] = span
        
        return span
    
    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Generator[Span, None, None]:
        """上下文管理器创建 span"""
        parent_span_id = self.context.current_span_id
        span = self.create_span(name, kind, attributes, parent_span_id)
        
        # 保存旧的上下文
        old_trace_id = self.context.current_trace_id
        old_span_id = self.context.current_span_id
        
        # 设置新的上下文
        self.context._set_context(span.trace_id, span.span_id)
        
        try:
            yield span
            span.finish(TraceStatus.FINISHED)
        except Exception as e:
            span.add_error(e)
            span.finish(TraceStatus.ERROR)
            raise
        finally:
            # 恢复上下文
            if old_trace_id:
                self.context._set_context(old_trace_id, old_span_id)
            else:
                self.context._clear_context()
            
            # 导出 span
            self._export_span(span)
    
    def add_exporter(self, exporter: Callable):
        """添加导出器"""
        self._exporters.append(exporter)
    
    def _export_span(self, span: Span):
        """导出 span"""
        for exporter in self._exporters:
            try:
                exporter(span)
            except Exception as e:
                logger.error(f"Error exporting span: {e}")
    
    def _process_spans(self):
        """处理 span 队列"""
        while self._running:
            try:
                span = self._span_processor.get(timeout=1)
                self._export_span(span)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing span: {e}")
    
    def _flush_spans(self):
        """刷新剩余的 spans"""
        while True:
            try:
                span = self._span_processor.get_nowait()
                self._export_span(span)
            except:
                break
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """获取追踪"""
        with self._lock:
            return [
                span for span in self._spans.values()
                if span.trace_id == trace_id
            ]
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """获取 span"""
        with self._lock:
            return self._spans.get(span_id)
    
    def clear(self):
        """清除所有追踪数据"""
        with self._lock:
            self._spans.clear()
            while not self._span_processor.empty():
                try:
                    self._span_processor.get_nowait()
                except:
                    break
    
    def export_json(self) -> str:
        """导出为 JSON"""
        with self._lock:
            data = {
                "service_name": self.service_name,
                "spans": [span.to_dict() for span in self._spans.values()],
                "timestamp": datetime.utcnow().isoformat()
            }
        return json.dumps(data, indent=2, ensure_ascii=False)


# 全局追踪器实例
_tracer: Optional[Tracing] = None


def get_tracer(service_name: str = "agent-os-kernel") -> Tracing:
    """获取全局追踪器"""
    global _tracer
    if _tracer is None:
        _tracer = Tracing(service_name)
    return _tracer


def set_tracer(tracer: Tracing):
    """设置全局追踪器"""
    global _tracer
    _tracer = tracer


@contextmanager
def trace(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    tracer: Optional[Tracing] = None
) -> Generator[Span, None, None]:
    """便捷的追踪上下文管理器"""
    if tracer is None:
        tracer = get_tracer()
    with tracer.span(name, kind, attributes) as span:
        yield span
