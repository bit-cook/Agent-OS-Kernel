# -*- coding: utf-8 -*-
"""
Circuit Breaker Module

A robust implementation of the Circuit Breaker pattern for preventing
cascade failures and improving system resilience.
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Dict
from functools import wraps
import threading


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Circuit tripped, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery, limited requests


class CircuitError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker monitoring."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_transitions: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rejected_requests": self.rejected_requests,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "state_transitions": self.state_transitions,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "failure_rate": (
                self.failed_requests / self.total_requests 
                if self.total_requests > 0 else 0.0
            ),
        }


@dataclass
class CircuitConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5           # Failures before opening circuit
    success_threshold: int = 3           # Successes in half-open to close
    timeout_seconds: float = 30.0        # Time before attempting recovery
    half_open_max_requests: int = 3       # Max requests in half-open state
    window_size_seconds: float = 60.0    # Sliding window for failure counting
    
    def __post_init__(self):
        """Validate configuration."""
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.success_threshold <= 0:
            raise ValueError("success_threshold must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class CircuitBreaker:
    """
    Circuit Breaker implementation for preventing cascade failures.
    
    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Circuit tripped, requests are rejected
        - HALF_OPEN: Testing recovery, limited requests allowed
    
    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=30)
        >>> try:
        >>>     result = breaker.call(my_function, arg1, arg2)
        >>> except CircuitError:
        >>>     print("Circuit is open!")
    """
    
    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitConfig] = None,
        on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker
            config: Configuration settings
            on_state_change: Callback for state changes (name, old_state, new_state)
        """
        self.name = name
        self.config = config or CircuitConfig()
        self.on_state_change = on_state_change
        
        self._state = CircuitState.CLOSED
        self._state_lock = threading.Lock()
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._failure_times: list = []
        self._metrics = CircuitMetrics()
        self._half_open_requests = 0
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def metrics(self) -> CircuitMetrics:
        """Get current metrics."""
        return self._metrics
    
    def _try_open(self) -> bool:
        """Try to open the circuit based on failure count."""
        self._cleanup_old_failures()
        return self._failure_count >= self.config.failure_threshold
    
    def _cleanup_old_failures(self):
        """Remove failures outside the sliding window."""
        current_time = time.time()
        cutoff = current_time - self.config.window_size_seconds
        self._failure_times = [
            t for t in self._failure_times if t > cutoff
        ]
        self._failure_count = len(self._failure_times)
    
    def _change_state(self, new_state: CircuitState):
        """Change circuit state with callback."""
        old_state = self._state
        if old_state != new_state:
            self._state = new_state
            self._metrics.state_transitions += 1
            if self.on_state_change:
                try:
                    self.on_state_change(self.name, old_state, new_state)
                except Exception:
                    pass  # Don't let callback failures affect circuit
    
    def _record_failure(self):
        """Record a failure and potentially open circuit."""
        current_time = time.time()
        self._failure_times.append(current_time)
        self._failure_count += 1
        self._last_failure_time = current_time
        
        self._metrics.failed_requests += 1
        self._metrics.total_requests += 1
        self._metrics.consecutive_failures += 1
        self._metrics.consecutive_successes = 0
        
        if self._try_open():
            self._change_state(CircuitState.OPEN)
    
    def _record_success(self):
        """Record a success and potentially close circuit."""
        current_time = time.time()
        self._last_success_time = current_time
        
        self._metrics.successful_requests += 1
        self._metrics.total_requests += 1
        self._metrics.consecutive_successes += 1
        self._metrics.consecutive_failures = 0
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_requests += 1
            if self._half_open_requests >= self.config.success_threshold:
                self._change_state(CircuitState.CLOSED)
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self._state == CircuitState.CLOSED:
            return True
        elif self._state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout_seconds:
                    self._change_state(CircuitState.HALF_OPEN)
                    self._half_open_requests = 0
                    return True
            return False
        elif self._state == CircuitState.HALF_OPEN:
            # Allow limited requests
            if self._half_open_requests < self.config.half_open_max_requests:
                self._half_open_requests += 1
                return True
            return False
        return False
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from function
            
        Raises:
            CircuitError: If circuit is open
            Exception: Any exception from the function
        """
        with self._state_lock:
            if not self._should_allow_request():
                self._metrics.rejected_requests += 1
                self._metrics.total_requests += 1
                raise CircuitError(
                    f"Circuit '{self.name}' is OPEN. "
                    f"Requests are blocked until timeout."
                )
        
        try:
            result = func(*args, **kwargs)
            with self._state_lock:
                self._record_success()
            return result
        except Exception as e:
            with self._state_lock:
                self._record_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function through the circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from async function
            
        Raises:
            CircuitError: If circuit is open
            Exception: Any exception from the function
        """
        with self._state_lock:
            if not self._should_allow_request():
                self._metrics.rejected_requests += 1
                self._metrics.total_requests += 1
                raise CircuitError(
                    f"Circuit '{self.name}' is OPEN. "
                    f"Requests are blocked until timeout."
                )
        
        try:
            result = await func(*args, **kwargs)
            with self._state_lock:
                self._record_success()
            return result
        except Exception as e:
            with self._state_lock:
                self._record_failure()
            raise
    
    def reset(self):
        """Reset circuit breaker to initial closed state."""
        with self._state_lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._failure_times.clear()
            self._last_failure_time = None
            self._last_success_time = None
            self._half_open_requests = 0
            self._metrics = CircuitMetrics()
    
    def force_open(self):
        """Force circuit breaker to open state."""
        with self._state_lock:
            self._change_state(CircuitState.OPEN)
            self._last_failure_time = time.time()
    
    def force_close(self):
        """Force circuit breaker to close state."""
        with self._state_lock:
            self._change_state(CircuitState.CLOSED)
    
    def get_info(self) -> Dict[str, Any]:
        """Get circuit breaker status information."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.config.failure_threshold,
            "timeout_seconds": self.config.timeout_seconds,
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
            "metrics": self._metrics.to_dict(),
        }


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    
    Provides centralized management of circuit breakers for different
    services or dependencies.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitConfig] = None,
        on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None,
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create new one.
        
        Args:
            name: Circuit breaker name
            config: Configuration for new breaker
            on_state_change: State change callback
            
        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config,
                    on_state_change=on_state_change,
                )
            return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def remove(self, name: str) -> bool:
        """Remove circuit breaker by name."""
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                return True
            return False
    
    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
    
    def get_all_info(self) -> Dict[str, Dict[str, Any]]:
        """Get info for all circuit breakers."""
        with self._lock:
            return {
                name: breaker.get_info() 
                for name, breaker in self._breakers.items()
            }


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()


def circuit_breaker(
    name: Optional[str] = None,
    config: Optional[CircuitConfig] = None,
    on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None,
):
    """
    Decorator to add circuit breaker protection to a function.
    
    Args:
        name: Circuit breaker name (defaults to function name)
        config: Circuit breaker configuration
        on_state_change: State change callback
        
    Example:
        @circuit_breaker(name="api_calls", failure_threshold=3)
        async def call_api(url):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """
    def decorator(func):
        breaker_name = name or func.__name__
        breaker = circuit_breaker_manager.get_or_create(
            name=breaker_name,
            config=config,
            on_state_change=on_state_change,
        )
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


# Convenience function to get or create circuit breaker
def get_circuit_breaker(
    name: str,
    config: Optional[CircuitConfig] = None,
    on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    return circuit_breaker_manager.get_or_create(
        name=name,
        config=config,
        on_state_change=on_state_change,
    )
