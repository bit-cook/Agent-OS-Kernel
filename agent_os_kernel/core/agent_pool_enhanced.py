"""
Enhanced Agent Pool for Agent-OS-Kernel

This module provides an enhanced agent pool with:
- Priority-based agent scheduling
- Auto-scaling capabilities
- Health monitoring
- Load balancing
- Resource limits
"""

import asyncio
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from queue import PriorityQueue
import psutil

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    HEALTH_CHECK = "health_check"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    REMOVED = "removed"


class AgentPriority(Enum):
    """Agent priority levels (lower number = higher priority)"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(order=True)
class AgentTask:
    """Represents a task in the agent priority queue"""
    priority: int
    task_id: str = field(compare=False)
    data: Any = field(compare=False)
    created_at: float = field(compare=False, default_factory=time.time)
    
    def __post_init__(self):
        object.__setattr__(self, 'priority', self.priority.value if isinstance(self.priority, AgentPriority) else self.priority)


class AgentHealthChecker(ABC):
    """Abstract base class for agent health checks"""
    
    @abstractmethod
    async def check_health(self, agent: "Agent") -> bool:
        """Check if the agent is healthy"""
        pass
    
    @abstractmethod
    async def recover(self, agent: "Agent") -> bool:
        """Attempt to recover a failed agent"""
        pass


class DefaultHealthChecker(AgentHealthChecker):
    """Default health checker implementation"""
    
    def __init__(self, check_interval: float = 30.0, timeout: float = 10.0):
        self.check_interval = check_interval
        self.timeout = timeout
        self._last_check_time: Dict[str, float] = {}
        self._consecutive_failures: Dict[str, int] = {}
        self.max_consecutive_failures = 3
    
    async def check_health(self, agent: "Agent") -> bool:
        """Perform health check on agent"""
        try:
            # Simulate health check with timeout
            await asyncio.wait_for(
                self._perform_check(agent),
                timeout=self.timeout
            )
            self._consecutive_failures[agent.id] = 0
            self._last_check_time[agent.id] = time.time()
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for agent {agent.id}")
            self._record_failure(agent.id)
            return False
        except Exception as e:
            logger.error(f"Health check failed for agent {agent.id}: {e}")
            self._record_failure(agent.id)
            return False
    
    async def _perform_check(self, agent: "Agent") -> bool:
        """Actual health check implementation"""
        # Default implementation checks if agent process is alive
        if hasattr(agent, 'process') and agent.process is not None:
            try:
                return agent.process.is_alive()
            except Exception:
                return False
        return True
    
    async def recover(self, agent: "Agent") -> bool:
        """Attempt to recover the agent"""
        try:
            # Reset agent state
            agent.state = AgentState.INITIALIZING
            await agent.initialize()
            agent.state = AgentState.RUNNING
            self._consecutive_failures[agent.id] = 0
            logger.info(f"Agent {agent.id} recovered successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to recover agent {agent.id}: {e}")
            return False
    
    def _record_failure(self, agent_id: str):
        """Record a health check failure"""
        self._consecutive_failures[agent_id] = self._consecutive_failures.get(agent_id, 0) + 1
    
    def needs_recovery(self, agent_id: str) -> bool:
        """Check if agent needs recovery"""
        return self._consecutive_failures.get(agent_id, 0) >= self.max_consecutive_failures


class LoadBalancer(ABC):
    """Abstract base class for load balancing strategies"""
    
    @abstractmethod
    def select_agent(self, agents: List["Agent"], task: AgentTask) -> Optional["Agent"]:
        """Select the best agent for a task"""
        pass


class RoundRobinLoadBalancer(LoadBalancer):
    """Round-robin load balancer"""
    
    def __init__(self):
        self._index = 0
    
    def select_agent(self, agents: List["Agent"], task: AgentTask) -> Optional["Agent"]:
        """Select next available agent in round-robin fashion"""
        if not agents:
            return None
        
        # Filter to available agents only
        available = [a for a in agents if a.state in (AgentState.IDLE, AgentState.RUNNING)]
        if not available:
            return None
        
        # Round-robin selection
        self._index = (self._index + 1) % len(available)
        return available[self._index - 1]


class LeastConnectionsLoadBalancer(LoadBalancer):
    """Least connections load balancer"""
    
    def select_agent(self, agents: List["Agent"], task: AgentTask) -> Optional["Agent"]:
        """Select agent with fewest active connections/tasks"""
        if not agents:
            return None
        
        available = [a for a in agents if a.state in (AgentState.IDLE, AgentState.RUNNING)]
        if not available:
            return None
        
        # Sort by current load (connections count)
        return min(available, key=lambda a: a.current_load)


class PriorityLoadBalancer(LoadBalancer):
    """Priority-based load balancer"""
    
    def select_agent(self, agents: List["Agent"], task: AgentTask) -> Optional["Agent"]:
        """Select highest priority agent that can handle the task"""
        if not agents:
            return None
        
        # Filter agents that can handle the task priority
        suitable = []
        for agent in agents:
            if agent.state in (AgentState.IDLE, AgentState.RUNNING):
                if agent.can_handle_priority(task.priority):
                    suitable.append(agent)
        
        if not suitable:
            return None
        
        # Among suitable, select least loaded
        return min(suitable, key=lambda a: a.current_load)


class Agent:
    """
    Enhanced Agent with priority support and health monitoring
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "UnnamedAgent",
        priority: AgentPriority = AgentPriority.NORMAL,
        max_concurrent_tasks: int = 1,
        resource_limits: Optional[Dict[str, float]] = None,
        tags: Optional[Set[str]] = None
    ):
        self.id = agent_id or str(uuid.uuid4())[:8]
        self.name = name
        self.priority = priority
        self.max_concurrent_tasks = max_concurrent_tasks
        self.resource_limits = resource_limits or {
            'cpu_percent': 80.0,
            'memory_percent': 80.0
        }
        self.tags = tags or set()
        
        self.state = AgentState.PENDING
        self.process: Optional[threading.Thread] = None
        self.current_load = 0
        self.active_tasks: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.created_at = time.time()
        self.last_activity = time.time()
        self._lock = threading.Lock()
        
        logger.info(f"Agent {self.id} ({self.name}) created with priority {self.priority}")
    
    def can_handle_priority(self, task_priority: int) -> bool:
        """Check if agent can handle a task with given priority"""
        # Lower priority number = higher priority
        # Agent can handle tasks with priority >= its own (i.e., equal or lower priority number)
        agent_prio_num = self.priority.value if isinstance(self.priority, AgentPriority) else self.priority
        return task_priority >= agent_prio_num
    
    def can_accept_task(self) -> bool:
        """Check if agent can accept more tasks"""
        return self.current_load < self.max_concurrent_tasks
    
    def add_task(self, task_id: str, task_data: Any) -> bool:
        """Add a task to the agent"""
        with self._lock:
            if not self.can_accept_task():
                return False
            self.active_tasks[task_id] = task_data
            self.current_load = len(self.active_tasks)
            self.last_activity = time.time()
            return True
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the agent"""
        with self._lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                self.current_load = len(self.active_tasks)
                return True
            return False
    
    def update_load(self, load_delta: int) -> int:
        """Update current load"""
        with self._lock:
            self.current_load = max(0, self.current_load + load_delta)
            return self.current_load
    
    async def initialize(self) -> bool:
        """Initialize the agent"""
        try:
            self.state = AgentState.INITIALIZING
            # Perform initialization logic here
            await asyncio.sleep(0.1)  # Simulated async init
            self.state = AgentState.RUNNING
            logger.info(f"Agent {self.id} initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize agent {self.id}: {e}")
            self.state = AgentState.FAILED
            return False
    
    async def start(self) -> bool:
        """Start the agent"""
        try:
            self.state = AgentState.RUNNING
            logger.info(f"Agent {self.id} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start agent {self.id}: {e}")
            self.state = AgentState.FAILED
            return False
    
    async def stop(self) -> bool:
        """Stop the agent"""
        try:
            self.state = AgentState.STOPPING
            # Cleanup logic here
            await asyncio.sleep(0.1)
            self.state = AgentState.STOPPED
            logger.info(f"Agent {self.id} stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop agent {self.id}: {e}")
            return False
    
    def check_resource_usage(self) -> Dict[str, float]:
        """Check current resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent
        }
    
    def is_within_limits(self) -> bool:
        """Check if agent is within resource limits"""
        usage = self.check_resource_usage()
        return (
            usage['cpu_percent'] <= self.resource_limits.get('cpu_percent', 100.0) and
            usage['memory_percent'] <= self.resource_limits.get('memory_percent', 100.0)
        )
    
    @property
    def is_healthy(self) -> bool:
        """Check if agent is healthy"""
        return (
            self.state in (AgentState.RUNNING, AgentState.IDLE) and
            self.is_within_limits()
        )


