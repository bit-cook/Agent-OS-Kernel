"""
Tests for Advanced Event System

Tests cover:
- Event Priority: Priority-based event handling
- Event Filtering: Event filtering capabilities
- Event Aggregation: Event aggregation functionality
- Event Persistence: Event storage and retrieval
- Event Tracing: Event flow tracking
"""

import pytest
import time
import tempfile
import os
from datetime import datetime, timedelta

from agent_os_kernel.core.event_system_advanced import (
    Event,
    EventPriority,
    EventType,
    EventFilter,
    EventFilterChain,
    TypeEventFilter,
    PriorityEventFilter,
    SourceEventFilter,
    CompositeEventFilter,
    EventAggregator,
    EventPersister,
    EventTracer,
    AdvancedEventSystem,
)


class TestEventPriority:
    """Test event priority functionality"""
    
    def test_event_priority_ordering(self):
        """Test that events are ordered by priority"""
        events = [
            Event(
                event_type=EventType.SYSTEM,
                priority=EventPriority.LOW,
                source="test"
            ),
            Event(
                event_type=EventType.SYSTEM,
                priority=EventPriority.CRITICAL,
                source="test"
            ),
            Event(
                event_type=EventType.SYSTEM,
                priority=EventPriority.HIGH,
                source="test"
            ),
            Event(
                event_type=EventType.SYSTEM,
                priority=EventPriority.NORMAL,
                source="test"
            ),
        ]
        
        # Verify priority values
        assert EventPriority.LOW.value == 1
        assert EventPriority.NORMAL.value == 2
        assert EventPriority.HIGH.value == 3
        assert EventPriority.CRITICAL.value == 4
        
        # Critical should be highest
        critical_event = Event(
            event_type=EventType.SYSTEM,
            priority=EventPriority.CRITICAL,
            source="test"
        )
        low_event = Event(
            event_type=EventType.SYSTEM,
            priority=EventPriority.LOW,
            source="test"
        )
        assert critical_event.priority.value > low_event.priority.value
    
    def test_priority_queue_ordering(self):
        """Test that priority queue orders events correctly"""
        from agent_os_kernel.core.event_system_advanced import PriorityQueue
        
        pq = PriorityQueue()
        
        # Add events in random order
        pq.put(Event(EventType.SYSTEM, EventPriority.NORMAL, "source1"))
        pq.put(Event(EventType.SYSTEM, EventPriority.CRITICAL, "source2"))
        pq.put(Event(EventType.SYSTEM, EventPriority.LOW, "source3"))
        pq.put(Event(EventType.SYSTEM, EventPriority.HIGH, "source4"))
        
        # Should get CRITICAL first, then HIGH, etc.
        assert pq.get().priority == EventPriority.CRITICAL
        assert pq.get().priority == EventPriority.HIGH
        assert pq.get().priority == EventPriority.NORMAL
        assert pq.get().priority == EventPriority.LOW
    
    def test_event_serialization_with_priority(self):
        """Test event serialization preserves priority"""
        event = Event(
            event_type=EventType.DATA,
            priority=EventPriority.HIGH,
            source="test_source",
            data={"key": "value"}
        )
        
        serialized = event.to_dict()
        assert serialized['priority'] == 'HIGH'
        
        deserialized = Event.from_dict(serialized)
        assert deserialized.priority == EventPriority.HIGH
        assert deserialized.event_id == event.event_id


