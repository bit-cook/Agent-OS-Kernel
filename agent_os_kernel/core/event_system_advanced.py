"""
Advanced Event System for Agent-OS-Kernel

This module provides advanced event handling capabilities including:
- Event Priority: Assign and process events based on priority levels
- Event Filtering: Filter events by type, source, or custom criteria
- Event Aggregation: Aggregate multiple events into summarized reports
- Event Persistence: Save and load events to/from persistent storage
- Event Tracing: Track event flow and history for debugging
"""

import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from datetime import timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union, Generic, TypeVar
from collections import defaultdict, deque
import copy


class EventPriority(Enum):
    """Event priority levels (higher = more urgent)"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventType(Enum):
    """Basic event types for categorization"""
    SYSTEM = auto()
    USER = auto()
    NETWORK = auto()
    DATA = auto()
    ERROR = auto()
    TIMER = auto()
    CUSTOM = auto()


@dataclass
class Event:
    """
    Core event class representing an occurrence in the system.
    
    Attributes:
        event_type: Type/category of the event
        priority: Event priority level
        source: Origin of the event (component name, etc.)
        data: Payload/data associated with the event
        timestamp: When the event was created
        event_id: Unique identifier for the event
        trace_id: Optional tracing identifier for tracking event flow
        metadata: Additional metadata for filtering and aggregation
    """
    event_type: EventType
    priority: EventPriority
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['event_type'] = self.event_type.name
        result['priority'] = self.priority.name
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create Event from dictionary"""
        data = copy.deepcopy(data)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['event_type'] = EventType[data['event_type']]
        data['priority'] = EventPriority[data['priority']]
        return cls(**data)


class EventFilter(ABC):
    """Abstract base class for event filters"""
    
    @abstractmethod
    def filter(self, event: Event) -> bool:
        """Return True if event passes the filter"""
        pass


class EventFilterChain:
    """Chain of multiple event filters"""
    
    def __init__(self, filters: Optional[List[EventFilter]] = None):
        self.filters: List[EventFilter] = filters or []
    
    def add_filter(self, filter: EventFilter) -> 'EventFilterChain':
        """Add a filter to the chain"""
        self.filters.append(filter)
        return self
    
    def filter(self, event: Event) -> bool:
        """Apply all filters to the event"""
        return all(f.filter(event) for f in self.filters)


class TypeEventFilter(EventFilter):
    """Filter events by type"""
    
    def __init__(self, allowed_types: Set[EventType]):
        self.allowed_types = allowed_types
    
    def filter(self, event: Event) -> bool:
        return event.event_type in self.allowed_types


class PriorityEventFilter(EventFilter):
    """Filter events by minimum priority"""
    
    def __init__(self, min_priority: EventPriority):
        self.min_priority = min_priority
    
    def filter(self, event: Event) -> bool:
        return event.priority.value >= self.min_priority.value


class SourceEventFilter(EventFilter):
    """Filter events by source"""
    
    def __init__(self, allowed_sources: Set[str]):
        self.allowed_sources = allowed_sources
    
    def filter(self, event: Event) -> bool:
        return event.source in self.allowed_sources


class CompositeEventFilter(EventFilter):
    """Combine multiple filter conditions with AND/OR logic"""
    
    def __init__(self, filters: List[EventFilter], combine_with_and: bool = True):
        self.filters = filters
        self.combine_with_and = combine_with_and
    
    def filter(self, event: Event) -> bool:
        if self.combine_with_and:
            return all(f.filter(event) for f in self.filters)
        return any(f.filter(event) for f in self.filters)


