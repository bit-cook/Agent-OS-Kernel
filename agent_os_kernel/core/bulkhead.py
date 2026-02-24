"""
Bulkhead Pattern Implementation for Agent-OS-Kernel

The bulkhead pattern isolates failures and limits resource usage by partitioning
a system into independent sections. This prevents cascading failures and ensures
system stability under high load.

Features:
- Concurrency limiting via semaphore
- Resource isolation with named bulkheads
- Timeout control for operations
- Thread-safe implementation
"""

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict, List, TypeVar, Generic
from contextlib import contextmanager
import asyncio
from functools import wraps


T = TypeVar('T')


@dataclass
class BulkheadConfig:
    """Configuration for bulkhead behavior."""
    max_concurrent: int = 10  # Maximum concurrent operations
    max_wait_time: float = 30.0  # Maximum time to wait for semaphore (seconds)
    timeout: float = 60.0  # Operation timeout (seconds)
    failure_isolation: bool = True  # Isolate failures
    isolation_name: str = "default"  # Name for resource isolation grouping


@dataclass
class BulkheadState:
    """Current state of a bulkhead."""
    active_count: int = 0
    waiting_count: int = 0
    total_executed: int = 0
    total_failed: int = 0
    total_timed_out: int = 0
    last_failure_time: Optional[float] = None
    is_isolated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "active_count": self.active_count,
            "waiting_count": self.waiting_count,
            "total_executed": self.total_executed,
            "total_failed": self.total_failed,
            "total_timed_out": self.total_timed_out,
            "last_failure_time": self.last_failure_time,
            "is_isolated": self.is_isolated,
        }


class BulkheadError(Exception):
    """Base exception for bulkhead-related errors."""
    pass


class BulkheadFullError(BulkheadError):
    """Raised when bulkhead is at capacity."""
    pass


class BulkheadTimeoutError(BulkheadError):
    """Raised when operation times out."""
    pass


class BulkheadIsolatedError(BulkheadError):
    """Raised when bulkhead is isolated due to failures."""
    pass


class BulkheadBase(ABC):
    """Abstract base class for bulkhead implementations."""
    
    @abstractmethod
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with bulkhead protection."""
        pass
    
    @abstractmethod
    def get_state(self) -> BulkheadState:
        """Get current bulkhead state."""
        pass
    
    @abstractmethod
    def reset_state(self) -> None:
        """Reset bulkhead state."""
        pass
    
    @abstractmethod
    def isolate(self, isolate: bool = True) -> None:
        """Manually isolate/unisolate the bulkhead."""
        pass


class SemaphoreBulkhead(BulkheadBase):
    """
    Semaphore-based Bulkhead Implementation
    
    Uses a semaphore to limit concurrent access to resources.
    Provides resource isolation and failure containment.
    """
    
    def __init__(self, config: Optional[BulkheadConfig] = None):
        """
        Initialize the bulkhead.
        
        Args:
            config: Bulkhead configuration (uses defaults if not provided)
        """
        self.config = config or BulkheadConfig()
        self._semaphore = threading.Semaphore(self.config.max_concurrent)
        self._state = BulkheadState()
        self._lock = threading.RLock()
        self._isolation_lock = threading.Lock()
    
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with bulkhead protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of the function
            
        Raises:
            BulkheadFullError: If bulkhead is at capacity
            BulkheadTimeoutError: If operation times out
            BulkheadIsolatedError: If bulkhead is isolated
        """
        # Check if isolated
        if self._state.is_isolated:
            raise BulkheadIsolatedError(
                f"Bulkhead '{self.config.isolation_name}' is isolated due to failures"
            )
        
        # Try to acquire semaphore with timeout
        acquired = self._semaphore.acquire(timeout=self.config.max_wait_time)
        
        if not acquired:
            with self._lock:
                self._state.total_timed_out += 1
            raise BulkheadTimeoutError(
                f"Bulkhead '{self.config.isolation_name}' timeout: "
                f"waited {self.config.max_wait_time}s for semaphore"
            )
        
        # Track execution
        with self._lock:
            self._state.active_count += 1
        
        start_time = time.time()
        result = None
        exception = None
        
        try:
            # Execute with timeout
            remaining_time = self.config.timeout - (time.time() - start_time)
            
            if remaining_time <= 0:
                raise BulkheadTimeoutError(
                    f"Bulkhead '{self.config.isolation_name}' timeout: "
                    f"operation exceeded {self.config.timeout}s"
                )
            
            # Use threading wrapper for timeout support
            result = self._execute_with_timeout(
                func, remaining_time, *args, **kwargs
            )
            
        except Exception as e:
            exception = e
            with self._lock:
                self._state.total_failed += 1
                self._state.last_failure_time = time.time()
            
            # Auto-isolate on failure if configured
            if self.config.failure_isolation:
                self.isolate(True)
            
            raise
            
        finally:
            # Update state on completion
            with self._lock:
                self._state.active_count -= 1
                self._state.total_executed += 1
            
            self._semaphore.release()
        
        if exception:
            raise exception
        return result
    
    def _execute_with_timeout(
        self, 
        func: Callable[..., T], 
        timeout: float,
        *args: Any, 
        **kwargs: Any
    ) -> T:
        """Execute function with timeout using threading."""
        result = None
        exception = None
        thread_completed = threading.Event()
        
        def worker():
            nonlocal result, exception
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                exception = e
            finally:
                thread_completed.set()
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        completed = thread_completed.wait(timeout=timeout)
        
        if not completed:
            # Timeout - thread is still running
            raise BulkheadTimeoutError(
                f"Bulkhead '{self.config.isolation_name}' timeout: "
                f"operation exceeded {timeout}s"
            )
        
        if exception:
            raise exception
        return result
    
    def get_state(self) -> BulkheadState:
        """Get current bulkhead state."""
        with self._lock:
            return BulkheadState(
                active_count=self._state.active_count,
                waiting_count=self._state.waiting_count,
                total_executed=self._state.total_executed,
                total_failed=self._state.total_failed,
                total_timed_out=self._state.total_timed_out,
                last_failure_time=self._state.last_failure_time,
                is_isolated=self._state.is_isolated,
            )
    
    def reset_state(self) -> None:
        """Reset bulkhead state."""
        with self._lock:
            self._state = BulkheadState()
            # Reset isolation
            self._state.is_isolated = False
    
    def isolate(self, isolate: bool = True) -> None:
        """
        Manually isolate/unisolate the bulkhead.
        
        Args:
            isolate: True to isolate, False to unisolate
        """
        with self._isolation_lock:
            self._state.is_isolated = isolate
    
    def get_available_slots(self) -> int:
        """Get number of available slots in the bulkhead."""
        return self._semaphore._value if hasattr(self._semaphore, '_value') else 0
    
    @property
    def config_copy(self) -> BulkheadConfig:
        """Get a copy of the current configuration."""
        return BulkheadConfig(
            max_concurrent=self.config.max_concurrent,
            max_wait_time=self.config.max_wait_time,
            timeout=self.config.timeout,
            failure_isolation=self.config.failure_isolation,
            isolation_name=self.config.isolation_name,
        )


