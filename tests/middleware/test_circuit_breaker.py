"""Tests for circuit breaker middleware."""

import asyncio
import pytest
from agenkit.interfaces import Agent, Message
from agenkit.middleware import (
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    CircuitBreakerError,
    CircuitState,
)


class UnreliableAgent(Agent):
    """Agent that simulates failures based on a controllable pattern."""

    def __init__(self, failure_pattern: list[bool], delay: float = 0):
        """Initialize unreliable agent.

        Args:
            failure_pattern: List where True = fail, False = succeed
            delay: Delay in seconds before responding
        """
        self.failure_pattern = failure_pattern
        self.delay = delay
        self.attempts = 0

    @property
    def name(self) -> str:
        return "unreliable-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        index = self.attempts % len(self.failure_pattern)
        self.attempts += 1

        if self.failure_pattern[index]:
            raise Exception("simulated failure")

        return Message(role="agent", content="success")


@pytest.mark.asyncio
async def test_circuit_breaker_closed():
    """Test normal operation in closed state."""
    # Agent that always succeeds
    agent = UnreliableAgent([False, False, False])

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1,
            success_threshold=2,
            timeout=1.0,
        ),
    )

    # Should succeed in closed state
    for i in range(3):
        msg = Message(role="user", content="test")
        response = await cb.process(msg)

        assert response.content == "success", f"Attempt {i+1}: Expected 'success'"

    assert cb.state == CircuitState.CLOSED, "Expected CLOSED state"

    metrics = cb.metrics
    assert metrics.total_requests == 3, f"Expected 3 total requests, got {metrics.total_requests}"
    assert metrics.successful_requests == 3, f"Expected 3 successful requests, got {metrics.successful_requests}"


@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    """Test circuit opening after threshold failures."""
    # Agent that always fails
    agent = UnreliableAgent([True])

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1,
            success_threshold=2,
            timeout=1.0,
        ),
    )

    # Trigger failures to open circuit
    for i in range(3):
        msg = Message(role="user", content="test")
        with pytest.raises(Exception):
            await cb.process(msg)

    # Circuit should be open
    assert cb.state == CircuitState.OPEN, f"Expected OPEN state, got {cb.state.value}"

    metrics = cb.metrics
    assert metrics.failed_requests == 3, f"Expected 3 failed requests, got {metrics.failed_requests}"


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open():
    """Test that open circuit rejects requests."""
    # Agent that always fails
    agent = UnreliableAgent([True])

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1.0,  # Long timeout
            success_threshold=2,
            timeout=1.0,
        ),
    )

    # Open the circuit
    for i in range(2):
        msg = Message(role="user", content="test")
        with pytest.raises(Exception):
            await cb.process(msg)

    # Circuit should be open
    assert cb.state == CircuitState.OPEN, f"Expected OPEN state, got {cb.state.value}"

    # Next request should be rejected immediately
    msg = Message(role="user", content="test")
    with pytest.raises(CircuitBreakerError) as exc_info:
        await cb.process(msg)

    assert "OPEN" in str(exc_info.value), "Expected CircuitBreakerError with OPEN message"

    metrics = cb.metrics
    assert metrics.rejected_requests == 1, f"Expected 1 rejected request, got {metrics.rejected_requests}"


@pytest.mark.asyncio
async def test_circuit_breaker_half_open():
    """Test transition to half-open state."""
    # Agent that fails then succeeds
    agent = UnreliableAgent([True, True, False, False])

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.05,
            success_threshold=2,
            timeout=1.0,
        ),
    )

    # Open the circuit
    for i in range(2):
        msg = Message(role="user", content="test")
        with pytest.raises(Exception):
            await cb.process(msg)

    assert cb.state == CircuitState.OPEN, f"Expected OPEN state, got {cb.state.value}"

    # Wait for recovery timeout
    await asyncio.sleep(0.06)

    # Next request should transition to half-open
    msg = Message(role="user", content="test")
    response = await cb.process(msg)

    assert response.content == "success", f"Expected 'success', got '{response.content}'"

    # Should be in half-open state
    assert cb.state == CircuitState.HALF_OPEN, f"Expected HALF_OPEN state, got {cb.state.value}"