class AgentPool:
    """
    Enhanced Agent Pool with priority queue, auto-scaling, health checks, and load balancing
    """
    
    def __init__(
        self,
        min_size: int = 1,
        max_size: int = 10,
        health_checker: Optional[AgentHealthChecker] = None,
        load_balancer: Optional[LoadBalancer] = None,
        auto_scale_interval: float = 60.0,
        resource_limits: Optional[Dict[str, float]] = None
    ):
        self.min_size = min_size
        self.max_size = max_size
        self.auto_scale_interval = auto_scale_interval
        
        self._agents: Dict[str, Agent] = {}
        self._agent_queue: PriorityQueue = PriorityQueue()
        self._task_queue: PriorityQueue = PriorityQueue()
        
        self.health_checker = health_checker or DefaultHealthChecker()
        self.load_balancer = load_balancer or LeastConnectionsLoadBalancer()
        
        self._resource_limits = resource_limits or {
            'cpu_percent': 80.0,
            'memory_percent': 80.0
        }
        
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        # Statistics
        self._total_tasks_processed = 0
        self._total_tasks_failed = 0
        self._start_time = time.time()
        
        logger.info(f"AgentPool initialized with min={min_size}, max={max_size}")
    
    @property
    def size(self) -> int:
        """Current number of agents in the pool"""
        return len(self._agents)
    
    @property
    def available_agents(self) -> List[Agent]:
        """List of available agents"""
        return [a for a in self._agents.values() if a.state in (AgentState.IDLE, AgentState.RUNNING)]
    
    @property
    def busy_agents(self) -> List[Agent]:
        """List of busy agents"""
        return [a for a in self._agents.values() if a.state == AgentState.BUSY]
    
    def add_agent(self, agent: Agent) -> bool:
        """Add an agent to the pool"""
        with self._lock:
            if self.size >= self.max_size:
                logger.warning("Pool at maximum size, cannot add agent")
                return False
            
            agent.resource_limits = self._resource_limits
            self._agents[agent.id] = agent
            logger.info(f"Agent {agent.id} added to pool (size: {self.size})")
            return True
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the pool"""
        with self._lock:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                # Try to stop the agent, but handle if event loop is running
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Create a new event loop for stopping
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(agent.stop())
                        new_loop.close()
                    else:
                        loop.run_until_complete(agent.stop())
                except RuntimeError:
                    asyncio.run(agent.stop())
                del self._agents[agent_id]
                logger.info(f"Agent {agent_id} removed from pool (size: {self.size})")
                return True
            return False
    
    def submit_task(
        self,
        task_data: Any,
        priority: AgentPriority = AgentPriority.NORMAL,
        task_id: Optional[str] = None
    ) -> str:
        """Submit a task to the pool with priority"""
        task = AgentTask(
            priority=priority,
            task_id=task_id or str(uuid.uuid4())[:8],
            data=task_data
        )
        self._task_queue.put(task)
        logger.debug(f"Task {task.task_id} submitted with priority {priority}")
        return task.task_id
    
    async def process_task(self, task: AgentTask) -> bool:
        """Process a single task"""
        agent = self.load_balancer.select_agent(
            list(self._agents.values()),
            task
        )
        
        if agent is None:
            logger.warning(f"No available agent for task {task.task_id}")
            return False
        
        try:
            agent.state = AgentState.BUSY
            agent.add_task(task.task_id, task.data)
            
            # Simulate task processing
            await asyncio.sleep(0.1)
            
            agent.remove_task(task.task_id)
            if agent.current_load == 0:
                agent.state = AgentState.IDLE
            else:
                agent.state = AgentState.RUNNING
            
            self._total_tasks_processed += 1
            return True
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            self._total_tasks_failed += 1
            agent.state = AgentState.RUNNING
            return False
    
    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                await self._health_check()
                await self._auto_scale()
                await asyncio.sleep(self.auto_scale_interval)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    async def _health_check(self):
        """Perform health checks on all agents"""
        for agent in list(self._agents.values()):
            if agent.state in (AgentState.RUNNING, AgentState.IDLE):
                healthy = await self.health_checker.check_health(agent)
                if not healthy:
                    logger.warning(f"Agent {agent.id} failed health check")
                    if self.health_checker.needs_recovery(agent.id):
                        await self.health_checker.recover(agent)
    
    async def _auto_scale(self):
        """Automatically scale the pool based on load"""
        usage = self.check_pool_resources()
        avg_load = sum(a.current_load for a in self._agents.values()) / max(1, len(self._agents))
        
        # Scale up if overloaded
        if (usage['cpu_percent'] > 70 or avg_load > self.min_size) and self.size < self.max_size:
            logger.info("Auto-scaling up: pool is under high load")
            await self._scale_up()
        
        # Scale down if underutilized
        elif avg_load < 0.3 and self.size > self.min_size:
            logger.info("Auto-scaling down: pool is underutilized")
            await self._scale_down()
    
    async def _scale_up(self):
        """Add agents to the pool"""
        target_size = min(self.size + 1, self.max_size)
        while self.size < target_size:
            new_agent = Agent(
                name=f"AutoAgent-{self.size + 1}",
                priority=AgentPriority.NORMAL,
                resource_limits=self._resource_limits
            )
            await new_agent.initialize()
            self.add_agent(new_agent)
    
    async def _scale_down(self):
        """Remove agents from the pool"""
        target_size = max(self.size - 1, self.min_size)
        # Remove the least priority, least loaded agent
        candidates = sorted(
            self._agents.values(),
            key=lambda a: (a.priority.value, a.current_load)
        )
        if candidates:
            agent_to_remove = candidates[0]
            if agent_to_remove.current_load == 0:
                self.remove_agent(agent_to_remove.id)
    
    def check_pool_resources(self) -> Dict[str, float]:
        """Check overall pool resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'agent_count': self.size,
            'avg_load': sum(a.current_load for a in self._agents.values()) / max(1, len(self._agents))
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pool statistics"""
        uptime = time.time() - self._start_time
        return {
            'total_agents': self.size,
            'available_agents': len(self.available_agents),
            'busy_agents': len(self.busy_agents),
            'total_tasks_processed': self._total_tasks_processed,
            'total_tasks_failed': self._total_tasks_failed,
            'success_rate': (
                self._total_tasks_processed / 
                max(1, self._total_tasks_processed + self._total_tasks_failed)
            ),
            'uptime_seconds': uptime
        }
    
    async def start(self):
        """Start the agent pool"""
        if self._running:
            return
        
        self._running = True
        # Start with minimum agents
        for i in range(self.min_size):
            agent = Agent(
                name=f"PoolAgent-{i + 1}",
                priority=AgentPriority.NORMAL,
                resource_limits=self._resource_limits
            )
            await agent.initialize()
            self.add_agent(agent)
        
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("AgentPool started")
    
    async def stop(self):
        """Stop the agent pool"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all agents
        for agent in list(self._agents.values()):
            await agent.stop()
        
        logger.info("AgentPool stopped")
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
