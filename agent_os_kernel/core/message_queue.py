"""
Message Queue Module for Agent-OS-Kernel

This module provides message queue capabilities including:
- Message Persistence: Save and load messages to/from persistent storage
- Priority Queue: Messages with priority levels
- Publish/Subscribe Pattern: Topic-based messaging
- Message Acknowledgment: Confirm message processing
"""

import json
import os
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from heapq import heappush, heappop
from typing import Any, Callable, Dict, List, Optional, Set, Union, Generic, TypeVar
from collections import defaultdict, deque
from pathlib import Path
import copy
import copy


class MessagePriority(Enum):
    """Message priority levels (higher = more urgent)"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageStatus(Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"


@dataclass
class Message:
    """
    Core message class representing a message in the queue.
    
    Attributes:
        topic: Topic/channel of the message
        payload: Message content/data
        priority: Message priority level
        status: Current processing status
        message_id: Unique identifier for the message
        timestamp: When the message was created
        publisher_id: ID of the message publisher
        subscriber_id: ID of the subscriber processing the message
        metadata: Additional metadata
        retry_count: Number of retry attempts
        max_retries: Maximum retry attempts before marking as failed
    """
    topic: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    publisher_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['priority'] = self.priority.name
        result['status'] = self.status.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create Message from dictionary"""
        data = copy.deepcopy(data)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['priority'] = MessagePriority[data['priority']]
        data['status'] = MessageStatus[data['status']]
        return cls(**data)


class Subscription:
    """Represents a subscription to a topic"""
    
    def __init__(
        self,
        topic: str,
        subscriber_id: str,
        callback: Callable[[Message], None],
        filter_func: Optional[Callable[[Message], bool]] = None
    ):
        self.topic = topic
        self.subscriber_id = subscriber_id
        self.callback = callback
        self.filter_func = filter_func
        self.is_active = True
    
    def matches(self, message: Message) -> bool:
        """Check if message matches this subscription"""
        if not self.is_active:
            return False
        if self.topic != message.topic and self.topic != "*":
            return False
        if self.filter_func and not self.filter_func(message):
            return False
        return True


