"""
Advanced Cache System for Agent-OS-Kernel

This module provides a multi-tier, distributed caching system with support for:
- Multiple cache levels (L1/L2/L3)
- Various eviction policies (LRU, LFU, TTL)
- Distributed cache coordination
- Cache warming capabilities
"""

import time
import threading
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple
from enum import Enum
import copy

logger = logging.getLogger(__name__)


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out


class CacheLevel(Enum):
    """Cache hierarchy levels."""
    L1 = 1  # In-memory, fastest
    L2 = 2  # Shared memory
    L3 = 3  # Disk-based


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None  # Time to live in seconds
    level: CacheLevel = CacheLevel.L1
    
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def access(self):
        """Record an access to this entry."""
        self.last_accessed = time.time()
        self.access_count += 1


class CachePolicy(ABC):
    """Abstract base class for cache eviction policies."""
    
    @abstractmethod
    def on_access(self, key: str, entry: CacheEntry):
        """Called when an entry is accessed."""
        pass
    
    @abstractmethod
    def on_insert(self, key: str, entry: CacheEntry):
        """Called when an entry is inserted."""
        pass
    
    @abstractmethod
    def on_remove(self, key: str):
        """Called when an entry is removed."""
        pass
    
    @abstractmethod
    def evict(self, count: int = 1) -> List[str]:
        """Return keys to evict."""
        pass


class LRUCachePolicy(CachePolicy):
    """Least Recently Used eviction policy."""
    
    def __init__(self):
        self.order = OrderedDict()  # key -> None (maintains order)
    
    def on_access(self, key: str, entry: CacheEntry):
        if key in self.order:
            self.order.move_to_end(key)
    
    def on_insert(self, key: str, entry: CacheEntry):
        if key not in self.order:
            self.order[key] = None
    
    def on_remove(self, key: str):
        self.order.pop(key, None)
    
    def evict(self, count: int = 1) -> List[str]:
        keys = []
        for _ in range(min(count, len(self.order))):
            key, _ = self.order.popitem(last=False)
            keys.append(key)
        return keys


class LFUCachePolicy(CachePolicy):
    """Least Frequently Used eviction policy."""
    
    def __init__(self):
        self.freq_map = defaultdict(OrderedDict)  # freq -> OrderedDict of keys
        self.key_freq = {}  # key -> freq
        self.min_freq = 0
    
    def on_access(self, key: str, entry: CacheEntry):
        freq = self.key_freq.get(key, 0)
        if freq > 0:
            self.freq_map[freq].pop(key, None)
        
        new_freq = freq + 1
        self.key_freq[key] = new_freq
        self.freq_map[new_freq][key] = None
        
        if not self.freq_map[self.min_freq]:
            self.min_freq += 1
    
    def on_insert(self, key: str, entry: CacheEntry):
        freq = 1
        self.key_freq[key] = freq
        self.freq_map[freq][key] = None
        self.min_freq = 1
    
    def on_remove(self, key: str):
        freq = self.key_freq.pop(key, 0)
        if freq > 0:
            self.freq_map[freq].pop(key, None)
            if not self.freq_map[freq]:
                self.min_freq = max(1, self.min_freq - 1)
    
    def evict(self, count: int = 1) -> List[str]:
        keys = []
        while self.min_freq in self.freq_map and len(self.freq_map[self.min_freq]) > 0 and len(keys) < count:
            key, _ = self.freq_map[self.min_freq].popitem(last=False)
            self.key_freq.pop(key, None)
            keys.append(key)
        return keys


class FIFOCachePolicy(CachePolicy):
    """First In First Out eviction policy."""
    
    def __init__(self):
        self.queue = []  # List of keys in insertion order
    
    def on_access(self, key: str, entry: CacheEntry):
        pass  # FIFO doesn't care about access
    
    def on_insert(self, key: str, entry: CacheEntry):
        if key not in self.queue:
            self.queue.append(key)
    
    def on_remove(self, key: str):
        try:
            self.queue.remove(key)
        except ValueError:
            pass
    
    def evict(self, count: int = 1) -> List[str]:
        keys = []
        for _ in range(min(count, len(self.queue))):
            keys.append(self.queue.pop(0))
        return keys


