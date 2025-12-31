"""
Load Balancer Router - Distribute Load Across Agent Instances

Routes requests to the least-loaded agent instance to optimize resource
utilization and prevent overload.

Supports multiple load balancing strategies:
- Round Robin: Cycle through instances
- Least Connections: Route to instance with fewest active requests
- Least Response Time: Route to fastest instance
- Weighted: Route based on instance capacity weights

Example:
    >>> # Create agent instances
    >>> instances = [
    ...     AgentInstance(agent=agent1, weight=1.0, max_concurrent=10),
    ...     AgentInstance(agent=agent2, weight=2.0, max_concurrent=20),
    ...     AgentInstance(agent=agent3, weight=1.5, max_concurrent=15),
    ... ]
    >>>
    >>> # Create load balancer
    >>> balancer = LoadBalancerRouter(
    ...     instances=instances,
    ...     strategy=LoadBalancingStrategy.LEAST_CONNECTIONS
    ... )
    >>>
    >>> # Route messages automatically
    >>> response = await balancer.process(message)
"""

import asyncio
import contextlib
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..interfaces import Agent, Message


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"


@dataclass
class InstanceMetrics:
    """Metrics for an agent instance."""

    active_requests: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    last_request_time: float | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if self.successful_requests == 0:
            return float("inf")
        return self.total_response_time / self.successful_requests

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def error_rate(self) -> float:
        """Calculate error rate (0.0 to 1.0)."""
        return 1.0 - self.success_rate


@dataclass
class AgentInstance:
    """An agent instance with load balancing metadata."""

    agent: Agent
    weight: float = 1.0  # Relative capacity (higher = more requests)
    max_concurrent: int = 10  # Maximum concurrent requests
    enabled: bool = True  # Whether instance is accepting requests
    metrics: InstanceMetrics = field(default_factory=InstanceMetrics)

    @property
    def name(self) -> str:
        """Instance name."""
        return self.agent.name

    @property
    def load_factor(self) -> float:
        """Current load as fraction of capacity (0.0 to 1.0+)."""
        if self.max_concurrent == 0:
            return 0.0
        return self.metrics.active_requests / self.max_concurrent

    @property
    def can_accept_request(self) -> bool:
        """Check if instance can accept another request."""
        return self.enabled and self.metrics.active_requests < self.max_concurrent


class LoadBalancerError(Exception):
    """Raised when load balancer cannot route request."""

    pass


