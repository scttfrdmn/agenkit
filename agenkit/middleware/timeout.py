"""Timeout middleware for preventing long-running requests from blocking resources."""

import asyncio
import time
import warnings
from dataclasses import dataclass, field

from agenkit.interfaces import Agent, Message


@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior.

    Note: As of v0.50.0, timeout values are specified in milliseconds using
    timeout_ms. The old 'timeout' parameter (in seconds) is deprecated and
    will be removed in v0.51.0.
    """

    timeout_ms: int = 30000  # Default request timeout in milliseconds
    method_timeouts_ms: dict[str, int] | None = None  # Method-specific timeouts in milliseconds

    # Deprecated - will be removed in v0.51.0
    timeout: float | None = field(default=None, repr=False)  # Deprecated: use timeout_ms
    method_timeouts: dict[str, float] | None = field(default=None, repr=False)  # Deprecated

    def __post_init__(self):
        """Validate configuration and handle deprecated parameters."""
        # Handle deprecated 'timeout' parameter
        if self.timeout is not None:
            warnings.warn(
                "The 'timeout' parameter (in seconds) is deprecated and will be removed in v0.51.0. "
                "Use 'timeout_ms' (in milliseconds) instead. "
                f"To migrate: timeout_ms={int(self.timeout * 1000)}",
                DeprecationWarning,
                stacklevel=3
            )
            # Convert seconds to milliseconds if timeout_ms not explicitly set
            if self.timeout_ms == 30000:  # Default value
                self.timeout_ms = int(self.timeout * 1000)

        # Handle deprecated 'method_timeouts' parameter
        if self.method_timeouts is not None:
            warnings.warn(
                "The 'method_timeouts' parameter (in seconds) is deprecated and will be removed in v0.51.0. "
                "Use 'method_timeouts_ms' (in milliseconds) instead.",
                DeprecationWarning,
                stacklevel=3
            )
            if self.method_timeouts_ms is None:
                # Convert all method timeouts from seconds to milliseconds
                self.method_timeouts_ms = {
                    method: int(timeout_s * 1000)
                    for method, timeout_s in self.method_timeouts.items()
                }

        # Validate timeout_ms
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")

        # Validate method_timeouts_ms
        if self.method_timeouts_ms:
            for method, method_timeout_ms in self.method_timeouts_ms.items():
                if method_timeout_ms <= 0:
                    raise ValueError(f"timeout_ms for method '{method}' must be positive")


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

        # Create agent with 10-second timeout (10000ms)
        agent = MyAgent()
        timeout_agent = TimeoutDecorator(
            agent,
            TimeoutConfig(timeout_ms=10000)
        )

        try:
            result = await timeout_agent.process(message)
        except TimeoutError:
            print("Request timed out after 10000ms")
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

    def _get_timeout_for_message(self, message: Message) -> float:
        """Get the timeout for a specific message.

        Checks message metadata for 'method' or 'operation' field to determine
        the operation type, then returns the method-specific timeout if configured,
        otherwise returns the default timeout.

        Args:
            message: The message to determine timeout for

        Returns:
            Timeout in seconds (for asyncio.wait_for compatibility)
        """
        # Get timeout in milliseconds
        timeout_ms = self._config.timeout_ms

        if self._config.method_timeouts_ms:
            # Try to determine method from message metadata
            method = message.metadata.get("method") or message.metadata.get("operation", "process")
            # Return method-specific timeout if configured, otherwise default
            timeout_ms = self._config.method_timeouts_ms.get(method, timeout_ms)

        # Convert milliseconds to seconds for asyncio.wait_for
        return timeout_ms / 1000.0

    async def process(self, message: Message) -> Message:
        """Process a message with timeout protection.

        The timeout can be configured per-method by setting method_timeouts in the config.
        The method is determined from the message metadata 'method' or 'operation' field,
        defaulting to 'process' if not specified.

        Args:
            message: The input message

        Returns:
            The response message from the agent

        Raises:
            TimeoutError: If the request exceeds the configured timeout
            Exception: Any other exception raised by the underlying agent
        """
        start_time = time.time()

        # Get timeout for this specific message/method
        timeout = self._get_timeout_for_message(message)

        try:
            # Use asyncio.wait_for to implement timeout
            result = await asyncio.wait_for(self._agent.process(message), timeout=timeout)

            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_success(duration)

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_timeout(duration)

            timeout_ms = int(timeout * 1000)
            raise TimeoutError(f"Request to agent '{self.name}' timed out after {timeout_ms}ms")

        except Exception:
            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_failure(duration)

            raise

    async def stream(self, message: Message):
        """Stream responses with timeout protection.

        Note: Streaming operations apply the timeout to the entire stream.
        If the complete stream doesn't finish within the timeout, it will be cancelled.

        The timeout can be configured per-method by setting method_timeouts in the config,
        using 'stream' as the method name.

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

        # Get timeout for this specific message/method (stream operations)
        timeout = self._get_timeout_for_message(message)

        async def stream_with_timeout():
            """Helper to wrap the streaming operation."""
            async for chunk in self._agent.stream(message):
                yield chunk

        try:
            # Python 3.10 compatible timeout for streaming
            # Create a task for the streaming operation
            try:
                async for chunk in stream_with_timeout():
                    # Check if we've exceeded timeout
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        raise asyncio.TimeoutError()
                    yield chunk

                duration = time.time() - start_time
                async with self._lock:
                    self._metrics.record_success(duration)

            except asyncio.TimeoutError:
                duration = time.time() - start_time
                async with self._lock:
                    self._metrics.record_timeout(duration)

                timeout_ms = int(timeout * 1000)
                raise TimeoutError(
                    f"Streaming request to agent '{self.name}' timed out after {timeout_ms}ms"
                )

        except TimeoutError:
            # Re-raise our custom TimeoutError
            raise

        except Exception:
            duration = time.time() - start_time
            async with self._lock:
                self._metrics.record_failure(duration)

            raise
