#!/usr/bin/env python3
"""
Cache System Demo

This script demonstrates the usage of the advanced cache system including:
- Multi-tier cache configuration
- Different cache policies (LRU, LFU, FIFO)
- Cache warming
- Distributed cache concepts
"""

import time
import threading
import random
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_os_kernel.core.cache_system_enhanced import (
    MultiTierCache,
    TieredCache,
    CacheLevel,
    EvictionPolicy,
    DistributedCacheClient,
    CacheWarmer,
    create_cache,
)


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_basic_tiered_cache():
    """Demonstrate basic tiered cache usage."""
    print_header("Basic Tiered Cache")
    
    # Create a single tier cache
    cache = TieredCache(
        level=CacheLevel.L1,
        max_size=5,
        eviction_policy=EvictionPolicy.LRU
    )
    
    print("\nAdding items to cache...")
    for i in range(5):
        cache.put(f"key{i}", f"value{i}")
        print(f"  Put: key{i} -> value{i}")
    
    print(f"\nCache size: {cache.size()}")
    print(f"Contains 'key2': {cache.contains('key2')}")
    
    print("\nRetrieving items...")
    for i in range(3):
        value, found = cache.get(f"key{i}")
        print(f"  Get key{i}: {value} (found: {found})")
    
    print("\nAdding more items (should trigger eviction)...")
    for i in range(3, 8):
        cache.put(f"key{i}", f"value{i}")
        print(f"  Put: key{i} -> value{i}")
    
    print(f"\nCache size: {cache.size()}")
    print(f"Contains 'key0': {cache.contains('key0')}")
    print(f"Contains 'key6': {cache.contains('key6')}")


def demo_multi_tier_cache():
    """Demonstrate multi-tier cache."""
    print_header("Multi-Tier Cache")
    
    # Create multi-tier cache with different sizes
    cache = MultiTierCache(
        l1_size=3,      # L1: 3 items (fastest)
        l2_size=10,     # L2: 10 items
        l3_size=100,    # L3: 100 items (slower but larger)
        default_ttl=60  # 1 minute TTL
    )
    
    print("\nL1 (fastest): 3 items")
    print("L2 (medium):  10 items")
    print("L3 (largest): 100 items")
    print("\nDefault TTL: 60 seconds")
    
    print("\nAdding 5 items...")
    for i in range(5):
        cache.put(f"item{i}", f"data{i}")
        print(f"  Added: item{i}")
    
    print("\nChecking where items are stored...")
    for i in range(5):
        l1 = cache._tiers[CacheLevel.L1].contains(f"item{i}")
        l2 = cache._tiers[CacheLevel.L2].contains(f"item{i}")
        location = "L1" if l1 else ("L2" if l2 else "L3")
        print(f"  item{i}: {location}")
    
    print("\nAccessing items to trigger promotion to L1...")
    cache.get("item3")
    cache.get("item3")
    cache.get("item4")
    
    print("\nChecking L1 contents...")
    for i in range(5):
        if cache._tiers[CacheLevel.L1].contains(f"item{i}"):
            print(f"  item{i} is now in L1")
    
    print("\nGetting cache statistics...")
    stats = cache.get_tier_stats()
    for level, data in sorted(stats.items()):
        print(f"  Level {level}: {data['size']}/{data['max_size']} items")


