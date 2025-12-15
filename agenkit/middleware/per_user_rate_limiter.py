"""
Per-user rate limiting middleware with token bucket algorithm.

Provides fine-grained rate limiting per user/client while also supporting
global rate limits to protect system resources.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agenkit.interfaces import Agent, Message


@dataclass
class PerUserRateLimiterConfig:
    """Configuration for per-user rate limiter."""

    # Per-user limits
    user_rate: float = 10.0  # Requests per second per user
    user_capacity: int = 10  # Burst capacity per user

    # Global limits (optional, set to None to disable)
    global_rate: float | None = 100.0  # Total requests per second across all users
    global_capacity: int | None = 100  # Total burst capacity

    # Identifier function (extracts user ID from message)
    identifier_fn: Callable[[Message], str] | None = None

    # Cleanup settings
    cleanup_interval: int = 300  # Clean up inactive users every 5 minutes
    inactive_threshold: int = 600  # Consider user inactive after 10 minutes

    def __post_init__(self):
        """Validate configuration."""
        if self.user_rate <= 0:
            raise ValueError("user_rate must be positive")
        if self.user_capacity < 1:
            raise ValueError("user_capacity must be at least 1")
        if self.global_rate is not None and self.global_rate <= 0:
            raise ValueError("global_rate must be positive or None")
        if self.global_capacity is not None and self.global_capacity < 1:
            raise ValueError("global_capacity must be at least 1")
        if self.cleanup_interval < 0:
            raise ValueError("cleanup_interval must be non-negative")
        if self.inactive_threshold < 0:
            raise ValueError("inactive_threshold must be non-negative")


class PerUserRateLimitError(Exception):
    """Raised when per-user rate limit is exceeded."""

    def __init__(self, user_id: str, message: str):
        """
        Initialize rate limit error.

        Args:
            user_id: User identifier that exceeded the limit
            message: Error message
        """
        self.user_id = user_id
        super().__init__(message)


class GlobalRateLimitError(Exception):
    """Raised when global rate limit is exceeded."""

    pass


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    rate: float  # Tokens per second
    capacity: int  # Maximum tokens
    tokens: float = field(init=False)  # Current tokens
    last_update: float = field(init=False)  # Last refill timestamp

    def __post_init__(self):
        """Initialize bucket with full capacity."""
        self.tokens = float(self.capacity)
        self.last_update = time.time()

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.tokens + tokens_to_add, self.capacity)
        self.last_update = now

    def try_acquire(self, tokens_needed: int = 1) -> bool:
        """
        Try to acquire tokens from bucket.

        Args:
            tokens_needed: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        self.refill()
        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True
        return False

    def time_until_available(self, tokens_needed: int = 1) -> float:
        """
        Calculate time until tokens will be available.

        Args:
            tokens_needed: Number of tokens needed

        Returns:
            Time in seconds until tokens will be available
        """
        self.refill()
        if self.tokens >= tokens_needed:
            return 0.0

        tokens_deficit = tokens_needed - self.tokens
        return tokens_deficit / self.rate


@dataclass
class PerUserRateLimiterMetrics:
    """Metrics for per-user rate limiter."""

    total_requests: int = 0
    allowed_requests: int = 0
    rejected_user_limit: int = 0  # Rejected due to per-user limit
    rejected_global_limit: int = 0  # Rejected due to global limit
    active_users: int = 0  # Current number of tracked users
    total_users_seen: int = 0  # Total unique users seen
    total_wait_time: float = 0.0


