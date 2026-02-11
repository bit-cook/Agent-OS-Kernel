# -*- coding: utf-8 -*-
"""
Sliding Window Module for Agent-OS-Kernel

Provides sliding window counter algorithm for rate limiting and
time-based request tracking with improved accuracy.
"""

import time
import threading
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class SlidingWindowResult:
    """Result of a sliding window check."""
    allowed: bool
    count: int
    limit: int
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None


class SlidingWindowCounter:
    """
    Sliding Window Counter Implementation
    
    Uses a more accurate sliding window algorithm that doesn't have
    the boundary issues of fixed windows. Provides smooth rate limiting
    across time boundaries.
    """
    
    def __init__(self, limit: int, window_size_seconds: float = 1.0):
        """
        Initialize the sliding window counter.
        
        Args:
            limit: Maximum number of events allowed in the window
            window_size_seconds: Size of the sliding window in seconds
        """
        self.limit = limit
        self.window_size = window_size_seconds
        self._current_window: deque = deque()
        self._previous_window: deque = deque()
        self._window_start: float = time.time()
        self._lock = threading.RLock()
    
    def _get_current_weight(self) -> float:
        """
        Calculate the weight of the previous window for interpolation.
        
        Returns:
            Weight between 0 and 1 representing how much of the
            previous window's data should be counted
        """
        elapsed = time.time() - self._window_start
        
        if elapsed >= self.window_size:
            return 0.0
        
        return 1.0 - (elapsed / self.window_size)
    
    def _advance_window(self) -> Tuple[int, float]:
        """
        Advance the window if needed.
        
        Returns:
            Tuple of (previous_window_count, previous_window_weight)
        """
        current_time = time.time()
        elapsed = current_time - self._window_start
        
        if elapsed >= self.window_size:
            # Move current window to previous
            self._previous_window = self._current_window
            self._current_window = deque()
            self._window_start = current_time
            
            return len(self._previous_window), self._get_current_weight()
        
        return len(self._previous_window), self._get_current_weight()
    
    def record(self, count: int = 1) -> SlidingWindowResult:
        """
        Record events in the sliding window.
        
        Args:
            count: Number of events to record
            
        Returns:
            SlidingWindowResult with the current state
        """
        with self._lock:
            prev_count, weight = self._advance_window()
            
            # Calculate weighted count
            weighted_prev = prev_count * weight
            current_count = len(self._current_window) + count
            total_count = weighted_prev + current_count
            
            # Record the events with timestamps
            current_time = time.time()
            for _ in range(count):
                self._current_window.append(current_time)
            
            # Calculate retry after if over limit
            retry_after = None
            if total_count > self.limit:
                # Calculate when the count will drop below limit
                # We need to remove enough events from the weighted sum
                excess = total_count - self.limit
                
                # First try removing from current window
                removals_needed = min(excess, len(self._current_window))
                for _ in range(removals_needed):
                    try:
                        self._current_window.popleft()
                    except IndexError:
                        break
                
                # If still over, we need to wait for previous window to expire
                if weighted_prev + len(self._current_window) > self.limit:
                    retry_after = self.window_size - (current_time - self._window_start)
            
            # Clean old entries from current window
            cutoff_time = current_time - self.window_size
            while self._current_window and self._current_window[0] < cutoff_time:
                self._current_window.popleft()
            
            remaining = max(0, self.limit - int(total_count))
            
            return SlidingWindowResult(
                allowed=total_count <= self.limit,
                count=int(total_count),
                limit=self.limit,
                remaining=remaining,
                reset_time=self._window_start + self.window_size,
                retry_after=retry_after if retry_after and retry_after > 0 else None
            )
    
    def check(self) -> SlidingWindowResult:
        """
        Check current count without recording.
        
        Returns:
            SlidingWindowResult with the current state
        """
        with self._lock:
            prev_count, weight = self._advance_window()
            weighted_prev = prev_count * weight
            current_count = len(self._current_window)
            total_count = weighted_prev + current_count
            
            remaining = max(0, self.limit - int(total_count))
            
            return SlidingWindowResult(
                allowed=total_count <= self.limit,
                count=int(total_count),
                limit=self.limit,
                remaining=remaining,
                reset_time=self._window_start + self.window_size,
                retry_after=None
            )
    
    def reset(self) -> None:
        """Reset the counter to initial state."""
        with self._lock:
            self._current_window.clear()
            self._previous_window.clear()
            self._window_start = time.time()
    
    @property
    def current_count(self) -> int:
        """Get the current weighted count."""
        with self._lock:
            prev_count, weight = self._advance_window()
            return int(prev_count * weight + len(self._current_window))


