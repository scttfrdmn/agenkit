"""Tests for rate limiter middleware."""

import asyncio
import pytest
import time
from agenkit.interfaces import Agent, Message
from agenkit.middleware import (
    RateLimiterConfig,
    RateLimiterDecorator,
    RateLimitError,
)


class SimpleAgent(Agent):
    """Agent that always succeeds immediately."""

    def __init__(self):
        self.call_count = 0

    @property
    def name(self) -> str:
        return "simple-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        self.call_count += 1
        return Message(role="agent", content="success")


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiting functionality."""
    agent = SimpleAgent()

    # 10 tokens/sec, capacity 10
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=10.0, capacity=10, tokens_per_request=1),
    )

    # Should allow 10 requests immediately (full capacity)
    for i in range(10):
        msg = Message(role="user", content="test")
        response = await rl.process(msg)

        assert response.content == "success", f"Request {i+1}: Expected 'success'"

    assert agent.call_count == 10, f"Expected 10 calls to agent, got {agent.call_count}"

    metrics = rl.metrics
    assert metrics.total_requests == 10, f"Expected 10 total requests, got {metrics.total_requests}"
    assert metrics.allowed_requests == 10, f"Expected 10 allowed requests, got {metrics.allowed_requests}"


@pytest.mark.asyncio
async def test_rate_limiter_refill():
    """Test token refill over time."""
    agent = SimpleAgent()

    # 10 tokens/sec, capacity 5
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=10.0, capacity=5, tokens_per_request=1),
    )

    # Consume all tokens
    for i in range(5):
        msg = Message(role="user", content="test")
        await rl.process(msg)

    # Wait for 500ms (should refill 5 tokens)
    await asyncio.sleep(0.5)

    # Should be able to make ~5 more requests
    success_count = 0
    for i in range(5):
        msg = Message(role="user", content="test")
        try:
            await rl.process(msg)
            success_count += 1
        except Exception:
            break  # Stop on first error

    # Should have successfully made around 5 requests (allowing for timing variance)
    assert success_count >= 4, f"Expected at least 4 successful requests after refill, got {success_count}"


@pytest.mark.asyncio
async def test_rate_limiter_wait():
    """Test waiting for tokens."""
    agent = SimpleAgent()

    # 5 tokens/sec, capacity 5
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=5.0, capacity=5, tokens_per_request=1),
    )

    # Consume all tokens
    for i in range(5):
        msg = Message(role="user", content="test")
        await rl.process(msg)

    # Next request should wait for tokens
    start = time.time()
    msg = Message(role="user", content="test")
    response = await rl.process(msg)
    elapsed = time.time() - start

    assert response.content == "success", "Expected success after waiting"

    # Should have waited approximately 200ms (1 token / 5 tokens per second)
    expected_wait = 0.2
    assert elapsed >= expected_wait / 2, f"Expected to wait at least {expected_wait/2}s, but only waited {elapsed}s"

    metrics = rl.metrics
    assert metrics.total_wait_time > 0, "Expected non-zero total wait time"


@pytest.mark.asyncio
async def test_rate_limiter_burst():
    """Test burst capacity."""
    agent = SimpleAgent()

    # 2 tokens/sec, but capacity 10 (allows bursts)
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=2.0, capacity=10, tokens_per_request=1),
    )

    # Should allow 10 requests immediately despite low rate
    for i in range(10):
        msg = Message(role="user", content="test")
        response = await rl.process(msg)

        assert response.content == "success", f"Request {i+1}: Expected success in burst"

    assert agent.call_count == 10, f"Expected 10 calls in burst, got {agent.call_count}"


@pytest.mark.asyncio
async def test_rate_limiter_multiple_tokens():
    """Test requests requiring multiple tokens."""
    agent = SimpleAgent()

    # 10 tokens/sec, capacity 10, but 5 tokens per request
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=10.0, capacity=10, tokens_per_request=5),
    )

    # Should allow 2 requests (2 * 5 = 10 tokens)
    for i in range(2):
        msg = Message(role="user", content="test")
        response = await rl.process(msg)

        assert response.content == "success", f"Request {i+1}: Expected success"

    assert agent.call_count == 2, f"Expected 2 calls, got {agent.call_count}"


@pytest.mark.asyncio
async def test_rate_limiter_cancellation():
    """Test task cancellation during wait."""
    agent = SimpleAgent()

    # 5 tokens/sec, capacity 1
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=5.0, capacity=1, tokens_per_request=1),
    )

    # Consume the token
    msg = Message(role="user", content="test")
    await rl.process(msg)

    # Create task that will be cancelled
    async def process_with_timeout():
        try:
            msg = Message(role="user", content="test")
            await asyncio.wait_for(rl.process(msg), timeout=0.05)
        except asyncio.TimeoutError:
            raise

    # Should be cancelled before tokens refill
    with pytest.raises(asyncio.TimeoutError):
        await process_with_timeout()


@pytest.mark.asyncio
async def test_rate_limiter_metrics():
    """Test comprehensive metrics tracking."""
    agent = SimpleAgent()

    # 10 tokens/sec, capacity 5
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=10.0, capacity=5, tokens_per_request=1),
    )

    # Make 5 requests (consume all tokens)
    for i in range(5):
        msg = Message(role="user", content="test")
        await rl.process(msg)

    metrics = rl.metrics

    assert metrics.total_requests == 5, f"Expected 5 total requests, got {metrics.total_requests}"
    assert metrics.allowed_requests == 5, f"Expected 5 allowed requests, got {metrics.allowed_requests}"
    assert metrics.rejected_requests == 0, f"Expected 0 rejected requests, got {metrics.rejected_requests}"

    # Current tokens should be near 0
    assert metrics.current_tokens <= 1.0, f"Expected current tokens near 0, got {metrics.current_tokens}"


@pytest.mark.asyncio
async def test_rate_limiter_high_throughput():
    """Test rate limiter under high load."""
    agent = SimpleAgent()

    # 100 tokens/sec, capacity 100
    rl = RateLimiterDecorator(
        agent,
        RateLimiterConfig(rate=100.0, capacity=100, tokens_per_request=1),
    )

    # Should handle 100 requests immediately
    start = time.time()
    for i in range(100):
        msg = Message(role="user", content="test")
        response = await rl.process(msg)

        assert response.content == "success", f"Request {i+1}: Expected success"

    elapsed = time.time() - start

    # Should complete quickly (within 1 second)
    assert elapsed < 1.0, f"Expected to complete within 1s, took {elapsed}s"

    assert agent.call_count == 100, f"Expected 100 calls, got {agent.call_count}"

    metrics = rl.metrics
    assert metrics.allowed_requests == 100, f"Expected 100 allowed requests, got {metrics.allowed_requests}"
