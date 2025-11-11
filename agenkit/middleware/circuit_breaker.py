"""Circuit breaker middleware for preventing cascading failures."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from agenkit.interfaces import Agent, Message


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds before attempting recovery
    success_threshold: int = 2  # Successful calls in half-open to close
    timeout: float = 30.0  # Request timeout in seconds

    def __post_init__(self):
        """Validate configuration."""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # Rejected due to open circuit
    state_changes: dict[str, int] = field(default_factory=dict)
    last_state_change: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED


class CircuitBreakerDecorator(Agent):
    """Agent decorator that implements circuit breaker pattern.

    The circuit breaker prevents cascading failures by failing fast when
    a service is unhealthy. It has three states:

    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, fail fast without calling agent
    - HALF_OPEN: Testing if service has recovered

    State transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN -> CLOSED: After success_threshold consecutive successes
    - HALF_OPEN -> OPEN: On any failure
    """

    def __init__(
        self, agent: Agent, config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize circuit breaker decorator.

        Args:
            agent: The agent to wrap
            config: Circuit breaker configuration (uses defaults if not provided)
        """
        self._agent = agent
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        self._metrics = CircuitBreakerMetrics()

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def state(self) -> CircuitState:
        """Return current circuit breaker state."""
        return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Return circuit breaker metrics."""
        return self._metrics

    async def _change_state(self, new_state: CircuitState) -> None:
        """Change circuit breaker state and update metrics.

        Args:
            new_state: New state to transition to
        """
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._metrics.current_state = new_state
            self._metrics.last_state_change = time.time()

            # Track state changes
            transition = f"{old_state.value}->{new_state.value}"
            self._metrics.state_changes[transition] = (
                self._metrics.state_changes.get(transition, 0) + 1
            )

    async def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset from OPEN to HALF_OPEN.

        Returns:
            True if recovery timeout has elapsed
        """
        if self._last_failure_time is None:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self._config.recovery_timeout

    async def _on_success(self) -> None:
        """Handle successful request."""
        self._metrics.successful_requests += 1

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                # Recovered! Close the circuit
                await self._change_state(CircuitState.CLOSED)
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed request."""
        self._metrics.failed_requests += 1
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery test, reopen circuit
            await self._change_state(CircuitState.OPEN)
            self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self._config.failure_threshold:
                # Too many failures, open circuit
                await self._change_state(CircuitState.OPEN)

    async def process(self, message: Message) -> Message:
        """Process message with circuit breaker protection.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            CircuitBreakerError: If circuit is open
            TimeoutError: If request exceeds timeout
            Exception: If underlying agent raises an exception
        """
        async with self._lock:
            self._metrics.total_requests += 1

            # Check if circuit is open
            if self._state == CircuitState.OPEN:
                # Check if we should attempt recovery
                if await self._should_attempt_reset():
                    await self._change_state(CircuitState.HALF_OPEN)
                    self._success_count = 0
                else:
                    # Still open, fail fast
                    self._metrics.rejected_requests += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN (failed {self._failure_count} times)"
                    )

        # Attempt request with timeout
        try:
            result = await asyncio.wait_for(
                self._agent.process(message), timeout=self._config.timeout
            )

            async with self._lock:
                await self._on_success()

            return result

        except asyncio.TimeoutError as e:
            async with self._lock:
                await self._on_failure()
            raise TimeoutError(
                f"Request exceeded timeout of {self._config.timeout}s"
            ) from e

        except Exception as e:
            async with self._lock:
                await self._on_failure()
            raise