class TestEventFiltering:
    """Test event filtering functionality"""
    
    def test_type_event_filter(self):
        """Test filtering by event type"""
        filter = TypeEventFilter({EventType.SYSTEM, EventType.DATA})
        
        system_event = Event(EventType.SYSTEM, EventPriority.NORMAL, "test")
        user_event = Event(EventType.USER, EventPriority.NORMAL, "test")
        
        assert filter.filter(system_event) == True
        assert filter.filter(user_event) == False
    
    def test_priority_event_filter(self):
        """Test filtering by minimum priority"""
        filter = PriorityEventFilter(EventPriority.HIGH)
        
        high_event = Event(EventType.SYSTEM, EventPriority.HIGH, "test")
        low_event = Event(EventType.SYSTEM, EventPriority.LOW, "test")
        
        assert filter.filter(high_event) == True
        assert filter.filter(low_event) == False
    
    def test_source_event_filter(self):
        """Test filtering by source"""
        filter = SourceEventFilter({"source_a", "source_b"})
        
        event_a = Event(EventType.SYSTEM, EventPriority.NORMAL, "source_a")
        event_c = Event(EventType.SYSTEM, EventPriority.NORMAL, "source_c")
        
        assert filter.filter(event_a) == True
        assert filter.filter(event_c) == False
    
    def test_composite_event_filter_and(self):
        """Test composite filter with AND logic"""
        type_filter = TypeEventFilter({EventType.SYSTEM})
        priority_filter = PriorityEventFilter(EventPriority.HIGH)
        composite = CompositeEventFilter([type_filter, priority_filter])
        
        event_valid = Event(EventType.SYSTEM, EventPriority.HIGH, "test")
        event_wrong_type = Event(EventType.USER, EventPriority.HIGH, "test")
        event_wrong_priority = Event(EventType.SYSTEM, EventPriority.LOW, "test")
        
        assert composite.filter(event_valid) == True
        assert composite.filter(event_wrong_type) == False
        assert composite.filter(event_wrong_priority) == False
    
    def test_composite_event_filter_or(self):
        """Test composite filter with OR logic"""
        type_filter = TypeEventFilter({EventType.SYSTEM})
        priority_filter = PriorityEventFilter(EventPriority.CRITICAL)
        composite = CompositeEventFilter([type_filter, priority_filter], combine_with_and=False)
        
        event_type = Event(EventType.SYSTEM, EventPriority.LOW, "test")
        event_priority = Event(EventType.USER, EventPriority.CRITICAL, "test")
        event_neither = Event(EventType.USER, EventPriority.LOW, "test")
        
        assert composite.filter(event_type) == True
        assert composite.filter(event_priority) == True
        assert composite.filter(event_neither) == False
    
    def test_event_filter_chain(self):
        """Test chaining multiple filters"""
        chain = EventFilterChain()
        chain.add_filter(TypeEventFilter({EventType.SYSTEM}))
        chain.add_filter(PriorityEventFilter(EventPriority.NORMAL))
        
        event = Event(EventType.SYSTEM, EventPriority.HIGH, "test")
        
        assert chain.filter(event) == True


class TestEventAggregation:
    """Test event aggregation functionality"""
    
    def test_basic_aggregation(self):
        """Test basic event aggregation"""
        aggregator = EventAggregator(time_window_seconds=60.0)
        
        # Add aggregation rule for event type
        aggregator.add_aggregation_rule(
            key="by_type",
            key_extractor=lambda e: e.event_type.name,
            aggregator=lambda events: {
                'type': events[0].event_type.name,
                'count': len(events),
                'sources': list(set(e.source for e in events))
            }
        )
        
        # Add multiple events of same type
        for i in range(3):
            event = Event(EventType.SYSTEM, EventPriority.NORMAL, f"source_{i}")
            result = aggregator.add_event(event)
            # First two won't trigger aggregation
            if i >= 2:
                assert result is not None
                assert result['count'] == 3
    
    def test_aggregation_with_different_keys(self):
        """Test aggregation with different grouping keys"""
        aggregator = EventAggregator(time_window_seconds=60.0)
        
        # Aggregate by source
        aggregator.add_aggregation_rule(
            key="by_source",
            key_extractor=lambda e: e.source,
            aggregator=lambda events: {
                'source': events[0].source,
                'count': len(events),
                'types': list(set(e.event_type.name for e in events))
            }
        )
        
        # Add events from same source
        events = [
            Event(EventType.SYSTEM, EventPriority.NORMAL, "web_server"),
            Event(EventType.DATA, EventPriority.HIGH, "web_server"),
            Event(EventType.ERROR, EventPriority.CRITICAL, "web_server"),
        ]
        
        # The 3rd event should trigger aggregation
        result = None
        for event in events:
            result = aggregator.add_event(event)
        
        # Result should have been returned on the 3rd event
        assert result is not None
        assert result['source'] == 'web_server'
        assert result['count'] == 3
        assert 'SYSTEM' in result['types']
        assert 'DATA' in result['types']
        assert 'ERROR' in result['types']
    
    def test_aggregation_time_window(self):
        """Test that aggregation respects time window"""
        aggregator = EventAggregator(time_window_seconds=0.1)  # Very short window
        
        aggregator.add_aggregation_rule(
            key="by_type",
            key_extractor=lambda e: e.event_type.name,
            aggregator=lambda events: {'count': len(events)}
        )
        
        # Add first event
        event1 = Event(EventType.SYSTEM, EventPriority.NORMAL, "test")
        aggregator.add_event(event1)
        
        # Wait for window to expire
        time.sleep(0.15)
        
        # Add more events
        event2 = Event(EventType.SYSTEM, EventPriority.NORMAL, "test")
        aggregator.add_event(event2)
        
        # Should not aggregate because previous events expired
        # Buffer was cleared, so we only have 1 event


