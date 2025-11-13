"""
Middleware Resilience Under Chaos

Tests that resilience middleware (Retry, Circuit Breaker, Timeout, Rate Limiter)
behaves correctly under chaos conditions. These are the most critical tests
for validating production readiness.
"""
import asyncio
import time
from typing import Optional

import pytest

from agenkit.interfaces import Agent, Message
from tests.chaos.chaos_agents import (
    ChaosAgent,
    ChaosMode,
    FlakeyAgent,
    OverloadedAgent,
)


class SimpleAgent(Agent):
    """Simple agent for testing."""

    def __init__(self, name: str = "simple-agent"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="agent",
            content=f"Processed: {message.content}",
            metadata={"agent": self.name}
        )


# ============================================
# Retry Middleware Under Chaos
# ============================================

class RetryMiddleware:
    """Simple retry middleware for testing."""

    def __init__(
        self,
        agent: Agent,
        max_retries: int = 3,
        backoff_base: float = 0.1,
        exponential: bool = True,
    ):
        self._agent = agent
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._exponential = exponential
        self._retry_counts = []

    @property
    def name(self) -> str:
        return f"retry-{self._agent.name}"

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    def get_retry_counts(self) -> list[int]:
        """Get list of retry counts for each request."""
        return self._retry_counts

    async def process(self, message: Message) -> Message:
        """Process with retry logic."""
        retries = 0

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._agent.process(message)
                self._retry_counts.append(retries)
                return response
            except Exception as e:
                retries += 1
                if attempt < self._max_retries:
                    # Calculate backoff
                    if self._exponential:
                        delay = self._backoff_base * (2 ** attempt)
                    else:
                        delay = self._backoff_base

                    await asyncio.sleep(delay)
                else:
                    # Max retries exceeded
                    self._retry_counts.append(retries)
                    raise


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_retry_with_intermittent_failures():
    """Test that retry middleware handles intermittent failures."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.6  # 60% failure rate
    )
    retry_agent = RetryMiddleware(chaos_agent, max_retries=5)

    message = Message(role="user", content="Test")

    # With 60% failure rate and 6 attempts, probability of all failing is 0.6^6 = 0.047 (~4.7%)
    # Should almost always succeed
    response = await retry_agent.process(message)
    assert response.content == "Processed: Test"

    # Should have required at least 1 retry
    retry_counts = retry_agent.get_retry_counts()
    assert len(retry_counts) == 1
    # Most likely needed 1-3 retries
    assert 0 <= retry_counts[0] <= 5


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_retry_with_flakey_service():
    """Test retry with predictable failure pattern."""
    base_agent = SimpleAgent()

    # Fail twice, then succeed
    flakey_agent = FlakeyAgent(base_agent, failure_pattern=[False, False, True])
    retry_agent = RetryMiddleware(flakey_agent, max_retries=3)

    message = Message(role="user", content="Test")

    # Should succeed on 3rd attempt (after 2 retries)
    response = await retry_agent.process(message)
    assert response.content == "Processed: Test"

    retry_counts = retry_agent.get_retry_counts()
    assert retry_counts[0] == 2, "Should require exactly 2 retries"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_retry_exhaustion():
    """Test that retry gives up after max retries."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.CONNECTION_REFUSED)
    retry_agent = RetryMiddleware(chaos_agent, max_retries=3)

    message = Message(role="user", content="Test")

    # Should fail after 3 retries (4 total attempts)
    with pytest.raises(ConnectionRefusedError):
        await retry_agent.process(message)

    # Should have made 4 attempts (1 + 3 retries)
    assert chaos_agent.get_stats()["request_count"] == 4


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_retry_exponential_backoff():
    """Test that retry uses exponential backoff."""
    base_agent = SimpleAgent()

    # Fail 3 times, then succeed
    flakey_agent = FlakeyAgent(base_agent, failure_pattern=[False, False, False, True])
    retry_agent = RetryMiddleware(
        flakey_agent,
        max_retries=3,
        backoff_base=0.05,  # 50ms base
        exponential=True
    )

    message = Message(role="user", content="Test")

    # Measure total time (should include backoffs: 50ms + 100ms + 200ms = 350ms)
    start = time.time()
    response = await retry_agent.process(message)
    elapsed = time.time() - start

    assert response.content == "Processed: Test"
    # Should take at least 350ms (backoffs) but less than 500ms
    assert 0.35 <= elapsed < 0.5, f"Expected ~350ms with backoffs, took {elapsed:.3f}s"


