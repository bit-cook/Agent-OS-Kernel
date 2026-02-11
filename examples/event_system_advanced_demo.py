"""
Advanced Event System Demo

Demonstrates the advanced event system features:
- Event Priority: Priority-based event processing
- Event Filtering: Filtering events by type, priority, source
- Event Tracing: Tracking event flow for debugging
"""

import time
from datetime import datetime

from agent_os_kernel.core.event_system_advanced import (
    Event,
    EventPriority,
    EventType,
    TypeEventFilter,
    PriorityEventFilter,
    SourceEventFilter,
    CompositeEventFilter,
    EventAggregator,
    EventPersister,
    EventTracer,
    AdvancedEventSystem,
)


def demo_event_priority():
    """Demonstrate event priority functionality"""
    print("=" * 60)
    print("DEMO: Event Priority")
    print("=" * 60)
    
    from agent_os_kernel.core.event_system_advanced import PriorityQueue
    
    pq = PriorityQueue()
    
    # Create events with different priorities
    events = [
        Event(EventType.SYSTEM, EventPriority.NORMAL, "service_check"),
        Event(EventType.ERROR, EventPriority.CRITICAL, "database"),
        Event(EventType.USER, EventPriority.LOW, "analytics"),
        Event(EventType.NETWORK, EventPriority.HIGH, "connection"),
        Event(EventType.DATA, EventPriority.HIGH, "sync_job"),
    ]
    
    print("\nEvents added (in this order):")
    for event in events:
        print(f"  - [{event.priority.name}] {event.event_type.name} from {event.source}")
        pq.put(event)
    
    print("\nEvents processed (by priority - highest first):")
    while not pq.empty():
        event = pq.get()
        print(f"  - [{event.priority.name}] {event.event_type.name} from {event.source}")
    
    print("\n✓ Critical events are processed before high, normal, and low priority events\n")


def demo_event_filtering():
    """Demonstrate event filtering functionality"""
    print("=" * 60)
    print("DEMO: Event Filtering")
    print("=" * 60)
    
    # Create sample events
    events = [
        Event(EventType.SYSTEM, EventPriority.LOW, "heartbeat", data={"service": "web"}),
        Event(EventType.ERROR, EventPriority.CRITICAL, "database", data={"error": "connection failed"}),
        Event(EventType.USER, EventPriority.NORMAL, "api", data={"user": "alice"}),
        Event(EventType.SYSTEM, EventPriority.HIGH, "backup", data={"status": "running"}),
        Event(EventType.ERROR, EventPriority.CRITICAL, "api", data={"error": "timeout"}),
    ]
    
    print("\n1. Filter by Event Type (SYSTEM + ERROR only):")
    type_filter = TypeEventFilter({EventType.SYSTEM, EventType.ERROR})
    for event in events:
        passes = type_filter.filter(event)
        status = "✓" if passes else "✗"
        print(f"  {status} [{event.event_type.name}] {event.source}: {passes}")
    
    print("\n2. Filter by Priority (HIGH + CRITICAL only):")
    priority_filter = PriorityEventFilter(EventPriority.HIGH)
    for event in events:
        passes = priority_filter.filter(event)
        status = "✓" if passes else "✗"
        print(f"  {status} [{event.priority.name}] {event.source}: {passes}")
    
    print("\n3. Filter by Source (database + api only):")
    source_filter = SourceEventFilter({"database", "api"})
    for event in events:
        passes = source_filter.filter(event)
        status = "✓" if passes else "✗"
        print(f"  {status} [{event.source}]: {passes}")
    
    print("\n4. Composite Filter (ERROR events AND Critical priority):")
    error_filter = TypeEventFilter({EventType.ERROR})
    critical_filter = PriorityEventFilter(EventPriority.CRITICAL)
    composite = CompositeEventFilter([error_filter, critical_filter])
    for event in events:
        passes = composite.filter(event)
        status = "✓" if passes else "✗"
        print(f"  {status} [{event.event_type.name} + {event.priority.name}]: {passes}")
    
    print("\n✓ Filters can be combined to create complex filtering rules\n")


def demo_event_aggregation():
    """Demonstrate event aggregation functionality"""
    print("=" * 60)
    print("DEMO: Event Aggregation")
    print("=" * 60)
    
    aggregator = EventAggregator(time_window_seconds=60.0)
    
    # Add aggregation rule to count events by type
    aggregator.add_aggregation_rule(
        key="error_count",
        key_extractor=lambda e: "errors" if e.event_type == EventType.ERROR else "other",
        aggregator=lambda events: {
            'type': 'ERROR',
            'count': len(events),
            'sources': list(set(e.source for e in events)),
            'max_priority': max(p.value for p in [e.priority for e in events])
        }
    )
    
    # Simulate error events
    print("\nSimulating error events:")
    error_events = [
        Event(EventType.ERROR, EventPriority.LOW, "service_a"),
        Event(EventType.ERROR, EventPriority.NORMAL, "service_b"),
        Event(EventType.ERROR, EventPriority.CRITICAL, "service_c"),
        Event(EventType.ERROR, EventPriority.HIGH, "service_a"),
    ]
    
    for event in error_events:
        print(f"  - [{event.priority.name}] {event.source}")
        result = aggregator.add_event(event)
        if result:
            print(f"    → Aggregation triggered: {result}")
    
    # Force aggregation of remaining events
    print("\nForcing aggregation of remaining events:")
    results = aggregator.aggregate_all()
    for key, result in results.items():
        print(f"  {key}: {result}")
    
    print("\n✓ Events are aggregated when threshold is reached\n")