class BulkheadRegistry:
    """
    Registry for managing multiple bulkhead instances.
    
    Provides centralized management of bulkheads with isolation groups.
    """
    
    def __init__(self):
        self._bulkheads: Dict[str, BulkheadBase] = {}
        self._lock = threading.RLock()
    
    def get_or_create(
        self, 
        name: str, 
        config: Optional[BulkheadConfig] = None
    ) -> SemaphoreBulkhead:
        """
        Get existing bulkhead or create new one.
        
        Args:
            name: Name of the bulkhead
            config: Optional configuration for new bulkheads
            
        Returns:
            Existing or new bulkhead instance
        """
        with self._lock:
            if name not in self._bulkheads:
                self._bulkheads[name] = SemaphoreBulkhead(config)
            return self._bulkheads[name]
    
    def get(self, name: str) -> Optional[SemaphoreBulkhead]:
        """Get bulkhead by name."""
        return self._bulkheads.get(name)
    
    def remove(self, name: str) -> bool:
        """Remove bulkhead from registry."""
        with self._lock:
            if name in self._bulkheads:
                del self._bulkheads[name]
                return True
            return False
    
    def list_bulkheads(self) -> List[str]:
        """List all bulkhead names."""
        with self._lock:
            return list(self._bulkheads.keys())
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get state of all bulkheads."""
        with self._lock:
            return {
                name: bulkhead.get_state().to_dict()
                for name, bulkhead in self._bulkheads.items()
            }
    
    def reset_all(self) -> None:
        """Reset all bulkheads in the registry."""
        with self._lock:
            for bulkhead in self._bulkheads.values():
                bulkhead.reset_state()
    
    def isolate_all(self, isolate: bool = True) -> None:
        """Isolate or unisolate all bulkheads."""
        with self._lock:
            for bulkhead in self._bulkheads.values():
                bulkhead.isolate(isolate)


# Global registry instance
_global_registry: Optional[BulkheadRegistry] = None


def get_registry() -> BulkheadRegistry:
    """Get the global bulkhead registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = BulkheadRegistry()
    return _global_registry


