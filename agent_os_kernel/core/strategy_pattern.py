# -*- coding: utf-8 -*-
"""
Strategy Pattern Module

Provides a flexible implementation of the Strategy pattern for algorithm
selection and runtime behavior modification.

Features:
- Strategy definition
- Strategy switching
- Strategy context
- Default strategy support
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, Callable
from enum import Enum
import threading


T = TypeVar('T')


class StrategyType(Enum):
    """Types of strategies available in the system."""
    DEFAULT = "default"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    BALANCED = "balanced"
    CUSTOM = "custom"


class StrategyError(Exception):
    """Base exception for strategy-related errors."""
    pass


class StrategyNotFoundError(StrategyError):
    """Raised when a requested strategy is not found."""
    pass


class StrategyRegistrationError(StrategyError):
    """Raised when a strategy cannot be registered."""
    pass


class Strategy(ABC):
    """
    Abstract base class for all strategies.
    
    All concrete strategies must implement the execute method
    to define their specific behavior.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the strategy."""
        pass
    
    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        """Return the type of the strategy."""
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Execute the strategy's core logic.
        
        Args:
            *args: Positional arguments for the strategy
            **kwargs: Keyword arguments for the strategy
            
        Returns:
            Result of the strategy execution
        """
        pass
    
    def validate(self, *args, **kwargs) -> bool:
        """
        Validate input parameters for the strategy.
        
        Args:
            *args: Positional arguments to validate
            **kwargs: Keyword arguments to validate
            
        Returns:
            True if inputs are valid, False otherwise
        """
        return True


class StrategyContext:
    """
    Context class that executes strategies.
    
    Maintains a reference to the current strategy and delegates
    execution to it. Supports dynamic strategy switching.
    """
    
    def __init__(
        self,
        default_strategy: Optional[Strategy] = None,
        context_name: Optional[str] = None
    ):
        """
        Initialize the strategy context.
        
        Args:
            default_strategy: Default strategy to use if none specified
            context_name: Optional name for this context instance
        """
        self._current_strategy: Optional[Strategy] = default_strategy
        self._default_strategy: Optional[Strategy] = default_strategy
        self._context_name = context_name
        self._lock = threading.RLock()
        self._execution_count = 0
        self._metadata: Dict[str, Any] = {}
    
    @property
    def current_strategy(self) -> Optional[Strategy]:
        """Get the currently active strategy."""
        with self._lock:
            return self._current_strategy
    
    @property
    def has_strategy(self) -> bool:
        """Check if a strategy is currently set."""
        with self._lock:
            return self._current_strategy is not None
    
    @property
    def context_name(self) -> Optional[str]:
        """Get the context name."""
        return self._context_name
    
    @property
    def execution_count(self) -> int:
        """Get the number of times the strategy has been executed."""
        with self._lock:
            return self._execution_count
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get metadata about this context."""
        return self._metadata
    
    def set_strategy(self, strategy: Strategy) -> bool:
        """
        Set a new strategy for this context.
        
        Args:
            strategy: The strategy to set
            
        Returns:
            True if strategy was set successfully
        """
        with self._lock:
            if strategy is None:
                return False
            self._current_strategy = strategy
            self._metadata["last_strategy_change"] = self._current_strategy.name
            return True
    
    def switch_strategy(self, strategy: Strategy) -> bool:
        """
        Switch to a new strategy (alias for set_strategy).
        
        Args:
            strategy: The strategy to switch to
            
        Returns:
            True if switch was successful
        """
        return self.set_strategy(strategy)
    
    def reset_to_default(self) -> bool:
        """
        Reset the strategy to the default strategy.
        
        Returns:
            True if reset was successful
        """
        with self._lock:
            if self._default_strategy is not None:
                self._current_strategy = self._default_strategy
                return True
            return False
    
    def execute(self, *args, **kwargs) -> Any:
        """
        Execute the current strategy.
        
        Args:
            *args: Positional arguments for the strategy
            **kwargs: Keyword arguments for the strategy
            
        Returns:
            Result of the strategy execution
            
        Raises:
            StrategyError: If no strategy is set
        """
        with self._lock:
            if self._current_strategy is None:
                raise StrategyError("No strategy set for execution")
            
            # Validate inputs
            if not self._current_strategy.validate(*args, **kwargs):
                raise StrategyError(
                    f"Invalid inputs for strategy: {self._current_strategy.name}"
                )
            
            self._execution_count += 1
        
        return self._current_strategy.execute(*args, **kwargs)
    
    def execute_with_fallback(
        self,
        primary_strategy: Strategy,
        fallback_strategy: Optional[Strategy] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute with fallback on failure.
        
        Args:
            primary_strategy: The primary strategy to try
            fallback_strategy: Fallback strategy if primary fails
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of successful strategy execution
        """
        try:
            self.set_strategy(primary_strategy)
            return self.execute(*args, **kwargs)
        except StrategyError:
            if fallback_strategy is not None:
                self.set_strategy(fallback_strategy)
                return self.execute(*args, **kwargs)
            raise


