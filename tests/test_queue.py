"""
Tests for Basic Queue Module
"""

import sys
import threading
import time
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_os_kernel.core.queue import (
    BasicQueue,
    PriorityQueue,
    PriorityLevel,
    QueueEmpty,
    QueueFull,
    QueueStats,
    create_queue,
    create_priority_queue,
)


class TestQueueStats(unittest.TestCase):
    """Test QueueStats functionality"""
    
    def test_stats_creation(self):
        """Test creating queue statistics"""
        stats = QueueStats()
        self.assertEqual(stats.enqueue_count, 0)
        self.assertEqual(stats.dequeue_count, 0)
        self.assertEqual(stats.peek_count, 0)
        self.assertEqual(stats.total_items_added, 0)
        self.assertEqual(stats.total_items_removed, 0)
        self.assertEqual(stats.max_size_reached, 0)
    
    def test_stats_to_dict(self):
        """Test statistics serialization"""
        stats = QueueStats()
        stats.enqueue_count = 5
        stats.dequeue_count = 3
        stats.max_size_reached = 10
        
        data = stats.to_dict()
        self.assertEqual(data['enqueue_count'], 5)
        self.assertEqual(data['dequeue_count'], 3)
        self.assertEqual(data['max_size_reached'], 10)
    
    def test_stats_reset(self):
        """Test resetting statistics"""
        stats = QueueStats()
        stats.enqueue_count = 10
        stats.dequeue_count = 5
        stats.max_size_reached = 15
        
        stats.reset()
        
        self.assertEqual(stats.enqueue_count, 0)
        self.assertEqual(stats.dequeue_count, 0)
        self.assertEqual(stats.max_size_reached, 0)


class TestBasicQueue(unittest.TestCase):
    """Test BasicQueue functionality"""
    
    def test_queue_creation(self):
        """Test creating a basic queue"""
        queue = BasicQueue()
        self.assertEqual(queue.name, "default")
        self.assertTrue(queue.is_empty())
        self.assertFalse(queue.is_full())
        self.assertEqual(len(queue), 0)
    
    def test_enqueue_dequeue(self):
        """Test basic enqueue and dequeue operations"""
        queue = BasicQueue()
        
        queue.enqueue("item1")
        queue.enqueue("item2")
        queue.enqueue("item3")
        
        self.assertEqual(len(queue), 3)
        
        item = queue.dequeue()
        self.assertEqual(item, "item1")
        
        item = queue.dequeue()
        self.assertEqual(item, "item2")
        
        item = queue.dequeue()
        self.assertEqual(item, "item3")
        
        self.assertTrue(queue.is_empty())
    
    def test_peek(self):
        """Test peek operation"""
        queue = BasicQueue()
        queue.enqueue("first")
        queue.enqueue("second")
        
        item = queue.peek()
        self.assertEqual(item, "first")
        
        # Peek should not remove item
        self.assertEqual(len(queue), 2)
        
        item2 = queue.dequeue()
        self.assertEqual(item2, "first")
    
    def test_max_size(self):
        """Test queue with maximum size"""
        queue = BasicQueue(max_size=2)
        
        queue.enqueue("item1")
        queue.enqueue("item2")
        
        # Should raise exception when full
        with self.assertRaises(QueueFull):
            queue.enqueue("item3", block=False)
    
    def test_blocking_enqueue(self):
        """Test blocking enqueue with timeout"""
        queue = BasicQueue(max_size=1)
        
        # Fill the queue
        queue.enqueue("item1")
        
        # Try to enqueue with short timeout - should timeout
        start = time.time()
        try:
            queue.enqueue("item2", timeout=0.1)
            self.fail("Should have raised QueueFull")
        except QueueFull:
            elapsed = time.time() - start
            self.assertGreaterEqual(elapsed, 0.09)
    
    def test_blocking_dequeue(self):
        """Test blocking dequeue with timeout"""
        queue = BasicQueue()
        
        # Try to dequeue from empty queue with timeout
        start = time.time()
        try:
            queue.dequeue(timeout=0.1)
            self.fail("Should have raised QueueEmpty")
        except QueueEmpty:
            elapsed = time.time() - start
            self.assertGreaterEqual(elapsed, 0.09)
    
    def test_clear(self):
        """Test clearing the queue"""
        queue = BasicQueue()
        queue.enqueue("item1")
        queue.enqueue("item2")
        queue.enqueue("item3")
        
        count = queue.clear()
        self.assertEqual(count, 3)
        self.assertTrue(queue.is_empty())
    
    def test_contains(self):
        """Test 'in' operator"""
        queue = BasicQueue()
        queue.enqueue("item1")
        queue.enqueue("item2")
        
        self.assertTrue("item1" in queue)
        self.assertTrue("item2" in queue)
        self.assertFalse("item3" in queue)
    
    def test_get_all(self):
        """Test getting all items"""
        queue = BasicQueue()
        queue.enqueue("first")
        queue.enqueue("second")
        
        items = queue.get_all()
        self.assertEqual(items, ["first", "second"])
        # Should not remove items
        self.assertEqual(len(queue), 2)
    
    def test_close(self):
        """Test closing the queue"""
        queue = BasicQueue()
        queue.enqueue("item")
        
        queue.close()
        
        # Should not be able to enqueue after close
        with self.assertRaises(RuntimeError):
            queue.enqueue("new_item")
    
    def test_statistics(self):
        """Test queue statistics tracking"""
        queue = BasicQueue()
        queue.enqueue("item1")
        queue.enqueue("item2")
        queue.dequeue()
        queue.peek()
        
        stats = queue.get_stats()
        self.assertEqual(stats['enqueue_count'], 2)
        self.assertEqual(stats['dequeue_count'], 1)
        self.assertEqual(stats['peek_count'], 1)
        self.assertEqual(stats['total_items_added'], 2)
        self.assertEqual(stats['total_items_removed'], 1)
    
    def test_concurrent_access(self):
        """Test thread-safe concurrent access"""
        queue = BasicQueue(max_size=100)
        errors = []
        
        def producer():
            try:
                for i in range(50):
                    queue.enqueue(i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        def consumer():
            try:
                for _ in range(50):
                    queue.dequeue(timeout=1)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=producer),
            threading.Thread(target=producer),
            threading.Thread(target=consumer),
            threading.Thread(target=consumer),
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertEqual(errors, [])
        # Should have processed all items
        self.assertTrue(queue.is_empty())


