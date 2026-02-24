"""
Tests for the Advanced Cache System

Tests cover:
- Multi-tier cache functionality
- Cache policies (LRU, LFU, TTL)
- Cache warming
- Cache invalidation
"""

import unittest
import time
import threading
from unittest.mock import MagicMock, patch

from agent_os_kernel.core.cache_system_enhanced import (
    CacheEntry,
    CacheLevel,
    EvictionPolicy,
    TieredCache,
    MultiTierCache,
    DistributedCacheClient,
    CacheWarmer,
    create_cache,
)


class TestCacheEntry(unittest.TestCase):
    """Tests for CacheEntry class."""

    def test_create_entry_without_ttl(self):
        """Test creating an entry without TTL."""
        entry = CacheEntry(key="test", value="value")
        self.assertFalse(entry.is_expired())
        self.assertEqual(entry.access_count, 0)

    def test_create_entry_with_ttl(self):
        """Test creating an entry with TTL."""
        entry = CacheEntry(key="test", value="value", ttl=1.0)
        self.assertFalse(entry.is_expired())

    def test_entry_expiration(self):
        """Test that entry expires after TTL."""
        entry = CacheEntry(key="test", value="value", ttl=0.1)
        self.assertFalse(entry.is_expired())
        time.sleep(0.15)
        self.assertTrue(entry.is_expired())

    def test_entry_access(self):
        """Test entry access tracking."""
        entry = CacheEntry(key="test", value="value")
        self.assertEqual(entry.access_count, 0)

        entry.access()
        self.assertEqual(entry.access_count, 1)

        entry.access()
        self.assertEqual(entry.access_count, 2)

        self.assertGreater(entry.last_accessed, entry.created_at)


