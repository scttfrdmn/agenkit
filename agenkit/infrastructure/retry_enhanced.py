"""Enhanced retry logic with advanced production features.

Extends the basic retry middleware with:
- Jitter to prevent thundering herd
- Per-error-type retry strategies
- Budget-aware retry (stop if cost exceeds threshold)
- Retry budgets (limit retries across all requests)
- Backpressure detection
"""

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agenkit.interfaces import Agent, Message


class JitterType(Enum):
    """Types of jitter for retry backoff."""

    NONE = "none"  # No jitter
    FULL = "full"  # Random between 0 and backoff
    EQUAL = "equal"  # Random between backoff/2 and backoff
    DECORRELATED = "decorrelated"  # Exponential with randomness


class ErrorClass(Enum):
    """Classification of errors for retry strategies."""

    TRANSIENT = "transient"  # Temporary, retry immediately
    RATE_LIMIT = "rate_limit"  # Rate limited, longer backoff
    TIMEOUT = "timeout"  # Timeout, may need longer timeout
    SERVER_ERROR = "server_error"  # Server issue, retry with backoff
    CLIENT_ERROR = "client_error"  # Client issue, don't retry
    UNKNOWN = "unknown"  # Unknown error, use default strategy


@dataclass
class ErrorStrategy:
    """Retry strategy for specific error class."""

    error_class: ErrorClass
    max_retries: int
    initial_delay: float
    max_delay: float
    multiplier: float
    should_retry: bool = True


@dataclass
class RetryBudget:
    """Budget for limiting retry costs."""

    max_cost: float = float("inf")  # Maximum cost allowed
    current_cost: float = 0.0  # Current cost accumulated
    max_retries_per_hour: int = 1000  # Limit retries per hour
    retry_count: int = 0  # Current retry count
    window_start: float = field(default_factory=time.time)


@dataclass
class EnhancedRetryConfig:
    """Configuration for enhanced retry behavior."""

    # Basic retry settings
    max_retries: int = 3
    initial_delay: float = 0.1
    max_delay: float = 10.0
    multiplier: float = 2.0

    # Jitter settings
    jitter_type: JitterType = JitterType.FULL
    jitter_min_ratio: float = 0.5  # For EQUAL jitter

    # Error-specific strategies
    error_strategies: dict[ErrorClass, ErrorStrategy] = field(default_factory=dict)
    error_classifier: Callable[[Exception], ErrorClass] | None = None

    # Budget settings
    enable_budget: bool = False
    cost_tracker: Callable[[Message], float] | None = None  # Track cost per request
    max_cost_per_hour: float = 100.0  # Dollar limit per hour
    max_retries_per_hour: int = 1000

    # Backpressure detection
    enable_backpressure: bool = True
    backpressure_threshold: float = 0.5  # Fraction of failed requests
    backpressure_window: int = 100  # Requests to consider

    def __post_init__(self):
        """Set up default error strategies if not provided."""
        if not self.error_strategies:
            self.error_strategies = {
                ErrorClass.TRANSIENT: ErrorStrategy(
                    error_class=ErrorClass.TRANSIENT,
                    max_retries=5,
                    initial_delay=0.1,
                    max_delay=5.0,
                    multiplier=2.0,
                ),
                ErrorClass.RATE_LIMIT: ErrorStrategy(
                    error_class=ErrorClass.RATE_LIMIT,
                    max_retries=10,
                    initial_delay=60.0,  # Start with 1 minute
                    max_delay=300.0,  # Max 5 minutes
                    multiplier=1.5,
                ),
                ErrorClass.TIMEOUT: ErrorStrategy(
                    error_class=ErrorClass.TIMEOUT,
                    max_retries=3,
                    initial_delay=2.0,
                    max_delay=30.0,
                    multiplier=2.0,
                ),
                ErrorClass.SERVER_ERROR: ErrorStrategy(
                    error_class=ErrorClass.SERVER_ERROR,
                    max_retries=3,
                    initial_delay=5.0,
                    max_delay=60.0,
                    multiplier=2.0,
                ),
                ErrorClass.CLIENT_ERROR: ErrorStrategy(
                    error_class=ErrorClass.CLIENT_ERROR,
                    max_retries=1,
                    initial_delay=0.0,
                    max_delay=0.0,
                    multiplier=1.0,
                    should_retry=False,
                ),
            }


