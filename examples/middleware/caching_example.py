#!/usr/bin/env python3
"""Example demonstrating caching middleware.

This example shows how to use the caching middleware to:
1. Cache agent responses for repeated requests
2. Configure TTL-based expiration
3. Handle LRU eviction when cache is full
4. Invalidate cache entries
5. Track cache metrics (hits, misses, hit rate)
"""

import asyncio
import time

from agenkit import Agent, Message
from agenkit.middleware import CachingConfig, CachingDecorator


class SlowAgent(Agent):
    """Example agent that simulates slow processing."""

    @property
    def name(self) -> str:
        return "slow_agent"

    async def process(self, message: Message) -> Message:
        """Process message with artificial delay."""
        # Simulate expensive operation (e.g., LLM API call)
        await asyncio.sleep(0.5)
        return Message(
            role="agent",
            content=f"Processed: {message.content}",
            metadata={"processing_time": 0.5}
        )


async def scenario_1_basic_caching():
    """Scenario 1: Basic caching for repeated requests."""
    print("=" * 70)
    print("SCENARIO 1: Basic Caching")
    print("=" * 70)
    print()

    # Create agent with caching
    agent = SlowAgent()
    config = CachingConfig(
        max_cache_size=1000,
        default_ttl=300.0  # 5 minutes
    )
    cached_agent = CachingDecorator(agent, config)

    message = Message(role="user", content="What is AI?")

    # First request - cache miss
    print("Request 1 (cache miss - should take ~500ms):")
    start = time.time()
    response = await cached_agent.process(message)
    elapsed = time.time() - start
    print(f"  Response: {response.content}")
    print(f"  Time: {elapsed*1000:.0f}ms")
    print()

    # Second request - cache hit
    print("Request 2 (cache hit - should be instant):")
    start = time.time()
    response = await cached_agent.process(message)
    elapsed = time.time() - start
    print(f"  Response: {response.content}")
    print(f"  Time: {elapsed*1000:.0f}ms")
    print()

    # Show metrics
    print("Cache Metrics:")
    print(f"  Total requests: {cached_agent.metrics.total_requests}")
    print(f"  Cache hits: {cached_agent.metrics.cache_hits}")
    print(f"  Cache misses: {cached_agent.metrics.cache_misses}")
    print(f"  Hit rate: {cached_agent.metrics.hit_rate*100:.1f}%")
    print()


async def scenario_2_ttl_expiration():
    """Scenario 2: TTL-based cache expiration."""
    print("=" * 70)
    print("SCENARIO 2: TTL-Based Expiration")
    print("=" * 70)
    print()

    # Create agent with short TTL
    agent = SlowAgent()
    config = CachingConfig(
        max_cache_size=1000,
        default_ttl=1.0  # 1 second TTL
    )
    cached_agent = CachingDecorator(agent, config)

    message = Message(role="user", content="Tell me a joke")

    # First request
    print("Request 1:")
    start = time.time()
    await cached_agent.process(message)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache miss)")
    print()

    # Second request (within TTL)
    print("Request 2 (within 1s TTL):")
    start = time.time()
    await cached_agent.process(message)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache hit)")
    print()

    # Wait for expiration
    print("Waiting for TTL expiration (1.5s)...")
    await asyncio.sleep(1.5)
    print()

    # Third request (after TTL)
    print("Request 3 (after TTL expiration):")
    start = time.time()
    await cached_agent.process(message)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache miss - expired)")
    print()


async def scenario_3_lru_eviction():
    """Scenario 3: LRU eviction when cache is full."""
    print("=" * 70)
    print("SCENARIO 3: LRU Eviction")
    print("=" * 70)
    print()

    # Create agent with small cache
    agent = SlowAgent()
    config = CachingConfig(
        max_cache_size=3,  # Only 3 entries
        default_ttl=300.0
    )
    cached_agent = CachingDecorator(agent, config)

    # Fill cache
    print("Filling cache with 3 entries:")
    for i in range(3):
        msg = Message(role="user", content=f"Question {i}")
        await cached_agent.process(msg)
        print(f"  Added: Question {i}")

    print(f"\nCache size: {await cached_agent.get_cache_size()}")
    print()

    # Access first entry to make it recently used
    print("Accessing Question 0 (mark as recently used):")
    msg0 = Message(role="user", content="Question 0")
    start = time.time()
    await cached_agent.process(msg0)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache hit)")
    print()

    # Add new entry - should evict Question 1 (LRU)
    print("Adding Question 3 (should evict Question 1):")
    msg3 = Message(role="user", content="Question 3")
    await cached_agent.process(msg3)
    print(f"  Evictions: {cached_agent.metrics.evictions}")
    print()

    # Verify Question 0 is still cached
    print("Verifying Question 0 is still cached:")
    start = time.time()
    await cached_agent.process(msg0)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache hit)")
    print()

    # Verify Question 1 was evicted
    print("Verifying Question 1 was evicted:")
    msg1 = Message(role="user", content="Question 1")
    start = time.time()
    await cached_agent.process(msg1)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache miss - evicted)")
    print()


