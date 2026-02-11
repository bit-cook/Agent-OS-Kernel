# -*- coding: utf-8 -*-
"""
Trace Manager Module

Distributed tracing module for the Agent-OS-Kernel. This module provides:
- Span management for tracking operations
- Trace context propagation across processes/services
- Trace export in various formats (JSON, Zipkin, etc.)
- Thread-safe span recording and management
"""

import json
import time
import uuid
import threading
import enum
from datetime import datetime
from datetime import timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class SpanStatus(enum.Enum):
    """Status of a span"""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SpanKind(enum.Enum):
    """Kind of span"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class Span:
    """
    Represents a single span in a distributed trace.
    
    A span is a named, timed operation representing a segment of work.
    Spans can be nested to represent parent-child relationships.
    """
    
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = str(uuid.uuid4())
        if not self.span_id:
            self.span_id = str(uuid.uuid4())
    
    @property
    def duration(self) -> Optional[float]:
        """Get span duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute"""
        self.attributes[key] = value
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get a span attribute"""
        return self.attributes.get(key, default)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span"""
        event = {
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {}
        }
        self.events.append(event)
    
    def record_exception(self, exception: Exception) -> None:
        """Record an exception in the span"""
        self.add_event("exception", {
            "exception.type": type(exception).__name__,
            "exception.message": str(exception),
            "exception.stacktrace": getattr(exception, '__traceback__', None) is not None
        })
        self.status = SpanStatus.ERROR
    
    def end(self, status: Optional[SpanStatus] = None) -> None:
        """End the span"""
        self.end_time = datetime.now(timezone.utc)
        if status:
            self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "attributes": self.attributes,
            "events": self.events,
            "links": self.links
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Span':
        """Create span from dictionary"""
        start_time = data.get("start_time")
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        
        end_time = data.get("end_time")
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
        
        return cls(
            name=data["name"],
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            kind=SpanKind(data.get("kind", "internal")),
            status=SpanStatus(data.get("status", "unset")),
            start_time=start_time,
            end_time=end_time,
            attributes=data.get("attributes", {}),
            events=data.get("events", []),
            links=data.get("links", [])
        )


@dataclass
class TraceContext:
    """
    Manages the trace context including active spans and propagation data.
    
    The trace context maintains:
    - Current trace ID
    - Active span stack (for nested spans)
    - Span hierarchy information
    """
    
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spans: Dict[str, Span] = field(default_factory=dict)
    _span_stack: List[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    @property
    def current_span_id(self) -> Optional[str]:
        """Get the current active span ID"""
        return self._span_stack[-1] if self._span_stack else None
    
    @property
    def current_span(self) -> Optional[Span]:
        """Get the current active span"""
        span_id = self.current_span_id
        return self.spans.get(span_id) if span_id else None
    
    @property
    def root_span(self) -> Optional[Span]:
        """Get the root span (first span with no parent)"""
        for span in self.spans.values():
            if span.parent_span_id is None:
                return span
        return None
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span in this context"""
        with self._lock:
            # Determine parent
            if parent_span_id is None:
                parent_span_id = self.current_span_id
            
            # Create span
            span = Span(
                name=name,
                trace_id=self.trace_id,
                span_id=str(uuid.uuid4()),
                parent_span_id=parent_span_id,
                kind=kind,
                attributes=attributes or {}
            )
            
            # Register span
            self.spans[span.span_id] = span
            self._span_stack.append(span.span_id)
            
            return span
    
    def end_span(self, span_id: str) -> Optional[Span]:
        """End a span and remove it from the active stack"""
        with self._lock:
            if span_id in self.spans:
                span = self.spans[span_id]
                span.end()
                
                # Remove from stack
                if span_id in self._span_stack:
                    self._span_stack.remove(span_id)
                
                return span
            return None
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """Get a span by ID"""
        return self.spans.get(span_id)
    
    def get_child_spans(self, parent_span_id: str) -> List[Span]:
        """Get all child spans of a parent span"""
        return [s for s in self.spans.values() if s.parent_span_id == parent_span_id]
    
    def get_all_spans(self) -> List[Span]:
        """Get all spans in the trace"""
        return list(self.spans.values())
    
    def get_trace_tree(self) -> Dict[str, Any]:
        """Get the trace as a tree structure"""
        root = self.root_span
        if not root:
            return {"spans": []}
        
        def build_tree(span_id: str) -> Dict[str, Any]:
            span = self.spans.get(span_id)
            if not span:
                return None
            
            return {
                "span_id": span.span_id,
                "name": span.name,
                "kind": span.kind.value,
                "status": span.status.value,
                "start_time": span.start_time.isoformat(),
                "end_time": span.end_time.isoformat() if span.end_time else None,
                "duration": span.duration,
                "children": [
                    child for child in self.get_child_spans(span_id)
                ]
            }
        
        return {
            "trace_id": self.trace_id,
            "root_span": build_tree(root.span_id),
            "total_spans": len(self.spans)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "trace_id": self.trace_id,
            "spans": {sid: span.to_dict() for sid, span in self.spans.items()},
            "active_spans": list(self._span_stack)
        }
    
    def to_json(self) -> str:
        """Convert context to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraceContext':
        """Create trace context from dictionary"""
        context = cls(trace_id=data["trace_id"])
        
        for span_id, span_data in data.get("spans", {}).items():
            context.spans[span_id] = Span.from_dict(span_data)
        
        context._span_stack = data.get("active_spans", [])
        
        return context
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TraceContext':
        """Create trace context from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def get_propagation_headers(self) -> Dict[str, str]:
        """Get headers for propagating trace context across processes"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.current_span_id or "",
            "parent_span_id": self.current_span.span_id if self.current_span else ""
        }
    
    @classmethod
    def extract_from_headers(cls, headers: Dict[str, str]) -> Optional['TraceContext']:
        """Extract trace context from propagation headers"""
        trace_id = headers.get("trace_id")
        parent_span_id = headers.get("span_id")
        
        if not trace_id:
            return None
        
        context = cls(trace_id=trace_id)
        
        if parent_span_id:
            # Start a child span from the propagated context
            span = context.start_span(
                name="propagated",
                parent_span_id=parent_span_id
            )
            span.end()
            context._span_stack.pop()
        
        return context


class SpanExporter:
    """Base class for span exporters"""
    
    def export(self, spans: List[Span]) -> bool:
        """Export spans to the target system"""
        raise NotImplementedError
    
    def shutdown(self) -> None:
        """Shutdown the exporter and release resources"""
        pass


class ConsoleSpanExporter(SpanExporter):
    """Exports spans to console (for debugging)"""
    
    def __init__(self, pretty_print: bool = True):
        self.pretty_print = pretty_print
    
    def export(self, spans: List[Span]) -> bool:
        """Export spans to console"""
        for span in spans:
            if self.pretty_print:
                print(json.dumps(span.to_dict(), indent=2))
            else:
                print(json.dumps(span.to_dict()))
        return True


class JSONFileSpanExporter(SpanExporter):
    """Exports spans to a JSON file"""
    
    def __init__(self, file_path: str, append: bool = False):
        self.file_path = file_path
        self.append = append
    
    def export(self, spans: List[Span]) -> bool:
        """Export spans to JSON file"""
        mode = 'a' if self.append else 'w'
        
        with open(self.file_path, mode) as f:
            for span in spans:
                f.write(json.dumps(span.to_dict()) + '\n')
        
        logger.info(f"Exported {len(spans)} spans to {self.file_path}")
        return True
    
    def shutdown(self) -> None:
        """Close the file handle"""
        pass


class ZipkinSpanExporter(SpanExporter):
    """Exports spans in Zipkin format"""
    
    def __init__(self, zipkin_url: str, service_name: str = "agent-os-kernel"):
        self.zipkin_url = zipkin_url
        self.service_name = service_name
    
    def _to_zipkin_span(self, span: Span) -> Dict[str, Any]:
        """Convert span to Zipkin format"""
        return {
            "traceId": span.trace_id,
            "id": span.span_id,
            "parentId": span.parent_span_id or "",
            "name": span.name,
            "kind": span.kind.value.upper(),
            "timestamp": int(span.start_time.timestamp() * 1_000_000),
            "duration": int(span.duration * 1_000_000) if span.duration else None,
            "localEndpoint": {
                "serviceName": self.service_name,
                "ipv4": "",
                "port": None
            },
            "tags": span.attributes,
            "annotations": [
                {
                    "value": event["name"],
                    "timestamp": int(datetime.fromisoformat(event["timestamp"]).timestamp() * 1_000_000),
                    **event.get("attributes", {})
                }
                for event in span.events
            ]
        }
    
    def export(self, spans: List[Span]) -> bool:
        """Export spans to Zipkin"""
        import requests
        
        zipkin_spans = [self._to_zipkin_span(span) for span in spans]
        
        try:
            response = requests.post(
                f"{self.zipkin_url}/api/v2/spans",
                json=zipkin_spans,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Exported {len(zipkin_spans)} spans to Zipkin")
            return True
        except Exception as e:
            logger.error(f"Failed to export spans to Zipkin: {e}")
            return False
    
    def shutdown(self) -> None:
        """No-op for Zipkin exporter"""
        pass


class TraceManager:
    """
    Main class for managing distributed traces.
    
    The TraceManager provides:
    - Creation and management of trace contexts
    - Span recording with automatic timing
    - Context propagation across processes
    - Trace export to various backends
    - Thread-safe operations
    """
    
    def __init__(self, service_name: str = "agent-os-kernel"):
        self.service_name = service_name
        self._local = threading.local()
        self._global_context: Optional[TraceContext] = None
        self._lock = threading.Lock()
        self._exporters: List[SpanExporter] = []
        self._sampling_rate = 1.0
        self._trace_count = 0
    
    @property
    def _context(self) -> TraceContext:
        """Get the current trace context (thread-local or global)"""
        if not hasattr(self._local, 'context') or self._local.context is None:
            if self._global_context:
                return self._global_context
            # Create new context if none exists
            self._local.context = TraceContext()
        return self._local.context
    
    @_context.setter
    def _context(self, value: TraceContext) -> None:
        """Set the current trace context"""
        self._local.context = value
    
    def set_global_context(self, context: TraceContext) -> None:
        """Set a global trace context for all threads"""
        with self._lock:
            self._global_context = context
    
    def clear_global_context(self) -> None:
        """Clear the global trace context"""
        with self._lock:
            self._global_context = None
    
    def start_trace(self, name: str = "root") -> TraceContext:
        """Start a new trace and return its context"""
        context = TraceContext()
        span = context.start_span(name=name, kind=SpanKind.INTERNAL)
        
        # Set as thread-local context
        self._context = context
        
        return context
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span in the current trace context"""
        return self._context.start_span(
            name=name,
            kind=kind,
            parent_span_id=parent_span_id,
            attributes=attributes
        )
    
    def end_span(self, span_id: Optional[str] = None) -> Optional[Span]:
        """End a span in the current trace context"""
        if span_id is None:
            span_id = self._context.current_span_id
        
        return self._context.end_span(span_id)
    
    def record_exception(self, exception: Exception) -> None:
        """Record an exception in the current span"""
        span = self._context.current_span
        if span:
            span.record_exception(exception)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the current span"""
        span = self._context.current_span
        if span:
            span.add_event(name, attributes)
    
    def set_span_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the current span"""
        span = self._context.current_span
        if span:
            span.set_attribute(key, value)
    
    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID"""
        return self._context.trace_id
    
    def get_current_span_id(self) -> Optional[str]:
        """Get the current span ID"""
        return self._context.current_span_id
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current span"""
        return self._context.current_span
    
    def add_exporter(self, exporter: SpanExporter) -> None:
        """Add a span exporter"""
        with self._lock:
            self._exporters.append(exporter)
    
    def remove_exporter(self, exporter: SpanExporter) -> None:
        """Remove a span exporter"""
        with self._lock:
            if exporter in self._exporters:
                self._exporters.remove(exporter)
    
    def export_trace(self, context: Optional[TraceContext] = None) -> bool:
        """Export the current or specified trace"""
        trace_context = context or self._context
        
        if not trace_context:
            return False
        
        spans = trace_context.get_all_spans()
        
        if not spans:
            return True
        
        success = True
        for exporter in self._exporters:
            if not exporter.export(spans):
                success = False
        
        if success:
            self._trace_count += 1
        
        return success
    
    def shutdown(self) -> None:
        """Shutdown the trace manager and all exporters"""
        for exporter in self._exporters:
            exporter.shutdown()
        self._exporters.clear()
    
    def get_trace_context(self) -> TraceContext:
        """Get the current trace context"""
        return self._context
    
    def get_trace_tree(self) -> Dict[str, Any]:
        """Get the current trace as a tree structure"""
        return self._context.get_trace_tree()
    
    def get_propagation_headers(self) -> Dict[str, str]:
        """Get headers for propagating the current trace context"""
        return self._context.get_propagation_headers()
    
    @classmethod
    def extract_from_headers(cls, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from propagation headers"""
        return TraceContext.extract_from_headers(headers)
    
    def set_sampling_rate(self, rate: float) -> None:
        """Set the sampling rate (0.0 to 1.0)"""
        self._sampling_rate = max(0.0, min(1.0, rate))
    
    def should_sample(self) -> bool:
        """Check if the current trace should be sampled"""
        import random
        return random.random() < self._sampling_rate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get trace manager statistics"""
        return {
            "service_name": self.service_name,
            "total_traces_exported": self._trace_count,
            "num_exporters": len(self._exporters),
            "sampling_rate": self._sampling_rate,
            "has_global_context": self._global_context is not None
        }


@contextmanager
def create_span(
    trace_manager: TraceManager,
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Context manager for creating a span.
    
    Usage:
        with create_span(trace_manager, "operation_name") as span:
            # Do work
            trace_manager.set_span_attribute("key", "value")
    
    Args:
        trace_manager: The TraceManager instance
        name: Name of the span
        kind: Kind of span
        attributes: Initial attributes for the span
    """
    span = trace_manager.start_span(name, kind, attributes=attributes)
    try:
        yield span
    except Exception as e:
        span.record_exception(e)
        span.end(status=SpanStatus.ERROR)
        raise
    else:
        span.end(status=SpanStatus.OK)


# Factory functions
def create_trace_manager(service_name: str = "agent-os-kernel") -> TraceManager:
    """Create a new TraceManager instance"""
    return TraceManager(service_name)


def create_console_exporter(pretty_print: bool = True) -> ConsoleSpanExporter:
    """Create a console span exporter"""
    return ConsoleSpanExporter(pretty_print)


def create_json_file_exporter(file_path: str, append: bool = False) -> JSONFileSpanExporter:
    """Create a JSON file span exporter"""
    return JSONFileSpanExporter(file_path, append)


def create_zipkin_exporter(zipkin_url: str, service_name: str = "agent-os-kernel") -> ZipkinSpanExporter:
    """Create a Zipkin span exporter"""
    return ZipkinSpanExporter(zipkin_url, service_name)