# ============================================
# Circuit Breaker Under Chaos
# ============================================

class CircuitBreakerMiddleware:
    """Simple circuit breaker for testing."""

    def __init__(
        self,
        agent: Agent,
        failure_threshold: int = 3,
        success_threshold: int = 2,
        timeout: float = 1.0,
    ):
        self._agent = agent
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout = timeout

        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def name(self) -> str:
        return f"circuit-breaker-{self._agent.name}"

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    def get_state(self) -> str:
        return self._state

    def get_failure_count(self) -> int:
        return self._failure_count

    async def process(self, message: Message) -> Message:
        """Process with circuit breaker logic."""
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self._state == "OPEN":
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self._timeout:
                self._state = "HALF_OPEN"
                self._success_count = 0
            else:
                raise RuntimeError(f"Circuit breaker OPEN (failures={self._failure_count})")

        # Try to process
        try:
            response = await self._agent.process(message)

            # Success
            if self._state == "HALF_OPEN":
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    # Close circuit
                    self._state = "CLOSED"
                    self._failure_count = 0
            elif self._state == "CLOSED":
                # Reset failure count on success
                self._failure_count = 0

            return response

        except Exception as e:
            # Failure
            self._last_failure_time = time.time()

            if self._state == "CLOSED":
                self._failure_count += 1
                if self._failure_count >= self._failure_threshold:
                    self._state = "OPEN"
            elif self._state == "HALF_OPEN":
                # Failed during half-open, go back to open
                self._state = "OPEN"
                self._failure_count = self._failure_threshold

            raise


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_circuit_breaker_opens_after_failures():
    """Test that circuit breaker opens after failure threshold."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.CONNECTION_REFUSED)
    cb_agent = CircuitBreakerMiddleware(chaos_agent, failure_threshold=3)

    message = Message(role="user", content="Test")

    # First 3 failures should reach the agent
    for i in range(3):
        with pytest.raises(ConnectionRefusedError):
            await cb_agent.process(message)

    assert cb_agent.get_state() == "OPEN", "Circuit should be OPEN after 3 failures"
    assert cb_agent.get_failure_count() == 3

    # 4th request should be blocked by circuit breaker (not reach agent)
    with pytest.raises(RuntimeError) as exc_info:
        await cb_agent.process(message)

    assert "Circuit breaker OPEN" in str(exc_info.value)
    # Agent should still only have 3 requests (4th was blocked)
    assert chaos_agent.get_stats()["request_count"] == 3


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker transitions to HALF_OPEN and recovers."""
    base_agent = SimpleAgent()

    # Fail 3 times, then succeed
    flakey_agent = FlakeyAgent(
        base_agent,
        failure_pattern=[False, False, False, True, True]
    )

    cb_agent = CircuitBreakerMiddleware(
        flakey_agent,
        failure_threshold=3,
        success_threshold=2,
        timeout=0.1  # 100ms timeout
    )

    message = Message(role="user", content="Test")

    # Generate 3 failures -> circuit opens
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb_agent.process(message)

    assert cb_agent.get_state() == "OPEN"

    # Wait for timeout
    await asyncio.sleep(0.15)

    # Next request should transition to HALF_OPEN and succeed
    response = await cb_agent.process(message)
    assert response.content == "Processed: Test"
    assert cb_agent.get_state() == "HALF_OPEN"

    # Second success should close the circuit
    response = await cb_agent.process(message)
    assert response.content == "Processed: Test"
    assert cb_agent.get_state() == "CLOSED"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_circuit_breaker_prevents_cascade():
    """Test that circuit breaker prevents failure cascade."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.CONNECTION_REFUSED)
    cb_agent = CircuitBreakerMiddleware(chaos_agent, failure_threshold=5)

    message = Message(role="user", content="Test")

    # Open the circuit with 5 failures
    for _ in range(5):
        try:
            await cb_agent.process(message)
        except:
            pass

    assert cb_agent.get_state() == "OPEN"

    # Next 100 requests should be blocked immediately (not reach failing service)
    start_count = chaos_agent.get_stats()["request_count"]

    for _ in range(100):
        with pytest.raises(RuntimeError) as exc_info:
            await cb_agent.process(message)
        assert "Circuit breaker OPEN" in str(exc_info.value)

    # Agent should not receive any additional requests
    assert chaos_agent.get_stats()["request_count"] == start_count


# ============================================
# Timeout Middleware Under Chaos
# ============================================

class TimeoutMiddleware:
    """Simple timeout middleware for testing."""

    def __init__(self, agent: Agent, timeout: float = 1.0):
        self._agent = agent
        self._timeout = timeout
        self._timeout_count = 0

    @property
    def name(self) -> str:
        return f"timeout-{self._agent.name}"

    @property
    def capabilities(self) -> list[str]:
        return self._agent.capabilities

    def get_timeout_count(self) -> int:
        return self._timeout_count

    async def process(self, message: Message) -> Message:
        """Process with timeout."""
        try:
            return await asyncio.wait_for(
                self._agent.process(message),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            self._timeout_count += 1
            raise


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_timeout_with_slow_service():
    """Test timeout middleware with slow service."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.SLOW_RESPONSE,
        delay_ms=500  # 500ms delay
    )
    timeout_agent = TimeoutMiddleware(chaos_agent, timeout=0.2)

    message = Message(role="user", content="Test")

    # Should timeout
    with pytest.raises(asyncio.TimeoutError):
        await timeout_agent.process(message)

    assert timeout_agent.get_timeout_count() == 1


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_timeout_prevents_hang():
    """Test that timeout prevents indefinite hanging."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.TIMEOUT)
    timeout_agent = TimeoutMiddleware(chaos_agent, timeout=0.1)

    message = Message(role="user", content="Test")

    # Should timeout quickly, not hang
    start = time.time()
    with pytest.raises(asyncio.TimeoutError):
        await timeout_agent.process(message)
    elapsed = time.time() - start

    assert elapsed < 0.2, f"Should timeout in ~100ms, took {elapsed:.3f}s"


# ============================================
# Combined Middleware Under Chaos
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_retry_with_circuit_breaker():
    """Test retry + circuit breaker combination."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.CONNECTION_REFUSED)

    # Circuit breaker wraps chaos agent
    cb_agent = CircuitBreakerMiddleware(chaos_agent, failure_threshold=3)

    # Retry wraps circuit breaker
    retry_agent = RetryMiddleware(cb_agent, max_retries=2)

    message = Message(role="user", content="Test")

    # First request: 3 attempts (1 + 2 retries), all fail, circuit opens
    with pytest.raises(ConnectionRefusedError):
        await retry_agent.process(message)

    assert cb_agent.get_state() == "OPEN"

    # Second request: Immediately blocked by circuit breaker
    with pytest.raises(RuntimeError) as exc_info:
        await retry_agent.process(message)

    assert "Circuit breaker OPEN" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_timeout_with_retry():
    """Test timeout + retry combination."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.SLOW_RESPONSE,
        delay_ms=200
    )

    # Timeout wraps chaos agent
    timeout_agent = TimeoutMiddleware(chaos_agent, timeout=0.1)

    # Retry wraps timeout
    retry_agent = RetryMiddleware(timeout_agent, max_retries=3)

    message = Message(role="user", content="Test")

    # All retries should timeout
    with pytest.raises(asyncio.TimeoutError):
        await retry_agent.process(message)

    # Should have tried 4 times (1 + 3 retries)
    assert timeout_agent.get_timeout_count() == 4


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_full_resilience_stack():
    """Test full resilience stack: Retry + Circuit Breaker + Timeout."""
    base_agent = SimpleAgent()

    # Intermittent failures with slow responses
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.3,
        delay_ms=50
    )

    # Stack: Timeout -> Circuit Breaker -> Retry -> Chaos
    timeout_agent = TimeoutMiddleware(chaos_agent, timeout=2.0)
    cb_agent = CircuitBreakerMiddleware(timeout_agent, failure_threshold=5)
    retry_agent = RetryMiddleware(cb_agent, max_retries=3)

    message = Message(role="user", content="Test")

    # Run 20 requests - most should succeed due to retry
    successes = 0
    failures = 0

    for _ in range(20):
        try:
            response = await retry_agent.process(message)
            assert response.content == "Processed: Test"
            successes += 1
        except Exception:
            failures += 1

    # With 30% base failure rate and 4 attempts per request,
    # probability of all attempts failing: 0.3^4 = 0.0081 (~0.8%)
    # So out of 20 requests, expect ~0-1 failures
    assert successes >= 18, f"Expected >=18 successes with resilience stack, got {successes}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "chaos"])