class TestTieredCache(unittest.TestCase):
    """Tests for TieredCache class."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = TieredCache(
            level=CacheLevel.L1,
            max_size=3,
            eviction_policy=EvictionPolicy.LRU,
            ttl=60.0
        )

    def test_basic_put_get(self):
        """Test basic put and get operations."""
        self.cache.put("key1", "value1")
        value, found = self.cache.get("key1")
        self.assertEqual(value, "value1")
        self.assertTrue(found)

    def test_get_missing_key(self):
        """Test getting a missing key returns None."""
        value, found = self.cache.get("missing")
        self.assertIsNone(value)
        self.assertFalse(found)

    def test_delete(self):
        """Test deleting a key."""
        self.cache.put("key1", "value1")
        self.assertTrue(self.cache.contains("key1"))

        result = self.cache.delete("key1")
        self.assertTrue(result)
        self.assertFalse(self.cache.contains("key1"))

    def test_delete_missing_key(self):
        """Test deleting a missing key returns False."""
        result = self.cache.delete("missing")
        self.assertFalse(result)

    def test_contains(self):
        """Test contains method."""
        self.cache.put("key1", "value1")
        self.assertTrue(self.cache.contains("key1"))

        self.cache.delete("key1")
        self.assertFalse(self.cache.contains("key1"))

    def test_size(self):
        """Test cache size tracking."""
        self.assertEqual(self.cache.size(), 0)

        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.assertEqual(self.cache.size(), 2)

    def test_clear(self):
        """Test clearing the cache."""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.cache.clear()
        self.assertEqual(self.cache.size(), 0)
        self.assertFalse(self.cache.contains("key1"))

    def test_eviction_lru(self):
        """Test LRU eviction policy."""
        cache = TieredCache(
            level=CacheLevel.L1,
            max_size=3,
            eviction_policy=EvictionPolicy.LRU
        )

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key1 to make it most recently used
        cache.get("key1")

        # Add one more - should evict key2 (LRU)
        cache.put("key4", "value4")

        self.assertTrue(cache.contains("key1"))
        self.assertTrue(cache.contains("key3"))
        self.assertTrue(cache.contains("key4"))
        self.assertFalse(cache.contains("key2"))

    def test_ttl_expiration(self):
        """Test that TTL-based expiration works."""
        cache = TieredCache(
            level=CacheLevel.L1,
            max_size=100,
            eviction_policy=EvictionPolicy.LRU,
            ttl=0.1
        )

        cache.put("key1", "value1", ttl=0.1)
        self.assertTrue(cache.contains("key1"))

        time.sleep(0.15)
        self.assertFalse(cache.contains("key1"))

    def test_thread_safety(self):
        """Test cache operations are thread-safe."""
        cache = TieredCache(
            level=CacheLevel.L1,
            max_size=1000,
            eviction_policy=EvictionPolicy.LRU
        )

        def writer():
            for i in range(100):
                cache.put(f"key{i}", f"value{i}")

        def reader():
            for i in range(100):
                cache.get(f"key{i}")

        threads = []
        for _ in range(5):
            t = threading.Thread(target=writer)
            threads.append(t)
            t = threading.Thread(target=reader)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should complete without errors
        self.assertLessEqual(cache.size(), 1000)


class TestMultiTierCache(unittest.TestCase):
    """Tests for MultiTierCache class."""

    def test_multi_tier_cache(self):
        """Test basic multi-tier cache operations."""
        cache = MultiTierCache(
            l1_size=3,
            l2_size=10,
            l3_size=100,
            default_ttl=60.0
        )

        # Put should go to L1
        cache.put("key1", "value1")

        # Should be in L1
        value, found = cache.get("key1")
        self.assertTrue(found)
        self.assertEqual(value, "value1")

    def test_promotion_on_access(self):
        """Test that entries are promoted to L1 on access."""
        cache = MultiTierCache(
            l1_size=1,
            l2_size=10,
            l3_size=100
        )

        # Directly put into L2 (internal)
        cache._tiers[CacheLevel.L2].put("key1", "l2_value")

        # Get from L2
        value, found = cache.get("key1")
        self.assertTrue(found)

        # Should now be in L1 (promoted)
        self.assertTrue(cache._tiers[CacheLevel.L1].contains("key1"))

    def test_delete_from_all_tiers(self):
        """Test that delete removes from all tiers."""
        cache = MultiTierCache()

        cache.put("key1", "value1")

        # Manually add to L2 as well
        cache._tiers[CacheLevel.L2].put("key1", "value1")

        # Delete should remove from all tiers
        cache.delete("key1")

        self.assertFalse(cache.contains("key1"))
        self.assertFalse(cache._tiers[CacheLevel.L2].contains("key1"))

    def test_tier_stats(self):
        """Test getting tier statistics."""
        cache = MultiTierCache(
            l1_size=100,
            l2_size=200,
            l3_size=300
        )

        cache.put("key1", "value1")

        stats = cache.get_tier_stats()

        # Keys are integers (CacheLevel enum values)
        self.assertIn(1, stats)  # L1
        self.assertIn(2, stats)  # L2
        self.assertIn(3, stats)  # L3

        self.assertEqual(stats[1]["size"], 1)

    def test_lfu_policy(self):
        """Test LFU eviction policy in multi-tier."""
        # Test LFU eviction behavior using a single tier
        tier = TieredCache(
            level=CacheLevel.L1,
            max_size=2,
            eviction_policy=EvictionPolicy.LFU
        )

        tier.put("key1", "value1")
        tier.put("key2", "value2")

        # Access key1 multiple times
        tier.get("key1")
        tier.get("key1")
        tier.get("key1")

        # Access key2 once
        tier.get("key2")

        # Add new item - should evict key2 (LFU with 1 access vs key1 with 4)
        tier.put("key3", "value3")

        # key2 should be evicted
        self.assertFalse(tier.contains("key2"))
        self.assertTrue(tier.contains("key1"))
        self.assertTrue(tier.contains("key3"))


class TestCacheWarmer(unittest.TestCase):
    """Tests for CacheWarmer class."""

    def test_add_warmup_task(self):
        """Test adding warmup tasks."""
        cache = MultiTierCache()
        warmer = CacheWarmer(cache)

        def mock_task():
            return {"key1": "value1", "key2": "value2"}

        warmer.add_warmup_task(mock_task)
        self.assertEqual(len(warmer._warmup_tasks), 1)

    def test_warm_up(self):
        """Test running cache warmup."""
        cache = MultiTierCache()
        warmer = CacheWarmer(cache)

        def mock_task():
            return {"warmed1": "data1", "warmed2": "data2"}

        warmer.add_warmup_task(mock_task)
        warmer.warm_up()

        # Check data was warmed
        value, found = cache.get("warmed1")
        self.assertTrue(found)
        self.assertEqual(value, "data1")

    def test_record_access(self):
        """Test recording access patterns."""
        cache = MultiTierCache()
        warmer = CacheWarmer(cache)

        warmer.record_access("key1")
        warmer.record_access("key1")
        warmer.record_access("key2")

        self.assertEqual(warmer._access_patterns["key1"], 2)
        self.assertEqual(warmer._access_patterns["key2"], 1)

    def test_get_popular_keys(self):
        """Test getting popular keys."""
        cache = MultiTierCache()
        warmer = CacheWarmer(cache)

        warmer.record_access("key1")
        warmer.record_access("key1")
        warmer.record_access("key2")
        warmer.record_access("key3")
        warmer.record_access("key3")
        warmer.record_access("key3")

        popular = warmer.get_popular_keys(top_n=2)

        self.assertEqual(popular[0], "key3")  # Most popular
        self.assertEqual(popular[1], "key1")  # Second most


class TestCacheInvalidation(unittest.TestCase):
    """Tests for cache invalidation scenarios."""

    def test_ttl_invalidation(self):
        """Test automatic TTL-based invalidation."""
        cache = MultiTierCache()

        cache.put("temp", "data", ttl=0.1)

        self.assertTrue(cache.contains("temp"))

        time.sleep(0.15)
        self.assertFalse(cache.contains("temp"))

    def test_manual_invalidation(self):
        """Test manual cache invalidation."""
        cache = MultiTierCache()

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        cache.delete("key1")

        self.assertFalse(cache.contains("key1"))
        self.assertTrue(cache.contains("key2"))

    def test_clear_all(self):
        """Test clearing all cache entries."""
        cache = MultiTierCache()

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        cache.clear()

        self.assertFalse(cache.contains("key1"))
        self.assertFalse(cache.contains("key2"))
        self.assertFalse(cache.contains("key3"))

    def test_overwrite_invalidation(self):
        """Test that overwriting invalidates old value."""
        cache = MultiTierCache()

        cache.put("key", "old_value")
        value, _ = cache.get("key")
        self.assertEqual(value, "old_value")

        cache.put("key", "new_value")
        value, _ = cache.get("key")
        self.assertEqual(value, "new_value")


class TestDistributedCacheClient(unittest.TestCase):
    """Tests for DistributedCacheClient class."""

    def test_create_client(self):
        """Test creating a distributed cache client."""
        client = DistributedCacheClient(node_id="node1")

        self.assertEqual(client.node_id, "node1")
        self.assertEqual(len(client.peers), 0)

    def test_basic_operations(self):
        """Test basic get/put operations."""
        client = DistributedCacheClient(node_id="node1")

        client.put("key1", "value1")

        value, found = client.get("key1")
        self.assertTrue(found)
        self.assertEqual(value, "value1")

    def test_register_peer(self):
        """Test registering peers."""
        client = DistributedCacheClient(node_id="node1")

        client.register_peer("node2")
        client.register_peer("node3")

        self.assertEqual(len(client.peers), 2)
        self.assertIn("node2", client.peers)

    def test_invalidate(self):
        """Test invalidation across nodes."""
        client = DistributedCacheClient(node_id="node1")

        client.put("key1", "value1")
        client.invalidate("key1", across_nodes=False)

        # Local should be cleared
        self.assertFalse(client._local_cache.contains("key1"))

    def test_get_stats(self):
        """Test getting client statistics."""
        client = DistributedCacheClient(node_id="node1")
        client.put("key1", "value1")

        stats = client.get_stats()

        self.assertEqual(stats["node_id"], "node1")
        self.assertEqual(stats["peer_count"], 0)
        self.assertIn("tiers", stats)


class TestCacheFactory(unittest.TestCase):
    """Tests for cache factory function."""

    def test_create_single_tier_cache(self):
        """Test creating a single tier cache."""
        cache = create_cache(tier="l1", l1_size=100)

        self.assertIsInstance(cache, TieredCache)
        self.assertEqual(cache.max_size, 100)

    def test_create_multi_tier_cache(self):
        """Test creating a multi-tier cache."""
        cache = create_cache(tier="multi", l1_size=10, l2_size=20, l3_size=30)

        self.assertIsInstance(cache, MultiTierCache)

    def test_create_with_different_policies(self):
        """Test creating caches with different policies."""
        lru_cache = create_cache(tier="l1", policy="lru")
        lfu_cache = create_cache(tier="l1", policy="lfu")
        fifo_cache = create_cache(tier="l1", policy="fifo")

        # All should be valid tiered caches
        self.assertIsInstance(lru_cache, TieredCache)
        self.assertIsInstance(lfu_cache, TieredCache)
        self.assertIsInstance(fifo_cache, TieredCache)


if __name__ == "__main__":
    unittest.main()
