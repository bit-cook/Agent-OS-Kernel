"""
Advanced Rate Limiter for Agent-OS-Kernel

Provides multiple rate limiting algorithms:
- Sliding Window Algorithm
- Token Bucket Algorithm
- Multi-dimensional Rate Limiting
- Distributed Rate Limiting Support
"""

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any, Callable, Union
from collections import defaultdict
import hashlib
import json
from functools import wraps


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests: int = 100  # Maximum requests allowed
    window_seconds: float = 60.0  # Time window in seconds
    burst: Optional[int] = None  # Burst size (for token bucket)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None
    
    def to_headers(self, limit: int = 100) -> Dict[str, str]:
        """Convert to HTTP-style headers."""
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time)),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(int(self.retry_after))
        return headers


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    def check(self, key: str, amount: int = 1) -> RateLimitResult:
        """Check if request is allowed."""
        pass
    
    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        pass
    
    @abstractmethod
    def get_config(self, key: str) -> Optional[RateLimitConfig]:
        """Get current configuration for a key."""
        pass


class SlidingWindowLimiter(RateLimiter):
    """
    Sliding Window Rate Limiter
    
    Uses a more accurate sliding window algorithm that considers
    requests within the current window and the tail of the previous window.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._windows: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def _cleanup_old_entries(self, key: str, current_time: float) -> None:
        """Remove entries older than the window."""
        window_start = current_time - self.config.window_seconds
        self._windows[key] = [
            ts for ts in self._windows[key] 
            if ts > window_start
        ]
    
    def check(self, key: str, amount: int = 1) -> RateLimitResult:
        current_time = time.time()
        
        with self._lock:
            self._cleanup_old_entries(key, current_time)
            
            current_count = len(self._windows[key])
            
            if current_count + amount > self.config.requests:
                # Rate limit exceeded
                if self._windows[key]:
                    oldest = min(self._windows[key])
                    reset_time = oldest + self.config.window_seconds
                    retry_after = reset_time - current_time
                else:
                    reset_time = current_time + self.config.window_seconds
                    retry_after = self.config.window_seconds
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=max(0, retry_after)
                )
            
            # Add new request timestamps
            for _ in range(amount):
                self._windows[key].append(current_time)
            
            remaining = self.config.requests - current_count - amount
            reset_time = current_time + self.config.window_seconds
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_time=reset_time
            )
    
    def reset(self, key: str) -> None:
        with self._lock:
            self._windows[key].clear()
    
    def get_config(self, key: str) -> RateLimitConfig:
        return self.config


class TokenBucketLimiter(RateLimiter):
    """
    Token Bucket Rate Limiter
    
    Allows burst traffic up to the bucket capacity while maintaining
    a steady refill rate.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        # Burst defaults to requests if not specified
        self._burst = config.burst if config.burst is not None else config.requests
    
    def _get_bucket(self, key: str) -> Dict[str, Any]:
        """Get or create a bucket for the key."""
        if key not in self._buckets:
            current_time = time.time()
            self._buckets[key] = {
                "tokens": float(self._burst),
                "last_refill": current_time
            }
        return self._buckets[key]
    
    def _refill_tokens(self, bucket: Dict[str, Any], current_time: float) -> None:
        """Refill tokens based on elapsed time."""
        elapsed = current_time - bucket["last_refill"]
        refill_rate = self.config.requests / self.config.window_seconds
        tokens_to_add = elapsed * refill_rate
        
        # Only add tokens if enough time has passed
        if elapsed >= 0.001:  # At least 1ms elapsed
            bucket["tokens"] = min(
                bucket["tokens"] + tokens_to_add,
                float(self._burst)
            )
            bucket["last_refill"] = current_time
    
    def check(self, key: str, amount: int = 1) -> RateLimitResult:
        current_time = time.time()
        
        with self._lock:
            bucket = self._get_bucket(key)
            self._refill_tokens(bucket, current_time)
            
            if bucket["tokens"] >= amount:
                bucket["tokens"] -= amount
                
                return RateLimitResult(
                    allowed=True,
                    remaining=int(bucket["tokens"]),
                    reset_time=current_time + (bucket["tokens"] / (self.config.requests / self.config.window_seconds))
                )
            else:
                # Calculate retry time
                tokens_needed = amount - bucket["tokens"]
                refill_rate = self.config.requests / self.config.window_seconds
                retry_after = tokens_needed / refill_rate if refill_rate > 0 else self.config.window_seconds
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=current_time + self.config.window_seconds,
                    retry_after=retry_after
                )
    
    def reset(self, key: str) -> None:
        with self._lock:
            if key in self._buckets:
                current_time = time.time()
                self._buckets[key] = {
                    "tokens": float(self._burst),
                    "last_refill": current_time
                }
    
    def get_config(self, key: str) -> RateLimitConfig:
        return self.config


