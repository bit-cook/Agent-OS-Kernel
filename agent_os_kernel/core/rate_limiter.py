# -*- coding: utf-8 -*-
"""
Rate Limiter Module for Agent-OS-Kernel

Provides a simple and efficient rate limiting implementation using
the token bucket algorithm.
"""

import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None


class TokenBucket:
    """
    Token Bucket Rate Limiter
    
    A simple and efficient token bucket implementation that allows
    burst traffic while maintaining a steady refill rate.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize the token bucket.
        
        Args:
            capacity: Maximum number of tokens the bucket can hold (burst size)
            refill_rate: Number of tokens to add per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens: float = float(capacity)
        self._last_update: float = time.time()
        self._lock = threading.RLock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        current_time = time.time()
        elapsed = current_time - self._last_update
        tokens_to_add = elapsed * self.refill_rate
        
        self._tokens = min(
            self._tokens + tokens_to_add,
            float(self.capacity)
        )
        self._last_update = current_time
    
    def consume(self, tokens: int = 1) -> RateLimitResult:
        """
        Consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            RateLimitResult indicating if the request is allowed
        """
        with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return RateLimitResult(
                    allowed=True,
                    remaining=int(self._tokens),
                    reset_time=self._last_update + (self.capacity - self._tokens) / self.refill_rate if self.refill_rate > 0 else float('inf')
                )
            else:
                tokens_needed = tokens - self._tokens
                retry_after = tokens_needed / self.refill_rate if self.refill_rate > 0 else 1.0
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=self._last_update + self.capacity / self.refill_rate if self.refill_rate > 0 else float('inf'),
                    retry_after=max(0, retry_after)
                )
    
    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        with self._lock:
            self._tokens = float(self.capacity)
            self._last_update = time.time()
    
    @property
    def available_tokens(self) -> float:
        """Get the current number of available tokens."""
        with self._lock:
            self._refill()
            return self._tokens


class RateLimiter:
    """
    Simple Rate Limiter with Per-Key Support
    
    Manages multiple token buckets, each identified by a unique key.
    Each key has its own rate limit configuration.
    """
    
    def __init__(self, default_capacity: int = 100, default_refill_rate: float = 1.0):
        """
        Initialize the rate limiter.
        
        Args:
            default_capacity: Default maximum tokens per bucket
            default_refill_rate: Default tokens to add per second
        """
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.RLock()
    
    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create a bucket for the given key."""
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                self.default_capacity,
                self.default_refill_rate
            )
        return self._buckets[key]
    
    def check(self, key: str, tokens: int = 1) -> RateLimitResult:
        """
        Check if the request is allowed.
        
        Args:
            key: Unique identifier for the rate limit bucket
            tokens: Number of tokens to consume
            
        Returns:
            RateLimitResult indicating if the request is allowed
        """
        with self._lock:
            bucket = self._get_bucket(key)
            return bucket.consume(tokens)
    
    def reset(self, key: str) -> None:
        """
        Reset the rate limit for a specific key.
        
        Args:
            key: The key to reset
        """
        with self._lock:
            if key in self._buckets:
                self._buckets[key].reset()
    
    def reset_all(self) -> None:
        """Reset all rate limits."""
        with self._lock:
            for bucket in self._buckets.values():
                bucket.reset()
    
    def get_remaining(self, key: str) -> int:
        """
        Get remaining tokens for a key.
        
        Args:
            key: The key to check
            
        Returns:
            Number of remaining tokens
        """
        with self._lock:
            bucket = self._get_bucket(key)
            return int(bucket.available_tokens)
    
    def set_limit(self, key: str, capacity: int, refill_rate: float) -> None:
        """
        Set custom rate limit for a key.
        
        Args:
            key: The key to set
            capacity: New capacity for the bucket
            refill_rate: New refill rate for the bucket
        """
        with self._lock:
            self._buckets[key] = TokenBucket(capacity, refill_rate)


def create_rate_limiter(
    requests_per_second: float = 1.0,
    burst_capacity: int = 100,
    max_keys: int = 10000
) -> RateLimiter:
    """
    Create a rate limiter with common settings.
    
    Args:
        requests_per_second: Number of requests allowed per second
        burst_capacity: Maximum burst size
        max_keys: Maximum number of unique keys to track
        
    Returns:
        Configured RateLimiter instance
    """
    return RateLimiter(
        default_capacity=burst_capacity,
        default_refill_rate=requests_per_second
    )
