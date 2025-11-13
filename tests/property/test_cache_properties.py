"""
Cache Middleware Property-Based Tests

Validates invariants that should hold for caching behavior:
- Cache hit rate is always in [0.0, 1.0]
- LRU ordering (most recently used not evicted first)
- TTL expiration (expired entries never returned)
- Size bounds (cache size never exceeds max)
- Idempotency (same key returns same cached result)
"""
import asyncio
import time
from collections import OrderedDict

import pytest
from hypothesis import given, settings, assume, strategies as st

from agenkit.interfaces import Agent, Message
from tests.property.strategies import (
    positive_int_strategy,
    small_positive_int_strategy,
    short_content_strategy,
    message_strategy,
)


class SimpleAgent(Agent):
    """Simple test agent."""

    def __init__(self, name: str = "simple"):
        self._name = name
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        self._call_count += 1
        return Message(
            role="agent",
            content=f"Processed: {message.content}",
            metadata={"call_count": self._call_count}
        )

    def get_call_count(self) -> int:
        return self._call_count


class SimpleCache:
    """Simple cache implementation for property testing."""

    def __init__(self, max_size: int, default_ttl: float):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._expiry: dict = {}
        self._hits = 0
        self._misses = 0

    def get_cache_size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get(self, key: str) -> Message | None:
        """Get from cache."""
        # Check if key exists
        if key not in self._cache:
            self._misses += 1
            return None

        # Check if expired
        if time.time() > self._expiry.get(key, float('inf')):
            self._cache.pop(key, None)
            self._expiry.pop(key, None)
            self._misses += 1
            return None

        # Hit - move to end (most recently used)
        self._hits += 1
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: str, value: Message, ttl: float | None = None):
        """Put into cache."""
        # Evict if at capacity and key doesn't exist
        if key not in self._cache and len(self._cache) >= self._max_size:
            # Evict least recently used (first item)
            evicted_key = next(iter(self._cache))
            self._cache.pop(evicted_key)
            self._expiry.pop(evicted_key, None)

        # Add/update entry
        self._cache[key] = value
        self._cache.move_to_end(key)
        self._expiry[key] = time.time() + (ttl if ttl is not None else self._default_ttl)

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": self.get_cache_size(),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.get_hit_rate(),
        }


# ============================================
# Property: Cache Size Never Exceeds Max
# ============================================

@pytest.mark.property
@given(
    max_size=st.integers(min_value=1, max_value=50),
    num_requests=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100, deadline=None)
def test_cache_size_never_exceeds_max(max_size, num_requests):
    """Property: Cache size never exceeds max_cache_size."""
    cache = SimpleCache(max_size=max_size, default_ttl=3600)

    # Make many requests with different keys
    for i in range(num_requests):
        key = f"key_{i}"
        value = Message(role="user", content=f"Value {i}")
        cache.put(key, value)

        # Property: size never exceeds max
        assert cache.get_cache_size() <= max_size, \
            f"Cache size {cache.get_cache_size()} exceeds max {max_size}"


# ============================================
# Property: Hit Rate is in [0.0, 1.0]
# ============================================

@pytest.mark.property
@given(
    max_size=small_positive_int_strategy,
    num_puts=st.integers(min_value=1, max_value=20),
    num_gets=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=100, deadline=None)
def test_hit_rate_always_valid(max_size, num_puts, num_gets):
    """Property: Hit rate is always in [0.0, 1.0]."""
    cache = SimpleCache(max_size=max_size, default_ttl=3600)

    # Put some entries
    for i in range(num_puts):
        key = f"key_{i}"
        value = Message(role="user", content=f"Value {i}")
        cache.put(key, value)

    # Get entries (some hits, some misses)
    for i in range(num_gets):
        key = f"key_{i % (num_puts + 5)}"  # Mix of valid and invalid keys
        cache.get(key)

    # Property: hit rate in [0.0, 1.0]
    hit_rate = cache.get_hit_rate()
    assert 0.0 <= hit_rate <= 1.0, f"Hit rate {hit_rate} not in [0.0, 1.0]"


# ============================================
# Property: LRU Ordering
# ============================================

@pytest.mark.property
@given(
    max_size=st.integers(min_value=2, max_value=10),
)
@settings(max_examples=100, deadline=None)
def test_lru_ordering_most_recent_not_evicted(max_size):
    """Property: Most recently used items are not evicted first."""
    cache = SimpleCache(max_size=max_size, default_ttl=3600)

    # Fill cache to capacity
    for i in range(max_size):
        cache.put(f"key_{i}", Message(role="user", content=f"Value {i}"))

    # Access key_0 to make it most recently used
    result = cache.get("key_0")
    assert result is not None, "key_0 should be in cache"

    # Add new entry (should evict LRU, which is key_1)
    cache.put(f"key_{max_size}", Message(role="user", content=f"Value {max_size}"))

    # Property: Most recently used (key_0) should still be in cache
    result = cache.get("key_0")
    assert result is not None, "Most recently used key_0 should not be evicted"

    # Property: Least recently used (key_1) should be evicted
    result = cache.get("key_1")
    assert result is None, "Least recently used key_1 should be evicted"


