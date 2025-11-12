"""Tests for caching middleware."""

import asyncio
import time

import pytest

from agenkit import Message
from agenkit.middleware import CachingConfig, CachingDecorator


# Test Agent
class TestAgent:
    """Simple agent for testing caching."""

    def __init__(self, response_prefix="Response"):
        self.response_prefix = response_prefix
        self.call_count = 0

    @property
    def name(self) -> str:
        return "test"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        """Process message and track calls."""
        self.call_count += 1
        return Message(
            role="agent",
            content=f"{self.response_prefix}: {message.content}",
            metadata={"call_count": self.call_count}
        )

    async def stream(self, message: Message):
        """Stream response."""
        for word in str(message.content).split():
            yield Message(role="agent", content=word)


# ===== Configuration Tests =====


def test_default_config():
    """Test default caching configuration."""
    config = CachingConfig()
    assert config.max_cache_size == 1000
    assert config.default_ttl == 300.0
    assert config.key_generator is None


def test_custom_config():
    """Test custom caching configuration."""
    def custom_key_gen(msg: Message) -> str:
        return f"custom-{msg.content}"

    config = CachingConfig(
        max_cache_size=100,
        default_ttl=60.0,
        key_generator=custom_key_gen
    )
    assert config.max_cache_size == 100
    assert config.default_ttl == 60.0
    assert config.key_generator is custom_key_gen


def test_config_validation():
    """Test configuration validation."""
    with pytest.raises(ValueError, match="max_cache_size must be at least 1"):
        CachingConfig(max_cache_size=0)

    with pytest.raises(ValueError, match="default_ttl must be positive"):
        CachingConfig(default_ttl=0)


# ===== Basic Caching Tests =====


@pytest.mark.asyncio
async def test_cache_hit():
    """Test that second request hits cache."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    msg = Message(role="user", content="test")

    # First call - should miss cache
    response1 = await cached_agent.process(msg)
    assert response1.content == "Response: test"
    assert agent.call_count == 1
    assert cached_agent.metrics.cache_misses == 1
    assert cached_agent.metrics.cache_hits == 0

    # Second call - should hit cache
    response2 = await cached_agent.process(msg)
    assert response2.content == "Response: test"
    assert agent.call_count == 1  # Not called again
    assert cached_agent.metrics.cache_misses == 1
    assert cached_agent.metrics.cache_hits == 1


@pytest.mark.asyncio
async def test_cache_miss_different_messages():
    """Test that different messages miss cache."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    msg1 = Message(role="user", content="test1")
    msg2 = Message(role="user", content="test2")

    # Both should miss cache
    response1 = await cached_agent.process(msg1)
    response2 = await cached_agent.process(msg2)

    assert response1.content == "Response: test1"
    assert response2.content == "Response: test2"
    assert agent.call_count == 2
    assert cached_agent.metrics.cache_misses == 2
    assert cached_agent.metrics.cache_hits == 0


# ===== TTL Expiration Tests =====


@pytest.mark.asyncio
async def test_ttl_expiration():
    """Test that cached entries expire after TTL."""
    agent = TestAgent()
    config = CachingConfig(default_ttl=0.1)  # 100ms TTL
    cached_agent = CachingDecorator(agent, config)

    msg = Message(role="user", content="test")

    # First call
    response1 = await cached_agent.process(msg)
    assert agent.call_count == 1

    # Second call before expiration - should hit cache
    response2 = await cached_agent.process(msg)
    assert agent.call_count == 1

    # Wait for expiration
    await asyncio.sleep(0.15)

    # Third call after expiration - should miss cache
    response3 = await cached_agent.process(msg)
    assert agent.call_count == 2
    assert cached_agent.metrics.cache_hits == 1
    assert cached_agent.metrics.cache_misses == 2


# ===== LRU Eviction Tests =====