@dataclass
class EnhancedRetryMetrics:
    """Metrics for enhanced retry middleware."""

    total_attempts: int = 0
    successful_first_attempt: int = 0
    successful_on_retry: int = 0
    failed_after_retries: int = 0
    total_retries: int = 0
    total_jitter_added: float = 0.0
    budget_exceeded_count: int = 0
    backpressure_detected_count: int = 0
    error_class_counts: dict[ErrorClass, int] = field(default_factory=dict)
    recent_results: list[bool] = field(default_factory=list)  # For backpressure


class EnhancedRetryDecorator(Agent):
    """Agent decorator with enhanced retry features.

    Example:
        ```python
        def classify_error(e: Exception) -> ErrorClass:
            if "rate limit" in str(e).lower():
                return ErrorClass.RATE_LIMIT
            elif "timeout" in str(e).lower():
                return ErrorClass.TIMEOUT
            return ErrorClass.SERVER_ERROR

        config = EnhancedRetryConfig(
            jitter_type=JitterType.FULL,
            error_classifier=classify_error,
            enable_budget=True,
            max_cost_per_hour=50.0,
        )

        agent = EnhancedRetryDecorator(base_agent, config)
        response = await agent.process(message)
        ```
    """

    def __init__(self, agent: Agent, config: EnhancedRetryConfig | None = None):
        """Initialize enhanced retry decorator.

        Args:
            agent: The agent to wrap
            config: Enhanced retry configuration
        """
        self._agent = agent
        self._config = config or EnhancedRetryConfig()
        self._metrics = EnhancedRetryMetrics()
        self._budget = RetryBudget(
            max_cost=self._config.max_cost_per_hour,
            max_retries_per_hour=self._config.max_retries_per_hour,
        )

    @property
    def name(self) -> str:
        """Return the name of the underlying agent."""
        return self._agent.name

    @property
    def capabilities(self) -> list[str]:
        """Return capabilities of the underlying agent."""
        return self._agent.capabilities

    @property
    def metrics(self) -> EnhancedRetryMetrics:
        """Return current retry metrics."""
        return self._metrics

    def _classify_error(self, error: Exception) -> ErrorClass:
        """Classify error type for strategy selection."""
        if self._config.error_classifier:
            return self._config.error_classifier(error)

        # Default classification based on error message
        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return ErrorClass.RATE_LIMIT
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorClass.TIMEOUT
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return ErrorClass.SERVER_ERROR
        elif "400" in error_str or "401" in error_str or "403" in error_str or "404" in error_str:
            return ErrorClass.CLIENT_ERROR

        return ErrorClass.UNKNOWN

    def _get_strategy(self, error_class: ErrorClass) -> ErrorStrategy:
        """Get retry strategy for error class."""
        strategy = self._config.error_strategies.get(error_class)

        if strategy is None:
            # Use default strategy
            return ErrorStrategy(
                error_class=error_class,
                max_retries=self._config.max_retries,
                initial_delay=self._config.initial_delay,
                max_delay=self._config.max_delay,
                multiplier=self._config.multiplier,
            )

        return strategy

    def _calculate_backoff(self, base_backoff: float, attempt: int) -> float:
        """Calculate backoff with jitter."""
        jitter_type = self._config.jitter_type

        if jitter_type == JitterType.NONE:
            return base_backoff

        elif jitter_type == JitterType.FULL:
            # Random between 0 and backoff
            jittered = random.uniform(0, base_backoff)
            self._metrics.total_jitter_added += base_backoff - jittered
            return jittered

        elif jitter_type == JitterType.EQUAL:
            # Random between backoff/2 and backoff
            min_backoff = base_backoff * self._config.jitter_min_ratio
            jittered = random.uniform(min_backoff, base_backoff)
            self._metrics.total_jitter_added += base_backoff - jittered
            return jittered

        elif jitter_type == JitterType.DECORRELATED:
            # Decorrelated jitter: random between base and 3*previous
            if attempt == 1:
                return base_backoff
            previous = self._calculate_backoff(base_backoff, attempt - 1)
            jittered = random.uniform(base_backoff, previous * 3)
            return min(jittered, self._config.max_delay)

        return base_backoff

    def _check_budget(self, cost: float) -> bool:
        """Check if retry budget allows this attempt.

        Returns:
            True if budget allows, False otherwise
        """
        if not self._config.enable_budget:
            return True

        # Reset window if hour has passed
        if time.time() - self._budget.window_start > 3600:
            self._budget.current_cost = 0.0
            self._budget.retry_count = 0
            self._budget.window_start = time.time()

        # Check cost budget
        if self._budget.current_cost + cost > self._budget.max_cost:
            self._metrics.budget_exceeded_count += 1
            return False

        # Check retry count budget
        if self._budget.retry_count >= self._budget.max_retries_per_hour:
            self._metrics.budget_exceeded_count += 1
            return False

        return True

    def _check_backpressure(self) -> bool:
        """Check if system is under backpressure.

        Returns:
            True if backpressure detected, False otherwise
        """
        if not self._config.enable_backpressure:
            return False

        recent = self._metrics.recent_results

        if len(recent) < self._config.backpressure_window:
            return False

        # Calculate failure rate
        failures = sum(1 for success in recent if not success)
        failure_rate = failures / len(recent)

        if failure_rate > self._config.backpressure_threshold:
            self._metrics.backpressure_detected_count += 1
            return True

        return False

    async def process(self, message: Message) -> Message:
        """Process message with enhanced retry logic.

        Args:
            message: Input message

        Returns:
            Response message from agent

        Raises:
            Exception: If all retry attempts fail or budget exceeded
        """
        last_error: Exception | None = None
        error_class: ErrorClass | None = None
        strategy: ErrorStrategy | None = None

        for attempt in range(1, self._config.max_retries + 1):
            self._metrics.total_attempts += 1

            try:
                # Check budget before attempt
                if self._config.enable_budget and self._config.cost_tracker:
                    estimated_cost = self._config.cost_tracker(message)

                    if not self._check_budget(estimated_cost):
                        raise Exception("Retry budget exceeded")

                # Check backpressure
                if self._check_backpressure():
                    # Add extra delay during backpressure
                    await asyncio.sleep(5.0)

                # Process message
                response = await self._agent.process(message)

                # Success
                if attempt == 1:
                    self._metrics.successful_first_attempt += 1
                else:
                    self._metrics.successful_on_retry += 1

                # Track success for backpressure
                self._metrics.recent_results.append(True)
                if len(self._metrics.recent_results) > self._config.backpressure_window:
                    self._metrics.recent_results.pop(0)

                # Track cost
                if self._config.enable_budget and self._config.cost_tracker:
                    cost = self._config.cost_tracker(message)
                    self._budget.current_cost += cost

                return response

            except Exception as e:
                last_error = e

                # Track failure for backpressure
                self._metrics.recent_results.append(False)
                if len(self._metrics.recent_results) > self._config.backpressure_window:
                    self._metrics.recent_results.pop(0)

                # Classify error
                error_class = self._classify_error(e)
                self._metrics.error_class_counts[error_class] = (
                    self._metrics.error_class_counts.get(error_class, 0) + 1
                )

                # Get strategy for error class
                strategy = self._get_strategy(error_class)

                # Check if should retry
                if not strategy.should_retry:
                    self._metrics.failed_after_retries += 1
                    raise Exception(f"Non-retryable error ({error_class.value}): {e}") from e

                # Check if exceeded max attempts for this error class
                if attempt >= strategy.max_retries:
                    break

                # Don't sleep after last attempt
                if attempt == strategy.max_retries:
                    break

                # Track retry
                self._metrics.total_retries += 1
                self._budget.retry_count += 1

                # Calculate backoff with jitter
                base_backoff = strategy.initial_delay * (strategy.multiplier ** (attempt - 1))
                base_backoff = min(base_backoff, strategy.max_delay)
                backoff = self._calculate_backoff(base_backoff, attempt)

                # Sleep with backoff
                await asyncio.sleep(backoff)

        # All attempts failed
        self._metrics.failed_after_retries += 1

        if strategy and error_class:
            raise Exception(
                f"Max retry attempts ({strategy.max_retries}) exceeded for {error_class.value}: {last_error}"
            ) from last_error

        raise Exception(
            f"Max retry attempts ({self._config.max_retries}) exceeded: {last_error}"
        ) from last_error