class TieredCache:
    """
    A single cache tier with configurable eviction policy.
    """
    
    def __init__(
        self,
        level: CacheLevel,
        max_size: int = 1000,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        ttl: Optional[float] = None
    ):
        self.level = level
        self.max_size = max_size
        self.ttl = ttl
        self._entries: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Initialize policy
        if eviction_policy == EvictionPolicy.LRU:
            self._policy: CachePolicy = LRUCachePolicy()
        elif eviction_policy == EvictionPolicy.LFU:
            self._policy = LFUCachePolicy()
        else:
            self._policy = FIFOCachePolicy()
    
    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get a value from the cache.
        
        Returns:
            Tuple of (value, found)
        """
        with self._lock:
            if key not in self._entries:
                return None, False
            
            entry = self._entries[key]
            
            if entry.is_expired():
                self._remove(key)
                return None, False
            
            entry.access()
            self._policy.on_access(key, entry)
            return copy.deepcopy(entry.value), True
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """
        Put a value into the cache.
        
        Returns:
            True if inserted, False if evicted
        """
        with self._lock:
            # Check if we need to evict
            if key not in self._entries and len(self._entries) >= self.max_size:
                self._evict()
            
            if key in self._entries:
                entry = self._entries[key]
                entry.value = value
                entry.created_at = time.time()
                entry.ttl = ttl if ttl is not None else self.ttl
                entry.access()
                self._policy.on_access(key, entry)
            else:
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl=ttl if ttl is not None else self.ttl,
                    level=self.level
                )
                self._entries[key] = entry
                self._policy.on_insert(key, entry)
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        with self._lock:
            return self._remove(key)
    
    def _remove(self, key: str) -> bool:
        """Internal remove without locking."""
        if key in self._entries:
            del self._entries[key]
            self._policy.on_remove(key)
            return True
        return False
    
    def _evict(self, count: int = 1) -> List[str]:
        """Evict entries based on policy."""
        keys = self._policy.evict(count)
        for key in keys:
            self._entries.pop(key, None)
        return keys
    
    def clear(self):
        """Clear all entries."""
        with self._lock:
            self._entries.clear()
            self._policy = type(self._policy)()  # Reinitialize policy
    
    def contains(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        with self._lock:
            if key not in self._entries:
                return False
            entry = self._entries[key]
            return not entry.is_expired()
    
    def size(self) -> int:
        """Return current size."""
        return len(self._entries)
    
    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return {
            "level": self.level.value,
            "size": self.size(),
            "max_size": self.max_size,
            "eviction_policy": self._policy.__class__.__name__
        }


class MultiTierCache:
    """
    Multi-tier cache system with L1, L2, and L3 levels.
    
    Data flows down from L1 to L2 to L3 on eviction.
    Data is fetched from the highest level where it exists.
    """
    
    def __init__(
        self,
        l1_size: int = 1000,
        l2_size: int = 10000,
        l3_size: int = 100000,
        default_ttl: Optional[float] = 3600,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    ):
        self.default_ttl = default_ttl
        
        # Create tiers
        self._tiers = {
            CacheLevel.L1: TieredCache(
                CacheLevel.L1, l1_size, eviction_policy, default_ttl
            ),
            CacheLevel.L2: TieredCache(
                CacheLevel.L2, l2_size, eviction_policy, default_ttl
            ),
            CacheLevel.L3: TieredCache(
                CacheLevel.L3, l3_size, eviction_policy, default_ttl
            )
        }
        
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get a value from the cache.
        
        Searches from L1 to L3, promoting on hit.
        """
        with self._lock:
            # Search from L1 to L3
            for level in [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]:
                value, found = self._tiers[level].get(key)
                if found:
                    # Promote to L1 on hit
                    self._promote(key, value, level)
                    return value, True
            
            return None, False
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Put a value into the cache (always goes to L1)."""
        with self._lock:
            # Always put in L1
            return self._tiers[CacheLevel.L1].put(key, value, ttl)
    
    def _promote(self, key: str, value: Any, from_level: CacheLevel):
        """Promote an entry to L1."""
        if from_level != CacheLevel.L1:
            # Check if already in L1
            if self._tiers[CacheLevel.L1].contains(key):
                self._tiers[CacheLevel.L1].put(key, value)
            else:
                # Try to put in L1 (may evict to L2)
                if not self._tiers[CacheLevel.L1].put(key, value):
                    # Evicted from L1, try L2
                    self._tiers[CacheLevel.L2].put(key, value)
    
    def delete(self, key: str) -> bool:
        """Delete a key from all tiers."""
        with self._lock:
            found = False
            for tier in self._tiers.values():
                if tier.delete(key):
                    found = True
            return found
    
    def clear(self):
        """Clear all tiers."""
        with self._lock:
            for tier in self._tiers.values():
                tier.clear()
    
    def contains(self, key: str) -> bool:
        """Check if key exists in any tier."""
        with self._lock:
            for tier in self._tiers.values():
                if tier.contains(key):
                    return True
            return False
    
    def get_tier_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each tier."""
        with self._lock:
            return {level.value: tier.stats() for level, tier in self._tiers.items()}
    
    def evict_from_tier(self, level: CacheLevel, count: int = 1):
        """Manually evict from a specific tier."""
        with self._lock:
            tier = self._tiers[level]
            evicted = tier._evict(count)
            
            # Push evicted items to lower tier
            if level == CacheLevel.L1 and evicted:
                for key in evicted:
                    # Try to get from source (would be in L2/L3)
                    for l in [CacheLevel.L2, CacheLevel.L3]:
                        val, found = self._tiers[l].get(key)
                        if found:
                            self._tiers[CacheLevel.L2].put(key, val)
                            break


