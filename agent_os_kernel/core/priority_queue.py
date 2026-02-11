# -*- coding: utf-8 -*-
"""
Priority Queue Module for Agent-OS-Kernel

Provides a thread-safe priority queue implementation for managing
tasks and events with different priority levels.
"""

import heapq
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from enum import Enum, auto


class Priority(Enum):
    """Priority levels for queue items."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(order=True)
class QueueItem:
    """Item stored in the priority queue."""
    priority: Priority
    item_id: int
    data: Any
    created_at: float

    def __post_init__(self):
        object.__setattr__(self, 'priority', Priority(self.priority))


class PriorityQueue:
    """
    Thread-safe Priority Queue Implementation
    
    Uses a heap-based data structure for efficient priority-based
    ordering. Supports multiple priority levels and item tracking.
    """
    
    _item_counter = 0
    _counter_lock = threading.Lock()
    
    def __init__(self, max_size: Optional[int] = None):
        """
        Initialize the priority queue.
        
        Args:
            max_size: Maximum number of items (None for unlimited)
        """
        self._heap: List[QueueItem] = []
        self._max_size = max_size
        self._lock = threading.RLock()
        self._callbacks: Dict[Priority, List[Callable]] = {}
    
    def put(self, data: Any, priority: Priority = Priority.MEDIUM) -> int:
        """
        Add an item to the queue.
        
        Args:
            data: Item data to queue
            priority: Priority level of the item
            
        Returns:
            Item ID assigned to the queued item
        """
        with self._lock:
            if self._max_size and len(self._heap) >= self._max_size:
                raise QueueFullError("Queue has reached maximum capacity")
            
            with PriorityQueue._counter_lock:
                PriorityQueue._item_counter += 1
                item_id = PriorityQueue._item_counter
            
            item = QueueItem(
                priority=priority,
                item_id=item_id,
                data=data,
                created_at=__import__('time').time()
            )
            heapq.heappush(self._heap, item)
            return item_id
    
    def get(self) -> QueueItem:
        """
        Remove and return the highest priority item.
        
        Returns:
            The highest priority item in the queue
        """
        with self._lock:
            if not self._heap:
                raise QueueEmptyError("Queue is empty")
            return heapq.heappop(self._heap)
    
    def peek(self) -> QueueItem:
        """
        View the highest priority item without removing it.
        
        Returns:
            The highest priority item
        """
        with self._lock:
            if not self._heap:
                raise QueueEmptyError("Queue is empty")
            return self._heap[0]
    
    def size(self) -> int:
        """
        Get the current number of items in the queue.
        
        Returns:
            Number of items in the queue
        """
        with self._lock:
            return len(self._heap)
    
    def empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            True if queue is empty
        """
        with self._lock:
            return len(self._heap) == 0
    
    def clear(self) -> int:
        """
        Remove all items from the queue.
        
        Returns:
            Number of items that were removed
        """
        with self._lock:
            count = len(self._heap)
            self._heap.clear()
            return count
    
    def get_by_priority(self, priority: Priority) -> List[Any]:
        """
        Get all items of a specific priority.
        
        Args:
            priority: Priority level to filter by
            
        Returns:
            List of data items with the specified priority
        """
        with self._lock:
            return [item.data for item in self._heap if item.priority == priority]
    
    def register_callback(self, priority: Priority, callback: Callable) -> None:
        """
        Register a callback for when an item of specific priority is added.
        
        Args:
            priority: Priority level to listen for
            callback: Function to call when item is added
        """
        if priority not in self._callbacks:
            self._callbacks[priority] = []
        self._callbacks[priority].append(callback)


class QueueEmptyError(Exception):
    """Raised when trying to get from an empty queue."""
    pass


class QueueFullError(Exception):
    """Raised when trying to add to a full queue."""
    pass
