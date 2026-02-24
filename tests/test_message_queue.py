"""
Tests for Message Queue Module
"""

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_os_kernel.core.message_queue import (
    Message,
    MessagePriority,
    MessageStatus,
    PriorityMessageQueue,
    MessageBroker,
    Subscription,
    create_message_broker,
)


class TestMessage(unittest.TestCase):
    """Test Message class functionality"""
    
    def test_message_creation(self):
        """Test creating a message"""
        message = Message(
            topic="test_topic",
            payload={"key": "value"},
            priority=MessagePriority.HIGH
        )
        self.assertIsNotNone(message.message_id)
        self.assertEqual(message.topic, "test_topic")
        self.assertEqual(message.payload, {"key": "value"})
        self.assertEqual(message.priority, MessagePriority.HIGH)
        self.assertEqual(message.status, MessageStatus.PENDING)
    
    def test_message_to_dict(self):
        """Test message serialization"""
        message = Message(
            topic="test_topic",
            payload={"key": "value"},
            priority=MessagePriority.CRITICAL
        )
        data = message.to_dict()
        self.assertEqual(data['topic'], "test_topic")
        self.assertEqual(data['payload'], {"key": "value"})
        self.assertEqual(data['priority'], "CRITICAL")
        self.assertEqual(data['status'], "pending")
    
    def test_message_from_dict(self):
        """Test message deserialization"""
        data = {
            'topic': 'test_topic',
            'payload': {'key': 'value'},
            'priority': 'HIGH',
            'status': 'processing',
            'message_id': 'test-id-123',
            'timestamp': '2024-01-01T12:00:00',
            'publisher_id': 'pub-1',
            'subscriber_id': None,
            'metadata': {},
            'retry_count': 0,
            'max_retries': 3
        }
        message = Message.from_dict(data)
        self.assertEqual(message.topic, 'test_topic')
        self.assertEqual(message.priority, MessagePriority.HIGH)
        self.assertEqual(message.status, MessageStatus.PROCESSING)
        self.assertEqual(message.message_id, 'test-id-123')


