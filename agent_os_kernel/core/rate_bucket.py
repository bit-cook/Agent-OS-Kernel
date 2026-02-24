"""
Token Bucket Rate Limiter

A dedicated token bucket implementation for rate limiting with:
- Token generation (automatic refill)
- Token consumption
- Configurable bucket capacity
- Configurable refill rate

This module provides a clean, focused TokenBucket class separate from
the more complex rate limiter implementations.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenBucketConfig:
    """Configuration for the token bucket."""
    capacity: int = 100  # Maximum tokens the bucket can hold
    refill_rate: float = 10.0  # Tokens added per second
    initial_tokens: float = 0.0  # Initial tokens in the bucket


class TokenBucket:
    """
    Token Bucket Rate Limiter
    
    The token bucket algorithm allows burst traffic up to the bucket capacity
    while maintaining a steady refill rate. This is useful for rate limiting
    API calls, controlling resource consumption, and implementing various
    traffic shaping policies.
    
    Attributes:
        capacity: Maximum number of tokens the bucket can hold
        refill_rate: Number of tokens added per second
        available_tokens: Current number of tokens available
        
    Example:
        >>> bucket = TokenBucket(capacity=100, refill_rate=10)
        >>> if bucket.consume(5):
        ...     print("Request allowed")
        ... else:
        ...     print("Rate limited")
    """
    
    def __init__(
        self,
        capacity: int = 100,
        refill_rate: float = 10.0,
        initial_tokens: float = 0.0
    ):
        """
        Initialize a new token bucket.
        
        Args:
            capacity: Maximum tokens the bucket can hold (default: 100)
            refill_rate: Tokens added per second (default: 10.0)
            initial_tokens: Starting number of tokens (default: 0.0)
            
        Raises:
            ValueError: If capacity or refill_rate is negative
        """
        if capacity < 0:
            raise ValueError("Capacity cannot be negative")
        if refill_rate < 0:
            raise ValueError("Refill rate cannot be negative")
        if initial_tokens < 0:
            raise ValueError("Initial tokens cannot be negative")
        
        self._capacity = float(capacity)
        self._refill_rate = float(refill_rate)
        self._tokens = float(initial_tokens)
        self._last_refill_time = time.time()
        self._lock = threading.RLock()
    
    @property
    def capacity(self) -> int:
        """Maximum tokens the bucket can hold."""
        return int(self._capacity)
    
    @property
    def refill_rate(self) -> float:
        """Tokens added per second."""
        return self._refill_rate
    
    @property
    def available_tokens(self) -> float:
        """Current number of tokens available."""
        with self._lock:
            self._refill()
            return self._tokens
    
    @property
    def utilization(self) -> float:
        """Current bucket utilization as a fraction (0.0 to 1.0)."""
        with self._lock:
            self._refill()
            return self._tokens / self._capacity if self._capacity > 0 else 0.0
    
    def _refill(self) -> None:
        """
        Refill tokens based on elapsed time.
        
        This is called internally before any token operations.
        """
        current_time = time.time()
        elapsed = current_time - self._last_refill_time
        
        if elapsed > 0 and self._refill_rate > 0:
            tokens_to_add = elapsed * self._refill_rate
            self._tokens = min(
                self._tokens + tokens_to_add,
                self._capacity
            )
            self._last_refill_time = current_time
    
    def consume(self, tokens: float = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
            
        Raises:
            ValueError: If tokens is negative
        """
        if tokens < 0:
            raise ValueError("Cannot consume negative tokens")
        if tokens == 0:
            return True
        
        with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False
    
    def consume_or_wait(self, tokens: float = 1, timeout: Optional[float] = None) -> float:
        """
        Consume tokens, waiting if necessary.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            timeout: Maximum time to wait in seconds (None means wait forever)
            
        Returns:
            Time waited in seconds
            
        Raises:
            TimeoutError: If timeout expires before tokens available
            ValueError: If tokens is negative
        """
        if tokens < 0:
            raise ValueError("Cannot consume negative tokens")
        if tokens == 0:
            return 0.0
        
        with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return 0.0
            
            # Calculate wait time
            tokens_needed = tokens - self._tokens
            wait_time = tokens_needed / self._refill_rate if self._refill_rate > 0 else float('inf')
            
            if wait_time > 0:
                if timeout is not None and wait_time > timeout:
                    # Wait for timeout duration
                    time.sleep(timeout)
                    raise TimeoutError(f"Timeout after {timeout} seconds")
                
                # Wait for tokens to refill
                time.sleep(wait_time)
            
            # Refill and consume
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return wait_time
            
            # Should not reach here if calculations are correct
            raise TimeoutError("Failed to acquire tokens")
    
    def refill(self, tokens: float) -> float:
        """
        Manually add tokens to the bucket.
        
        Args:
            tokens: Number of tokens to add
            
        Returns:
            Number of tokens actually added (capped at capacity)
            
        Raises:
            ValueError: If tokens is negative
        """
        if tokens < 0:
            raise ValueError("Cannot add negative tokens")
        
        with self._lock:
            old_tokens = self._tokens
            self._tokens = min(self._tokens + tokens, self._capacity)
            return self._tokens - old_tokens
    
    def reset(self) -> None:
        """
        Reset the bucket to initial state.
        
        Sets tokens to zero and resets the refill timer.
        """
        with self._lock:
            self._tokens = 0.0
            self._last_refill_time = time.time()
    
    def reset_with_full_capacity(self) -> None:
        """
        Reset the bucket with full capacity.
        
        Fills the bucket to capacity and resets the refill timer.
        """
        with self._lock:
            self._tokens = self._capacity
            self._last_refill_time = time.time()
    
    def time_until_tokens(self, tokens: float) -> float:
        """
        Calculate time until specified tokens are available.
        
        Args:
            tokens: Number of tokens to check availability for
            
        Returns:
            Time in seconds until tokens are available
            
        Raises:
            ValueError: If tokens is negative
        """
        if tokens < 0:
            raise ValueError("Cannot check negative tokens")
        if tokens == 0:
            return 0.0
        
        with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self._tokens
            return tokens_needed / self._refill_rate if self._refill_rate > 0 else float('inf')
    
    def get_state(self) -> dict:
        """
        Get the current state of the token bucket.
        
        Returns:
            Dictionary containing bucket state
        """
        with self._lock:
            self._refill()
            return {
                "capacity": self._capacity,
                "refill_rate": self._refill_rate,
                "available_tokens": self._tokens,
                "utilization": self._tokens / self._capacity if self._capacity > 0 else 0.0,
                "last_refill_time": self._last_refill_time
            }
    
    def __repr__(self) -> str:
        with self._lock:
            return (
                f"TokenBucket(capacity={self._capacity}, "
                f"refill_rate={self._refill_rate}, "
                f"available_tokens={self._tokens:.2f})"
            )