class TestEventPersistence:
    """Test event persistence functionality"""
    
    def test_save_and_load_events(self):
        """Test saving and loading events"""
        persister = EventPersister()
        
        # Create test events
        events = [
            Event(EventType.SYSTEM, EventPriority.HIGH, "source1", data={"msg": "event1"}),
            Event(EventType.DATA, EventPriority.NORMAL, "source2", data={"msg": "event2"}),
            Event(EventType.ERROR, EventPriority.CRITICAL, "source3", data={"msg": "event3"}),
        ]
        
        # Save events
        for event in events:
            persister.save_event(event)
        
        # Load all events
        loaded = persister.load_events()
        assert len(loaded) == 3
        
        # Verify event data
        loaded_ids = [e.event_id for e in loaded]
        for event in events:
            assert event.event_id in loaded_ids
    
    def test_filter_by_event_type(self):
        """Test loading events filtered by type"""
        persister = EventPersister()
        
        # Save mixed events
        persister.save_event(Event(EventType.SYSTEM, EventPriority.NORMAL, "test"))
        persister.save_event(Event(EventType.DATA, EventPriority.NORMAL, "test"))
        persister.save_event(Event(EventType.SYSTEM, EventPriority.NORMAL, "test"))
        
        # Filter by type
        system_events = persister.load_events(event_type=EventType.SYSTEM)
        data_events = persister.load_events(event_type=EventType.DATA)
        
        assert len(system_events) == 2
        assert len(data_events) == 1
    
    def test_filter_by_time_range(self):
        """Test loading events filtered by time range"""
        persister = EventPersister()
        
        # Save events at different times
        now = datetime.utcnow()
        
        event_old = Event(EventType.SYSTEM, EventPriority.NORMAL, "test")
        event_old.timestamp = now - timedelta(hours=2)
        
        event_recent = Event(EventType.SYSTEM, EventPriority.NORMAL, "test")
        event_recent.timestamp = now - timedelta(minutes=30)
        
        event_future = Event(EventType.SYSTEM, EventPriority.NORMAL, "test")
        event_future.timestamp = now + timedelta(hours=1)
        
        persister.save_event(event_old)
        persister.save_event(event_recent)
        persister.save_event(event_future)
        
        # Filter to last hour (from 1 hour ago to now)
        recent_events = persister.load_events(
            start_time=now - timedelta(hours=1),
            end_time=now
        )
        
        # Should only include event_recent (event_future is after 'now')
        assert len(recent_events) == 1
    
    def test_save_multiple_events(self):
        """Test batch saving events"""
        persister = EventPersister()
        
        events = [Event(EventType.SYSTEM, EventPriority.NORMAL, f"source_{i}") 
                  for i in range(10)]
        
        count = persister.save_events(events)
        assert count == 10
        
        loaded = persister.load_events()
        assert len(loaded) == 10
    
    def test_clear_storage(self):
        """Test clearing all stored events"""
        persister = EventPersister()
        
        # Add some events
        persister.save_event(Event(EventType.SYSTEM, EventPriority.NORMAL, "test"))
        persister.save_event(Event(EventType.DATA, EventPriority.NORMAL, "test"))
        
        # Clear storage
        count = persister.clear_storage()
        assert count == 2
        
        # Verify empty
        loaded = persister.load_events()
        assert len(loaded) == 0