class EventAggregator:
    """Aggregate events based on various criteria"""
    
    def __init__(self, time_window_seconds: float = 60.0):
        self.time_window = time_window_seconds
        self.event_buffers: Dict[str, deque] = defaultdict(deque)
        self.aggregation_rules: Dict[str, Callable[[List[Event]], Any]] = {}
    
    def add_aggregation_rule(self, 
                            key: str, 
                            key_extractor: Callable[[Event], str],
                            aggregator: Callable[[List[Event]], Any]) -> 'EventAggregator':
        """Add a custom aggregation rule"""
        self.aggregation_rules[key] = {
            'key': key,  # Save the key here
            'extractor': key_extractor,
            'aggregator': aggregator
        }
        return self
    
    def add_event(self, event: Event) -> Optional[Any]:
        """Add an event and return aggregated result if conditions are met"""
        results = []
        
        for rule_key, rule in self.aggregation_rules.items():
            key = rule['extractor'](event)
            buffer = self.event_buffers[rule_key]
            
            # Add event to buffer
            buffer.append((event.timestamp, event))
            
            # Remove expired events
            cutoff = datetime.now(timezone.utc)
            while buffer and (cutoff - buffer[0][0]).total_seconds() > self.time_window:
                buffer.popleft()
            
            # Check if we should aggregate
            if len(buffer) >= 3:  # Aggregate when we have at least 3 events
                aggregated = rule['aggregator']([e[1] for e in buffer])
                buffer.clear()
                results.append(aggregated)
        
        return results[0] if results else None
    
    def aggregate_all(self) -> Dict[str, Any]:
        """Force aggregation of all current buffers"""
        results = {}
        for rule_key, buffer in self.event_buffers.items():
            if buffer and rule_key in self.aggregation_rules:
                rule = self.aggregation_rules[rule_key]
                results[rule_key] = rule['aggregator']([e[1] for e in buffer])
                buffer.clear()
        return results


