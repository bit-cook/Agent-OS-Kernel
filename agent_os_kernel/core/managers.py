# -*- coding: utf-8 -*-
"""
Core Managers Module

Provides centralized management for all Agent-OS-Kernel subsystems.
This module offers a unified interface to access, configure, and coordinate
various managers and services within the kernel.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ManagerState(Enum):
    """Manager lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ManagerType(Enum):
    """Types of managers in the system."""
    INIT = "init"
    SHUTDOWN = "shutdown"
    POOL = "pool"
    PROXY = "proxy"
    RESOURCE = "resource"
    HEALTH = "health"
    METRICS = "metrics"
    TRACING = "tracing"
    CACHE = "cache"
    CONNECTION = "connection"
    RATE_LIMIT = "rate_limit"
    CIRCUIT_BREAKER = "circuit_breaker"
    EVENT = "event"
    MESSAGE_QUEUE = "message_queue"
    WORKFLOW = "workflow"
    LOCK = "lock"
    CONFIG = "config"


@dataclass
class ManagerConfig:
    """Base configuration for managers."""
    enabled: bool = True
    auto_start: bool = True
    priority: int = 0
    max_retries: int = 3
    timeout_seconds: float = 30.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManagerStatus:
    """Status report from a manager."""
    manager_type: ManagerType
    state: ManagerState
    is_healthy: bool
    uptime_seconds: float
    metrics: Dict[str, Any]
    error_message: Optional[str] = None
    last_updated: float = 0.0


class BaseManager(ABC):
    """Abstract base class for all managers."""
    
    def __init__(self, name: str, config: Optional[ManagerConfig] = None):
        self.name = name
        self.config = config or ManagerConfig()
        self._state = ManagerState.UNINITIALIZED
        self._start_time: Optional[float] = None
        self._metrics: Dict[str, Any] = {}
        
    @property
    def state(self) -> ManagerState:
        """Get current manager state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._state == ManagerState.RUNNING
    
    @property
    def is_ready(self) -> bool:
        """Check if manager is ready."""
        return self._state in (ManagerState.READY, ManagerState.RUNNING)
    
    @property
    def uptime(self) -> float:
        """Get manager uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return asyncio.get_event_loop().time() - self._start_time
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the manager. Returns True on success."""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the manager. Returns True on success."""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the manager. Returns True on success."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check. Returns True if healthy."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get manager metrics."""
        pass
    
    async def _set_state(self, new_state: ManagerState) -> None:
        """Safely update manager state."""
        old_state = self._state
        self._state = new_state
        logger.debug(f"Manager {self.name}: {old_state.value} -> {new_state.value}")
    
    def _update_metrics(self, key: str, value: Any) -> None:
        """Update a metric value."""
        self._metrics[key] = value


class CompositeManager(BaseManager):
    """Manager that wraps multiple sub-managers."""
    
    def __init__(self, name: str, config: Optional[ManagerConfig] = None):
        super().__init__(name, config)
        self._managers: Dict[str, BaseManager] = {}
        self._dependencies: Dict[str, List[str]] = {}
    
    def register(self, manager: BaseManager, dependencies: Optional[List[str]] = None) -> None:
        """Register a sub-manager."""
        self._managers[manager.name] = manager
        if dependencies:
            self._dependencies[manager.name] = dependencies
        logger.info(f"Registered manager: {manager.name}")
    
    def get(self, name: str) -> Optional[BaseManager]:
        """Get a registered manager by name."""
        return self._managers.get(name)
    
    def get_by_type(self, manager_type: ManagerType) -> Optional[BaseManager]:
        """Get a manager by type."""
        for manager in self._managers.values():
            if isinstance(manager, TypedManager) and manager.manager_type == manager_type:
                return manager
        return None
    
    async def initialize(self) -> bool:
        """Initialize all registered managers."""
        await self._set_state(ManagerState.INITIALIZING)
        
        try:
            # Initialize in dependency order
            initialized = set()
            remaining = list(self._managers.values())
            
            while remaining:
                progress = False
                for manager in remaining[:]:
                    deps = self._dependencies.get(manager.name, [])
                    if all(d in initialized for d in deps):
                        if await manager.initialize():
                            initialized.add(manager.name)
                            remaining.remove(manager)
                            progress = True
                
                if not progress and remaining:
                    raise RuntimeError(f"Circular dependency detected. Remaining: {[m.name for m in remaining]}")
            
            await self._set_state(ManagerState.READY)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize composite manager {self.name}: {e}")
            await self._set_state(ManagerState.ERROR)
            return False
    
    async def start(self) -> bool:
        """Start all registered managers."""
        await self._set_state(ManagerState.STARTING)
        self._start_time = asyncio.get_event_loop().time()
        
        try:
            for manager in self._managers.values():
                if manager.config.auto_start:
                    if not await manager.start():
                        logger.warning(f"Manager {manager.name} failed to start")
            
            await self._set_state(ManagerState.RUNNING)
            return True
        except Exception as e:
            logger.error(f"Failed to start composite manager {self.name}: {e}")
            await self._set_state(ManagerState.ERROR)
            return False
    
    async def stop(self) -> bool:
        """Stop all registered managers."""
        await self._set_state(ManagerState.STOPPING)
        
        try:
            # Stop in reverse dependency order
            for name, manager in reversed(list(self._managers.items())):
                try:
                    await manager.stop()
                except Exception as e:
                    logger.warning(f"Error stopping manager {name}: {e}")
            
            await self._set_state(ManagerState.STOPPED)
            return True
        except Exception as e:
            logger.error(f"Failed to stop composite manager {self.name}: {e}")
            await self._set_state(ManagerState.ERROR)
            return False
    
    async def health_check(self) -> bool:
        """Check health of all managers."""
        for manager in self._managers.values():
            if not await manager.health_check():
                return False
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from all managers."""
        result = {}
        for name, manager in self._managers.items():
            result[name] = manager.get_metrics()
        return result
    
    @property
    def managers(self) -> Dict[str, BaseManager]:
        """Get all registered managers."""
        return self._managers.copy()


