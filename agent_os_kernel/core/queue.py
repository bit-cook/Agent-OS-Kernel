"""
Basic Queue Module for Agent-OS-Kernel

This module provides basic queue capabilities including:
- FIFO Queue: Standard first-in-first-out queue
- Priority Queue: Elements with priority levels
- Thread-safe operations for concurrent access
- Queue statistics and monitoring
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union


class QueueEmpty(Exception):
    """Exception raised when attempting to dequeue from an empty queue"""
    pass


class QueueFull(Exception):
    """Exception raised when queue has reached maximum capacity"""
    pass


class QueueStats:
    """Statistics for queue operations"""
    
    def __init__(self):
        self.enqueue_count = 0
        self.dequeue_count = 0
        self.peek_count = 0
        self.total_items_added = 0
        self.total_items_removed = 0
        self.total_wait_time = 0.0
        self.max_size_reached = 0
        self.last_enqueue_time: Optional[float] = None
        self.last_dequeue_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary"""
        return {
            'enqueue_count': self.enqueue_count,
            'dequeue_count': self.dequeue_count,
            'peek_count': self.peek_count,
            'total_items_added': self.total_items_added,
            'total_items_removed': self.total_items_removed,
            'total_wait_time': self.total_wait_time,
            'max_size_reached': self.max_size_reached,
            'last_enqueue_time': self.last_enqueue_time,
            'last_dequeue_time': self.last_dequeue_time
        }
    
    def reset(self) -> None:
        """Reset all statistics"""
        self.enqueue_count = 0
        self.dequeue_count = 0
        self.peek_count = 0
        self.total_items_added = 0
        self.total_items_removed = 0
        self.total_wait_time = 0.0
        self.max_size_reached = 0
        self.last_enqueue_time = None
        self.last_dequeue_time = None


T = TypeVar('T')