class MultiDimensionalLimiter:
    """
    Multi-dimensional Rate Limiter
    
    Allows rate limiting across multiple dimensions (e.g., per-user, per-IP, per-endpoint).
    All dimensions must be satisfied for a request to be allowed.
    """
    
    def __init__(self):
        self._limiters: Dict[str, Dict[str, RateLimiter]] = defaultdict(dict)
        self._lock = threading.RLock()
    
    def add_dimension(self, dimension_name: str, key: str, config: RateLimitConfig) -> None:
        """Add a rate limiter for a specific dimension and key."""
        with self._lock:
            # Choose algorithm based on config
            if config.burst is not None:
                self._limiters[dimension_name][key] = TokenBucketLimiter(config)
            else:
                self._limiters[dimension_name][key] = SlidingWindowLimiter(config)
    
    def check(self, dimensions: Dict[str, str], amount: int = 1) -> RateLimitResult:
        """
        Check rate limits across all dimensions.
        
        Args:
            dimensions: Dict mapping dimension names to keys
            amount: Number of tokens to consume
        
        Returns:
            Combined rate limit result
        """
        with self._lock:
            most_restrictive = RateLimitResult(
                allowed=True,
                remaining=float('inf'),
                reset_time=0,
                retry_after=0
            )
            
            for dim_name, dim_key in dimensions.items():
                if dim_name not in self._limiters:
                    continue
                    
                if dim_key not in self._limiters[dim_name]:
                    # Auto-create limiter if not exists
                    self._limiters[dim_name][dim_key] = SlidingWindowLimiter(
                        RateLimitConfig()
                    )
                
                result = self._limiters[dim_name][dim_key].check(dim_key, amount)
                
                if not result.allowed:
                    return result
                
                # Track most restrictive limit
                if result.remaining < most_restrictive.remaining:
                    most_restrictive = result
            
            return most_restrictive
    
    def check_single(self, dimension: str, key: str, amount: int = 1) -> RateLimitResult:
        """Check rate limit for a single dimension."""
        with self._lock:
            if dimension not in self._limiters:
                return RateLimitResult(
                    allowed=True,
                    remaining=100,
                    reset_time=time.time() + 60
                )
            
            if key not in self._limiters[dimension]:
                return RateLimitResult(
                    allowed=True,
                    remaining=100,
                    reset_time=time.time() + 60
                )
            
            return self._limiters[dimension][key].check(key, amount)
    
    def reset(self, dimension: str, key: str) -> None:
        with self._lock:
            if dimension in self._limiters and key in self._limiters[dimension]:
                self._limiters[dimension][key].reset(key)
    
    def reset_all(self) -> None:
        with self._lock:
            for dim_limiters in self._limiters.values():
                for limiter in dim_limiters.values():
                    # Reset all keys (we'd need to track keys)
                    pass


