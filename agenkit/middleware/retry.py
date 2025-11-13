"""Retry middleware with exponential backoff."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from agenkit.interfaces import Agent, Message


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_backoff: float = 1.0  # seconds
    max_backoff: float = 30.0  # seconds
    backoff_multiplier: float = 2.0
    should_retry: Callable[[Exception], bool] | None = None

    def __post_init__(self):
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_backoff <= 0:
            raise ValueError("initial_backoff must be positive")
        if self.max_backoff < self.initial_backoff:
            raise ValueError("max_backoff must be >= initial_backoff")
        if self.backoff_multiplier <= 1.0:
            raise ValueError("backoff_multiplier must be > 1.0")


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

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    async def process(self, message: Message) -> Message:
        """Process message with retry logic.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            Exception: If all retry attempts fail
        """
        last_error: Exception | None = None
        backoff = self._config.initial_backoff

        for attempt in range(1, self._config.max_attempts + 1):
            try:
                return await self._agent.process(message)
            except Exception as e:
                last_error = e

                # Check if we should retry this error
                if self._config.should_retry and not self._config.should_retry(e):
                    raise Exception(f"Non-retryable error: {e}") from e

                # Don't sleep after last attempt
                if attempt == self._config.max_attempts:
                    break

                # Exponential backoff
                await asyncio.sleep(backoff)
                backoff = min(backoff * self._config.backoff_multiplier, self._config.max_backoff)

        # All attempts failed
        raise Exception(
            f"Max retry attempts ({self._config.max_attempts}) exceeded: {last_error}"
        ) from last_error
