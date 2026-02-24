"""
Tests for the Observer Pattern Module
"""

import unittest
import time
import threading
from typing import List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel.core.observer_pattern import (
    Subject, Observer, Event, EventPriority, ObserverRegistry
)


class MockObserver(Observer):
    """Test observer for unit testing"""
    
    def __init__(self, name: str = "MockObserver"):
        self.name = name
        self.received_events: List[Event] = []
        self.update_count = 0
    
    def update(self, event: Event) -> None:
        self.received_events.append(event)
        self.update_count += 1


class CallbackReceiver:
    """Test class for callback testing"""
    
    def __init__(self):
        self.received_events: List[Event] = []
        self.call_count = 0
    
    def callback(self, event: Event) -> None:
        self.received_events.append(event)
        self.call_count += 1


class TestSubjectSubscription(unittest.TestCase):
    """Test cases for subject subscription functionality"""
    
    def test_subject_creation(self):
        """Test subject can be created with optional name"""
        subject = Subject("TestSubject")
        self.assertEqual(subject.name, "TestSubject")
        self.assertEqual(subject.get_observer_count(), 0)
    
    def test_subject_default_name(self):
        """Test subject gets auto-generated name if not provided"""
        subject = Subject()
        self.assertIsNotNone(subject.name)
        self.assertTrue(subject.name.startswith("Subject-"))
    
    def test_subject_subscription_returns_id(self):
        """Test subscribe returns unique subscription ID"""
        subject = Subject()
        observer = MockObserver()
        
        sub_id = subject.subscribe(observer)
        
        self.assertIsNotNone(sub_id)
        self.assertIsInstance(sub_id, str)
        self.assertEqual(subject.get_observer_count(), 1)
    
    def test_multiple_subscriptions(self):
        """Test multiple observers can subscribe"""
        subject = Subject()
        observer1 = MockObserver("Observer1")
        observer2 = MockObserver("Observer2")
        
        subject.subscribe(observer1)
        subject.subscribe(observer2)
        
        self.assertEqual(subject.get_observer_count(), 2)
    
    def test_callback_subscription(self):
        """Test callback functions can be registered"""
        subject = Subject()
        receiver = CallbackReceiver()
        
        callback_id = subject.register_callback(receiver.callback)
        
        self.assertIsNotNone(callback_id)
        self.assertEqual(subject.get_observer_count(), 1)
    
    def test_context_manager_subscription(self):
        """Test subject can be used as context manager"""
        subject = Subject()
        
        with subject:
            observer = MockObserver()
            subject.subscribe(observer)
            self.assertEqual(subject.get_observer_count(), 1)
        
        # After context exit, all observers should be cleared
        self.assertEqual(subject.get_observer_count(), 0)


class TestObserverRegistration(unittest.TestCase):
    """Test cases for observer registration functionality"""
    
    def test_observer_receives_events(self):
        """Test registered observer receives emitted events"""
        subject = Subject()
        observer = MockObserver()
        subject.subscribe(observer)
        
        event = Event(type="test_event", data={"key": "value"})
        subject.emit(event)
        
        self.assertEqual(len(observer.received_events), 1)
        self.assertEqual(observer.received_events[0].type, "test_event")
    
    def test_observer_receives_event_data(self):
        """Test observer receives correct event data"""
        subject = Subject()
        observer = MockObserver()
        subject.subscribe(observer)
        
        test_data = {"message": "hello", "count": 42}
        event = Event(type="test", data=test_data)
        subject.emit(event)
        
        self.assertEqual(observer.received_events[0].data, test_data)
    
    def test_multiple_observers_all_receive(self):
        """Test all registered observers receive events"""
        subject = Subject()
        observer1 = MockObserver("O1")
        observer2 = MockObserver("O2")
        observer3 = MockObserver("O3")
        
        subject.subscribe(observer1)
        subject.subscribe(observer2)
        subject.subscribe(observer3)
        
        subject.notify("test", {"data": "value"})
        
        self.assertEqual(observer1.update_count, 1)
        self.assertEqual(observer2.update_count, 1)
        self.assertEqual(observer3.update_count, 1)
    
    def test_callback_receives_events(self):
        """Test registered callbacks receive emitted events"""
        subject = Subject()
        receiver = CallbackReceiver()
        subject.register_callback(receiver.callback)
        
        event = Event(type="callback_test", data={"test": True})
        subject.emit(event)
        
        self.assertEqual(receiver.call_count, 1)
        self.assertEqual(receiver.received_events[0].type, "callback_test")
    
    def test_get_observers(self):
        """Test get_observers returns all registered observers"""
        subject = Subject()
        observer1 = MockObserver()
        observer2 = MockObserver()
        
        subject.subscribe(observer1)
        subject.subscribe(observer2)
        
        observers = subject.get_observers()
        
        self.assertEqual(len(observers), 2)
        self.assertIn(observer1, observers)
        self.assertIn(observer2, observers)


