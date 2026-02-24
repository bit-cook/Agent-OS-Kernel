#!/usr/bin/env python3
"""
Message Queue Demo

This script demonstrates the message queue module features including:
- Basic publish/subscribe
- Priority messages
- Message acknowledgment
- Multiple subscribers
- Message persistence
"""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_os_kernel.core.message_queue import (
    Message,
    MessagePriority,
    MessageStatus,
    PriorityMessageQueue,
    MessageBroker,
    create_message_broker,
)


def demo_basic_publish_subscribe():
    """Demo: Basic publish/subscribe pattern"""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Publish/Subscribe")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    broker = create_message_broker(persistence_path=temp_dir)
    
    received_messages = []
    
    def subscriber_callback(message):
        received_messages.append({
            'message_id': message.message_id,
            'topic': message.topic,
            'payload': message.payload,
            'timestamp': message.timestamp.isoformat()
        })
        print(f"  [Subscriber] Received: {message.payload}")
    
    # Subscribe to topic
    print("\n1. Subscribing to 'notifications' topic...")
    broker.subscribe(
        topic="notifications",
        subscriber_id="subscriber-1",
        callback=subscriber_callback
    )
    
    # Publish messages
    print("\n2. Publishing messages to 'notifications' topic...")
    msg1 = broker.publish(
        topic="notifications",
        payload={"type": "info", "content": "System started"},
        publisher_id="system"
    )
    print(f"   Published message: {msg1}")
    
    msg2 = broker.publish(
        topic="notifications",
        payload={"type": "alert", "content": "High memory usage"},
        publisher_id="monitor"
    )
    print(f"   Published message: {msg2}")
    
    # Receive messages
    print("\n3. Receiving messages...")
    for _ in range(2):
        message = broker.receive("notifications", "subscriber-1", timeout=1.0)
        if message:
            print(f"   [Received] {message.payload}")
            # Acknowledge the message
            broker.acknowledge(message.message_id)
            print(f"   [Acknowledged] {message.message_id}")
    
    print(f"\n   Total messages received: {len(received_messages)}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_priority_queue():
    """Demo: Priority message handling"""
    print("\n" + "=" * 60)
    print("Demo 2: Priority Message Queue")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    broker = create_message_broker(persistence_path=temp_dir)
    
    print("\n1. Publishing messages with different priorities...")
    
    # Publish messages with different priorities
    broker.publish(
        topic="alerts",
        payload={"level": "low", "message": "Background task completed"},
        priority=MessagePriority.LOW,
        publisher_id="task-manager"
    )
    
    broker.publish(
        topic="alerts",
        payload={"level": "critical", "message": "System overheating!"},
        priority=MessagePriority.CRITICAL,
        publisher_id="hardware-monitor"
    )
    
    broker.publish(
        topic="alerts",
        payload={"level": "normal", "message": "Daily backup completed"},
        priority=MessagePriority.NORMAL,
        publisher_id="backup-service"
    )
    
    broker.publish(
        topic="alerts",
        payload={"level": "high", "message": "Disk space low"},
        priority=MessagePriority.HIGH,
        publisher_id="storage-monitor"
    )
    
    print("\n2. Receiving messages (should be ordered by priority)...")
    
    order_received = []
    for i in range(4):
        message = broker.receive("alerts", "alert-processor", timeout=1.0)
        if message:
            order_received.append(message.payload['level'])
            print(f"   [{i+1}] Priority: {message.payload['level'].upper():8} - {message.payload['message']}")
            broker.acknowledge(message.message_id)
    
    print(f"\n   Priority order: {' -> '.join(order_received)}")
    print("   Expected order: CRITICAL -> HIGH -> NORMAL -> LOW")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_message_acknowledgment():
    """Demo: Message acknowledgment mechanism"""
    print("\n" + "=" * 60)
    print("Demo 3: Message Acknowledgment")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    broker = create_message_broker(persistence_path=temp_dir)
    
    print("\n1. Publishing a task message...")
    task_message = broker.publish(
        topic="tasks",
        payload={
            "task_id": "task-123",
            "action": "process_data",
            "data_size": 1024
        },
        priority=MessagePriority.HIGH,
        publisher_id="task-scheduler"
    )
    print(f"   Published: {task_message}")
    
    print("\n2. Worker receiving and processing message...")
    message = broker.receive("tasks", "worker-1", timeout=1.0)
    
    if message:
        print(f"   [Received] Task: {message.payload['task_id']}")
        print(f"   [Status] Processing: {message.status.value}")
        
        # Simulate processing
        print("   [Processing] Processing data...")
        time.sleep(0.5)
        print("   [Processing] Complete!")
        
        # Acknowledge the message
        print(f"\n3. Acknowledging message: {message.message_id}")
        success = broker.acknowledge(message.message_id)
        print(f"   [Result] Acknowledgment {'successful' if success else 'failed'}")
        
        # Check message status
        print(f"   [Status] Final: {message.status.value}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_multiple_subscribers():
    """Demo: Multiple subscribers to the same topic"""
    print("\n" + "=" * 60)
    print("Demo 4: Multiple Subscribers")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    broker = create_message_broker(persistence_path=temp_dir)
    
    received_by_logger = []
    received_by_analytics = []
    
    def logger_callback(message):
        received_by_logger.append(message.message_id)
        print(f"   [Logger] Logged: {message.payload}")
    
    def analytics_callback(message):
        received_by_analytics.append(message.message_id)
        print(f"   [Analytics] Tracked: {message.payload}")
    
    # Subscribe both subscribers
    print("\n1. Setting up subscribers...")
    broker.subscribe(topic="events", subscriber_id="logger", callback=logger_callback)
    broker.subscribe(topic="events", subscriber_id="analytics", callback=analytics_callback)
    
    # Publish event
    print("\n2. Publishing an event...")
    event_id = broker.publish(
        topic="events",
        payload={"event": "user_login", "user_id": "user-456"},
        publisher_id="auth-service"
    )
    print(f"   Published: {event_id}")
    
    # Both subscribers receive
    print("\n3. Both subscribers receiving...")
    for _ in range(2):
        message = broker.receive("events", "logger", timeout=1.0)
        if message:
            broker.acknowledge(message.message_id)
    
    for _ in range(2):
        message = broker.receive("events", "analytics", timeout=1.0)
        if message:
            broker.acknowledge(message.message_id)
    
    print(f"\n   Logger received: {len(received_by_logger)} messages")
    print(f"   Analytics received: {len(received_by_analytics)} messages")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_subscription_filter():
    """Demo: Subscription with message filtering"""
    print("\n" + "=" * 60)
    print("Demo 5: Subscription Filters")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    broker = create_message_broker(persistence_path=temp_dir)
    
    received_by_alerts = []
    received_by_all = []
    
    # Alert subscriber - only receives high/critical priority
    def alert_filter(message):
        return message.priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]
    
    def alert_callback(message):
        received_by_alerts.append(message.message_id)
        print(f"   [Alerts] Received: {message.payload} (Priority: {message.priority.name})")
    
    # General subscriber - receives everything
    def general_callback(message):
        received_by_all.append(message.message_id)
        print(f"   [General] Received: {message.payload}")
    
    print("\n1. Setting up filtered subscriptions...")
    broker.subscribe(
        topic="notifications",
        subscriber_id="alert-system",
        callback=alert_callback,
        filter_func=alert_filter
    )
    broker.subscribe(
        topic="notifications",
        subscriber_id="general-listener",
        callback=general_callback
    )
    
    # Publish various messages
    print("\n2. Publishing messages...")
    broker.publish("notifications", {"msg": "Low priority info"}, priority=MessagePriority.LOW)
    broker.publish("notifications", {"msg": "High priority alert"}, priority=MessagePriority.HIGH)
    broker.publish("notifications", {"msg": "Normal update"}, priority=MessagePriority.NORMAL)
    broker.publish("notifications", {"msg": "Critical error!"}, priority=MessagePriority.CRITICAL)
    
    print("\n3. Receiving messages...")
    
    # Alert system only receives high/critical
    for _ in range(4):
        message = broker.receive("notifications", "alert-system", timeout=1.0)
        if message:
            broker.acknowledge(message.message_id)
    
    # General listener receives all
    for _ in range(4):
        message = broker.receive("notifications", "general-listener", timeout=1.0)
        if message:
            broker.acknowledge(message.message_id)
    
    print(f"\n   Alert system received: {len(received_by_alerts)} messages (only HIGH/CRITICAL)")
    print(f"   General listener received: {len(received_by_all)} messages (all priorities)")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_message_persistence():
    """Demo: Message persistence across broker restarts"""
    print("\n" + "=" * 60)
    print("Demo 6: Message Persistence")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    
    print("\n1. Creating first broker instance and publishing messages...")
    
    broker1 = create_message_broker(persistence_path=temp_dir)
    broker1.publish("persistent-topic", {"message": "This message will persist", "step": 1})
    broker1.publish("persistent-topic", {"message": "Another persistent message", "step": 2})
    
    print(f"   Messages in queue: {broker1.get_queue_size('persistent-topic')}")
    
    # Simulate broker shutdown
    print("\n2. Simulating broker shutdown...")
    del broker1
    
    print("\n3. Creating new broker instance with same persistence...")
    broker2 = create_message_broker(persistence_path=temp_dir)
    print(f"   Messages in queue: {broker2.get_queue_size('persistent-topic')}")
    
    print("\n4. Receiving persisted messages...")
    for _ in range(2):
        message = broker2.receive("persistent-topic", "new-consumer", timeout=1.0)
        if message:
            print(f"   [Received] {message.payload}")
            broker2.acknowledge(message.message_id)
    
    print("\n   Messages persisted successfully across broker restart!")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_concurrent_processing():
    """Demo: Concurrent message processing"""
    print("\n" + "=" * 60)
    print("Demo 7: Concurrent Processing")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    broker = create_message_broker(persistence_path=temp_dir)
    
    results = {}
    lock = threading.Lock()
    
    def worker(worker_id, message_count):
        worker_results = []
        for i in range(message_count):
            message = broker.receive("concurrent", f"worker-{worker_id}", timeout=2.0)
            if message:
                # Simulate processing
                time.sleep(0.1)
                worker_results.append(message.payload)
                broker.acknowledge(message.message_id)
        with lock:
            results[f"worker-{worker_id}"] = worker_results
    
    print("\n1. Publishing messages from multiple sources...")
    for i in range(6):
        broker.publish("concurrent", {"source": "publisher-1", "num": i})
    for i in range(6):
        broker.publish("concurrent", {"source": "publisher-2", "num": i})
    
    print(f"   Total messages published: {broker.get_queue_size('concurrent')}")
    
    print("\n2. Starting worker threads...")
    threads = [
        threading.Thread(target=worker, args=(1, 4)),
        threading.Thread(target=worker, args=(2, 4)),
        threading.Thread(target=worker, args=(3, 4)),
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    print("\n3. Processing complete!")
    total_processed = sum(len(r) for r in results.values())
    print(f"   Total messages processed: {total_processed}")
    
    for worker_id, worker_results in results.items():
        print(f"   {worker_id}: processed {len(worker_results)} messages")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("     MESSAGE QUEUE DEMO")
    print("=" * 60)
    
    # Run demos
    demo_basic_publish_subscribe()
    demo_priority_queue()
    demo_message_acknowledgment()
    demo_multiple_subscribers()
    demo_subscription_filter()
    demo_message_persistence()
    demo_concurrent_processing()
    
    print("\n" + "=" * 60)
    print("     ALL DEMOS COMPLETED")
    print("=" * 60)
    print("\nSummary:")
    print("  ✓ Basic publish/subscribe pattern")
    print("  ✓ Priority message handling")
    print("  ✓ Message acknowledgment mechanism")
    print("  ✓ Multiple subscribers per topic")
    print("  ✓ Subscription filtering")
    print("  ✓ Message persistence")
    print("  ✓ Concurrent message processing")
    print()


if __name__ == "__main__":
    main()