async def scenario_4_cache_invalidation():
    """Scenario 4: Manual cache invalidation."""
    print("=" * 70)
    print("SCENARIO 4: Cache Invalidation")
    print("=" * 70)
    print()

    agent = SlowAgent()
    cached_agent = CachingDecorator(agent, CachingConfig())

    # Cache some responses
    msg1 = Message(role="user", content="Weather today")
    msg2 = Message(role="user", content="Stock price")

    print("Caching two messages:")
    await cached_agent.process(msg1)
    await cached_agent.process(msg2)
    print(f"  Cache size: {await cached_agent.get_cache_size()}")
    print()

    # Invalidate specific entry
    print("Invalidating 'Weather today':")
    await cached_agent.invalidate(msg1)
    print(f"  Cache size: {await cached_agent.get_cache_size()}")
    print()

    # Verify msg1 is invalidated (miss) but msg2 is still cached (hit)
    print("Testing cache after invalidation:")
    start = time.time()
    await cached_agent.process(msg1)
    elapsed1 = time.time() - start
    print(f"  Weather today: {elapsed1*1000:.0f}ms (cache miss)")

    start = time.time()
    await cached_agent.process(msg2)
    elapsed2 = time.time() - start
    print(f"  Stock price: {elapsed2*1000:.0f}ms (cache hit)")
    print()

    # Invalidate entire cache
    print("Invalidating entire cache:")
    await cached_agent.invalidate()
    print(f"  Cache size: {await cached_agent.get_cache_size()}")
    print(f"  Total invalidations: {cached_agent.metrics.invalidations}")
    print()


async def scenario_5_custom_key_generator():
    """Scenario 5: Custom cache key generation."""
    print("=" * 70)
    print("SCENARIO 5: Custom Key Generator")
    print("=" * 70)
    print()

    # Key generator that ignores metadata
    def content_only_key(message: Message) -> str:
        return f"key:{message.content}"

    agent = SlowAgent()
    config = CachingConfig(
        max_cache_size=1000,
        default_ttl=300.0,
        key_generator=content_only_key
    )
    cached_agent = CachingDecorator(agent, config)

    # Same content, different metadata
    msg1 = Message(role="user", content="Translate: Hello", metadata={"lang": "es"})
    msg2 = Message(role="user", content="Translate: Hello", metadata={"lang": "fr"})

    print("Request 1 (Spanish):")
    start = time.time()
    await cached_agent.process(msg1)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache miss)")
    print()

    print("Request 2 (French - same content, different metadata):")
    start = time.time()
    await cached_agent.process(msg2)
    elapsed = time.time() - start
    print(f"  Time: {elapsed*1000:.0f}ms (cache hit - key ignores metadata)")
    print()

    print("Note: Custom key generator treats these as same request")
    print()


async def scenario_6_cache_metrics():
    """Scenario 6: Comprehensive cache metrics."""
    print("=" * 70)
    print("SCENARIO 6: Cache Metrics")
    print("=" * 70)
    print()

    agent = SlowAgent()
    cached_agent = CachingDecorator(agent, CachingConfig(max_cache_size=100))

    # Make various requests
    print("Making 10 requests (5 unique, 5 repeated):")
    for i in range(10):
        # First 5 are unique, next 5 repeat
        msg_id = i % 5
        msg = Message(role="user", content=f"Question {msg_id}")
        await cached_agent.process(msg)

    print()

    # Get detailed cache info
    info = await cached_agent.get_cache_info()

    print("Cache Configuration:")
    print(f"  Max size: {info['max_size']}")
    print(f"  TTL: {info['default_ttl']}s")
    print()

    print("Cache Statistics:")
    print(f"  Current size: {info['size']}")
    print(f"  Total requests: {info['metrics']['total_requests']}")
    print(f"  Cache hits: {info['metrics']['cache_hits']}")
    print(f"  Cache misses: {info['metrics']['cache_misses']}")
    print(f"  Hit rate: {info['metrics']['hit_rate']*100:.1f}%")
    print(f"  Miss rate: {info['metrics']['miss_rate']*100:.1f}%")
    print(f"  Evictions: {info['metrics']['evictions']}")
    print(f"  Invalidations: {info['metrics']['invalidations']}")
    print()


async def main():
    """Run all caching examples."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "Caching Middleware Demo" + " " * 25 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    await scenario_1_basic_caching()
    await asyncio.sleep(0.5)

    await scenario_2_ttl_expiration()
    await asyncio.sleep(0.5)

    await scenario_3_lru_eviction()
    await asyncio.sleep(0.5)

    await scenario_4_cache_invalidation()
    await asyncio.sleep(0.5)

    await scenario_5_custom_key_generator()
    await asyncio.sleep(0.5)

    await scenario_6_cache_metrics()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("Caching Benefits:")
    print("  ✓ Reduces latency for repeated requests")
    print("  ✓ Reduces cost (fewer LLM API calls)")
    print("  ✓ Improves throughput")
    print("  ✓ Configurable TTL and LRU eviction")
    print("  ✓ Cache invalidation support")
    print("  ✓ Comprehensive metrics")
    print()
    print("Use caching when:")
    print("  • Requests are frequently repeated")
    print("  • Responses are deterministic or acceptable to be stale")
    print("  • Cost/latency reduction is more important than freshness")
    print("  • Traffic patterns have locality (similar requests)")
    print()
    print("Avoid caching when:")
    print("  • Responses must always be fresh")
    print("  • Requests are always unique")
    print("  • Memory is constrained")
    print()


if __name__ == "__main__":
    asyncio.run(main())