class TestEventNotification(unittest.TestCase):
    """Test cases for event notification functionality"""
    
    def test_notify_creates_event(self):
        """Test notify method creates and emits an event"""
        subject = Subject()
        observer = MockObserver()
        subject.subscribe(observer)
        
        subject.notify("test_event", {"key": "value"})
        
        self.assertEqual(len(observer.received_events), 1)
        self.assertEqual(observer.received_events[0].type, "test_event")
    
    def test_notify_with_priority(self):
        """Test notify method respects event priority"""
        subject = Subject()
        observer = MockObserver()
        subject.subscribe(observer)
        
        subject.notify("urgent", {"alert": True}, priority=EventPriority.URGENT)
        
        self.assertEqual(observer.received_events[0].priority, EventPriority.URGENT)
    
    def test_notify_with_source(self):
        """Test notify method includes source"""
        subject = Subject()
        observer = MockObserver()
        subject.subscribe(observer)
        
        subject.notify("event", source="CustomSource")
        
        self.assertEqual(observer.received_events[0].source, "CustomSource")
    
    def test_event_history_tracking(self):
        """Test events are tracked in history"""
        subject = Subject()
        observer = MockObserver()
        subject.subscribe(observer)
        
        subject.notify("event1", {"id": 1})
        subject.notify("event2", {"id": 2})
        
        history = subject.get_event_history()
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].type, "event1")
        self.assertEqual(history[1].type, "event2")
    
    def test_event_history_limit(self):
        """Test event history respects max limit"""
        subject = Subject()
        subject._max_history = 5
        
        for i in range(10):
            subject.notify(f"event{i}")
        
        history = subject.get_event_history()
        
        self.assertEqual(len(history), 5)
        # Should contain the last 5 events
        self.assertEqual(history[0].type, "event5")
        self.assertEqual(history[-1].type, "event9")
    
    def test_multiple_events_sequence(self):
        """Test multiple events are received in order"""
        subject = Subject()
        observer = MockObserver()
        subject.subscribe(observer)
        
        for i in range(5):
            subject.notify(f"event_{i}", {"index": i})
        
        self.assertEqual(observer.update_count, 5)
        
        for i, event in enumerate(observer.received_events):
            self.assertEqual(event.data["index"], i)
    
    def test_thread_safety(self):
        """Test subject works correctly with concurrent access"""
        subject = Subject()
        errors = []
        
        def emitter():
            try:
                for i in range(10):
                    subject.notify(f"event_{i}")
            except Exception as e:
                errors.append(e)
        
        def subscriber():
            try:
                observer = MockObserver()
                subject.subscribe(observer)
                time.sleep(0.01)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for _ in range(3):
            t1 = threading.Thread(target=emitter)
            t2 = threading.Thread(target=subscriber)
            threads.extend([t1, t2])
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)