def demo_event_tracing():
    """Demonstrate event tracing functionality"""
    print("=" * 60)
    print("DEMO: Event Tracing")
    print("=" * 60)
    
    tracer = EventTracer()
    
    # Start tracing session
    trace_id = tracer.start_tracing()
    print(f"\nStarted tracing session: {trace_id[:8]}...")
    
    # Simulate event lifecycle
    events = [
        (EventType.SYSTEM, EventPriority.NORMAL, "service_startup", {"service": "web"}),
        (EventType.DATA, EventPriority.HIGH, "data_loading", {"records": 1000}),
        (EventType.ERROR, EventPriority.CRITICAL, "database_error", {"error": "timeout"}),
        (EventType.SYSTEM, EventPriority.NORMAL, "service_recovery", {"status": "ok"}),
    ]
    
    print("\nEvent lifecycle:")
    for event_type, priority, source, data in events:
        event = Event(event_type, priority, source, data=data)
        event.trace_id = trace_id
        
        tracer.record_event(event, "created")
        tracer.record_event(event, "validated")
        tracer.record_event(event, "published")
        tracer.record_event(event, "processed")
        
        print(f"  - [{event_type.name}] {source}")
    
    # Show trace records
    print("\nTrace records:")
    trace = tracer.get_trace()
    for record in trace:
        print(f"  [{record['timestamp'][-8:]}] {record['event_type']}: {record['action']}")
    
    # Show trace summary
    print("\nTrace summary:")
    summary = tracer.get_trace_summary()
    print(f"  Total events: {summary['total_events']}")
    print(f"  Event types: {summary['event_types']}")
    print(f"  Actions: {summary['actions']}")
    
    # Stop tracing
    tracer.stop_tracing()
    print(f"\nStopped tracing session: {trace_id[:8]}...")
    
    print("\n✓ Trace records help debug event flow and identify issues\n")


def demo_complete_event_system():
    """Demonstrate the complete event system"""
    print("=" * 60)
    print("DEMO: Complete Advanced Event System")
    print("=" * 60)
    
    # Create event system
    system = AdvancedEventSystem("DemoSystem")
    system.start()
    
    # Add filters
    system.add_filter(TypeEventFilter({EventType.SYSTEM, EventType.ERROR, EventType.DATA}))
    system.add_filter(PriorityEventFilter(EventPriority.NORMAL))
    
    print("\n✓ System started with filters (SYSTEM/ERROR/DATA types, NORMAL+ priority)")
    
    # Simulate event processing
    events = [
        Event(EventType.SYSTEM, EventPriority.LOW, "heartbeat"),  # Will be filtered (low priority)
        Event(EventType.USER, EventPriority.NORMAL, "request"),  # Will be filtered (wrong type)
        Event(EventType.ERROR, EventPriority.CRITICAL, "database"),  # Will pass
        Event(EventType.SYSTEM, EventPriority.HIGH, "backup"),  # Will pass
        Event(EventType.DATA, EventPriority.NORMAL, "sync"),  # Will pass
    ]
    
    print("\nPublishing events:")
    for event in events:
        published = system.publish_event(event)
        status = "✓" if published else "✗ (filtered)"
        print(f"  {status} [{event.priority.name}] {event.event_type.name}: {event.source}")
    
    # Process events
    print(f"\nProcessing {system.event_queue.qsize()} events from queue...")
    processed = system.process_events(max_events=10)
    print(f"  Processed: {processed} events")
    
    # Show stats
    print("\nSystem statistics:")
    stats = system.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Show trace summary
    print("\nEvent trace summary:")
    trace_summary = system.tracer.get_trace_summary()
    print(f"  Total trace records: {trace_summary['total_events']}")
    print(f"  Event types in trace: {trace_summary['event_types']}")
    
    # Stop system
    system.stop()
    print("\n✓ System stopped\n")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print(" ADVANCED EVENT SYSTEM DEMONSTRATION")
    print("=" * 60 + "\n")
    
    demo_event_priority()
    demo_event_filtering()
    demo_event_aggregation()
    demo_event_tracing()
    demo_complete_event_system()
    
    print("=" * 60)
    print(" DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("""
This advanced event system provides:

1. Event Priority
   - 4 priority levels: LOW, NORMAL, HIGH, CRITICAL
   - Priority queue ensures high-priority events are processed first
   - Critical events bypass lower priority events

2. Event Filtering
   - Filter by event type, priority, source, or custom criteria
   - Chain filters together for complex filtering
   - Composite filters with AND/OR logic

3. Event Aggregation
   - Aggregate events within time windows
   - Custom aggregation rules by event properties
   - Useful for summarizing high-frequency events

4. Event Persistence
   - Save events to persistent storage
   - Load events with type and time filters
   - Batch save and clear operations

5. Event Tracing
   - Track event lifecycle for debugging
   - Record actions, details, and timestamps
   - Generate trace summaries

6. Complete Event System
   - Combines all features into one system
   - Publish-subscribe model
   - Thread-safe operations
   - Statistics and monitoring
""")


if __name__ == "__main__":
    main()