def bulkhead(
    name: Optional[str] = None,
    max_concurrent: int = 10,
    max_wait_time: float = 30.0,
    timeout: float = 60.0,
    failure_isolation: bool = True
) -> Callable:
    """
    Decorator for applying bulkhead protection to functions.
    
    Args:
        name: Optional bulkhead name (defaults to function name)
        max_concurrent: Maximum concurrent operations
        max_wait_time: Maximum wait time for semaphore
        timeout: Operation timeout
        failure_isolation: Enable failure isolation
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        config = BulkheadConfig(
            max_concurrent=max_concurrent,
            max_wait_time=max_wait_time,
            timeout=timeout,
            failure_isolation=failure_isolation,
            isolation_name=name or func.__name__,
        )
        bulkhead_instance = get_registry().get_or_create(
            name or func.__name__, config
        )
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return bulkhead_instance.execute(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await bulkhead_instance.execute_async(func, *args, **kwargs)
        
        # Check if function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


class AsyncSemaphoreBulkhead(BulkheadBase):
    """
    Async-compatible Semaphore Bulkhead Implementation
    
    Uses asyncio semaphore for async operations with the same bulkhead features.
    """
    
    def __init__(self, config: Optional[BulkheadConfig] = None):
        """Initialize the async bulkhead."""
        self.config = config or BulkheadConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._state = BulkheadState()
        self._lock = asyncio.Lock()
    
    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute an async function with bulkhead protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of the function
        """
        # Check if isolated
        if self._state.is_isolated:
            raise BulkheadIsolatedError(
                f"Bulkhead '{self.config.isolation_name}' is isolated due to failures"
            )
        
        # Try to acquire semaphore with timeout
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.config.max_wait_time
            )
        except asyncio.TimeoutError:
            with (await self._lock):
                self._state.total_timed_out += 1
            raise BulkheadTimeoutError(
                f"Bulkhead '{self.config.isolation_name}' timeout: "
                f"waited {self.config.max_wait_time}s for semaphore"
            )
        
        # Track execution
        async with self._lock:
            self._state.active_count += 1
        
        start_time = time.time()
        result = None
        exception = None
        
        try:
            # Execute with timeout
            remaining_time = self.config.timeout - (time.time() - start_time)
            
            if remaining_time <= 0:
                raise BulkheadTimeoutError(
                    f"Bulkhead '{self.config.isolation_name}' timeout: "
                    f"operation exceeded {self.config.timeout}s"
                )
            
            # Execute the async function
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=remaining_time
            )
            
        except asyncio.TimeoutError:
            async with self._lock:
                self._state.total_timed_out += 1
            raise BulkheadTimeoutError(
                f"Bulkhead '{self.config.isolation_name}' timeout: "
                f"operation exceeded {self.config.timeout}s"
            )
            
        except Exception as e:
            exception = e
            async with self._lock:
                self._state.total_failed += 1
                self._state.last_failure_time = time.time()
            
            if self.config.failure_isolation:
                await self.isolate(True)
            
            raise
            
        finally:
            async with self._lock:
                self._state.active_count -= 1
                self._state.total_executed += 1
            
            self._semaphore.release()
        
        if exception:
            raise exception
        return result
    
    async def execute_async(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Alias for execute for async functions."""
        return await self.execute(func, *args, **kwargs)
    
    def get_state(self) -> BulkheadState:
        """Get current bulkhead state."""
        # Note: This is a simplified sync version for async bulkhead
        return BulkheadState(
            active_count=self._state.active_count,
            waiting_count=0,  # Not tracked for async
            total_executed=self._state.total_executed,
            total_failed=self._state.total_failed,
            total_timed_out=self._state.total_timed_out,
            last_failure_time=self._state.last_failure_time,
            is_isolated=self._state.is_isolated,
        )
    
    def reset_state(self) -> None:
        """Reset bulkhead state."""
        self._state = BulkheadState()
        self._state.is_isolated = False
    
    async def isolate(self, isolate: bool = True) -> None:
        """Isolate or unisolate the bulkhead."""
        async with self._lock:
            self._state.is_isolated = isolate


# Convenience function for creating bulkheads
def create_bulkhead(
    name: str,
    max_concurrent: int = 10,
    max_wait_time: float = 30.0,
    timeout: float = 60.0,
    failure_isolation: bool = True,
    async_mode: bool = False
) -> BulkheadBase:
    """
    Create a new bulkhead instance.
    
    Args:
        name: Name for the bulkhead
        max_concurrent: Maximum concurrent operations
        max_wait_time: Maximum wait time for semaphore
        timeout: Operation timeout
        failure_isolation: Enable failure isolation
        async_mode: Use async-compatible implementation
        
    Returns:
        Bulkhead instance
    """
    config = BulkheadConfig(
        max_concurrent=max_concurrent,
        max_wait_time=max_wait_time,
        timeout=timeout,
        failure_isolation=failure_isolation,
        isolation_name=name,
    )
    
    if async_mode:
        return AsyncSemaphoreBulkhead(config)
    
    return SemaphoreBulkhead(config)