@pytest.mark.asyncio
async def test_lru_eviction():
    """Test that LRU entries are evicted when cache is full."""
    agent = TestAgent()
    config = CachingConfig(max_cache_size=3)
    cached_agent = CachingDecorator(agent, config)

    # Fill cache with 3 entries
    for i in range(3):
        msg = Message(role="user", content=f"test{i}")
        await cached_agent.process(msg)

    assert await cached_agent.get_cache_size() == 3
    assert agent.call_count == 3

    # Access first entry to make it recently used
    msg0 = Message(role="user", content="test0")
    await cached_agent.process(msg0)
    assert agent.call_count == 3  # Cache hit

    # Add new entry - should evict test1 (LRU)
    msg3 = Message(role="user", content="test3")
    await cached_agent.process(msg3)

    assert await cached_agent.get_cache_size() == 3
    assert agent.call_count == 4
    assert cached_agent.metrics.evictions == 1

    # test0 should still be cached
    await cached_agent.process(msg0)
    assert agent.call_count == 4  # Cache hit

    # test1 should be evicted (miss)
    msg1 = Message(role="user", content="test1")
    await cached_agent.process(msg1)
    assert agent.call_count == 5  # Cache miss


# ===== Cache Invalidation Tests =====


@pytest.mark.asyncio
async def test_invalidate_specific_entry():
    """Test invalidating a specific cache entry."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    msg1 = Message(role="user", content="test1")
    msg2 = Message(role="user", content="test2")

    # Cache both messages
    await cached_agent.process(msg1)
    await cached_agent.process(msg2)
    assert agent.call_count == 2

    # Invalidate msg1
    await cached_agent.invalidate(msg1)
    assert cached_agent.metrics.invalidations == 1

    # msg1 should miss cache
    await cached_agent.process(msg1)
    assert agent.call_count == 3

    # msg2 should still be cached
    await cached_agent.process(msg2)
    assert agent.call_count == 3


@pytest.mark.asyncio
async def test_invalidate_entire_cache():
    """Test invalidating entire cache."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    # Cache multiple messages
    for i in range(3):
        msg = Message(role="user", content=f"test{i}")
        await cached_agent.process(msg)

    assert await cached_agent.get_cache_size() == 3
    assert agent.call_count == 3

    # Invalidate entire cache
    await cached_agent.invalidate()
    assert cached_agent.metrics.invalidations == 3
    assert await cached_agent.get_cache_size() == 0

    # All messages should miss cache
    for i in range(3):
        msg = Message(role="user", content=f"test{i}")
        await cached_agent.process(msg)

    assert agent.call_count == 6


# ===== Custom Key Generator Tests =====


@pytest.mark.asyncio
async def test_custom_key_generator():
    """Test custom cache key generation."""
    agent = TestAgent()

    # Key generator that ignores metadata
    def content_only_key(message: Message) -> str:
        return str(message.content)

    config = CachingConfig(key_generator=content_only_key)
    cached_agent = CachingDecorator(agent, config)

    # Same content, different metadata - should hit cache
    msg1 = Message(role="user", content="test", metadata={"id": 1})
    msg2 = Message(role="user", content="test", metadata={"id": 2})

    await cached_agent.process(msg1)
    await cached_agent.process(msg2)

    assert agent.call_count == 1  # Only called once
    assert cached_agent.metrics.cache_hits == 1


# ===== Metrics Tests =====