class PriorityMessageQueue:
    """
    Thread-safe priority message queue with persistence support.
    
    Messages are ordered by priority (higher priority first) and
    timestamp (earlier first) for messages with the same priority.
    """
    
    def __init__(self, name: str = "default", persistence_path: Optional[str] = None):
        """
        Initialize the priority message queue.
        
        Args:
            name: Queue name
            persistence_path: Path to store persisted messages (None for no persistence)
        """
        self.name = name
        self.persistence_path = persistence_path
        self._queue: List[tuple] = []  # Heap queue: (priority_level, timestamp, message_id, message)
        self._lock = threading.RLock()
        self._acking_lock = threading.RLock()
        self._id_counter = 0
        
        # Create persistence directory if needed
        if self.persistence_path:
            Path(self.persistence_path).mkdir(parents=True, exist_ok=True)
            self._load_persisted_messages()
    
    def _get_next_id(self) -> int:
        """Get next unique ID for queue ordering"""
        self._id_counter += 1
        return self._id_counter
    
    def _get_priority_level(self, priority: MessagePriority) -> int:
        """Convert enum priority to numeric level (higher = more urgent)"""
        return priority.value
    
    def _get_message_key(self, message: Message) -> tuple:
        """Generate a key for heap ordering: (priority, timestamp, id)"""
        priority_level = self._get_priority_level(message.priority)
        return (-priority_level, message.timestamp, self._get_next_id())
    
    def push(self, message: Message) -> str:
        """
        Add a message to the queue.
        
        Args:
            message: Message to add
            
        Returns:
            Message ID
        """
        with self._lock:
            heappush(self._queue, self._get_message_key(message))
            if self.persistence_path:
                self._persist_message(message)
            return message.message_id
    
    def pop(self) -> Optional[Message]:
        """
        Remove and return the highest priority message.
        
        Returns:
            Highest priority message, or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None
            _, _, _, message = heappop(self._queue)
            message.status = MessageStatus.PROCESSING
            return message
    
    def peek(self) -> Optional[Message]:
        """
        Peek at the highest priority message without removing it.
        
        Returns:
            Highest priority message, or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None
            _, _, _, message = self._queue[0]
            return message
    
    def __len__(self) -> int:
        """Return the number of messages in the queue"""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        with self._lock:
            return len(self._queue) == 0
    
    def get_all(self) -> List[Message]:
        """Get all messages in priority order"""
        with self._lock:
            return [msg for _, _, _, msg in sorted(self._queue)]
    
    def _persist_message(self, message: Message) -> None:
        """Persist a message to disk"""
        if not self.persistence_path:
            return
        try:
            file_path = os.path.join(self.persistence_path, f"{message.message_id}.msg")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(message.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Silently fail on persistence errors
    
    def _load_persisted_messages(self) -> None:
        """Load persisted messages from disk"""
        if not self.persistence_path:
            return
        try:
            Path(self.persistence_path).mkdir(parents=True, exist_ok=True)
            for filename in os.listdir(self.persistence_path):
                if filename.endswith('.msg'):
                    file_path = os.path.join(self.persistence_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            message = Message.from_dict(data)
                            if message.status == MessageStatus.PENDING:
                                heappush(self._queue, self._get_message_key(message))
                    except Exception:
                        pass  # Skip corrupted files
        except Exception:
            pass  # Silently fail on load errors
    
    def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge a message has been processed.
        
        Args:
            message_id: ID of the message to acknowledge
            
        Returns:
            True if message was found and acknowledged, False otherwise
        """
        # Remove from persistence
        if self.persistence_path:
            try:
                file_path = os.path.join(self.persistence_path, f"{message_id}.msg")
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        return True
    
    def clear(self) -> int:
        """
        Clear all messages from the queue.
        
        Returns:
            Number of messages removed
        """
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            
            # Clear persisted messages
            if self.persistence_path:
                try:
                    for filename in os.listdir(self.persistence_path):
                        if filename.endswith('.msg'):
                            os.remove(os.path.join(self.persistence_path, filename))
                except Exception:
                    pass
            
            return count


class MessageBroker:
    """
    Message broker implementing publish/subscribe pattern with:
    - Topic-based messaging
    - Multiple subscribers per topic
    - Message persistence
    - Message acknowledgment
    - Thread-safe operations
    """
    
    def __init__(self, persistence_path: Optional[str] = None):
        """
        Initialize the message broker.
        
        Args:
            persistence_path: Path for message persistence (None for no persistence)
        """
        self.persistence_path = persistence_path
        self._queues: Dict[str, PriorityMessageQueue] = defaultdict(
            lambda: PriorityMessageQueue(persistence_path=persistence_path)
        )
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._subscriber_ids: Set[str] = set()
        self._lock = threading.RLock()
        self._pending_acks: Dict[str, Message] = {}  # Messages awaiting acknowledgment
        
        # Create persistence directory if needed
        if self.persistence_path:
            Path(self.persistence_path).mkdir(parents=True, exist_ok=True)
    
    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        publisher_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            payload: Message payload
            priority: Message priority
            publisher_id: ID of the publisher
            metadata: Additional metadata
            
        Returns:
            Message ID
        """
        message = Message(
            topic=topic,
            payload=payload,
            priority=priority,
            publisher_id=publisher_id,
            metadata=metadata or {}
        )
        
        # Add to topic queue
        self._queues[topic].push(message)
        
        return message.message_id
    
    def subscribe(
        self,
        topic: str,
        subscriber_id: str,
        callback: Callable[[Message], None],
        filter_func: Optional[Callable[[Message], bool]] = None
    ) -> Subscription:
        """
        Subscribe to a topic.
        
        Args:
            topic: Topic to subscribe to (use "*" for all topics)
            subscriber_id: Unique subscriber ID
            callback: Function to call when message is received
            filter_func: Optional function to filter messages
            
        Returns:
            Subscription object
        """
        with self._lock:
            subscription = Subscription(
                topic=topic,
                subscriber_id=subscriber_id,
                callback=callback,
                filter_func=filter_func
            )
            self._subscriptions[topic].append(subscription)
            self._subscriber_ids.add(subscriber_id)
            return subscription
    
    def unsubscribe(self, subscription: Subscription) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            subscription: Subscription to remove
            
        Returns:
            True if unsubscribed successfully
        """
        with self._lock:
            if subscription.topic in self._subscriptions:
                try:
                    self._subscriptions[subscription.topic].remove(subscription)
                    subscription.is_active = False
                    return True
                except ValueError:
                    pass
            return False
    
    def receive(
        self,
        topic: str,
        subscriber_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Message]:
        """
        Receive a message from a topic.
        
        Args:
            topic: Topic to receive from
            subscriber_id: ID of the subscriber
            timeout: Maximum time to wait (None for no timeout)
            
        Returns:
            Message or None if no message available
        """
        start_time = time.time()
        
        while True:
            # Try to get message from topic queue
            queue = self._queues.get(topic)
            if queue and not queue.is_empty():
                message = queue.pop()
                if message:
                    message.subscriber_id = subscriber_id
                    message.status = MessageStatus.PROCESSING
                    self._pending_acks[message.message_id] = message
                    
                    # Try to match and deliver to matching subscriptions
                    with self._lock:
                        for sub in self._subscriptions.get(topic, []):
                            if sub.matches(message):
                                try:
                                    sub.callback(message)
                                except Exception:
                                    pass  # Callbacks should not crash the broker
            
            # Check all matching topics
            found_message = None
            with self._lock:
                for t in [topic, "*"]:
                    queue = self._queues.get(t)
                    if queue and not queue.is_empty():
                        message = queue.pop()
                        if message:
                            message.subscriber_id = subscriber_id
                            message.status = MessageStatus.PROCESSING
                            self._pending_acks[message.message_id] = message
                            
                            # Deliver to matching subscriptions
                            for sub in self._subscriptions.get(t, []):
                                if sub.matches(message):
                                    try:
                                        sub.callback(message)
                                    except Exception:
                                        pass
                            found_message = message
                            break
            
            if found_message:
                return found_message
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None
                time.sleep(0.01)  # Small sleep to avoid busy waiting
    
    def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge a message has been processed.
        
        Args:
            message_id: ID of the message to acknowledge
            
        Returns:
            True if acknowledged successfully
        """
        with self._acking_lock:
            if message_id in self._pending_acks:
                message = self._pending_acks.pop(message_id)
                message.status = MessageStatus.ACKNOWLEDGED
                
                # Acknowledge in queue
                for queue in self._queues.values():
                    queue.acknowledge(message_id)
                
                return True
            return False
    
    def get_queue_size(self, topic: str) -> int:
        """Get the number of pending messages for a topic"""
        return len(self._queues.get(topic, []))
    
    def get_topics(self) -> List[str]:
        """Get list of active topics"""
        with self._lock:
            return list(set(self._queues.keys()) | set(self._subscriptions.keys()))
    
    def get_subscribers(self, topic: str) -> List[str]:
        """Get list of subscriber IDs for a topic"""
        with self._lock:
            return [sub.subscriber_id for sub in self._subscriptions.get(topic, [])]
    
    def clear_topic(self, topic: str) -> int:
        """Clear all messages for a topic"""
        with self._lock:
            if topic in self._queues:
                count = len(self._queues[topic])
                self._queues[topic].clear()
                return count
            return 0


# Convenience function to create a message broker
def create_message_broker(persistence_path: Optional[str] = None) -> MessageBroker:
    """
    Create a new message broker instance.
    
    Args:
        persistence_path: Path for message persistence
        
    Returns:
        MessageBroker instance
    """
    return MessageBroker(persistence_path=persistence_path)