class SlidingWindowLimiter:
    """
    Sliding Window Rate Limiter with Per-Key Support
    
    Manages multiple sliding window counters, each identified by a unique key.
    Each key has its own rate limit configuration.
    """
    
    def __init__(
        self,
        default_limit: int = 100,
        default_window_seconds: float = 1.0
    ):
        """
        Initialize the sliding window limiter.
        
        Args:
            default_limit: Default maximum events per window
            default_window_seconds: Default window size in seconds
        """
        self.default_limit = default_limit
        self.default_window_seconds = default_window_seconds
        self._counters: Dict[str, SlidingWindowCounter] = {}
        self._lock = threading.RLock()
    
    def _get_counter(self, key: str) -> SlidingWindowCounter:
        """Get or create a counter for the given key."""
        if key not in self._counters:
            self._counters[key] = SlidingWindowCounter(
                self.default_limit,
                self.default_window_seconds
            )
        return self._counters[key]
    
    def check(self, key: str) -> SlidingWindowResult:
        """
        Check the current rate for a key without recording.
        
        Args:
            key: Unique identifier for the rate limit
            
        Returns:
            SlidingWindowResult indicating the current state
        """
        with self._lock:
            counter = self._get_counter(key)
            return counter.check()
    
    def record(self, key: str, count: int = 1) -> SlidingWindowResult:
        """
        Record events for a key.
        
        Args:
            key: Unique identifier for the rate limit
            count: Number of events to record
            
        Returns:
            SlidingWindowResult indicating if allowed
        """
        with self._lock:
            counter = self._get_counter(key)
            return counter.record(count)
    
    def allow(self, key: str) -> Tuple[bool, SlidingWindowResult]:
        """
        Check and record in one operation.
        
        Args:
            key: Unique identifier for the rate limit
            
        Returns:
            Tuple of (is_allowed, SlidingWindowResult)
        """
        with self._lock:
            counter = self._get_counter(key)
            result = counter.record(1)
            return result.allowed, result
    
    def reset(self, key: str) -> None:
        """
        Reset the rate limit for a specific key.
        
        Args:
            key: The key to reset
        """
        with self._lock:
            if key in self._counters:
                self._counters[key].reset()
    
    def reset_all(self) -> None:
        """Reset all rate limits."""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()
    
    def set_limit(self, key: str, limit: int, window_seconds: float) -> None:
        """
        Set custom rate limit for a key.
        
        Args:
            key: The key to set
            limit: New limit for the window
            window_seconds: New window size in seconds
        """
        with self._lock:
            self._counters[key] = SlidingWindowCounter(limit, window_seconds)


def create_sliding_window_limiter(
    requests_per_second: float = 100.0,
    window_size_seconds: float = 1.0
) -> SlidingWindowLimiter:
    """
    Create a sliding window limiter with common settings.
    
    Args:
        requests_per_second: Number of requests allowed per second
        window_size_seconds: Size of the sliding window
        
    Returns:
        Configured SlidingWindowLimiter instance
    """
    return SlidingWindowLimiter(
        default_limit=int(requests_per_second),
        default_window_seconds=window_size_seconds
    )