def demo_cache_policies():
    """Demonstrate different cache eviction policies."""
    print_header("Cache Eviction Policies")
    
    policies = [
        ("LRU (Least Recently Used)", EvictionPolicy.LRU),
        ("LFU (Least Frequently Used)", EvictionPolicy.LFU),
        ("FIFO (First In First Out)", EvictionPolicy.FIFO),
    ]
    
    for policy_name, policy in policies:
        print(f"\n--- {policy_name} ---")
        
        cache = TieredCache(
            level=CacheLevel.L1,
            max_size=3,
            eviction_policy=policy
        )
        
        # Add items in order
        for i in range(1, 4):
            cache.put(f"item{i}", f"value{i}")
            print(f"  Added: item{i}")
        
        if policy == EvictionPolicy.LFU:
            # Access item1 more often for LFU
            print("\n  Accessing item1 multiple times...")
            cache.get("item1")
            cache.get("item1")
            cache.get("item1")
            cache.get("item2")
        
        if policy == EvictionPolicy.LRU:
            # Access item1 to make it recent
            print("\n  Accessing item1 to make it recent...")
            cache.get("item1")
        
        print("\n  Adding item4 (triggers eviction)...")
        cache.put("item4", "value4")
        
        print("\n  Remaining in cache:")
        for i in range(1, 5):
            found = cache.contains(f"item{i}")
            status = "IN CACHE" if found else "EVICTED"
            print(f"    item{i}: {status}")


def demo_ttl_expiration():
    """Demonstrate TTL-based expiration."""
    print_header("TTL-Based Expiration")
    
    # Create cache with short TTL
    cache = TieredCache(
        level=CacheLevel.L1,
        max_size=100,
        ttl=1.0  # 1 second TTL
    )
    
    print("\nCache TTL: 1 second")
    
    cache.put("short-lived", "data")
    print("\nAdded: short-lived")
    print(f"Contains short-lived: {cache.contains('short-lived')}")
    
    print("\nWaiting 2 seconds...")
    time.sleep(2)
    
    print(f"Contains short-lived: {cache.contains('short-lived')}")
    
    print("\nPer-key TTL override:")
    cache.put("long-lived", "data", ttl=5.0)
    cache.put("short", "data", ttl=0.2)
    
    print("  Added: long-lived (5s TTL)")
    print("  Added: short (0.2s TTL)")
    
    time.sleep(0.5)
    print(f"  long-lived still present: {cache.contains('long-lived')}")
    print(f"  short still present: {cache.contains('short')}")


def demo_cache_warming():
    """Demonstrate cache warming functionality."""
    print_header("Cache Warming")
    
    cache = MultiTierCache(l1_size=10, l2_size=100)
    warmer = CacheWarmer(cache)
    
    print("\nCreating warmup tasks...")
    
    def warmup_users():
        """Simulate warming user data."""
        return {
            "user:1001": {"name": "Alice", "email": "alice@example.com"},
            "user:1002": {"name": "Bob", "email": "bob@example.com"},
            "user:1003": {"name": "Charlie", "email": "charlie@example.com"},
        }
    
    def warmup_config():
        """Simulate warming config data."""
        return {
            "config:theme": "dark",
            "config:language": "en",
            "config:timezone": "UTC",
        }
    
    warmer.add_warmup_task(warmup_users)
    warmer.add_warmup_task(warmup_config)
    
    print("  Task 1: User data (3 items)")
    print("  Task 2: Config data (3 items)")
    
    print("\nRunning cache warmup...")
    warmer.warm_up()
    
    print("\nChecking warmed cache...")
    value, found = cache.get("user:1001")
    print(f"  user:1001: {value} (found: {found})}")
    
    value, found = cache.get("config:theme")
    print(f"  config:theme: {value} (found: {found})}")
    
    print("\nSimulating access patterns...")
    for i in range(1, 5):
        for _ in range(i * 2):
            warmer.record_access(f"user:100{i}")
    
    print("\nTop 3 popular keys:")
    popular = warmer.get_popular_keys(top_n=3)
    for i, key in enumerate(popular, 1):
        print(f"  {i}. {key}")