@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    """Test full recovery (half-open -> closed)."""
    # Agent that fails then succeeds
    agent = UnreliableAgent([True, True, False, False, False])

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.05,
            success_threshold=2,
            timeout=1.0,
        ),
    )

    # Open the circuit
    for i in range(2):
        msg = Message(role="user", content="test")
        with pytest.raises(Exception):
            await cb.process(msg)

    # Wait for recovery timeout
    await asyncio.sleep(0.06)

    # Make successful requests to close circuit
    for i in range(2):
        msg = Message(role="user", content="test")
        response = await cb.process(msg)

        assert response.content == "success", f"Attempt {i+1}: Expected 'success'"

    # Circuit should be closed
    assert cb.state == CircuitState.CLOSED, f"Expected CLOSED state after recovery, got {cb.state.value}"

    metrics = cb.metrics
    assert metrics.state_changes.get("closed->open", 0) == 1, "Expected 1 closed->open transition"
    assert metrics.state_changes.get("open->half_open", 0) == 1, "Expected 1 open->half_open transition"
    assert metrics.state_changes.get("half_open->closed", 0) == 1, "Expected 1 half_open->closed transition"


@pytest.mark.asyncio
async def test_circuit_breaker_reopens_from_half_open():
    """Test reopening on failure in half-open."""
    # Agent that fails, then succeeds once, then fails again
    agent = UnreliableAgent([True, True, False, True])

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.05,
            success_threshold=2,
            timeout=1.0,
        ),
    )

    # Open the circuit
    for i in range(2):
        msg = Message(role="user", content="test")
        with pytest.raises(Exception):
            await cb.process(msg)

    # Wait for recovery timeout
    await asyncio.sleep(0.06)

    # First request succeeds (half-open)
    msg = Message(role="user", content="test")
    await cb.process(msg)

    assert cb.state == CircuitState.HALF_OPEN, f"Expected HALF_OPEN state, got {cb.state.value}"

    # Second request fails, should reopen
    msg = Message(role="user", content="test")
    with pytest.raises(Exception):
        await cb.process(msg)

    assert cb.state == CircuitState.OPEN, f"Expected OPEN state after failure in half-open, got {cb.state.value}"

    metrics = cb.metrics
    assert metrics.state_changes.get("half_open->open", 0) == 1, "Expected 1 half_open->open transition"


@pytest.mark.asyncio
async def test_circuit_breaker_timeout():
    """Test timeout handling."""
    # Agent that takes too long
    agent = UnreliableAgent([False], delay=0.2)

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=2,
            timeout=0.05,  # Timeout before agent response
        ),
    )

    # Trigger timeouts to open circuit
    for i in range(2):
        msg = Message(role="user", content="test")
        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            await cb.process(msg)

    # Circuit should be open due to timeouts
    assert cb.state == CircuitState.OPEN, f"Expected OPEN state after timeouts, got {cb.state.value}"

    metrics = cb.metrics
    assert metrics.failed_requests == 2, f"Expected 2 failed requests, got {metrics.failed_requests}"


@pytest.mark.asyncio
async def test_circuit_breaker_metrics():
    """Test metrics tracking."""
    # Agent with mixed success/failure pattern
    agent = UnreliableAgent([False, False, True, True, True])

    cb = CircuitBreakerDecorator(
        agent,
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1,
            success_threshold=2,
            timeout=1.0,
        ),
    )

    # Make requests
    for i in range(5):
        msg = Message(role="user", content="test")
        try:
            await cb.process(msg)
        except Exception:
            pass  # Expected failures

    metrics = cb.metrics

    assert metrics.total_requests == 5, f"Expected 5 total requests, got {metrics.total_requests}"
    assert metrics.successful_requests == 2, f"Expected 2 successful requests, got {metrics.successful_requests}"
    assert metrics.failed_requests == 3, f"Expected 3 failed requests, got {metrics.failed_requests}"
    assert metrics.current_state == CircuitState.OPEN, f"Expected OPEN state, got {metrics.current_state.value}"
    assert metrics.last_state_change is not None, "Expected last_state_change to be set"
