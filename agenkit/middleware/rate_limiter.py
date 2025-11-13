"""Rate limiting middleware using token bucket algorithm."""

import asyncio
import time
from dataclasses import dataclass

from agenkit.interfaces import Agent, Message


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter behavior."""

    rate: float = 10.0  # Tokens per second
    capacity: int = 10  # Maximum burst capacity
    tokens_per_request: int = 1  # Tokens consumed per request

    def __post_init__(self):
        """Validate configuration."""
        if self.rate <= 0:
            raise ValueError("rate must be positive")
        if self.capacity < 1:
            raise ValueError("capacity must be at least 1")
        if self.tokens_per_request < 1:
            raise ValueError("tokens_per_request must be at least 1")
        if self.tokens_per_request > self.capacity:
            raise ValueError("tokens_per_request cannot exceed capacity")


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    pass


@dataclass
class RateLimiterMetrics:
    """Metrics for rate limiter."""

    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    total_wait_time: float = 0.0  # Total time spent waiting for tokens
    current_tokens: float = 0.0


class RateLimiterDecorator(Agent):
    """Agent decorator that implements rate limiting using token bucket algorithm.

    The token bucket algorithm allows for smooth rate limiting with burst capacity:
    - Tokens are added to the bucket at a constant rate
    - Each request consumes tokens from the bucket
    - If insufficient tokens are available, the request waits or is rejected
    - Burst capacity allows temporary spikes in traffic

    This is useful for:
    - Protecting downstream services from overload
    - Complying with API rate limits (e.g., OpenAI: 3500 RPM)
    - Fair resource allocation across tenants
    - Cost control
    """

    def __init__(
        self, agent: Agent, config: RateLimiterConfig | None = None
    ):
        """Initialize rate limiter decorator.

        Args:
            agent: The agent to wrap
            config: Rate limiter configuration (uses defaults if not provided)
        """
        self._agent = agent
        self._config = config or RateLimiterConfig()
        self._tokens = float(self._config.capacity)  # Start with full capacity
        self._last_update = time.time()
        self._lock = asyncio.Lock()
        self._metrics = RateLimiterMetrics(current_tokens=self._tokens)

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def metrics(self) -> RateLimiterMetrics:
        """Return rate limiter metrics."""
        return self._metrics

    async def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self._config.rate
        self._tokens = min(self._tokens + tokens_to_add, self._config.capacity)
        self._last_update = now

        # Update metrics
        self._metrics.current_tokens = self._tokens

    async def _acquire_tokens(
        self, tokens_needed: int, wait: bool = True
    ) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens_needed: Number of tokens to acquire
            wait: If True, wait for tokens; if False, return immediately

        Returns:
            True if tokens were acquired, False otherwise

        Raises:
            RateLimitError: If wait=False and insufficient tokens available
        """
        async with self._lock:
            await self._refill_tokens()

            if self._tokens >= tokens_needed:
                # Sufficient tokens available
                self._tokens -= tokens_needed
                self._metrics.current_tokens = self._tokens
                return True

            if not wait:
                # Insufficient tokens and not waiting
                raise RateLimitError(
                    f"Rate limit exceeded: need {tokens_needed} tokens, "
                    f"only {self._tokens:.2f} available"
                )

            # Calculate wait time for tokens
            tokens_deficit = tokens_needed - self._tokens
            wait_time = tokens_deficit / self._config.rate

        # Wait outside the lock to allow other operations
        await asyncio.sleep(wait_time)

        # Re-acquire lock and try again
        async with self._lock:
            await self._refill_tokens()

            if self._tokens >= tokens_needed:
                self._tokens -= tokens_needed
                self._metrics.current_tokens = self._tokens
                self._metrics.total_wait_time += wait_time
                return True

            # Should not happen, but handle defensively
            raise RateLimitError(
                f"Failed to acquire {tokens_needed} tokens after waiting"
            )

    async def process(self, message: Message) -> Message:
        """Process message with rate limiting.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            RateLimitError: If rate limit is exceeded and wait=False
            Exception: If underlying agent raises an exception
        """
        self._metrics.total_requests += 1

        # Acquire tokens
        try:
            await self._acquire_tokens(self._config.tokens_per_request, wait=True)
            self._metrics.allowed_requests += 1
        except RateLimitError:
            self._metrics.rejected_requests += 1
            raise

        # Process request
        return await self._agent.process(message)