def demo_distributed_cache():
    """Demonstrate distributed cache concepts."""
    print_header("Distributed Cache")
    
    print("\nCreating two cache nodes...")
    
    node1 = DistributedCacheClient(node_id="node1", peers=["node2"])
    node2 = DistributedCacheClient(node_id="node2", peers=["node1"])
    
    print(f"  Node 1 ID: {node1.node_id}")
    print(f"  Node 2 ID: {node2.node_id}")
    print(f"  Node 1 Peers: {node1.peers}")
    
    print("\nNode 1 putting data...")
    node1.put("shared_key", "data_from_node1")
    
    print("\nNode 1 retrieving data...")
    value, found = node1.get("shared_key")
    print(f"  shared_key: {value} (found: {found})")
    
    print("\nNode 2 registering a new peer...")
    node2.register_peer("node3")
    print(f"  Node 2 peers: {node2.peers}")
    
    print("\nInvalidating data...")
    node1.invalidate("shared_key", across_nodes=False)
    print(f"  After invalidation: {node1.contains('shared_key')}")
    
    print("\nGetting statistics...")
    stats = node1.get_stats()
    print(f"  Node: {stats['node_id']}")
    print(f"  Peers: {stats['peer_count']}")


def demo_factory_function():
    """Demonstrate the cache factory function."""
    print_header("Cache Factory")
    
    print("\nCreating different cache configurations...")
    
    # Fast L1 only cache
    l1_only = create_cache(tier="l1", l1_size=100, policy="lru")
    print("\nL1-only cache (100 items, LRU):")
    print(f"  Type: {type(l1_only).__name__}")
    
    # Multi-tier cache
    multi_tier = create_cache(
        tier="multi",
        l1_size=50,
        l2_size=500,
        l3_size=5000,
        policy="lfu"
    )
    print("\nMulti-tier cache (L1:50, L2:500, L3:5000, LFU):")
    print(f"  Type: {type(multi_tier).__name__}")
    
    # L2 cache
    l2_only = create_cache(tier="l2", l1_size=100, policy="fifo")
    print("\nL2 cache (FIFO):")
    print(f"  Type: {type(l2_only).__name__}")


def demo_thread_safety():
    """Demonstrate thread-safe cache operations."""
    print_header("Thread Safety Demo")
    
    cache = MultiTierCache(l1_size=1000, l2_size=10000)
    
    errors = []
    stop_events = []
    
    def writer_thread(thread_id: int, count: int, stop_event: threading.Event):
        """Thread that writes to cache."""
        stop_events.append(stop_event)
        try:
            for i in range(count):
                if stop_event.is_set():
                    break
                cache.put(f"thread{thread_id}_key{i}", f"value_{thread_id}_{i}")
        except Exception as e:
            errors.append(f"Writer {thread_id}: {e}")
    
    def reader_thread(thread_id: int, count: int, stop_event: threading.Event):
        """Thread that reads from cache."""
        try:
            for i in range(count):
                if stop_event.is_set():
                    break
                cache.get(f"thread{thread_id}_key{i % 100}")
        except Exception as e:
            errors.append(f"Reader {thread_id}: {e}")
    
    print("\nStarting 5 writer threads and 5 reader threads...")
    
    threads = []
    stop_event = threading.Event()
    
    for i in range(5):
        t = threading.Thread(target=writer_thread, args=(i, 100, stop_event))
        threads.append(t)
        t = threading.Thread(target=reader_thread, args=(i, 100, stop_event))
        threads.append(t)
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"\nCompleted without errors: {len(errors) == 0}")
    
    if errors:
        print(f"Errors encountered: {len(errors)}")
        for err in errors[:3]:
            print(f"  - {err}")
    
    print(f"\nFinal cache stats:")
    stats = cache.get_tier_stats()
    for level, data in sorted(stats.items()):
        print(f"  L{level}: {data['size']} items")


def main():
    """Run all demos."""
    print("\n" + "#" * 60)
    print("#" + " " * 18 + "CACHE SYSTEM DEMO" + " " * 18 + "#")
    print("#" * 60)
    
    try:
        demo_basic_tiered_cache()
        demo_multi_tier_cache()
        demo_cache_policies()
        demo_ttl_expiration()
        demo_cache_warming()
        demo_distributed_cache()
        demo_factory_function()
        demo_thread_safety()
        
        print("\n" + "#" * 60)
        print("#" + " " * 20 + "DEMO COMPLETE" + " " * 21 + "#")
        print("#" * 60 + "\n")
    
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