class EventPersister:
    """Handle event persistence to storage"""
    
    def __init__(self, storage_backend: Optional[str] = None):
        self.storage_backend = storage_backend or "memory"
        self.storage: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.persist_lock = threading.Lock()
    
    def save_event(self, event: Event) -> bool:
        """Persist an event"""
        with self.persist_lock:
            try:
                self.storage[event.event_type.name].append(event.to_dict())
                return True
            except Exception:
                return False
    
    def save_events(self, events: List[Event]) -> int:
        """Persist multiple events"""
        count = 0
        with self.persist_lock:
            for event in events:
                if self.save_event(event):
                    count += 1
        return count
    
    def load_events(self, 
                   event_type: Optional[EventType] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[Event]:
        """Load events with optional filters"""
        with self.persist_lock:
            events = []
            storage_key = event_type.name if event_type else None
            
            for key, event_list in self.storage.items():
                if storage_key and key != storage_key:
                    continue
                    
                for event_dict in event_list:
                    event = Event.from_dict(event_dict)
                    
                    # Apply time filter
                    if start_time and event.timestamp < start_time:
                        continue
                    if end_time and event.timestamp > end_time:
                        continue
                    
                    events.append(event)
            
            return events
    
    def clear_storage(self) -> int:
        """Clear all stored events and return count of removed events"""
        with self.persist_lock:
            count = sum(len(events) for events in self.storage.values())
            self.storage.clear()
            return count


class EventTracer:
    """Track event flow and history for debugging"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.trace_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.global_trace_id: Optional[str] = None
        self.tracing_active = False
    
    def start_tracing(self) -> str:
        """Start a new global trace session"""
        self.global_trace_id = str(uuid.uuid4())
        self.tracing_active = True
        return self.global_trace_id
    
    def stop_tracing(self) -> Optional[str]:
        """Stop global tracing and return trace ID"""
        trace_id = self.global_trace_id
        self.global_trace_id = None
        self.tracing_active = False
        return trace_id
    
    def record_event(self, event: Event, action: str, details: Optional[Dict[str, Any]] = None) -> str:
        """Record an event in the trace"""
        trace_id = event.trace_id or self.global_trace_id
        
        if not trace_id:
            return ""
        
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_id': event.event_id,
            'event_type': event.event_type.name,
            'priority': event.priority.name,
            'source': event.source,
            'action': action,
            'details': details or {}
        }
        
        self.trace_records[trace_id].append(record)
        
        # Trim history if needed
        if len(self.trace_records[trace_id]) > self.max_history:
            self.trace_records[trace_id] = self.trace_records[trace_id][-self.max_history:]
        
        return trace_id
    
    def get_trace(self, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get trace records for a trace ID"""
        target_id = trace_id or self.global_trace_id
        if not target_id:
            return []
        return self.trace_records.get(target_id, [])
    
    def get_trace_summary(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of the trace"""
        trace = self.get_trace(trace_id)
        if not trace:
            return {'total_events': 0, 'event_types': {}, 'actions': {}}
        
        event_types = {}
        actions = {}
        
        for record in trace:
            event_type = record['event_type']
            action = record['action']
            event_types[event_type] = event_types.get(event_type, 0) + 1
            actions[action] = actions.get(action, 0) + 1
        
        return {
            'total_events': len(trace),
            'event_types': event_types,
            'actions': actions,
            'duration_seconds': None  # Could calculate from first/last timestamp
        }


class AdvancedEventSystem:
    """
    Main event system class combining all advanced features.
    
    This class provides a complete event handling system with:
    - Priority-based event processing
    - Flexible event filtering
    - Event aggregation capabilities
    - Persistent storage
    - Event tracing and debugging
    """
    
    def __init__(self, name: str = "AdvancedEventSystem"):
        self.name = name
        self.event_queue: 'PriorityQueue[Event]' = None  # Set in initialize()
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.filter_chain = EventFilterChain()
        self.aggregator = EventAggregator()
        self.persister = EventPersister()
        self.tracer = EventTracer()
        self.event_history: deque = deque(maxlen=10000)
        self._lock = threading.Lock()
        self._running = False
        self._initialize_priority_queue()
    
    def _initialize_priority_queue(self):
        """Initialize the priority queue"""
        self.event_queue = PriorityQueue()
    
    def start(self) -> bool:
        """Start the event system"""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self.tracer.start_tracing()
            return True
    
    def stop(self) -> bool:
        """Stop the event system"""
        with self._lock:
            if not self._running:
                return False
            self._running = False
            self.tracer.stop_tracing()
            return True
    
    def publish_event(self, event: Event) -> bool:
        """Publish an event to the system"""
        if not self._running:
            return False
        
        # Record in history
        self.event_history.append(event)
        
        # Record trace
        self.tracer.record_event(event, "published")
        
        # Apply filters
        if not self.filter_chain.filter(event):
            self.tracer.record_event(event, "filtered_out")
            return False
        
        # Add to queue based on priority
        self.event_queue.put(event)
        
        # Record trace
        self.tracer.record_event(event, "queued")
        
        return True
    
    def subscribe(self, 
                 event_type: Optional[EventType] = None,
                 callback: Optional[Callable] = None) -> str:
        """Subscribe to events"""
        subscription_id = str(uuid.uuid4())
        key = event_type.name if event_type else "*"
        if callback:
            self.subscribers[key].append(callback)
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription"""
        # Note: In a real implementation, we'd track callback->subscription_id mappings
        return True
    
    def process_events(self, max_events: int = 100) -> int:
        """Process events from the queue"""
        processed = 0
        
        while processed < max_events and not self.event_queue.empty():
            event = self.event_queue.get()
            
            # Record trace
            self.tracer.record_event(event, "processing")
            
            # Try aggregation
            aggregated = self.aggregator.add_event(event)
            if aggregated:
                self.tracer.record_event(event, "aggregated", {'result': str(aggregated)})
            
            # Persist
            self.persister.save_event(event)
            
            # Notify subscribers
            for callback in self.subscribers.get(event.event_type.name, []):
                try:
                    callback(event)
                except Exception:
                    pass
            
            # Notify wildcard subscribers
            for callback in self.subscribers.get("*", []):
                try:
                    callback(event)
                except Exception:
                    pass
            
            # Record trace
            self.tracer.record_event(event, "processed")
            
            processed += 1
        
        return processed
    
    def add_filter(self, filter: EventFilter) -> 'AdvancedEventSystem':
        """Add a filter to the chain"""
        self.filter_chain.add_filter(filter)
        return self
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            'queue_size': self.event_queue.qsize(),
            'subscribers': {k: len(v) for k, v in self.subscribers.items()},
            'history_size': len(self.event_history),
            'tracing_active': self.tracer.tracing_active,
            'storage_count': sum(len(v) for v in self.persister.storage.values())
        }


class PriorityQueue:
    """Thread-safe priority queue for events"""
    
    def __init__(self):
        self._queue: List[Event] = []
        self._lock = threading.Lock()
    
    def put(self, item: Event):
        """Add an item to the queue (sorted by priority)"""
        with self._lock:
            self._queue.append(item)
            # Sort by priority (higher priority first)
            self._queue.sort(key=lambda e: e.priority.value, reverse=True)
    
    def get(self) -> Optional[Event]:
        """Remove and return the highest priority item"""
        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        with self._lock:
            return len(self._queue) == 0
    
    def qsize(self) -> int:
        """Get queue size"""
        with self._lock:
            return len(self._queue)