class LoadBalancerRouter(Agent):
    """
    Load balancer router for distributing requests across agent instances.

    Routes requests to the best available agent instance based on the
    selected load balancing strategy and instance health metrics.

    Example:
        >>> # Create instances
        >>> instances = [
        ...     AgentInstance(agent=agent1, weight=1.0, max_concurrent=10),
        ...     AgentInstance(agent=agent2, weight=1.0, max_concurrent=10),
        ... ]
        >>>
        >>> # Create load balancer
        >>> balancer = LoadBalancerRouter(
        ...     instances=instances,
        ...     strategy=LoadBalancingStrategy.LEAST_CONNECTIONS
        ... )
        >>>
        >>> # Process requests (automatically routed)
        >>> for message in messages:
        ...     response = await balancer.process(message)
    """

    def __init__(
        self,
        instances: list[AgentInstance],
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS,
        name: str = "load_balancer",
        health_check_interval: float = 30.0,
        circuit_breaker_threshold: int = 5,
    ):
        """Initialize load balancer router.

        Args:
            instances: List of agent instances
            strategy: Load balancing strategy
            name: Router name
            health_check_interval: Seconds between health checks
            circuit_breaker_threshold: Consecutive failures before disabling instance
        """
        if not instances:
            raise ValueError("Load balancer requires at least one instance")

        self.instances = instances
        self.strategy = strategy
        self._name = name
        self.health_check_interval = health_check_interval
        self.circuit_breaker_threshold = circuit_breaker_threshold

        # Round robin state
        self._rr_index = 0
        self._rr_lock = asyncio.Lock()

        # Weighted round robin state
        self._wrr_current_weight = 0
        self._wrr_index = 0

        # Health check task
        self._health_check_task: asyncio.Task | None = None

    @property
    def name(self) -> str:
        """Router name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Combined capabilities of all instances."""
        caps = set()
        for instance in self.instances:
            caps.update(instance.agent.capabilities)
        return list(caps)

    async def start_health_checks(self) -> None:
        """Start background health check task."""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self) -> None:
        """Stop background health check task."""
        if self._health_check_task:
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task
            self._health_check_task = None

    async def _health_check_loop(self) -> None:
        """Background loop for checking instance health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_instance_health()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue health checks
                pass

    async def _check_instance_health(self) -> None:
        """Check health of all instances."""
        for instance in self.instances:
            # Check error rate
            if instance.metrics.error_rate > 0.5 and instance.metrics.total_requests > 10:
                # High error rate, consider disabling
                if len(instance.metrics.errors) >= self.circuit_breaker_threshold:
                    instance.enabled = False

            # Re-enable if error rate improves
            if not instance.enabled and instance.metrics.error_rate < 0.2:
                instance.enabled = True
                instance.metrics.errors.clear()

    async def process(self, message: Message) -> Message:
        """Route message to best available instance.

        Args:
            message: Input message

        Returns:
            Response from selected instance

        Raises:
            LoadBalancerError: If no instances are available
            Exception: If selected instance fails
        """
        # Select instance
        instance = await self._select_instance()

        if instance is None:
            raise LoadBalancerError("No available instances to handle request")

        # Update metrics
        instance.metrics.active_requests += 1
        instance.metrics.total_requests += 1
        instance.metrics.last_request_time = time.time()

        start_time = time.time()

        try:
            # Process request
            response = await instance.agent.process(message)

            # Record success
            elapsed = time.time() - start_time
            instance.metrics.successful_requests += 1
            instance.metrics.total_response_time += elapsed

            return response

        except Exception as e:
            # Record failure
            instance.metrics.failed_requests += 1
            instance.metrics.errors.append(str(e))

            # Trim error list to recent errors
            if len(instance.metrics.errors) > self.circuit_breaker_threshold:
                instance.metrics.errors = instance.metrics.errors[-self.circuit_breaker_threshold :]

            raise

        finally:
            # Always decrement active requests
            instance.metrics.active_requests -= 1

    async def _select_instance(self) -> AgentInstance | None:
        """Select best instance based on strategy.

        Returns:
            Selected instance or None if no instances available
        """
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._select_round_robin()
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._select_least_connections()
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._select_least_response_time()
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin()
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._select_random()
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    async def _select_round_robin(self) -> AgentInstance | None:
        """Select next instance in round-robin order."""
        async with self._rr_lock:
            available = [i for i in self.instances if i.can_accept_request]

            if not available:
                return None

            # Find next available instance
            attempts = 0
            while attempts < len(self.instances):
                instance = self.instances[self._rr_index % len(self.instances)]
                self._rr_index += 1

                if instance.can_accept_request:
                    return instance

                attempts += 1

            return None

    def _select_least_connections(self) -> AgentInstance | None:
        """Select instance with fewest active connections."""
        available = [i for i in self.instances if i.can_accept_request]

        if not available:
            return None

        # Sort by active requests (ascending)
        available.sort(key=lambda x: x.metrics.active_requests)
        return available[0]

    def _select_least_response_time(self) -> AgentInstance | None:
        """Select instance with lowest average response time."""
        available = [i for i in self.instances if i.can_accept_request]

        if not available:
            return None

        # Sort by average response time (ascending)
        available.sort(key=lambda x: x.metrics.avg_response_time)
        return available[0]

    def _select_weighted_round_robin(self) -> AgentInstance | None:
        """Select instance based on weight using smooth weighted round-robin algorithm.

        SWRR ensures fair distribution based on weights by maintaining a running
        weight counter for each instance. Higher weights receive proportionally more requests.
        """
        available = [i for i in self.instances if i.can_accept_request]

        if not available:
            return None

        # Initialize current_weight attribute if not present
        for instance in available:
            if not hasattr(instance, '_current_weight'):
                instance._current_weight = 0

        # Smooth weighted round robin (SWRR) algorithm
        total_weight = sum(i.weight for i in available)

        # Increment each instance's current weight by its weight
        for instance in available:
            instance._current_weight += instance.weight

        # Select instance with highest current weight
        best_instance = max(available, key=lambda i: i._current_weight)

        # Reduce selected instance's current weight by total weight
        best_instance._current_weight -= total_weight

        return best_instance

    def _select_random(self) -> AgentInstance | None:
        """Select random available instance."""
        available = [i for i in self.instances if i.can_accept_request]

        if not available:
            return None

        return random.choice(available)

    def add_instance(self, instance: AgentInstance) -> None:
        """Add an instance to the load balancer.

        Args:
            instance: Instance to add
        """
        self.instances.append(instance)

    def remove_instance(self, agent_name: str) -> bool:
        """Remove an instance from the load balancer.

        Args:
            agent_name: Name of agent instance to remove

        Returns:
            True if instance was removed, False if not found
        """
        for i, instance in enumerate(self.instances):
            if instance.name == agent_name:
                self.instances.pop(i)
                return True
        return False

    def get_instance(self, agent_name: str) -> AgentInstance | None:
        """Get instance by agent name.

        Args:
            agent_name: Name of agent instance

        Returns:
            Instance or None if not found
        """
        for instance in self.instances:
            if instance.name == agent_name:
                return instance
        return None

    def get_statistics(self) -> dict[str, Any]:
        """Get load balancer statistics.

        Returns:
            Dictionary with statistics for all instances
        """
        return {
            "total_instances": len(self.instances),
            "enabled_instances": sum(1 for i in self.instances if i.enabled),
            "disabled_instances": sum(1 for i in self.instances if not i.enabled),
            "strategy": self.strategy.value,
            "total_active_requests": sum(i.metrics.active_requests for i in self.instances),
            "total_requests": sum(i.metrics.total_requests for i in self.instances),
            "overall_success_rate": self._calculate_overall_success_rate(),
            "instances": [
                {
                    "name": i.name,
                    "enabled": i.enabled,
                    "weight": i.weight,
                    "load_factor": i.load_factor,
                    "active_requests": i.metrics.active_requests,
                    "total_requests": i.metrics.total_requests,
                    "success_rate": i.metrics.success_rate,
                    "avg_response_time": i.metrics.avg_response_time,
                }
                for i in self.instances
            ],
        }

    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all instances."""
        total_requests = sum(i.metrics.total_requests for i in self.instances)
        if total_requests == 0:
            return 1.0

        total_successful = sum(i.metrics.successful_requests for i in self.instances)
        return total_successful / total_requests