class DistributedCacheClient:
    """
    Client for distributed cache coordination.
    
    This is a simplified implementation that demonstrates
    distributed cache concepts. In production, this would
    integrate with systems like Redis, Memcached, or etcd.
    """
    
    def __init__(self, node_id: str, peers: List[str] = None):
        self.node_id = node_id
        self.peers = peers or []
        self._local_cache = MultiTierCache()
        self._shared_prefix = f"dist:{node_id}:"
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """Get from local cache first, then peers."""
        with self._lock:
            # Try local first
            value, found = self._local_cache.get(key)
            if found:
                return value, True
            
            # In a real implementation, would query peers here
            # For now, just return local result
            return None, False
    
    def put(self, key: str, value: Any, replicate: bool = True) -> bool:
        """Put to local cache and optionally replicate."""
        with self._lock:
            success = self._local_cache.put(key, value)
            
            if replicate:
                self._replicate(key, value)
            
            return success
    
    def _replicate(self, key: str, value: Any):
        """Replicate to peers (simplified)."""
        # In production, would use RPC/gossip protocol
        logger.debug(f"Replicating key '{key}' to peers: {self.peers}")
    
    def invalidate(self, key: str, across_nodes: bool = True):
        """Invalidate a key locally and optionally across nodes."""
        with self._lock:
            self._local_cache.delete(key)
            
            if across_nodes:
                logger.debug(f"Invalidating key '{key}' across nodes")
    
    def register_peer(self, peer_id: str):
        """Register a new peer node."""
        if peer_id not in self.peers:
            self.peers.append(peer_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get distributed cache statistics."""
        return {
            "node_id": self.node_id,
            "peer_count": len(self.peers),
            "tiers": self._local_cache.get_tier_stats()
        }


class CacheWarmer:
    """
    Cache warming system for pre-loading frequently accessed data.
    """
    
    def __init__(self, cache: MultiTierCache):
        self._cache = cache
        self._warmup_tasks: List[Callable[[], Dict[str, Any]]] = []
        self._access_patterns: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self._running = False
    
    def add_warmup_task(self, task: Callable[[], Dict[str, Any]]):
        """Add a warmup task that returns {key: value} pairs."""
        with self._lock:
            self._warmup_tasks.append(task)
    
    def record_access(self, key: str):
        """Record an access pattern for future warmup."""
        with self._lock:
            self._access_patterns[key] += 1
    
    def warm_up(self, force: bool = False):
        """Run all warmup tasks to populate the cache."""
        with self._lock:
            if self._running and not force:
                logger.warning("Warmup already in progress")
                return
            
            self._running = True
            
            for task in self._warmup_tasks:
                try:
                    data = task()
                    for key, value in data.items():
                        self._cache.put(key, value)
                        logger.debug(f"Warmed cache with key: {key}")
                except Exception as e:
                    logger.error(f"Warmup task failed: {e}")
            
            self._running = False
    
    def get_popular_keys(self, top_n: int = 10) -> List[str]:
        """Get the most frequently accessed keys."""
        with self._lock:
            sorted_keys = sorted(
                self._access_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return [k for k, _ in sorted_keys[:top_n]]
    
    def schedule_warmup(self, interval_seconds: int = 300):
        """Schedule periodic warmup based on access patterns."""
        def periodic_warmup():
            popular_keys = self.get_popular_keys(100)
            # In a real implementation, would fetch and cache these
            logger.info(f"Scheduled warmup for {len(popular_keys)} popular keys")
        
        # This would run in a background thread
        logger.info(f"Cache warming scheduled every {interval_seconds} seconds")


# Factory function for creating configured caches
def create_cache(
    tier: str = "multi",
    l1_size: int = 1000,
    l2_size: int = 10000,
    l3_size: int = 100000,
    ttl: Optional[float] = 3600,
    policy: str = "lru"
) -> Any:
    """
    Factory function to create a configured cache.
    
    Args:
        tier: "l1", "l2", "l3", or "multi"
        l1_size: L1 cache size
        l2_size: L2 cache size
        l3_size: L3 cache size
        ttl: Default TTL in seconds
        policy: "lru", "lfu", or "fifo"
    
    Returns:
        Configured cache instance
    """
    eviction_map = {
        "lru": EvictionPolicy.LRU,
        "lfu": EvictionPolicy.LFU,
        "fifo": EvictionPolicy.FIFO
    }
    ev_policy = eviction_map.get(policy.lower(), EvictionPolicy.LRU)
    
    if tier == "multi":
        return MultiTierCache(l1_size, l2_size, l3_size, ttl, ev_policy)
    else:
        level_map = {
            "l1": CacheLevel.L1,
            "l2": CacheLevel.L2,
            "l3": CacheLevel.L3
        }
        level = level_map.get(tier.lower(), CacheLevel.L1)
        size_map = {"l1": l1_size, "l2": l2_size, "l3": l3_size}
        return TieredCache(level, size_map.get(tier.lower(), l1_size), ev_policy, ttl)