class AsyncTokenBucket:
    """
    Async-compatible Token Bucket
    
    Provides the same functionality as TokenBucket but with async support.
    Uses asyncio for non-blocking operations.
    """
    
    def __init__(
        self,
        capacity: int = 100,
        refill_rate: float = 10.0,
        initial_tokens: float = 0.0
    ):
        """
        Initialize an async token bucket.
        
        Args:
            capacity: Maximum tokens the bucket can hold (default: 100)
            refill_rate: Tokens added per second (default: 10.0)
            initial_tokens: Starting number of tokens (default: 0.0)
        """
        if capacity < 0:
            raise ValueError("Capacity cannot be negative")
        if refill_rate < 0:
            raise ValueError("Refill rate cannot be negative")
        
        self._capacity = float(capacity)
        self._refill_rate = float(refill_rate)
        self._tokens = float(initial_tokens)
        self._last_refill_time = time.time()
        self._lock = asyncio.Lock()
    
    @property
    def capacity(self) -> int:
        return int(self._capacity)
    
    @property
    def refill_rate(self) -> float:
        return self._refill_rate
    
    @property
    async def available_tokens(self) -> float:
        """Current number of tokens available."""
        async with self._lock:
            self._refill()
            return self._tokens
    
    async def consume(self, tokens: float = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        if tokens < 0:
            raise ValueError("Cannot consume negative tokens")
        
        async with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False
    
    async def consume_or_wait(self, tokens: float = 1) -> float:
        """
        Consume tokens, waiting if necessary.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            Time waited in seconds
        """
        if tokens < 0:
            raise ValueError("Cannot consume negative tokens")
        
        async with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return 0.0
            
            # Calculate wait time
            tokens_needed = tokens - self._tokens
            wait_time = tokens_needed / self._refill_rate if self._refill_rate > 0 else float('inf')
            
            if wait_time > 0:
                # Release lock during sleep to allow other operations
                self._lock.release()
                await asyncio.sleep(wait_time)
                await self._lock.acquire()
            
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return wait_time
            
            return float('inf')
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        current_time = time.time()
        elapsed = current_time - self._last_refill_time
        
        if elapsed > 0 and self._refill_rate > 0:
            tokens_to_add = elapsed * self._refill_rate
            self._tokens = min(
                self._tokens + tokens_to_add,
                self._capacity
            )
            self._last_refill_time = current_time
    
    async def refill(self, tokens: float) -> float:
        """Manually add tokens to the bucket."""
        if tokens < 0:
            raise ValueError("Cannot add negative tokens")
        
        async with self._lock:
            old_tokens = self._tokens
            self._tokens = min(self._tokens + tokens, self._capacity)
            return self._tokens - old_tokens
    
    async def reset(self) -> None:
        """Reset the bucket to initial state."""
        async with self._lock:
            self._tokens = 0.0
            self._last_refill_time = time.time()
    
    def __repr__(self) -> str:
        return (
            f"AsyncTokenBucket(capacity={self._capacity}, "
            f"refill_rate={self._refill_rate}, "
            f"available_tokens={self._tokens:.2f})"
        )


# Import asyncio for AsyncTokenBucket
import asyncio
