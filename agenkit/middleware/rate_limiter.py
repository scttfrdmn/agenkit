"""Rate limiting middleware using token bucket algorithm."""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from agenkit.interfaces import Agent, Message


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter behavior.

    Timeout values are specified in milliseconds.
    """

    rate: float = 10.0  # Tokens per second
    capacity: int = 10  # Maximum burst capacity
    tokens_per_request: int = 1  # Tokens consumed per request
    max_wait_ms: int | None = (
        None  # Maximum milliseconds to wait for tokens (None = wait indefinitely)
    )

    def __post_init__(self):
        """Validate configuration."""
        # Validate configuration
        if self.rate <= 0:
            raise ValueError("rate must be positive")
        if self.capacity < 1:
            raise ValueError("capacity must be at least 1")
        if self.tokens_per_request < 1:
            raise ValueError("tokens_per_request must be at least 1")
        if self.tokens_per_request > self.capacity:
            raise ValueError("tokens_per_request cannot exceed capacity")
        if self.max_wait_ms is not None and self.max_wait_ms <= 0:
            raise ValueError("max_wait_ms must be positive")


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

    def __init__(self, agent: Agent, config: RateLimiterConfig | None = None):
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

    async def _acquire_tokens(self, tokens_needed: int, wait: bool = True) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens_needed: Number of tokens to acquire
            wait: If True, wait for tokens; if False, return immediately

        Returns:
            True if tokens were acquired, False otherwise

        Raises:
            RateLimitError: If wait=False and insufficient tokens available
        """
        # Wait-and-retry loop. A single wait is not enough, for two independent
        # reasons, and the old code raised from a branch it labelled "should not
        # happen" when either bit:
        #
        # 1. _refill_tokens credits elapsed * rate from the wall clock, so a
        #    busy event loop can return from the sleep having credited
        #    marginally less than tokens_needed.
        # 2. The lock is released across the sleep, so a concurrent waiter can
        #    acquire it first and drain the tokens this one was waiting for --
        #    a lost wakeup. With capacity=1 and 8 concurrent callers this
        #    raised on every single run (#750), despite max_wait_ms being set.
        #
        # Re-checking instead of raising makes the outcome depend on the token
        # math rather than on scheduler order. max_wait_ms still bounds the
        # total, measured against cumulative wait so repeated short retries
        # cannot outlast the budget, so this cannot spin forever when the
        # configured rate genuinely cannot satisfy the request.
        total_waited = 0.0

        while True:
            async with self._lock:
                await self._refill_tokens()

                if self._tokens >= tokens_needed:
                    # Sufficient tokens available
                    self._tokens -= tokens_needed
                    self._metrics.current_tokens = self._tokens
                    if total_waited > 0:
                        self._metrics.total_wait_time += total_waited
                    return True

                if not wait:
                    # Insufficient tokens and not waiting
                    raise RateLimitError(
                        f"Rate limit exceeded: need {tokens_needed} tokens, "
                        f"only {self._tokens:.2f} available"
                    )

                # Calculate wait time for the outstanding deficit (in seconds
                # for asyncio.sleep).
                tokens_deficit = tokens_needed - self._tokens
                wait_time = tokens_deficit / self._config.rate

                # Check if the cumulative wait would exceed max_wait_ms.
                if self._config.max_wait_ms is not None:
                    max_wait_seconds = self._config.max_wait_ms / 1000.0
                    if total_waited + wait_time > max_wait_seconds:
                        wait_time_ms = int((total_waited + wait_time) * 1000)
                        raise RateLimitError(
                            f"Rate limit exceeded: would need to wait {wait_time_ms}ms "
                            f"for {tokens_needed} tokens, but max_wait_ms is "
                            f"{self._config.max_wait_ms}ms"
                        )

            # Wait outside the lock to allow other operations
            await asyncio.sleep(wait_time)
            total_waited += wait_time

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

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """Stream responses with rate limiting.

        Note: Rate limiting is applied once per stream() call, not per chunk.

        Args:
            message: Input message

        Yields:
            Response messages from agent

        Raises:
            RateLimitError: If rate limit is exceeded and wait=False
            NotImplementedError: If underlying agent doesn't support streaming
            Exception: If underlying agent raises an exception
        """
        self._metrics.total_requests += 1

        # Acquire tokens once for the stream
        try:
            await self._acquire_tokens(self._config.tokens_per_request, wait=True)
            self._metrics.allowed_requests += 1
        except RateLimitError:
            self._metrics.rejected_requests += 1
            raise

        # Stream from underlying agent
        async for chunk in self._agent.stream(message):
            yield chunk