class DistributedRateLimiter:
    """
    Distributed Rate Limiter (Redis-backed implementation interface)
    
    This class provides the interface for distributed rate limiting.
    In production, connect to Redis or similar distributed store.
    """
    
    def __init__(self, redis_client: Optional[Any] = None, prefix: str = "ratelimit"):
        self.redis = redis_client
        self.prefix = prefix
        self._local_cache: Dict[str, RateLimitResult] = {}
        self._cache_ttl: float = 1.0  # Cache for 1 second
        self._last_cache_update: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def _get_cache_key(self, key: str, algo: str) -> str:
        """Generate cache key for local caching."""
        return f"{self.prefix}:{algo}:{key}"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached result is still valid."""
        if key not in self._last_cache_update:
            return False
        return time.time() - self._last_cache_update[key] < self._cache_ttl
    
    def check(self, key: str, limit: int, window: int, algo: str = "sliding") -> RateLimitResult:
        """
        Distributed rate limit check.
        
        In production, this would use Redis for coordination.
        Falls back to local-only mode if no Redis client.
        """
        cache_key = self._get_cache_key(key, algo)
        
        # Try local cache first
        with self._lock:
            if self._is_cache_valid(cache_key):
                return self._local_cache[cache_key]
        
        if self.redis:
            # Redis implementation would go here
            result = self._distributed_check_redis(key, limit, window, algo)
        else:
            # Local fallback
            result = self._local_fallback_check(key, limit, window, algo)
        
        # Cache result
        with self._lock:
            self._local_cache[cache_key] = result
            self._last_cache_update[cache_key] = time.time()
        
        return result
    
    def _local_fallback_check(self, key: str, limit: int, window: int, algo: str) -> RateLimitResult:
        """Local fallback when no Redis available."""
        config = RateLimitConfig(requests=limit, window_seconds=window)
        
        if algo == "token_bucket":
            limiter = TokenBucketLimiter(config)
        else:
            limiter = SlidingWindowLimiter(config)
        
        return limiter.check(key)
    
    def _distributed_check_redis(self, key: str, limit: int, window: int, algo: str) -> RateLimitResult:
        """Redis-based distributed check."""
        # This would be the production implementation using Redis
        # For now, use local fallback
        return self._local_fallback_check(key, limit, window, algo)
    
    def set_redis_client(self, redis_client: Any) -> None:
        """Set Redis client for distributed mode."""
        self.redis = redis_client


class RateLimiterRegistry:
    """
    Registry for managing multiple rate limiters.
    """
    
    def __init__(self):
        self._registry: Dict[str, RateLimiter] = {}
        self._lock = threading.RLock()
    
    def register(self, name: str, limiter: RateLimiter) -> None:
        """Register a named rate limiter."""
        with self._lock:
            self._registry[name] = limiter
    
    def get(self, name: str) -> Optional[RateLimiter]:
        """Get a rate limiter by name."""
        with self._lock:
            return self._registry.get(name)
    
    def create_sliding_window(self, name: str, config: RateLimitConfig) -> SlidingWindowLimiter:
        """Create and register a sliding window limiter."""
        limiter = SlidingWindowLimiter(config)
        self.register(name, limiter)
        return limiter
    
    def create_token_bucket(self, name: str, config: RateLimitConfig) -> TokenBucketLimiter:
        """Create and register a token bucket limiter."""
        limiter = TokenBucketLimiter(config)
        self.register(name, limiter)
        return limiter
    
    def create_multi_dimensional(self, name: str) -> MultiDimensionalLimiter:
        """Create and register a multi-dimensional limiter."""
        limiter = MultiDimensionalLimiter()
        self.register(name, limiter)
        return limiter


def rate_limit(
    limiter: Union[RateLimiter, str],
    key_func: Optional[Callable] = None,
    default_key: str = "default"
):
    """
    Decorator for easy rate limiting of functions.
    
    Args:
        limiter: RateLimiter instance or name registered in registry
        key_func: Function to extract rate limit key from args/kwargs
        default_key: Default key if no key_func provided
    
    Example:
        @rate_limit(my_limiter, key_func=lambda u: user_id)
        def api_call(user_id: int, data: dict):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if isinstance(limiter, str):
                registry = RateLimiterRegistry()
                lim = registry.get(limiter)
                if lim is None:
                    raise ValueError(f"Rate limiter '{limiter}' not found")
            else:
                lim = limiter
            
            # Extract key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = default_key
            
            # Check rate limit
            result = lim.check(key)
            
            if not result.allowed:
                raise RateLimitExceeded(
                    "Rate limit exceeded",
                    retry_after=result.retry_after
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after