class StrategyRegistry:
    """
    Registry for managing available strategies.
    
    Provides a central repository for registering, retrieving,
    and managing strategy instances.
    """
    
    _instance: Optional['StrategyRegistry'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._strategies: Dict[str, Strategy] = {}
        self._strategy_types: Dict[StrategyType, Dict[str, Strategy]] = {}
        self._lock = threading.RLock()
        self._initialized = True
    
    def register(self, strategy: Strategy, overwrite: bool = False) -> bool:
        """
        Register a strategy in the registry.
        
        Args:
            strategy: The strategy to register
            overwrite: Whether to overwrite an existing strategy
            
        Returns:
            True if registration was successful
        """
        with self._lock:
            name = strategy.name
            
            if name in self._strategies and not overwrite:
                raise StrategyRegistrationError(
                    f"Strategy '{name}' already registered. Use overwrite=True to replace."
                )
            
            self._strategies[name] = strategy
            
            # Also register by type
            if strategy.strategy_type not in self._strategy_types:
                self._strategy_types[strategy.strategy_type] = {}
            self._strategy_types[strategy.strategy_type][name] = strategy
            
            return True
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a strategy by name.
        
        Args:
            name: Name of the strategy to unregister
            
        Returns:
            True if unregistration was successful
        """
        with self._lock:
            if name not in self._strategies:
                return False
            
            strategy = self._strategies.pop(name)
            
            # Also remove from type mapping
            if strategy.strategy_type in self._strategy_types:
                self._strategy_types[strategy.strategy_type].pop(name, None)
            
            return True
    
    def get(self, name: str) -> Strategy:
        """
        Get a strategy by name.
        
        Args:
            name: Name of the strategy to retrieve
            
        Returns:
            The strategy instance
            
        Raises:
            StrategyNotFoundError: If strategy is not found
        """
        with self._lock:
            if name not in self._strategies:
                raise StrategyNotFoundError(f"Strategy '{name}' not found")
            return self._strategies[name]
    
    def get_by_type(self, strategy_type: StrategyType) -> Dict[str, Strategy]:
        """
        Get all strategies of a specific type.
        
        Args:
            strategy_type: The type of strategies to retrieve
            
        Returns:
            Dictionary mapping strategy names to instances
        """
        with self._lock:
            return self._strategy_types.get(strategy_type, {}).copy()
    
    def list_all(self) -> Dict[str, Strategy]:
        """
        List all registered strategies.
        
        Returns:
            Dictionary mapping strategy names to instances
        """
        with self._lock:
            return self._strategies.copy()
    
    def clear(self) -> None:
        """Clear all registered strategies."""
        with self._lock:
            self._strategies.clear()
            self._strategy_types.clear()
    
    def count(self) -> int:
        """Get the number of registered strategies."""
        with self._lock:
            return len(self._strategies)


def get_strategy_registry() -> StrategyRegistry:
    """
    Get the global strategy registry instance.
    
    Returns:
        The global StrategyRegistry instance
    """
    return StrategyRegistry()


# Convenience functions

def create_strategy_context(
    strategy_name: Optional[str] = None,
    context_name: Optional[str] = None
) -> StrategyContext:
    """
    Create a strategy context with an optional initial strategy.
    
    Args:
        strategy_name: Name of a registered strategy to use as default
        context_name: Optional name for the context
        
    Returns:
        Configured StrategyContext instance
    """
    registry = get_strategy_registry()
    
    default_strategy = None
    if strategy_name:
        default_strategy = registry.get(strategy_name)
    
    return StrategyContext(default_strategy=default_strategy, context_name=context_name)


def register_builtin_strategies() -> None:
    """
    Register built-in strategies for common use cases.
    
    Includes default, performance, reliability, and balanced strategies.
    """
    registry = get_strategy_registry()
    
    # Default Strategy
    class DefaultStrategy(Strategy):
        @property
        def name(self) -> str:
            return "default"
        
        @property
        def strategy_type(self) -> StrategyType:
            return StrategyType.DEFAULT
        
        def execute(self, *args, **kwargs) -> Any:
            if args:
                return args[0] if len(args) == 1 else args
            return kwargs.get("default_result", None)
    
    # Performance Strategy
    class PerformanceStrategy(Strategy):
        @property
        def name(self) -> str:
            return "performance"
        
        @property
        def strategy_type(self) -> StrategyType:
            return StrategyType.PERFORMANCE
        
        def execute(self, *args, **kwargs) -> Any:
            # Optimize for speed, minimal processing
            return {"strategy": "performance", "optimized": True}
    
    # Reliability Strategy
    class ReliabilityStrategy(Strategy):
        @property
        def name(self) -> str:
            return "reliability"
        
        @property
        def strategy_type(self) -> StrategyType:
            return StrategyType.RELIABILITY
        
        def execute(self, *args, **kwargs) -> Any:
            # Focus on error handling and retries
            return {"strategy": "reliability", "error_handling": True}
    
    # Balanced Strategy
    class BalancedStrategy(Strategy):
        @property
        def name(self) -> str:
            return "balanced"
        
        @property
        def strategy_type(self) -> StrategyType:
            return StrategyType.BALANCED
        
        def execute(self, *args, **kwargs) -> Any:
            # Balance between performance and reliability
            return {"strategy": "balanced", "balanced": True}
    
    # Register all strategies
    strategies = [
        DefaultStrategy(),
        PerformanceStrategy(),
        ReliabilityStrategy(),
        BalancedStrategy(),
    ]
    
    for strategy in strategies:
        registry.register(strategy)


# Auto-register built-in strategies on module import
try:
    register_builtin_strategies()
except StrategyRegistrationError:
    # Already registered, which is fine
    pass
