"""Timeout middleware for preventing long-running requests from blocking resources."""

import asyncio
import time
from dataclasses import dataclass

from agenkit.interfaces import Agent, Message


@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior."""

    timeout: float = 30.0  # Request timeout in seconds

    def __post_init__(self):
        """Validate configuration."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


class TimeoutError(Exception):
    """Raised when a request exceeds the configured timeout."""

    pass


@dataclass
class TimeoutMetrics:
    """Metrics for timeout middleware."""

    total_requests: int = 0
    successful_requests: int = 0
    timed_out_requests: int = 0
    failed_requests: int = 0  # Failed for reasons other than timeout
    total_timeout_duration: float = 0.0  # Sum of all timeout durations
    min_duration: float | None = None
    max_duration: float | None = None
    avg_duration: float = 0.0

    def record_success(self, duration: float):
        """Record a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self._update_duration_stats(duration)

    def record_timeout(self, duration: float):
        """Record a timed-out request."""
        self.total_requests += 1
        self.timed_out_requests += 1
        self._update_duration_stats(duration)

    def record_failure(self, duration: float):
        """Record a failed request (non-timeout error)."""
        self.total_requests += 1
        self.failed_requests += 1
        self._update_duration_stats(duration)

    def _update_duration_stats(self, duration: float):
        """Update duration statistics."""
        self.total_timeout_duration += duration

        if self.min_duration is None or duration < self.min_duration:
            self.min_duration = duration

        if self.max_duration is None or duration > self.max_duration:
            self.max_duration = duration

        self.avg_duration = self.total_timeout_duration / self.total_requests


class TimeoutDecorator(Agent):
    """Agent decorator that implements timeout for request processing.

    The timeout middleware prevents long-running requests from blocking resources
    by cancelling them after a configured timeout period. This is essential for:

    - Protecting against hung requests or infinite loops
    - Ensuring predictable request latency
    - Preventing resource exhaustion from slow operations
    - Meeting SLA requirements

    Example:
        ```python
        from agenkit.middleware import TimeoutConfig, TimeoutDecorator, TimeoutError

        # Create agent with 10-second timeout
        agent = MyAgent()
        timeout_agent = TimeoutDecorator(
            agent,
            TimeoutConfig(timeout=10.0)
        )

        try:
            result = await timeout_agent.process(message)
        except TimeoutError:
            print("Request timed out after 10 seconds")
        ```
    """

    def __init__(self, agent: Agent, config: TimeoutConfig | None = None):
        """Initialize timeout decorator.

        Args:
            agent: The agent to wrap
            config: Timeout configuration (uses defaults if not provided)
        """
        self._agent = agent
        self._config = config or TimeoutConfig()
        self._metrics = TimeoutMetrics()
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return the capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def metrics(self) -> TimeoutMetrics:
        """Get current metrics."""
        return self._metrics

    async def process(self, message: Message) -> Message:
        """Process a message with timeout protection.

        Args:
            message: The input message

        Returns:
            The response message from the agent

        Raises:
            TimeoutError: If the request exceeds the configured timeout
            Exception: Any other exception raised by the underlying agent
        """
        start_time = time.time()

        try:
            # Use asyncio.wait_for to implement timeout
            result = await asyncio.wait_for(
                self._agent.process(message), timeout=self._config.timeout
            )

            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_success(duration)

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_timeout(duration)

            raise TimeoutError(
                f"Request to agent '{self.name}' timed out after {self._config.timeout}s"
            )

        except Exception:
            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_failure(duration)

            raise

    async def stream(self, message: Message):
        """Stream responses with timeout protection.

        Note: Streaming operations apply the timeout to the entire stream.
        If the complete stream doesn't finish within the timeout, it will be cancelled.

        Args:
            message: The input message

        Yields:
            Response messages from the agent

        Raises:
            TimeoutError: If the stream exceeds the configured timeout
            Exception: Any other exception raised by the underlying agent
        """
        if not hasattr(self._agent, "stream"):
            raise NotImplementedError(f"Agent '{self.name}' does not support streaming")

        start_time = time.time()

        async def stream_with_timeout():
            """Helper to wrap the streaming operation."""
            async for chunk in self._agent.stream(message):
                yield chunk

        try:
            # Use asyncio.timeout for the entire streaming operation
            async with asyncio.timeout(self._config.timeout):
                async for chunk in stream_with_timeout():
                    yield chunk

            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_success(duration)

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_timeout(duration)

            raise TimeoutError(
                f"Streaming request to agent '{self.name}' timed out after {self._config.timeout}s"
            )

        except Exception:
            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_failure(duration)

            raise
