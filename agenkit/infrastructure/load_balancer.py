"""Load balancing for distributing requests across multiple agents.

Provides multiple load balancing strategies for production deployments:
- Round Robin: Simple rotation through agents
- Least Connections: Route to agent with fewest active requests
- Weighted Round Robin: Distribute based on agent weights
- Random: Random selection (useful for testing)

Features:
- Automatic health checking
- Failover on agent failure
- Metrics tracking
- Thread-safe for concurrent requests
"""

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agenkit.interfaces import Agent, Message


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"


@dataclass
class AgentBackend:
    """Backend agent with metadata."""

    agent: Agent
    weight: int = 1  # For weighted strategies
    healthy: bool = True
    active_connections: int = 0
    total_requests: int = 0
    total_failures: int = 0
    last_health_check: float | None = None


@dataclass
class LoadBalancerConfig:
    """Configuration for load balancer."""

    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    health_check_interval: float = 30.0  # seconds
    health_check_timeout: float = 5.0  # seconds
    failure_threshold: int = 3  # Consecutive failures before marking unhealthy
    success_threshold: int = 2  # Consecutive successes to mark healthy again
    enable_failover: bool = True  # Try next agent on failure


@dataclass
class LoadBalancerMetrics:
    """Metrics for load balancer."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    failover_attempts: int = 0
    backend_health_changes: dict[str, int] = field(default_factory=dict)


class LoadBalancer(Agent):
    """Load balancer for distributing requests across multiple agents.

    Example:
        ```python
        agents = [
            OpenAILLM("gpt-4", api_key="..."),
            OpenAILLM("gpt-4", api_key="..."),  # Second instance
            ClaudeLLM("claude-3", api_key="..."),  # Fallback
        ]

        balancer = LoadBalancer(
            agents,
            config=LoadBalancerConfig(
                strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
                enable_failover=True,
            )
        )

        response = await balancer.process(message)
        ```
    """

    def __init__(
        self,
        agents: list[Agent],
        config: LoadBalancerConfig | None = None,
        weights: list[int] | None = None,
    ):
        """Initialize load balancer.

        Args:
            agents: List of backend agents
            config: Load balancer configuration
            weights: Optional weights for weighted strategies (defaults to 1 for all)

        Raises:
            ValueError: If agents list is empty or weights don't match agents
        """
        if not agents:
            raise ValueError("At least one agent required")

        self._config = config or LoadBalancerConfig()
        self._metrics = LoadBalancerMetrics()

        # Initialize backends
        if weights is None:
            weights = [1] * len(agents)
        elif len(weights) != len(agents):
            raise ValueError(
                f"Weights length ({len(weights)}) must match agents length ({len(agents)})"
            )

        self._backends = [
            AgentBackend(agent=agent, weight=weight)
            for agent, weight in zip(agents, weights, strict=False)
        ]

        # State for round-robin
        self._current_index = 0
        self._lock = asyncio.Lock()

        # Health check task
        self._health_check_task: asyncio.Task | None = None
        self._should_stop = False

    @property
    def name(self) -> str:
        """Return load balancer name."""
        return f"LoadBalancer({len(self._backends)} backends)"

    @property
    def capabilities(self) -> list[str]:
        """Return union of all backend capabilities."""
        all_caps = set()
        for backend in self._backends:
            all_caps.update(backend.agent.capabilities)
        return list(all_caps)

    @property
    def metrics(self) -> LoadBalancerMetrics:
        """Return current metrics."""
        return self._metrics

    def get_backend_stats(self) -> list[dict[str, Any]]:
        """Get statistics for all backends.

        Returns:
            List of backend statistics dictionaries
        """
        return [
            {
                "name": backend.agent.name,
                "healthy": backend.healthy,
                "weight": backend.weight,
                "active_connections": backend.active_connections,
                "total_requests": backend.total_requests,
                "total_failures": backend.total_failures,
                "last_health_check": backend.last_health_check,
            }
            for backend in self._backends
        ]

    async def start_health_checks(self) -> None:
        """Start background health check task."""
        if self._health_check_task is not None:
            return

        self._should_stop = False
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self) -> None:
        """Stop background health check task."""
        if self._health_check_task is None:
            return

        self._should_stop = True
        await self._health_check_task
        self._health_check_task = None

    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while not self._should_stop:
            await asyncio.sleep(self._config.health_check_interval)

            for backend in self._backends:
                try:
                    # Simple health check: test if agent responds
                    test_message = Message(role="system", content="health_check")

                    async with asyncio.timeout(self._config.health_check_timeout):
                        await backend.agent.process(test_message)

                    # Success - mark healthy if was unhealthy
                    if not backend.healthy:
                        backend.healthy = True
                        self._track_health_change(backend.agent.name, "recovered")

                except Exception:
                    # Failure - increment failure count
                    backend.total_failures += 1

                    # Mark unhealthy if exceeded threshold
                    if backend.healthy and backend.total_failures >= self._config.failure_threshold:
                        backend.healthy = False
                        self._track_health_change(backend.agent.name, "unhealthy")

                backend.last_health_check = time.time()

    def _track_health_change(self, agent_name: str, change_type: str) -> None:
        """Track backend health state changes."""
        key = f"{agent_name}:{change_type}"
        self._metrics.backend_health_changes[key] = (
            self._metrics.backend_health_changes.get(key, 0) + 1
        )

    async def _select_backend(self) -> AgentBackend | None:
        """Select a backend based on configured strategy.

        Returns:
            Selected backend or None if all unhealthy
        """
        healthy_backends = [b for b in self._backends if b.healthy]

        if not healthy_backends:
            return None

        strategy = self._config.strategy

        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._select_round_robin(healthy_backends)

        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._select_least_connections(healthy_backends)

        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._select_weighted_round_robin(healthy_backends)

        elif strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(healthy_backends)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    async def _select_round_robin(self, backends: list[AgentBackend]) -> AgentBackend:
        """Select backend using round-robin."""
        async with self._lock:
            # Find next healthy backend in rotation
            for _ in range(len(backends)):
                self._current_index = (self._current_index + 1) % len(self._backends)
                if self._backends[self._current_index] in backends:
                    return self._backends[self._current_index]

            # Fallback to first healthy
            return backends[0]

    def _select_least_connections(self, backends: list[AgentBackend]) -> AgentBackend:
        """Select backend with least active connections."""
        return min(backends, key=lambda b: b.active_connections)

    async def _select_weighted_round_robin(self, backends: list[AgentBackend]) -> AgentBackend:
        """Select backend using weighted round-robin.

        Higher weight means more requests. Weight=2 gets twice as many requests as weight=1.
        """
        # Calculate total weight
        total_weight = sum(b.weight for b in backends)

        # Generate weighted list
        weighted_backends: list[AgentBackend] = []
        for backend in backends:
            weighted_backends.extend([backend] * backend.weight)

        # Round-robin through weighted list
        async with self._lock:
            self._current_index = (self._current_index + 1) % len(weighted_backends)
            return weighted_backends[self._current_index]

    async def process(self, message: Message) -> Message:
        """Process message using load-balanced backend.

        Args:
            message: Input message

        Returns:
            Response from selected backend

        Raises:
            Exception: If all backends fail or are unhealthy
        """
        self._metrics.total_requests += 1

        # Try backends until one succeeds or all fail
        attempted_backends: set[str] = set()

        while True:
            # Select backend
            backend = await self._select_backend()

            if backend is None:
                raise Exception("All backends unhealthy")

            # Avoid retrying same backend
            if backend.agent.name in attempted_backends:
                if not self._config.enable_failover or len(attempted_backends) >= len(
                    self._backends
                ):
                    raise Exception(f"All backends attempted: {attempted_backends}")

                # Try next backend
                continue

            attempted_backends.add(backend.agent.name)

            # Track request
            backend.active_connections += 1
            backend.total_requests += 1

            try:
                # Process message
                response = await backend.agent.process(message)

                # Success
                self._metrics.successful_requests += 1
                return response

            except Exception as e:
                # Failure
                backend.total_failures += 1
                self._metrics.failed_requests += 1

                # Check if should mark unhealthy
                if backend.total_failures >= self._config.failure_threshold:
                    backend.healthy = False
                    self._track_health_change(backend.agent.name, "unhealthy")

                # Try failover if enabled
                if self._config.enable_failover and len(attempted_backends) < len(self._backends):
                    self._metrics.failover_attempts += 1
                    continue

                # No more failover, re-raise
                raise Exception(f"Backend {backend.agent.name} failed: {e}") from e

            finally:
                backend.active_connections -= 1
