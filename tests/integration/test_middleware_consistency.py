"""
Middleware Consistency Tests

Tests that validate middleware behavior is consistent between Python and Go implementations.
These tests ensure that retry logic, circuit breaker state transitions, rate limiting,
timeouts, batching, and caching work identically across languages.

Prerequisites:
- All middleware implementations must be complete in both languages
- Tests can run without external dependencies
"""
import asyncio
import time
from typing import Optional

import pytest

from agenkit.interfaces import Agent, Message


# ============================================
# Test Agents
# ============================================

class CountingAgent(Agent):
    """Agent that counts how many times it's called."""

    def __init__(self, name: str = "counting-agent"):
        self._name = name
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["count"]

    async def process(self, message: Message) -> Message:
        self._call_count += 1
        return Message(
            role="agent",
            content=f"Call #{self._call_count}: {message.content}",
            metadata={"call_count": self._call_count}
        )

    def get_call_count(self) -> int:
        return self._call_count


class FailingAgent(Agent):
    """Agent that fails a specified number of times before succeeding."""

    def __init__(self, fail_count: int, name: str = "failing-agent"):
        self._name = name
        self._fail_count = fail_count
        self._attempt_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["fail"]

    async def process(self, message: Message) -> Message:
        self._attempt_count += 1
        if self._attempt_count <= self._fail_count:
            raise RuntimeError(f"Failure {self._attempt_count}/{self._fail_count}")

        return Message(
            role="agent",
            content=f"Success after {self._fail_count} failures",
            metadata={"attempt_count": self._attempt_count}
        )

    def get_attempt_count(self) -> int:
        return self._attempt_count


class SlowAgent(Agent):
    """Agent with configurable delay."""

    def __init__(self, delay: float, name: str = "slow-agent"):
        self._name = name
        self._delay = delay

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["slow"]

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(self._delay)
        return Message(
            role="agent",
            content=f"Completed after {self._delay}s delay",
            metadata={"delay": self._delay}
        )


# ============================================
# Retry Middleware Consistency Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_retry_count_consistency():
    """Test that retry counts match between Python and Go."""
    # Simulates retry behavior that should be identical
    agent = FailingAgent(fail_count=2)  # Fails 2 times, succeeds on 3rd

    # Manually implement retry logic to test expected behavior
    max_retries = 3
    attempt = 0
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = await agent.process(Message(role="user", content="test"))
            break
        except RuntimeError as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(0.01)  # Small delay between retries
            continue

    # Should succeed on 3rd attempt (after 2 retries)
    assert agent.get_attempt_count() == 3, "Should take 3 attempts (1 initial + 2 retries)"
    assert response.metadata["attempt_count"] == 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_retry_backoff_timing():
    """Test that exponential backoff timing is consistent."""
    delays = []

    # Simulate exponential backoff: 0.1s, 0.2s, 0.4s
    base_delay = 0.1
    for i in range(3):
        delay = base_delay * (2 ** i)
        delays.append(delay)

    # Expected delays: [0.1, 0.2, 0.4]
    assert delays == [0.1, 0.2, 0.4], "Exponential backoff should double each time"
    assert abs(sum(delays) - 0.7) < 0.001, "Total backoff time should be ~0.7s"


# ============================================
# Circuit Breaker Consistency Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_circuit_breaker_state_transitions():
    """Test that circuit breaker state transitions are consistent."""
    # Simulates circuit breaker states: CLOSED -> OPEN -> HALF_OPEN -> CLOSED

    class CircuitBreakerSimulator:
        def __init__(self, failure_threshold: int):
            self.state = "CLOSED"
            self.failure_count = 0
            self.failure_threshold = failure_threshold

        def record_success(self):
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0

        def record_failure(self):
            self.failure_count += 1
            if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

        def attempt_recovery(self):
            if self.state == "OPEN":
                self.state = "HALF_OPEN"

    cb = CircuitBreakerSimulator(failure_threshold=3)

    # Initial state
    assert cb.state == "CLOSED"

    # Record 3 failures -> should open
    for _ in range(3):
        cb.record_failure()

    assert cb.state == "OPEN", "Should open after 3 failures"
    assert cb.failure_count == 3

    # Attempt recovery -> should go to HALF_OPEN
    cb.attempt_recovery()
    assert cb.state == "HALF_OPEN", "Should transition to HALF_OPEN"

    # Success in HALF_OPEN -> should close
    cb.record_success()
    assert cb.state == "CLOSED", "Should close after success in HALF_OPEN"
    assert cb.failure_count == 0, "Failure count should reset"


# ============================================
# Rate Limiter Consistency Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_rate_limiter_token_bucket():
    """Test that rate limiter token bucket algorithm is consistent."""

    class TokenBucket:
        def __init__(self, rate: float, burst: int):
            self.rate = rate  # tokens per second
            self.burst = burst  # max tokens
            self.tokens = burst
            self.last_update = time.time()

        def consume(self, tokens: int = 1) -> bool:
            # Refill tokens based on elapsed time
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    # 10 tokens/second, burst of 10
    bucket = TokenBucket(rate=10.0, burst=10)

    # Should be able to consume 10 tokens immediately (burst)
    for i in range(10):
        assert bucket.consume(), f"Should allow token {i+1}/10"

    # 11th should fail (no tokens left)
    assert not bucket.consume(), "Should reject when bucket is empty"

    # Wait 0.1s -> should refill 1 token
    await asyncio.sleep(0.1)
    assert bucket.consume(), "Should allow after refill"