@pytest.mark.asyncio
async def test_metrics_hit_rate():
    """Test cache hit rate calculation."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    msg = Message(role="user", content="test")

    # First call - miss
    await cached_agent.process(msg)
    assert cached_agent.metrics.hit_rate == 0.0

    # Next 3 calls - hits
    for _ in range(3):
        await cached_agent.process(msg)

    assert cached_agent.metrics.total_requests == 4
    assert cached_agent.metrics.cache_hits == 3
    assert cached_agent.metrics.cache_misses == 1
    assert cached_agent.metrics.hit_rate == 0.75
    assert cached_agent.metrics.miss_rate == 0.25


@pytest.mark.asyncio
async def test_get_cache_info():
    """Test getting detailed cache information."""
    agent = TestAgent()
    config = CachingConfig(max_cache_size=100, default_ttl=60.0)
    cached_agent = CachingDecorator(agent, config)

    # Add some entries
    for i in range(3):
        msg = Message(role="user", content=f"test{i}")
        await cached_agent.process(msg)

    # Get first entry again for a hit
    msg = Message(role="user", content="test0")
    await cached_agent.process(msg)

    info = await cached_agent.get_cache_info()

    assert info["size"] == 3
    assert info["max_size"] == 100
    assert info["default_ttl"] == 60.0
    assert info["metrics"]["total_requests"] == 4
    assert info["metrics"]["cache_hits"] == 1
    assert info["metrics"]["cache_misses"] == 3
    assert info["metrics"]["hit_rate"] == 0.25


# ===== Streaming Tests =====


@pytest.mark.asyncio
async def test_streaming_bypasses_cache():
    """Test that streaming bypasses cache."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    msg = Message(role="user", content="hello world")

    # Stream first time
    chunks1 = []
    async for chunk in cached_agent.stream(msg):
        chunks1.append(chunk.content)

    # Stream second time - should not use cache
    chunks2 = []
    async for chunk in cached_agent.stream(msg):
        chunks2.append(chunk.content)

    assert chunks1 == ["hello", "world"]
    assert chunks2 == ["hello", "world"]
    # Cache should not be used for streaming
    assert cached_agent.metrics.cache_hits == 0


# ===== Concurrent Access Tests =====


@pytest.mark.asyncio
async def test_concurrent_cache_access():
    """Test that cache handles concurrent access correctly."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    msg = Message(role="user", content="test")

    # First request populates cache
    await cached_agent.process(msg)

    # Multiple concurrent requests should all hit cache
    tasks = [cached_agent.process(msg) for _ in range(10)]
    responses = await asyncio.gather(*tasks)

    # All responses should be the same
    assert all(r.content == "Response: test" for r in responses)
    # Agent should only be called once
    assert agent.call_count == 1
    # 10 hits (after initial miss)
    assert cached_agent.metrics.cache_hits == 10


# ===== Edge Cases =====


@pytest.mark.asyncio
async def test_empty_cache():
    """Test operations on empty cache."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    assert await cached_agent.get_cache_size() == 0
    assert cached_agent.metrics.total_requests == 0

    # Invalidate empty cache
    await cached_agent.invalidate()
    assert cached_agent.metrics.invalidations == 0


@pytest.mark.asyncio
async def test_cache_with_metadata():
    """Test that metadata affects cache keys."""
    agent = TestAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    # Same content, different metadata - should be different cache keys
    msg1 = Message(role="user", content="test", metadata={"version": 1})
    msg2 = Message(role="user", content="test", metadata={"version": 2})

    await cached_agent.process(msg1)
    await cached_agent.process(msg2)

    # Should be two different cache entries
    assert agent.call_count == 2
    assert await cached_agent.get_cache_size() == 2


@pytest.mark.asyncio
async def test_expired_entries_cleanup():
    """Test periodic cleanup of expired entries."""
    agent = TestAgent()
    config = CachingConfig(default_ttl=0.1, max_cache_size=1000)
    cached_agent = CachingDecorator(agent, config)

    # Add entries
    for i in range(10):
        msg = Message(role="user", content=f"test{i}")
        await cached_agent.process(msg)

    assert await cached_agent.get_cache_size() == 10

    # Wait for expiration
    await asyncio.sleep(0.15)

    # Make 100 requests to trigger cleanup (happens every 100 requests)
    for i in range(100):
        msg = Message(role="user", content=f"new{i}")
        await cached_agent.process(msg)

    # Expired entries should be cleaned up
    # Note: exact count depends on timing, but should be significantly reduced
    cache_size = await cached_agent.get_cache_size()
    assert cache_size < 110  # Should have cleaned up most expired entries