class BasicQueue(Generic[T]):
    """
    Thread-safe basic FIFO queue with statistics and monitoring.
    
    A simple first-in-first-out queue designed for concurrent access
    with built-in statistics tracking.
    """
    
    def __init__(
        self,
        max_size: Optional[int] = None,
        name: str = "default"
    ):
        """
        Initialize the basic queue.
        
        Args:
            max_size: Maximum queue size (None for unlimited)
            name: Queue name for identification
        """
        self.name = name
        self.max_size = max_size
        self._queue: deque = deque()
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._stats = QueueStats()
        self._closed = False
    
    def enqueue(self, item: T, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Add an item to the queue.
        
        Args:
            item: Item to add
            block: If True, block when queue is full
            timeout: Maximum time to wait (None for no timeout)
            
        Returns:
            True if item was added successfully
            
        Raises:
            QueueFull: If queue is full and blocking is False
        """
        start_time = time.time()
        
        with self._lock:
            # Check if closed
            if self._closed:
                raise RuntimeError("Queue is closed")
            
            # Wait for space if queue is full
            if self.max_size is not None and len(self._queue) >= self.max_size:
                if not block:
                    raise QueueFull(f"Queue '{self.name}' is full")
                
                remaining_timeout = timeout
                while len(self._queue) >= self.max_size:
                    if remaining_timeout is not None and remaining_timeout <= 0:
                        raise QueueFull(f"Queue '{self.name}' is full (timeout)")
                    
                    self._not_full.wait(timeout=remaining_timeout)
                    if self._closed:
                        raise RuntimeError("Queue is closed")
                    
                    if remaining_timeout is not None:
                        remaining_timeout = timeout - (time.time() - start_time)
                        if remaining_timeout < 0:
                            raise QueueFull(f"Queue '{self.name}' is full (timeout)")
            
            # Add item
            self._queue.append(item)
            self._stats.enqueue_count += 1
            self._stats.total_items_added += 1
            self._stats.last_enqueue_time = time.time()
            
            # Update max size statistic
            if len(self._queue) > self._stats.max_size_reached:
                self._stats.max_size_reached = len(self._queue)
            
            # Notify waiting consumers
            self._not_empty.notify()
            
            return True
    
    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> T:
        """
        Remove and return an item from the queue.
        
        Args:
            block: If True, block when queue is empty
            timeout: Maximum time to wait (None for no timeout)
            
        Returns:
            Item from the queue
            
        Raises:
            QueueEmpty: If queue is empty and blocking is False
        """
        start_time = time.time()
        
        with self._lock:
            # Wait for items
            while len(self._queue) == 0:
                if not block:
                    raise QueueEmpty(f"Queue '{self.name}' is empty")
                
                if self._closed:
                    raise QueueEmpty(f"Queue '{self.name}' is closed")
                
                remaining_timeout = timeout
                if remaining_timeout is not None:
                    if remaining_timeout <= 0:
                        raise QueueEmpty(f"Queue '{self.name}' is empty (timeout)")
                    
                    self._not_empty.wait(timeout=remaining_timeout)
                    if remaining_timeout is not None:
                        remaining_timeout = timeout - (time.time() - start_time)
                        if remaining_timeout < 0:
                            raise QueueEmpty(f"Queue '{self.name}' is empty (timeout)")
                else:
                    self._not_empty.wait()
                
                if self._closed and len(self._queue) == 0:
                    raise QueueEmpty(f"Queue '{self.name}' is closed")
            
            # Remove and return item
            item = self._queue.popleft()
            self._stats.dequeue_count += 1
            self._stats.total_items_removed += 1
            self._stats.last_dequeue_time = time.time()
            self._stats.total_wait_time += time.time() - start_time
            
            # Notify waiting producers
            self._not_full.notify()
            
            return item
    
    def peek(self) -> T:
        """
        Return the next item without removing it.
        
        Returns:
            Next item in queue
            
        Raises:
            QueueEmpty: If queue is empty
        """
        with self._lock:
            if len(self._queue) == 0:
                raise QueueEmpty(f"Queue '{self.name}' is empty")
            
            self._stats.peek_count += 1
            return self._queue[0]
    
    def __len__(self) -> int:
        """Return the number of items in the queue"""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        with self._lock:
            return len(self._queue) == 0
    
    def is_full(self) -> bool:
        """Check if queue is full"""
        with self._lock:
            if self.max_size is None:
                return False
            return len(self._queue) >= self.max_size
    
    def clear(self) -> int:
        """
        Remove all items from the queue.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._lock:
            return self._stats.to_dict()
    
    def close(self) -> None:
        """Close the queue, preventing further enqueues"""
        with self._lock:
            self._closed = True
            self._not_empty.notify_all()
            self._not_full.notify_all()
    
    def __contains__(self, item: T) -> bool:
        """Check if item is in queue"""
        with self._lock:
            return item in self._queue
    
    def get_all(self) -> List[T]:
        """Get all items without removing them"""
        with self._lock:
            return list(self._queue)


class PriorityLevel(Enum):
    """Priority levels (higher = more urgent)"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(order=True)
class PriorityItem(Generic[T]):
    """Wrapper for items with priority"""
    priority: int = field(compare=True)
    item: T = field(compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)


class PriorityQueue(Generic[T]):
    """
    Thread-safe priority queue.
    
    Items are dequeued based on priority (higher priority first)
    and then by insertion order (FIFO for same priority).
    """
    
    def __init__(
        self,
        max_size: Optional[int] = None,
        name: str = "priority"
    ):
        """
        Initialize the priority queue.
        
        Args:
            max_size: Maximum queue size (None for unlimited)
            name: Queue name for identification
        """
        self.name = name
        self.max_size = max_size
        self._queue: List[PriorityItem] = []
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._stats = QueueStats()
        self._closed = False
    
    def enqueue(
        self,
        item: T,
        priority: Union[int, PriorityLevel] = PriorityLevel.MEDIUM,
        block: bool = True,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Add an item with priority.
        
        Args:
            item: Item to add
            priority: Priority level (higher = more urgent)
            block: If True, block when queue is full
            timeout: Maximum time to wait
            
        Returns:
            True if item was added successfully
        """
        start_time = time.time()
        
        # Convert enum to int if needed
        if isinstance(priority, PriorityLevel):
            priority_value = priority.value
        else:
            priority_value = priority
        
        with self._lock:
            if self._closed:
                raise RuntimeError("Queue is closed")
            
            if self.max_size is not None and len(self._queue) >= self.max_size:
                if not block:
                    raise QueueFull(f"PriorityQueue '{self.name}' is full")
                
                remaining_timeout = timeout
                while len(self._queue) >= self.max_size:
                    if remaining_timeout is not None:
                        remaining_timeout -= (time.time() - start_time)
                        if remaining_timeout <= 0:
                            raise QueueFull(f"PriorityQueue '{self.name}' is full (timeout)")
                    
                    self._not_full.wait(timeout=remaining_timeout)
                    if self._closed:
                        raise RuntimeError("Queue is closed")
            
            # Create priority item and add to heap
            # Negate priority so higher values come first (ascending sort)
            priority_item = PriorityItem(priority=-priority_value, item=item)
            self._queue.append(priority_item)
            self._queue.sort()  # Maintain heap property
            
            self._stats.enqueue_count += 1
            self._stats.total_items_added += 1
            self._stats.last_enqueue_time = time.time()
            
            if len(self._queue) > self._stats.max_size_reached:
                self._stats.max_size_reached = len(self._queue)
            
            self._not_empty.notify()
            
            return True
    
    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> T:
        """
        Remove and return the highest priority item.
        
        Args:
            block: If True, block when queue is empty
            timeout: Maximum time to wait
            
        Returns:
            Highest priority item
        """
        start_time = time.time()
        
        with self._lock:
            while len(self._queue) == 0:
                if not block:
                    raise QueueEmpty(f"PriorityQueue '{self.name}' is empty")
                
                if self._closed:
                    raise QueueEmpty(f"PriorityQueue '{self.name}' is closed")
                
                remaining_timeout = timeout
                if remaining_timeout is not None:
                    if remaining_timeout <= 0:
                        raise QueueEmpty(f"PriorityQueue '{self.name}' is empty (timeout)")
                    
                    self._not_empty.wait(timeout=remaining_timeout)
                    remaining_timeout = timeout - (time.time() - start_time)
                    if remaining_timeout < 0:
                        raise QueueEmpty(f"PriorityQueue '{self.name}' is empty (timeout)")
                else:
                    self._not_empty.wait()
                
                if self._closed and len(self._queue) == 0:
                    raise QueueEmpty(f"PriorityQueue '{self.name}' is closed")
            
            # Get highest priority item (first in sorted list)
            priority_item = self._queue.pop(0)
            
            self._stats.dequeue_count += 1
            self._stats.total_items_removed += 1
            self._stats.last_dequeue_time = time.time()
            self._stats.total_wait_time += time.time() - start_time
            
            self._not_full.notify()
            
            return priority_item.item
    
    def peek(self) -> T:
        """Return the highest priority item without removing it"""
        with self._lock:
            if len(self._queue) == 0:
                raise QueueEmpty(f"PriorityQueue '{self.name}' is empty")
            return self._queue[0].item
    
    def __len__(self) -> int:
        """Return number of items in queue"""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        with self._lock:
            return len(self._queue) == 0
    
    def is_full(self) -> bool:
        """Check if queue is full"""
        with self._lock:
            if self.max_size is None:
                return False
            return len(self._queue) >= self.max_size
    
    def clear(self) -> int:
        """Remove all items"""
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._lock:
            return self._stats.to_dict()
    
    def close(self) -> None:
        """Close the queue"""
        with self._lock:
            self._closed = True
            self._not_empty.notify_all()
            self._not_full.notify_all()
    
    def get_all(self) -> List[T]:
        """Get all items sorted by priority"""
        with self._lock:
            return [item.item for item in sorted(self._queue)]


# Convenience functions
def create_queue(max_size: Optional[int] = None, name: str = "default") -> BasicQueue:
    """Create a basic FIFO queue"""
    return BasicQueue(max_size=max_size, name=name)


def create_priority_queue(
    max_size: Optional[int] = None,
    name: str = "priority"
) -> PriorityQueue:
    """Create a priority queue"""
    return PriorityQueue(max_size=max_size, name=name)