# ============================================
# Property: TTL Expiration
# ============================================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    ttl=st.floats(min_value=0.05, max_value=0.2),
)
@settings(max_examples=50, deadline=None)
async def test_ttl_expiration_never_returns_expired(ttl):
    """Property: Expired entries are never returned."""
    cache = SimpleCache(max_size=10, default_ttl=ttl)

    # Put entry with short TTL
    cache.put("key", Message(role="user", content="Value"), ttl=ttl)

    # Should be available immediately
    result = cache.get("key")
    assert result is not None, "Entry should be available before expiration"

    # Wait for expiration
    await asyncio.sleep(ttl + 0.05)

    # Property: Expired entry should not be returned
    result = cache.get("key")
    assert result is None, "Expired entry should not be returned"


# ============================================
# Property: Idempotency
# ============================================

@pytest.mark.property
@given(
    content=short_content_strategy,
    num_accesses=st.integers(min_value=2, max_value=20),
)
@settings(max_examples=100, deadline=None)
def test_cache_idempotency_same_key_same_result(content, num_accesses):
    """Property: Same key always returns same cached result."""
    cache = SimpleCache(max_size=10, default_ttl=3600)

    # Put entry
    key = "test_key"
    value = Message(role="user", content=content)
    cache.put(key, value)

    # Access multiple times
    results = []
    for _ in range(num_accesses):
        result = cache.get(key)
        if result is not None:
            results.append(result)

    # Property: All results should be identical
    assert len(results) > 0, "Should have at least one result"
    first_result = results[0]
    for result in results[1:]:
        assert result.content == first_result.content, \
            "Same key should return same content"
        assert result.role == first_result.role, \
            "Same key should return same role"


# ============================================
# Property: Cache Statistics Consistency
# ============================================

@pytest.mark.property
@given(
    max_size=small_positive_int_strategy,
    operations=st.lists(
        st.tuples(
            st.sampled_from(["put", "get"]),
            st.integers(min_value=0, max_value=20)  # key index
        ),
        min_size=1,
        max_size=50
    ),
)
@settings(max_examples=100, deadline=None)
def test_cache_statistics_consistency(max_size, operations):
    """Property: total_requests = hits + misses."""
    cache = SimpleCache(max_size=max_size, default_ttl=3600)

    total_gets = 0

    for op_type, key_idx in operations:
        key = f"key_{key_idx}"

        if op_type == "put":
            value = Message(role="user", content=f"Value {key_idx}")
            cache.put(key, value)
        else:  # get
            cache.get(key)
            total_gets += 1

    # Property: hits + misses = total get requests
    stats = cache.get_stats()
    assert stats["hits"] + stats["misses"] == total_gets, \
        f"hits ({stats['hits']}) + misses ({stats['misses']}) != total gets ({total_gets})"


# ============================================
# Property: Size Bounds After Eviction
# ============================================

@pytest.mark.property
@given(
    max_size=st.integers(min_value=1, max_value=20),
    num_entries=st.integers(min_value=1, max_value=100),
)
@settings(max_examples=100, deadline=None)
def test_cache_size_bounds_after_eviction(max_size, num_entries):
    """Property: After eviction, cache size is exactly max_size (if enough entries)."""
    assume(num_entries > max_size)  # Only test when eviction would occur

    cache = SimpleCache(max_size=max_size, default_ttl=3600)

    # Add more entries than max_size
    for i in range(num_entries):
        cache.put(f"key_{i}", Message(role="user", content=f"Value {i}"))

    # Property: Cache should be exactly at max_size
    assert cache.get_cache_size() == max_size, \
        f"Cache size {cache.get_cache_size()} should equal max_size {max_size} after eviction"


# ============================================
# Property: No Duplicate Keys
# ============================================

@pytest.mark.property
@given(
    max_size=small_positive_int_strategy,
    key_indices=st.lists(st.integers(min_value=0, max_value=50), min_size=1, max_size=100),
)
@settings(max_examples=100, deadline=None)
def test_cache_no_duplicate_keys(max_size, key_indices):
    """Property: Cache never contains duplicate keys."""
    cache = SimpleCache(max_size=max_size, default_ttl=3600)

    # Add entries (may have duplicate indices)
    for idx in key_indices:
        key = f"key_{idx}"
        value = Message(role="user", content=f"Value {idx}")
        cache.put(key, value)

    # Property: All keys in cache are unique
    keys_in_cache = list(cache._cache.keys())
    assert len(keys_in_cache) == len(set(keys_in_cache)), \
        "Cache should not contain duplicate keys"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
