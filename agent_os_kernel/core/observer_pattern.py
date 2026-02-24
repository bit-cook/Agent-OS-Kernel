"""
Observer Pattern Implementation

This module provides a generic observer pattern implementation for event-driven
communication between components in the agent OS kernel.

Features:
- Subject subscription
- Observer registration
- Event notification
- Unsubscribe support
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Set, Type, OptionalVar
from dataclasses import dataclass, field
from enum import Enum
import threading
import uuid


T = TypeVar('T')


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Event:
    """Event data structure"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class Observer(ABC):
    """Abstract base class for observers"""
    
    @abstractmethod
    def update(self, event: Event) -> None:
        """Called when an observed subject emits an event"""
        pass


class Subject:
    """
    Subject that maintains a list of observers and notifies them of events.
    
    Supports:
    - Registration/deregistration of observers
    - Event broadcasting with priority support
    - Thread-safe operations
    """
    
    def __init__(self, name: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.name = name or f"Subject-{self.id[:8]}"
        self._observers: Dict[str, Observer] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._event_history: List[Event] = []
        self._max_history: int = 100
        
    def subscribe(self, observer: Observer) -> str:
        """
        Register an observer to receive events from this subject.
        
        Args:
            observer: The observer instance to register
            
        Returns:
            Subscription ID for later unsubscribe
        """
        with self._lock:
            sub_id = str(uuid.uuid4())
            self._observers[sub_id] = observer
            return sub_id
    
    def register_callback(self, callback: Callable[[Event], None]) -> str:
        """
        Register a callback function to receive events.
        
        Args:
            callback: Function to call when events are emitted
            
        Returns:
            Callback ID for later removal
        """
        with self._lock:
            callback_id = str(uuid.uuid4())
            self._callbacks[callback_id] = callback
            return callback_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove an observer or callback by subscription ID.
        
        Args:
            subscription_id: The ID returned from subscribe/register_callback
            
        Returns:
            True if successfully removed, False if not found
        """
        with self._lock:
            if subscription_id in self._observers:
                del self._observers[subscription_id]
                return True
            if subscription_id in self._callbacks:
                del self._callbacks[subscription_id]
                return True
            return False
    
    def remove_observer(self, observer: Observer) -> bool:
        """
        Remove an observer instance from the subject.
        
        Args:
            observer: The observer instance to remove
            
        Returns:
            True if successfully removed, False if not found
        """
        with self._lock:
            removed = False
            for sub_id, obs in list(self._observers.items()):
                if obs is observer:
                    del self._observers[sub_id]
                    removed = True
            return removed
    
    def emit(self, event: Event) -> None:
        """
        Emit an event to all registered observers and callbacks.
        
        Args:
            event: The event to emit
        """
        with self._lock:
            # Store in history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
        
        # Sort observers and callbacks by priority (if applicable)
        # For now, notify in registration order
        
        # Notify observers
        with self._lock:
            observers_copy = list(self._observers.items())
            callbacks_copy = list(self._callbacks.items())
        
        for sub_id, observer in observers_copy:
            try:
                observer.update(event)
            except Exception as e:
                # Log error but continue notifying other observers
                print(f"Error notifying observer {sub_id}: {e}")
        
        # Notify callbacks
        for callback_id, callback in callbacks_copy:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in callback {callback_id}: {e}")
    
    def notify(self, event_type: str, data: Dict[str, Any] = None, 
               priority: EventPriority = EventPriority.NORMAL,
               source: Optional[str] = None) -> None:
        """
        Convenience method to create and emit an event.
        
        Args:
            event_type: Type of the event
            data: Event data dictionary
            priority: Event priority
            source: Optional source identifier
        """
        event = Event(
            type=event_type,
            data=data or {},
            priority=priority,
            source=source or self.name
        )
        self.emit(event)
    
    def get_observers(self) -> List[Observer]:
        """Get list of all registered observers"""
        with self._lock:
            return list(self._observers.values())
    
    def get_observer_count(self) -> int:
        """Get the number of registered observers"""
        with self._lock:
            return len(self._observers) + len(self._callbacks)
    
    def clear_all(self) -> None:
        """Remove all observers and callbacks"""
        with self._lock:
            self._observers.clear()
            self._callbacks.clear()
    
    def get_event_history(self) -> List[Event]:
        """Get the event history"""
        with self._lock:
            return list(self._event_history)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.clear_all()
        return False


class ObserverRegistry:
    """
    Registry for managing multiple subjects and their observers.
    Useful for complex event systems with multiple channels.
    """
    
    def __init__(self):
        self._subjects: Dict[str, Subject] = {}
        self._lock = threading.RLock()
    
    def create_subject(self, name: str) -> Subject:
        """
        Create a new subject with the given name.
        
        Args:
            name: Unique subject name
            
        Returns:
            The created subject
        """
        with self._lock:
            if name in self._subjects:
                raise ValueError(f"Subject '{name}' already exists")
            subject = Subject(name)
            self._subjects[name] = subject
            return subject
    
    def get_subject(self, name: str) -> Optional[Subject]:
        """
        Get a subject by name.
        
        Args:
            name: Subject name
            
        Returns:
            The subject or None if not found
        """
        with self._lock:
            return self._subjects.get(name)
    
    def remove_subject(self, name: str) -> bool:
        """
        Remove a subject by name.
        
        Args:
            name: Subject name
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self._subjects:
                del self._subjects[name]
                return True
            return False
    
    def get_all_subjects(self) -> List[Subject]:
        """Get all registered subjects"""
        with self._lock:
            return list(self._subjects.values())
    
    def get_subject_count(self) -> int:
        """Get the number of subjects"""
        with self._lock:
            return len(self._subjects)
    
    def clear_all(self) -> None:
        """Remove all subjects"""
        with self._lock:
            self._subjects.clear()


# Example usage functions
def create_observer_pattern_demo():
    """Create a demonstration of the observer pattern"""
    
    # Create a subject (publisher)
    news_subject = Subject("NewsPublisher")
    
    # Create an observer
    class NewsSubscriber(Observer):
        def __init__(self, name: str):
            self.name = name
            self.received_news = []
        
        def update(self, event: Event):
            self.received_news.append(event)
            print(f"[{self.name}] Received news: {event.type} - {event.data}")
    
    # Create subscribers
    subscriber1 = NewsSubscriber("Alice")
    subscriber2 = NewsSubscriber("Bob")
    
    # Subscribe
    sub1_id = news_subject.subscribe(subscriber1)
    sub2_id = news_subject.subscribe(subscriber2)
    
    # Publish news
    news_subject.notify("breaking_news", {"headline": "Important event!", "content": "..."})
    news_subject.notify("sports_news", {"headline": "Game results", "score": "3-1"})
    
    # Unsubscribe one
    news_subject.unsubscribe(sub1_id)
    
    # More news - only Bob receives
    news_subject.notify("weather_alert", {"temp": 25, "condition": "Sunny"})
    
    print(f"\nAlice received {len(subscriber1.received_news)} news items")
    print(f"Bob received {len(subscriber2.received_news)} news items")
    
    return news_subject, subscriber1, subscriber2


if __name__ == "__main__":
    create_observer_pattern_demo()
