"""Retry middleware with exponential backoff."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from agenkit.interfaces import Agent, Message


class MaxRetriesExceededError(Exception):
    """Raised when maximum retry attempts are exhausted."""

    def __init__(self, message: str, attempts: int):
        """Initialize error.

        Args:
            message: Error message
            attempts: Number of attempts made
        """
        super().__init__(message)
        self.attempts = attempts


@dataclass
class RetryMetrics:
    """Metrics for retry middleware."""

    total_attempts: int = 0
    """Total number of requests (including retries)."""

    successful_first_attempt: int = 0
    """Number of requests that succeeded on first try."""

    successful_on_retry: int = 0
    """Number of requests that succeeded after retry."""

    failed_after_retries: int = 0
    """Number of requests that failed after all retries."""

    total_retries: int = 0
    """Total number of retry attempts across all requests."""


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 0.1 = 100ms)
        max_delay: Maximum delay in seconds (default: 10.0)
        multiplier: Backoff multiplier for exponential backoff (default: 2.0)
        should_retry: Optional function to determine if error should be retried
    """

    max_retries: int = 3
    initial_delay: float = 0.1  # 100ms
    max_delay: float = 10.0  # 10 seconds
    multiplier: float = 2.0
    should_retry: Callable[[Exception], bool] | None = None

    def __post_init__(self):
        """Validate configuration."""
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.multiplier <= 1.0:
            raise ValueError("multiplier must be > 1.0")


class RetryDecorator(Agent):
    """Agent decorator that adds retry logic with exponential backoff."""

    def __init__(self, agent: Agent, config: RetryConfig | None = None):
        """Initialize retry decorator.

        Args:
            agent: The agent to wrap
            config: Retry configuration (uses defaults if not provided)
        """
        self._agent = agent
        self._config = config or RetryConfig()
        self._metrics = RetryMetrics()

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def metrics(self) -> RetryMetrics:
        """Return current retry metrics."""
        return self._metrics

    async def process(self, message: Message) -> Message:
        """Process message with retry logic.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            MaxRetriesExceededError: If all retry attempts fail
            Exception: For non-retryable errors
        """
        last_error: Exception | None = None
        backoff = self._config.initial_delay

        for attempt in range(1, self._config.max_retries + 1):
            # Track attempt
            self._metrics.total_attempts += 1

            try:
                response = await self._agent.process(message)

                # Track success
                if attempt == 1:
                    self._metrics.successful_first_attempt += 1
                else:
                    self._metrics.successful_on_retry += 1

                return response

            except Exception as e:
                last_error = e

                # Check if we should retry this error
                if self._config.should_retry and not self._config.should_retry(e):
                    self._metrics.failed_after_retries += 1
                    raise Exception(f"Non-retryable error: {e}") from e

                # Don't sleep after last attempt
                if attempt == self._config.max_retries:
                    break

                # Track retry
                self._metrics.total_retries += 1

                # Exponential backoff
                await asyncio.sleep(backoff)
                backoff = min(backoff * self._config.multiplier, self._config.max_delay)

        # All attempts failed
        self._metrics.failed_after_retries += 1
        raise MaxRetriesExceededError(
            f"Max retry attempts ({self._config.max_retries}) exceeded: {last_error}",
            attempts=self._config.max_retries,
        ) from last_error