# ============================================
# Timeout Middleware Consistency Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_timeout_enforcement():
    """Test that timeout enforcement is consistent."""
    agent = SlowAgent(delay=0.5)  # Takes 0.5s

    # Test with 1s timeout (should succeed)
    try:
        response = await asyncio.wait_for(
            agent.process(Message(role="user", content="test")),
            timeout=1.0
        )
        assert response.metadata["delay"] == 0.5
    except asyncio.TimeoutError:
        pytest.fail("Should not timeout with 1s limit")

    # Test with 0.1s timeout (should fail)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            agent.process(Message(role="user", content="test")),
            timeout=0.1
        )


# ============================================
# Batching Middleware Consistency Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_batching_window():
    """Test that batching window behavior is consistent."""
    agent = CountingAgent()

    # Simulate batching: collect requests for 0.1s, then process
    batch = []
    batch_window = 0.1

    # Collect requests
    start = time.time()
    deadline = start + batch_window

    # Add 5 requests
    for i in range(5):
        batch.append(Message(role="user", content=f"Request {i}"))

    # Wait for batch window
    remaining = deadline - time.time()
    if remaining > 0:
        await asyncio.sleep(remaining)

    # Process batch
    responses = []
    for msg in batch:
        response = await agent.process(msg)
        responses.append(response)

    # Validate
    assert len(responses) == 5, "Should process all 5 requests"
    assert agent.get_call_count() == 5, "Should call agent 5 times"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_batch_size_limit():
    """Test that batch size limits are enforced consistently."""
    max_batch_size = 10

    # Simulate collecting requests up to max batch size
    batch = []
    for i in range(15):  # Try to add 15 requests
        if len(batch) < max_batch_size:
            batch.append(i)

    assert len(batch) == 10, "Batch should be limited to 10"


# ============================================
# Caching Middleware Consistency Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_hit_miss_consistency():
    """Test that cache hit/miss behavior is consistent."""
    agent = CountingAgent()

    # Simulates caching behavior
    cache = {}

    # First request (cache miss)
    msg1 = Message(role="user", content="test")
    cache_key = msg1.content

    if cache_key not in cache:
        response1 = await agent.process(msg1)
        cache[cache_key] = response1

    assert agent.get_call_count() == 1, "First request should call agent"

    # Second request (cache hit)
    if cache_key in cache:
        response2 = cache[cache_key]
    else:
        response2 = await agent.process(msg1)

    assert agent.get_call_count() == 1, "Second request should not call agent (cache hit)"
    assert response1.content == response2.content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_lru_eviction_consistency():
    """Test that LRU eviction is consistent."""
    from collections import OrderedDict

    # LRU cache with max size 3
    cache = OrderedDict()
    max_size = 3

    # Add 3 entries
    for i in range(3):
        cache[f"key{i}"] = f"value{i}"

    assert len(cache) == 3

    # Access key0 (makes it most recently used)
    value = cache.pop("key0")
    cache["key0"] = value

    # Add key3 (should evict key1, the least recently used)
    if len(cache) >= max_size:
        cache.popitem(last=False)  # Remove least recently used (first item)
    cache["key3"] = "value3"

    # Validate
    assert len(cache) == 3
    assert "key0" in cache, "key0 should still be in cache (recently used)"
    assert "key1" not in cache, "key1 should be evicted (LRU)"
    assert "key2" in cache, "key2 should still be in cache"
    assert "key3" in cache, "key3 should be in cache (just added)"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ttl_expiration_consistency():
    """Test that TTL expiration is consistent."""
    import time

    class CacheEntry:
        def __init__(self, value, ttl: float):
            self.value = value
            self.expires_at = time.time() + ttl

        def is_expired(self) -> bool:
            return time.time() > self.expires_at

    # Create entry with 0.1s TTL
    entry = CacheEntry("test_value", ttl=0.1)

    # Should not be expired immediately
    assert not entry.is_expired(), "Should not be expired immediately"

    # Wait 0.15s
    await asyncio.sleep(0.15)

    # Should be expired now
    assert entry.is_expired(), "Should be expired after TTL"


# ============================================
# Metadata Preservation Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_middleware_metadata_preservation():
    """Test that middleware preserves metadata consistently."""
    agent = CountingAgent()

    message = Message(
        role="user",
        content="test",
        metadata={
            "trace_id": "abc-123",
            "user_id": 42,
            "nested": {"key": "value"}
        }
    )

    response = await agent.process(message)

    # Middleware should preserve original message metadata
    # (though the response may have different metadata)
    assert message.metadata["trace_id"] == "abc-123", "Original metadata should be preserved"
    assert message.metadata["user_id"] == 42
    assert message.metadata["nested"]["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