class TestUnsubscribe(unittest.TestCase):
    """Test cases for unsubscribe functionality"""
    
    def test_unsubscribe_by_id(self):
        """Test observer can be unsubscribed by subscription ID"""
        subject = Subject()
        observer = MockObserver()
        
        sub_id = subject.subscribe(observer)
        self.assertEqual(subject.get_observer_count(), 1)
        
        result = subject.unsubscribe(sub_id)
        
        self.assertTrue(result)
        self.assertEqual(subject.get_observer_count(), 0)
    
    def test_unsubscribe_nonexistent_id(self):
        """Test unsubscribe returns False for non-existent ID"""
        subject = Subject()
        
        result = subject.unsubscribe("nonexistent-id")
        
        self.assertFalse(result)
    
    def test_unsubscribe_stops_notifications(self):
        """Test unsubscribed observer doesn't receive events"""
        subject = Subject()
        observer = MockObserver()
        
        sub_id = subject.subscribe(observer)
        subject.notify("before_unsubscribe")
        
        subject.unsubscribe(sub_id)
        subject.notify("after_unsubscribe")
        
        self.assertEqual(observer.update_count, 1)
        self.assertEqual(observer.received_events[0].type, "before_unsubscribe")
    
    def test_unsubscribe_callback(self):
        """Test callback can be unsubscribed"""
        subject = Subject()
        receiver = CallbackReceiver()
        
        callback_id = subject.register_callback(receiver.callback)
        subject.notify("before")
        
        subject.unsubscribe(callback_id)
        subject.notify("after")
        
        self.assertEqual(receiver.call_count, 1)
    
    def test_remove_observer_by_instance(self):
        """Test observer can be removed by instance reference"""
        subject = Subject()
        observer = MockObserver()
        observer2 = MockObserver()
        
        subject.subscribe(observer)
        subject.subscribe(observer2)
        
        result = subject.remove_observer(observer)
        
        self.assertTrue(result)
        self.assertEqual(subject.get_observer_count(), 1)
        self.assertNotIn(observer, subject.get_observers())
    
    def test_remove_nonexistent_observer(self):
        """Test removing non-existent observer returns False"""
        subject = Subject()
        observer = MockObserver()
        
        result = subject.remove_observer(observer)
        
        self.assertFalse(result)
    
    def test_clear_all_observers(self):
        """Test clear_all removes all observers"""
        subject = Subject()
        
        for i in range(5):
            subject.subscribe(MockObserver())
        
        self.assertEqual(subject.get_observer_count(), 5)
        
        subject.clear_all()
        
        self.assertEqual(subject.get_observer_count(), 0)
    
    def test_mixed_observer_and_callback_unsubscribe(self):
        """Test unsubscribe works with both observers and callbacks"""
        subject = Subject()
        observer = MockObserver()
        receiver = CallbackReceiver()
        
        sub_id = subject.subscribe(observer)
        callback_id = subject.register_callback(receiver.callback)
        
        self.assertEqual(subject.get_observer_count(), 2)
        
        subject.unsubscribe(sub_id)
        
        self.assertEqual(subject.get_observer_count(), 1)
        
        subject.unsubscribe(callback_id)
        
        self.assertEqual(subject.get_observer_count(), 0)


class TestObserverRegistry(unittest.TestCase):
    """Test cases for ObserverRegistry"""
    
    def test_create_subject(self):
        """Test registry creates subjects"""
        registry = ObserverRegistry()
        
        subject = registry.create_subject("TestSubject")
        
        self.assertIsNotNone(subject)
        self.assertEqual(subject.name, "TestSubject")
        self.assertEqual(registry.get_subject_count(), 1)
    
    def test_duplicate_subject_name_raises(self):
        """Test creating duplicate subject name raises error"""
        registry = ObserverRegistry()
        
        registry.create_subject("TestSubject")
        
        with self.assertRaises(ValueError):
            registry.create_subject("TestSubject")
    
    def test_get_subject(self):
        """Test registry can retrieve subjects"""
        registry = ObserverRegistry()
        created = registry.create_subject("MySubject")
        
        retrieved = registry.get_subject("MySubject")
        
        self.assertIs(created, retrieved)
    
    def test_get_nonexistent_subject(self):
        """Test get_subject returns None for non-existent"""
        registry = ObserverRegistry()
        
        result = registry.get_subject("NonExistent")
        
        self.assertIsNone(result)
    
    def test_remove_subject(self):
        """Test registry can remove subjects"""
        registry = ObserverRegistry()
        registry.create_subject("ToRemove")
        
        result = registry.remove_subject("ToRemove")
        
        self.assertTrue(result)
        self.assertEqual(registry.get_subject_count(), 0)
    
    def test_remove_nonexistent_subject(self):
        """Test removing non-existent subject returns False"""
        registry = ObserverRegistry()
        
        result = registry.remove_subject("NonExistent")
        
        self.assertFalse(result)


class TestEventPriority(unittest.TestCase):
    """Test cases for EventPriority enum"""
    
    def test_priority_values(self):
        """Test priority enum values"""
        self.assertEqual(EventPriority.LOW.value, 1)
        self.assertEqual(EventPriority.NORMAL.value, 2)
        self.assertEqual(EventPriority.HIGH.value, 3)
        self.assertEqual(EventPriority.URGENT.value, 4)


class TestEvent(unittest.TestCase):
    """Test cases for Event dataclass"""
    
    def test_event_creation(self):
        """Test event can be created"""
        event = Event(type="test", data={"key": "value"})
        
        self.assertEqual(event.type, "test")
        self.assertEqual(event.data, {"key": "value"})
        self.assertEqual(event.priority, EventPriority.NORMAL)
        self.assertIsNone(event.source)
    
    def test_event_auto_generates_id(self):
        """Test event auto-generates ID"""
        event1 = Event(type="test")
        event2 = Event(type="test")
        
        self.assertNotEqual(event1.id, event2.id)
    
    def test_event_auto_generates_timestamp(self):
        """Test event auto-generates timestamp"""
        before = time.time()
        event = Event(type="test")
        after = time.time()
        
        self.assertGreaterEqual(event.timestamp, before)
        self.assertLessEqual(event.timestamp, after)


if __name__ == "__main__":
    unittest.main()