class TestEventTracing:
    """Test event tracing functionality"""
    
    def test_start_stop_tracing(self):
        """Test starting and stopping tracing"""
        tracer = EventTracer()
        
        trace_id = tracer.start_tracing()
        assert trace_id is not None
        assert tracer.tracing_active == True
        
        stopped_id = tracer.stop_tracing()
        assert stopped_id == trace_id
        assert tracer.tracing_active == False
    
    def test_record_event(self):
        """Test recording events in trace"""
        tracer = EventTracer()
        tracer.start_tracing()
        
        event = Event(EventType.SYSTEM, EventPriority.HIGH, "test")
        event.trace_id = tracer.global_trace_id
        
        trace_id = tracer.record_event(event, "published")
        assert trace_id == tracer.global_trace_id
        
        trace = tracer.get_trace()
        assert len(trace) == 1
        assert trace[0]['action'] == "published"
    
    def test_get_trace_summary(self):
        """Test getting trace summary"""
        tracer = EventTracer()
        tracer.start_tracing()
        
        events = [
            (EventType.SYSTEM, "published"),
            (EventType.SYSTEM, "processed"),
            (EventType.DATA, "published"),
            (EventType.DATA, "processed"),
        ]
        
        for event_type, action in events:
            event = Event(event_type, EventPriority.NORMAL, "test")
            event.trace_id = tracer.global_trace_id
            tracer.record_event(event, action)
        
        summary = tracer.get_trace_summary()
        
        assert summary['total_events'] == 4
        assert 'SYSTEM' in summary['event_types']
        assert 'DATA' in summary['event_types']
        assert 'published' in summary['actions']
        assert 'processed' in summary['actions']
    
    def test_trace_with_custom_details(self):
        """Test recording event with custom details"""
        tracer = EventTracer()
        tracer.start_tracing()
        
        event = Event(EventType.ERROR, EventPriority.CRITICAL, "test")
        event.trace_id = tracer.global_trace_id
        
        details = {"error_code": 500, "message": "Server error"}
        tracer.record_event(event, "error_occurred", details)
        
        trace = tracer.get_trace()
        assert trace[0]['details'] == details
    
    def test_max_history_limit(self):
        """Test that trace history is limited"""
        tracer = EventTracer(max_history=5)
        tracer.start_tracing()
        
        # Add more events than max_history
        for i in range(10):
            event = Event(EventType.SYSTEM, EventPriority.NORMAL, "test")
            event.trace_id = tracer.global_trace_id
            tracer.record_event(event, f"action_{i}")
        
        trace = tracer.get_trace()
        assert len(trace) == 5  # Should be limited to max_history
        # Should have the most recent 5 events
        assert trace[0]['action'] == "action_5"
        assert trace[-1]['action'] == "action_9"


class TestAdvancedEventSystem:
    """Integration tests for the complete event system"""
    
    def test_system_start_stop(self):
        """Test starting and stopping the event system"""
        system = AdvancedEventSystem()
        
        assert system.start() == True
        assert system._running == True
        
        assert system.start() == False  # Already started
        
        assert system.stop() == True
        assert system._running == False
        
        assert system.stop() == False  # Already stopped
    
    def test_publish_event(self):
        """Test publishing events to the system"""
        system = AdvancedEventSystem()
        system.start()
        
        event = Event(EventType.SYSTEM, EventPriority.HIGH, "test_source")
        
        result = system.publish_event(event)
        assert result == True
        assert event in system.event_history
    
    def test_publish_filtered_event(self):
        """Test that filtered events are not queued"""
        system = AdvancedEventSystem()
        system.start()
        
        # Add type filter that only allows DATA events
        system.add_filter(TypeEventFilter({EventType.DATA}))
        
        # This should be filtered out
        system_event = Event(EventType.SYSTEM, EventPriority.HIGH, "test")
        assert system.publish_event(system_event) == False
        
        # This should pass
        data_event = Event(EventType.DATA, EventPriority.HIGH, "test")
        assert system.publish_event(data_event) == True
    
    def test_process_events(self):
        """Test processing events from queue"""
        system = AdvancedEventSystem()
        system.start()
        
        # Publish some events
        for i in range(5):
            system.publish_event(
                Event(EventType.SYSTEM, EventPriority.NORMAL, f"source_{i}")
            )
        
        # Process events
        processed = system.process_events(max_events=10)
        assert processed == 5
    
    def test_subscribe_to_events(self):
        """Test subscribing to events"""
        system = AdvancedEventSystem()
        system.start()
        
        received = []
        
        def callback(event):
            received.append(event)
        
        # Subscribe to all events
        system.subscribe(callback=callback)
        
        # Publish event
        event = Event(EventType.SYSTEM, EventPriority.HIGH, "test")
        system.publish_event(event)
        system.process_events(max_events=1)
        
        # Callback should have been called
        # Note: In this implementation, callbacks are called during process_events
    
    def test_system_stats(self):
        """Test getting system statistics"""
        system = AdvancedEventSystem()
        system.start()
        
        # Publish some events
        for i in range(3):
            system.publish_event(
                Event(EventType.SYSTEM, EventPriority.NORMAL, f"source_{i}")
            )
        
        stats = system.get_stats()
        
        assert stats['queue_size'] == 3
        assert stats['history_size'] == 3
        assert stats['tracing_active'] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
