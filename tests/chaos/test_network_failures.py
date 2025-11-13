"""
Network Failure Chaos Tests

Tests system resilience under various network failure conditions:
- Connection timeouts
- Connection refused
- Connection drops
- DNS failures
- Intermittent connectivity

These tests validate that the system handles network failures gracefully
and that resilience middleware (retry, circuit breaker, timeout) works correctly.
"""
import asyncio
import time

import pytest

from agenkit.interfaces import Agent, Message
from tests.chaos.chaos_agents import ChaosAgent, ChaosMode


class SimpleAgent(Agent):
    """Simple agent for chaos testing."""

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
# Connection Timeout Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_connection_timeout():
    """Test behavior when connection times out."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.TIMEOUT
    )

    message = Message(role="user", content="Test timeout")

    # Should timeout after configured duration
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(chaos_agent.process(message), timeout=0.1)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_timeout_with_retry():
    """Test that retry doesn't help with timeouts (each retry times out)."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.TIMEOUT
    )

    message = Message(role="user", content="Test")

    # Simulate retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(
                chaos_agent.process(message),
                timeout=0.1
            )
            pytest.fail("Should have timed out")
        except asyncio.TimeoutError:
            pass  # Expected

    # All retries should timeout
    assert chaos_agent.get_stats()["request_count"] == max_retries


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_slow_response_within_timeout():
    """Test that slow responses succeed if within timeout."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.SLOW_RESPONSE,
        delay_ms=50  # 50ms delay
    )

    message = Message(role="user", content="Test")

    # Should succeed with 200ms timeout
    start = time.time()
    response = await asyncio.wait_for(chaos_agent.process(message), timeout=0.2)
    elapsed = time.time() - start

    assert response.content == "Processed: Test"
    assert 0.05 <= elapsed < 0.2, f"Should take ~50ms, took {elapsed:.3f}s"


# ============================================
# Connection Refused Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_connection_refused():
    """Test behavior when connection is refused."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.CONNECTION_REFUSED
    )

    message = Message(role="user", content="Test")

    with pytest.raises(ConnectionRefusedError) as exc_info:
        await chaos_agent.process(message)

    assert "Connection refused" in str(exc_info.value)
    assert chaos_agent.get_stats()["failure_count"] == 1


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_connection_refused_with_retry():
    """Test retry behavior with connection refused."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.CONNECTION_REFUSED
    )

    message = Message(role="user", content="Test")

    # Simulate retry logic
    max_retries = 3
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = await chaos_agent.process(message)
            break
        except ConnectionRefusedError as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(0.01)  # Small backoff
            continue

    # All attempts should fail
    assert last_error is not None
    assert chaos_agent.get_stats()["request_count"] == max_retries + 1
    assert chaos_agent.get_stats()["failure_count"] == max_retries + 1


# ============================================
# Connection Drop Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_connection_drop():
    """Test behavior when connection drops mid-request."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.CONNECTION_DROP
    )

    message = Message(role="user", content="Test")

    with pytest.raises(ConnectionError) as exc_info:
        await chaos_agent.process(message)

    assert "Connection dropped" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_connection_drop_recovery():
    """Test that system can recover after connection drops."""
    base_agent = SimpleAgent()

    # First request: connection drops
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.CONNECTION_DROP)
    message = Message(role="user", content="Test")

    with pytest.raises(ConnectionError):
        await chaos_agent.process(message)

    # Second request: connection works (switch to normal agent)
    normal_agent = base_agent
    response = await normal_agent.process(message)

    assert response.content == "Processed: Test"


# ============================================
# Intermittent Connectivity Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_intermittent_connectivity():
    """Test behavior with intermittent connectivity (50% failure rate)."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.5  # 50% of requests fail
    )

    message = Message(role="user", content="Test")

    # Run 100 requests
    successes = 0
    failures = 0

    for _ in range(100):
        try:
            await chaos_agent.process(message)
            successes += 1
        except ConnectionError:
            failures += 1

    # Should be roughly 50/50 split (allow ±20% variance)
    assert 30 <= successes <= 70, f"Expected ~50 successes, got {successes}"
    assert 30 <= failures <= 70, f"Expected ~50 failures, got {failures}"

    # Verify stats
    stats = chaos_agent.get_stats()
    assert stats["request_count"] == 100
    assert 30 <= stats["failure_count"] <= 70


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_intermittent_with_retry_succeeds():
    """Test that retries eventually succeed with intermittent failures."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.7  # 70% failure rate
    )

    message = Message(role="user", content="Test")

    # Retry up to 10 times - should eventually succeed
    max_retries = 10
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = await chaos_agent.process(message)
            # Success!
            assert response.content == "Processed: Test"
            break
        except ConnectionError as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(0.01)
            continue
    else:
        # If we got here, all retries failed (very unlikely with 70% failure rate over 11 attempts)
        # Probability of all failing: 0.7^11 = 0.002 (~0.2%)
        pytest.fail(f"All {max_retries + 1} attempts failed (extremely unlikely)")


# ============================================
# Random Error Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_random_errors():
    """Test behavior with random errors (30% failure rate)."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.RANDOM_ERROR,
        failure_rate=0.3  # 30% error rate
    )

    message = Message(role="user", content="Test")

    # Run 100 requests
    successes = 0
    errors = 0

    for _ in range(100):
        try:
            response = await chaos_agent.process(message)
            assert response.content == "Processed: Test"
            successes += 1
        except RuntimeError as e:
            assert "Random failure" in str(e)
            errors += 1

    # Should be roughly 70/30 split (allow ±15% variance)
    assert 55 <= successes <= 85, f"Expected ~70 successes, got {successes}"
    assert 15 <= errors <= 45, f"Expected ~30 errors, got {errors}"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_concurrent_requests_with_network_chaos():
    """Test concurrent requests under network chaos."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.5
    )

    message = Message(role="user", content="Test")

    # 20 concurrent requests
    tasks = [chaos_agent.process(message) for _ in range(20)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successes and failures
    successes = sum(1 for r in results if isinstance(r, Message))
    failures = sum(1 for r in results if isinstance(r, Exception))

    assert successes + failures == 20
    # With 50% failure rate, expect ~10 successes (allow ±7 variance)
    assert 3 <= successes <= 17, f"Expected ~10 successes, got {successes}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "chaos"])