class TypedManager(BaseManager):
    """A manager with a specific type."""
    
    def __init__(
        self,
        name: str,
        manager_type: ManagerType,
        config: Optional[ManagerConfig] = None
    ):
        super().__init__(name, config)
        self.manager_type = manager_type


class CoreManager(CompositeManager):
    """
    Central Core Manager for Agent-OS-Kernel.
    
    Provides unified access to all kernel subsystems and manages
    their lifecycle, configuration, and coordination.
    """
    
    _instance: Optional['CoreManager'] = None
    
    def __init__(self, config: Optional[ManagerConfig] = None):
        super().__init__("core", config)
        self._instance = self
        self._event_bus: Optional[Any] = None
        self._config_source: Optional[Any] = None
        
    @classmethod
    def get_instance(cls) -> Optional['CoreManager']:
        """Get the singleton CoreManager instance."""
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
    
    def set_event_bus(self, event_bus: Any) -> None:
        """Set the event bus for internal communication."""
        self._event_bus = event_bus
    
    def set_config_source(self, config_source: Any) -> None:
        """Set the configuration source."""
        self._config_source = config_source
    
    def register_init_manager(self, manager: BaseManager) -> None:
        """Register the initialization manager."""
        self.register(manager, dependencies=[])
    
    def register_shutdown_manager(self, manager: BaseManager) -> None:
        """Register the shutdown manager."""
        self.register(manager, dependencies=["init"])
    
    def register_pool_manager(self, manager: BaseManager) -> None:
        """Register the pool manager."""
        self.register(manager, dependencies=["init"])
    
    def register_proxy_manager(self, manager: BaseManager) -> None:
        """Register the proxy manager."""
        self.register(manager, dependencies=["init", "pool"])
    
    def register_resource_manager(self, manager: BaseManager) -> None:
        """Register the resource monitor manager."""
        self.register(manager, dependencies=["init"])
    
    def register_health_manager(self, manager: BaseManager) -> None:
        """Register the health check manager."""
        self.register(manager, dependencies=["init", "resource"])
    
    def register_metrics_manager(self, manager: BaseManager) -> None:
        """Register the metrics manager."""
        self.register(manager, dependencies=["init"])
    
    def register_tracing_manager(self, manager: BaseManager) -> None:
        """Register the tracing manager."""
        self.register(manager, dependencies=["init"])
    
    async def get_status(self) -> List[ManagerStatus]:
        """Get status of all managers."""
        statuses = []
        for name, manager in self._managers.items():
            status = ManagerStatus(
                manager_type=getattr(manager, 'manager_type', ManagerType.INIT),
                state=manager.state,
                is_healthy=await manager.health_check(),
                uptime_seconds=manager.uptime,
                metrics=manager.get_metrics(),
                error_message=None
            )
            statuses.append(status)
        return statuses
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of overall system health."""
        all_healthy = True
        manager_health = {}
        
        for name, manager in self._managers.items():
            is_healthy = await manager.health_check()
            manager_health[name] = {
                "state": manager.state.value,
                "healthy": is_healthy,
                "uptime": manager.uptime
            }
            if not is_healthy:
                all_healthy = False
        
        return {
            "overall_healthy": all_healthy,
            "manager_count": len(self._managers),
            "managers": manager_health,
            "timestamp": asyncio.get_event_loop().time()
        }


class ManagerRegistry:
    """Registry for manager types and factories."""
    
    _registry: Dict[ManagerType, Type[BaseManager]] = {}
    
    @classmethod
    def register(cls, manager_type: ManagerType, manager_class: Type[BaseManager]) -> None:
        """Register a manager class for a type."""
        cls._registry[manager_type] = manager_class
    
    @classmethod
    def get(cls, manager_type: ManagerType) -> Optional[Type[BaseManager]]:
        """Get the registered class for a type."""
        return cls._registry.get(manager_type)
    
    @classmethod
    def create(cls, manager_type: ManagerType, name: str, **kwargs) -> Optional[BaseManager]:
        """Create a manager instance by type."""
        manager_class = cls.get(manager_type)
        if manager_class:
            return manager_class(name, **kwargs)
        return None


class ManagerBuilder:
    """Builder for creating and configuring managers."""
    
    def __init__(self):
        self._managers: List[BaseManager] = []
        self._config: Dict[str, ManagerConfig] = {}
    
    def add_manager(self, manager: BaseManager, config: Optional[ManagerConfig] = None) -> 'ManagerBuilder':
        """Add a manager to the builder."""
        self._managers.append(manager)
        if config:
            self._config[manager.name] = config
        return self
    
    def with_config(self, name: str, config: ManagerConfig) -> 'ManagerBuilder':
        """Set configuration for a manager."""
        self._config[name] = config
        return self
    
    def build(self, core: Optional[CoreManager] = None) -> CoreManager:
        """Build the core manager with all registered managers."""
        if core is None:
            core = CoreManager()
        
        for manager in self._managers:
            config = self._config.get(manager.name)
            if config:
                manager.config = config
            core.register(manager)
        
        return core
    
    def create_standalone(self) -> List[BaseManager]:
        """Create managers as standalone instances."""
        return self._managers.copy()


@asynccontextmanager
async def manager_lifecycle(manager: BaseManager):
    """Context manager for manager lifecycle (initialize -> start -> stop)."""
    try:
        await manager.initialize()
        await manager.start()
        yield manager
    finally:
        await manager.stop()


def create_core_manager(
    init_manager: Optional[BaseManager] = None,
    shutdown_manager: Optional[BaseManager] = None,
    pool_manager: Optional[BaseManager] = None,
    resource_manager: Optional[BaseManager] = None,
    health_manager: Optional[BaseManager] = None
) -> CoreManager:
    """
    Factory function to create a configured CoreManager.
    
    Args:
        init_manager: Initialization manager
        shutdown_manager: Shutdown manager
        pool_manager: Pool manager
        resource_manager: Resource monitor manager
        health_manager: Health check manager
    
    Returns:
        Configured CoreManager instance
    """
    core = CoreManager()
    
    if init_manager:
        core.register_init_manager(init_manager)
    if shutdown_manager:
        core.register_shutdown_manager(shutdown_manager)
    if pool_manager:
        core.register_pool_manager(pool_manager)
    if resource_manager:
        core.register_resource_manager(resource_manager)
    if health_manager:
        core.register_health_manager(health_manager)
    
    return core


__all__ = [
    # Enums
    "ManagerState",
    "ManagerType",
    # Data classes
    "ManagerConfig",
    "ManagerStatus",
    # Base classes
    "BaseManager",
    "CompositeManager",
    "TypedManager",
    # Core
    "CoreManager",
    # Registry and Builder
    "ManagerRegistry",
    "ManagerBuilder",
    # Utilities
    "manager_lifecycle",
    "create_core_manager",
]