class TestPriorityMessageQueue(unittest.TestCase):
    """Test PriorityMessageQueue functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_queue_push_pop(self):
        """Test basic push and pop operations"""
        queue = PriorityMessageQueue(name="test", persistence_path=self.temp_dir)
        
        message1 = Message(topic="topic1", payload={"data": "1"})
        message2 = Message(topic="topic2", payload={"data": "2"})
        
        queue.push(message1)
        queue.push(message2)
        
        self.assertEqual(len(queue), 2)
        
        popped = queue.pop()
        self.assertIsNotNone(popped)
        self.assertEqual(popped.payload, {"data": "1"})
    
    def test_priority_queue_order(self):
        """Test that priority queue orders messages correctly"""
        queue = PriorityMessageQueue(name="test")
        
        low = Message(topic="t", payload={"p": "low"}, priority=MessagePriority.LOW)
        high = Message(topic="t", payload={"p": "high"}, priority=MessagePriority.HIGH)
        normal = Message(topic="t", payload={"p": "normal"}, priority=MessagePriority.NORMAL)
        critical = Message(topic="t", payload={"p": "critical"}, priority=MessagePriority.CRITICAL)
        
        queue.push(low)
        queue.push(high)
        queue.push(normal)
        queue.push(critical)
        
        # Should get critical first, then high, normal, low
        popped1 = queue.pop()
        popped2 = queue.pop()
        popped3 = queue.pop()
        popped4 = queue.pop()
        
        self.assertEqual(popped1.payload["p"], "critical")
        self.assertEqual(popped2.payload["p"], "high")
        self.assertEqual(popped3.payload["p"], "normal")
        self.assertEqual(popped4.payload["p"], "low")
    
    def test_queue_is_empty(self):
        """Test queue empty check"""
        queue = PriorityMessageQueue(name="test")
        self.assertTrue(queue.is_empty())
        
        queue.push(Message(topic="t", payload={}))
        self.assertFalse(queue.is_empty())
    
    def test_queue_peek(self):
        """Test peek without removing message"""
        queue = PriorityMessageQueue(name="test")
        
        message = Message(topic="t", payload={"data": "test"})
        queue.push(message)
        
        peeked = queue.peek()
        self.assertEqual(peeked.payload, {"data": "test"})
        self.assertEqual(len(queue), 1)  # Should still be in queue
    
    def test_acknowledge(self):
        """Test message acknowledgment"""
        queue = PriorityMessageQueue(name="test", persistence_path=self.temp_dir)
        
        message = Message(topic="t", payload={"data": "test"})
        queue.push(message)
        queue.acknowledge(message.message_id)
        
        # Should be removed from persistence
        persisted_file = os.path.join(self.temp_dir, f"{message.message_id}.msg")
        self.assertFalse(os.path.exists(persisted_file))
    
    def test_clear_queue(self):
        """Test clearing the queue"""
        queue = PriorityMessageQueue(name="test", persistence_path=self.temp_dir)
        
        for i in range(5):
            queue.push(Message(topic="t", payload={"data": i}))
        
        self.assertEqual(len(queue), 5)
        
        count = queue.clear()
        self.assertEqual(count, 5)
        self.assertTrue(queue.is_empty())


class TestMessageBroker(unittest.TestCase):
    """Test MessageBroker functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.received_messages = []
        self.broker = create_message_broker(persistence_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_publish_subscribe(self):
        """Test publish and subscribe pattern"""
        received = []
        
        def callback(message):
            received.append(message.message_id)
        
        # Subscribe to topic
        self.broker.subscribe(
            topic="test_topic",
            subscriber_id="sub-1",
            callback=callback
        )
        
        # Publish messages
        msg_id1 = self.broker.publish(
            topic="test_topic",
            payload={"data": "message1"}
        )
        msg_id2 = self.broker.publish(
            topic="test_topic",
            payload={"data": "message2"}
        )
        
        # Receive messages
        msg = self.broker.receive("test_topic", "sub-1", timeout=0.5)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.payload["data"], "message1")
        
        msg = self.broker.receive("test_topic", "sub-1", timeout=0.5)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.payload["data"], "message2")
    
    def test_message_persistence(self):
        """Test message persistence across broker restarts"""
        topic = "persistent_topic"
        
        # Publish a message
        msg_id = self.broker.publish(
            topic=topic,
            payload={"persistent": True}
        )
        
        # Create a new broker with same persistence path
        new_broker = create_message_broker(persistence_path=self.temp_dir)
        
        # Should have the persisted message
        size = new_broker.get_queue_size(topic)
        self.assertEqual(size, 1)
    
    def test_priority_queue_broker(self):
        """Test priority handling in broker"""
        # Publish messages with different priorities
        self.broker.publish(topic="priority_test", payload={"p": "low"}, priority=MessagePriority.LOW)
        self.broker.publish(topic="priority_test", payload={"p": "high"}, priority=MessagePriority.HIGH)
        self.broker.publish(topic="priority_test", payload={"p": "critical"}, priority=MessagePriority.CRITICAL)
        self.broker.publish(topic="priority_test", payload={"p": "normal"}, priority=MessagePriority.NORMAL)
        
        # Receive and check order
        msg1 = self.broker.receive("priority_test", "sub-1", timeout=0.5)
        msg2 = self.broker.receive("priority_test", "sub-1", timeout=0.5)
        msg3 = self.broker.receive("priority_test", "sub-1", timeout=0.5)
        msg4 = self.broker.receive("priority_test", "sub-1", timeout=0.5)
        
        self.assertEqual(msg1.payload["p"], "critical")
        self.assertEqual(msg2.payload["p"], "high")
        self.assertEqual(msg3.payload["p"], "normal")
        self.assertEqual(msg4.payload["p"], "low")
    
    def test_message_ack(self):
        """Test message acknowledgment"""
        # Publish a message
        msg_id = self.broker.publish(
            topic="ack_test",
            payload={"data": "test"}
        )
        
        # Receive the message
        msg = self.broker.receive("ack_test", "sub-1", timeout=0.5)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.status, MessageStatus.PROCESSING)
        
        # Acknowledge it
        result = self.broker.acknowledge(msg_id)
        self.assertTrue(result)
        
        # Message should be removed from pending
        self.assertNotIn(msg_id, self.broker._pending_acks)
    
    def test_multiple_subscribers(self):
        """Test multiple subscribers to the same topic"""
        received_by_sub1 = []
        received_by_sub2 = []
        
        def callback1(message):
            received_by_sub1.append(message.message_id)
        
        def callback2(message):
            received_by_sub2.append(message.message_id)
        
        # Subscribe both subscribers
        self.broker.subscribe("multi_topic", "sub-1", callback1)
        self.broker.subscribe("multi_topic", "sub-2", callback2)
        
        # Publish a message
        self.broker.publish("multi_topic", {"data": "test"})
        
        # Both should receive (each gets their own copy)
        self.broker.receive("multi_topic", "sub-1", timeout=0.5)
        self.broker.receive("multi_topic", "sub-2", timeout=0.5)
        
        self.assertEqual(len(received_by_sub1), 1)
        self.assertEqual(len(received_by_sub2), 1)
    
    def test_unsubscribe(self):
        """Test unsubscribe functionality"""
        received = []
        
        def callback(message):
            received.append(message.message_id)
        
        subscription = self.broker.subscribe("unsub_topic", "sub-1", callback)
        
        # Publish and receive
        msg_id = self.broker.publish("unsub_topic", {"data": "test"})
        self.broker.unsubscribe(subscription)
        
        # Should not receive after unsubscribe
        self.broker.receive("unsub_topic", "sub-1", timeout=0.5)
        self.assertEqual(len(received), 0)
    
    def test_subscription_filter(self):
        """Test subscription with filter function"""
        received = []
        
        def filter_func(message):
            return message.payload.get("should_receive", False)
        
        def callback(message):
            received.append(message.message_id)
        
        self.broker.subscribe("filter_topic", "sub-1", callback, filter_func=filter_func)
        
        # Publish filtered message
        msg_id1 = self.broker.publish("filter_topic", {"should_receive": False})
        # Publish non-filtered message
        msg_id2 = self.broker.publish("filter_topic", {"should_receive": True})
        
        self.broker.receive("filter_topic", "sub-1", timeout=0.5)
        
        # Only the filtered message should be received
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], msg_id2)
    
    def test_get_topics(self):
        """Test getting list of topics"""
        self.broker.publish("topic1", {"data": 1})
        self.broker.publish("topic2", {"data": 2})
        
        topics = self.broker.get_topics()
        
        self.assertIn("topic1", topics)
        self.assertIn("topic2", topics)
    
    def test_clear_topic(self):
        """Test clearing a specific topic"""
        self.broker.publish("clear_topic", {"data": 1})
        self.broker.publish("clear_topic", {"data": 2})
        
        count = self.broker.clear_topic("clear_topic")
        
        self.assertEqual(count, 2)
        self.assertEqual(self.broker.get_queue_size("clear_topic"), 0)


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of message queue"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.broker = create_message_broker(persistence_path=self.temp_dir)
        self.results = []
        self.lock = threading.Lock()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_concurrent_publish(self):
        """Test concurrent message publishing"""
        def publish_messages(subscriber_id, count):
            for i in range(count):
                self.broker.publish(
                    topic="concurrent",
                    payload={"from": subscriber_id, "num": i}
                )
        
        threads = [
            threading.Thread(target=publish_messages, args=("pub-1", 10)),
            threading.Thread(target=publish_messages, args=("pub-2", 10)),
            threading.Thread(target=publish_messages, args=("pub-3", 10)),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All messages should be in the queue
        total = self.broker.get_queue_size("concurrent")
        self.assertEqual(total, 30)


if __name__ == "__main__":
    unittest.main()