class TestPriorityQueue(unittest.TestCase):
    """Test PriorityQueue functionality"""
    
    def test_priority_queue_creation(self):
        """Test creating a priority queue"""
        queue = PriorityQueue()
        self.assertEqual(queue.name, "priority")
        self.assertTrue(queue.is_empty())
    
    def test_priority_order(self):
        """Test that higher priority items are dequeued first"""
        queue = PriorityQueue()
        
        queue.enqueue("low", priority=PriorityLevel.LOW)
        queue.enqueue("high", priority=PriorityLevel.HIGH)
        queue.enqueue("medium", priority=PriorityLevel.MEDIUM)
        
        # High priority should come first
        self.assertEqual(queue.dequeue(), "high")
        self.assertEqual(queue.dequeue(), "medium")
        self.assertEqual(queue.dequeue(), "low")
    
    def test_same_priority_fifo(self):
        """Test FIFO order for same priority items"""
        queue = PriorityQueue()
        
        queue.enqueue("first", priority=PriorityLevel.HIGH)
        queue.enqueue("second", priority=PriorityLevel.HIGH)
        queue.enqueue("third", priority=PriorityLevel.HIGH)
        
        self.assertEqual(queue.dequeue(), "first")
        self.assertEqual(queue.dequeue(), "second")
        self.assertEqual(queue.dequeue(), "third")
    
    def test_integer_priority(self):
        """Test using integer priorities"""
        queue = PriorityQueue()
        
        queue.enqueue("low", priority=1)
        queue.enqueue("high", priority=10)
        queue.enqueue("medium", priority=5)
        
        self.assertEqual(queue.dequeue(), "high")
        self.assertEqual(queue.dequeue(), "medium")
        self.assertEqual(queue.dequeue(), "low")
    
    def test_max_size(self):
        """Test priority queue with maximum size"""
        queue = PriorityQueue(max_size=2)
        
        queue.enqueue("item1", priority=1)
        queue.enqueue("item2", priority=2)
        
        with self.assertRaises(QueueFull):
            queue.enqueue("item3", priority=3, block=False)
    
    def test_blocking_operations(self):
        """Test blocking operations"""
        queue = PriorityQueue()
        
        # Test blocking dequeue
        try:
            queue.dequeue(timeout=0.1)
            self.fail("Should have raised QueueEmpty")
        except QueueEmpty:
            pass
    
    def test_get_all_sorted(self):
        """Test getting all items sorted by priority"""
        queue = PriorityQueue()
        
        queue.enqueue("low", priority=1)
        queue.enqueue("high", priority=3)
        queue.enqueue("medium", priority=2)
        
        items = queue.get_all()
        self.assertEqual(items, ["high", "medium", "low"])
    
    def test_priority_queue_stats(self):
        """Test priority queue statistics"""
        queue = PriorityQueue()
        
        queue.enqueue("item1", priority=1)
        queue.enqueue("item2", priority=2)
        queue.dequeue()
        
        stats = queue.get_stats()
        self.assertEqual(stats['enqueue_count'], 2)
        self.assertEqual(stats['dequeue_count'], 1)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_create_queue(self):
        """Test create_queue convenience function"""
        queue = create_queue(max_size=10, name="test_queue")
        self.assertEqual(queue.name, "test_queue")
        self.assertEqual(queue.max_size, 10)
    
    def test_create_priority_queue(self):
        """Test create_priority_queue convenience function"""
        queue = create_priority_queue(max_size=5, name="test_pq")
        self.assertEqual(queue.name, "test_pq")
        self.assertEqual(queue.max_size, 5)


if __name__ == "__main__":
    unittest.main()