class PerUserRateLimiterDecorator(Agent):
    """
    Agent decorator implementing per-user rate limiting.

    Provides fine-grained rate limiting per user/client with optional
    global rate limits. Uses token bucket algorithm for smooth rate
    limiting with burst capacity.

    Features:
    - Per-user rate limits (separate bucket per user)
    - Optional global rate limits (protect system resources)
    - Flexible user identification (user_id, api_key, ip_address)
    - Automatic cleanup of inactive users
    - Integration with audit logging

    Example:
        ```python
        from agenkit.middleware import PerUserRateLimiterDecorator, PerUserRateLimiterConfig

        # Extract user ID from message metadata
        def get_user_id(message):
            return message.metadata.get("user_id", "anonymous")

        config = PerUserRateLimiterConfig(
            user_rate=10.0,  # 10 requests/sec per user
            user_capacity=20,  # Burst of 20
            global_rate=100.0,  # 100 requests/sec total
            global_capacity=200,  # Global burst of 200
            identifier_fn=get_user_id,
        )

        agent = MyAgent()
        limited_agent = PerUserRateLimiterDecorator(agent, config)

        # Message with user ID
        message = Message(content="Hello", metadata={"user_id": "alice"})
        response = await limited_agent.process(message)
        ```
    """

    def __init__(
        self,
        agent: Agent,
        config: PerUserRateLimiterConfig | None = None,
        audit_logger=None,
    ):
        """
        Initialize per-user rate limiter.

        Args:
            agent: The agent to wrap
            config: Rate limiter configuration
            audit_logger: Optional audit logger for logging violations
        """
        self._agent = agent
        self._config = config or PerUserRateLimiterConfig()
        self._audit_logger = audit_logger

        # Per-user token buckets
        self._user_buckets: dict[str, TokenBucket] = {}
        self._user_last_seen: dict[str, float] = {}

        # Global token bucket (if enabled)
        if self._config.global_rate is not None and self._config.global_capacity is not None:
            self._global_bucket = TokenBucket(
                rate=self._config.global_rate,
                capacity=self._config.global_capacity,
            )
        else:
            self._global_bucket = None

        # Lock for thread safety
        self._lock = asyncio.Lock()

        # Metrics
        self._metrics = PerUserRateLimiterMetrics()

        # Start cleanup task
        self._cleanup_task = None
        if self._config.cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def metrics(self) -> PerUserRateLimiterMetrics:
        """Return rate limiter metrics."""
        return self._metrics

    def _get_user_id(self, message: Message) -> str:
        """
        Extract user identifier from message.

        Args:
            message: The message to extract user ID from

        Returns:
            User identifier string
        """
        if self._config.identifier_fn:
            return self._config.identifier_fn(message)

        # Default: try metadata fields
        if hasattr(message, "metadata") and message.metadata:
            # Try common identifier fields
            for field in ["user_id", "api_key", "client_id", "ip_address"]:
                if field in message.metadata:
                    return str(message.metadata[field])

        # Fallback to anonymous
        return "anonymous"

    def _get_or_create_user_bucket(self, user_id: str) -> TokenBucket:
        """
        Get or create token bucket for user.

        Args:
            user_id: User identifier

        Returns:
            Token bucket for the user
        """
        if user_id not in self._user_buckets:
            self._user_buckets[user_id] = TokenBucket(
                rate=self._config.user_rate,
                capacity=self._config.user_capacity,
            )
            self._metrics.total_users_seen += 1

        self._user_last_seen[user_id] = time.time()
        self._metrics.active_users = len(self._user_buckets)

        return self._user_buckets[user_id]

    async def _cleanup_loop(self) -> None:
        """Background task to clean up inactive user buckets."""
        try:
            while True:
                await asyncio.sleep(self._config.cleanup_interval)

                async with self._lock:
                    now = time.time()
                    inactive_users = [
                        user_id
                        for user_id, last_seen in self._user_last_seen.items()
                        if now - last_seen > self._config.inactive_threshold
                    ]

                    for user_id in inactive_users:
                        del self._user_buckets[user_id]
                        del self._user_last_seen[user_id]

                    if inactive_users:
                        self._metrics.active_users = len(self._user_buckets)

        except asyncio.CancelledError:
            pass

    async def process(self, message: Message) -> Message:
        """
        Process message with per-user rate limiting.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            PerUserRateLimitError: If per-user rate limit is exceeded
            GlobalRateLimitError: If global rate limit is exceeded
            Exception: If underlying agent raises an exception
        """
        self._metrics.total_requests += 1

        # Extract user identifier
        user_id = self._get_user_id(message)

        # Check global limit first (if enabled)
        if self._global_bucket is not None:
            async with self._lock:
                if not self._global_bucket.try_acquire():
                    self._metrics.rejected_global_limit += 1

                    # Log to audit logger if available
                    if self._audit_logger:
                        self._audit_logger.log_rate_limit_exceeded(
                            client_id=user_id,
                            endpoint="global",
                            limit=int(self._config.global_rate or 0),
                            window="1s",
                        )

                    raise GlobalRateLimitError(
                        f"Global rate limit exceeded: {self._config.global_rate} requests/sec"
                    )

        # Check per-user limit
        async with self._lock:
            user_bucket = self._get_or_create_user_bucket(user_id)

            if not user_bucket.try_acquire():
                self._metrics.rejected_user_limit += 1

                # Log to audit logger if available
                if self._audit_logger:
                    self._audit_logger.log_rate_limit_exceeded(
                        client_id=user_id,
                        endpoint=f"user:{user_id}",
                        limit=int(self._config.user_rate),
                        window="1s",
                    )

                wait_time = user_bucket.time_until_available()
                raise PerUserRateLimitError(
                    user_id=user_id,
                    message=f"Rate limit exceeded for user '{user_id}': "
                    f"{self._config.user_rate} requests/sec "
                    f"(retry after {wait_time:.2f}s)",
                )

        # Rate limit passed - process request
        self._metrics.allowed_requests += 1
        return await self._agent.process(message)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# Convenience function for common use cases
def default_identifier(message: Message) -> str:
    """
    Default identifier function that tries common fields.

    Args:
        message: The message to extract identifier from

    Returns:
        User identifier string
    """
    if hasattr(message, "metadata") and message.metadata:
        # Try common identifier fields in order of preference
        for field in ["user_id", "api_key", "client_id", "ip_address"]:
            if field in message.metadata:
                return str(message.metadata[field])

    return "anonymous"
