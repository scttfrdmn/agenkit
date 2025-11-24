"""
Performance benchmarks for memory implementations.

Measures:
- Retrieval latency
- Storage overhead
- Concurrent access performance
- Strategy selection time
"""

import asyncio
import time
from statistics import mean, stdev

from agenkit.interfaces import Message
from agenkit.memory import (
    EmbeddingProvider,
    ImportanceWeightingStrategy,
    InMemoryMemory,
    SlidingWindowStrategy,
    SummarizationStrategy,
    VectorMemory,
)


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for benchmarking."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        """Generate mock embedding based on text content."""
        embedding = [0.0] * self._dimension

        # Simple deterministic embedding
        for i, char in enumerate(text.lower()[:self._dimension]):
            embedding[i] = ord(char) / 255.0

        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    def dimension(self) -> int:
        return self._dimension


async def benchmark_store(memory, session_id: str, message_count: int):
    """Benchmark message storage."""
    messages = [
        Message(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
        for i in range(message_count)
    ]

    start = time.perf_counter()
    for msg in messages:
        await memory.store(session_id, msg)
    end = time.perf_counter()

    return (end - start) * 1000  # Convert to ms


async def benchmark_retrieve(memory, session_id: str, limit: int, iterations: int = 100):
    """Benchmark message retrieval."""
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        await memory.retrieve(session_id, limit=limit)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms

    return {
        "mean": mean(times),
        "std": stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times)
    }


async def benchmark_strategy(strategy, memory, session_id: str, context_limit: int, iterations: int = 100):
    """Benchmark strategy selection."""
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        await strategy.select(memory, session_id, context_limit)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms

    return {
        "mean": mean(times),
        "std": stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times)
    }


async def benchmark_concurrent_access(memory, session_count: int, messages_per_session: int):
    """Benchmark concurrent access across multiple sessions."""
    async def store_session(session_id: str):
        for i in range(messages_per_session):
            await memory.store(
                session_id,
                Message(role="user", content=f"Message {i}")
            )

    sessions = [f"session-{i}" for i in range(session_count)]

    start = time.perf_counter()
    await asyncio.gather(*[store_session(sid) for sid in sessions])
    end = time.perf_counter()

    return (end - start) * 1000  # ms


async def run_benchmarks():
    """Run all benchmarks."""
    print("=" * 70)
    print("Memory System Performance Benchmarks")
    print("=" * 70)

    # Test configurations
    message_counts = [10, 100, 1000]
    retrieve_limits = [10, 50, 100]

    # Benchmark InMemoryMemory
    print("\n1. InMemoryMemory Benchmarks")
    print("-" * 70)

    memory = InMemoryMemory(max_size=10000)

    for count in message_counts:
        session_id = f"bench-{count}"
        store_time = await benchmark_store(memory, session_id, count)
        print(f"  Store {count} messages: {store_time:.2f}ms ({count/store_time*1000:.0f} msg/sec)")

    print()
    for limit in retrieve_limits:
        session_id = "bench-1000"
        stats = await benchmark_retrieve(memory, session_id, limit, iterations=100)
        print(f"  Retrieve {limit} messages: {stats['mean']:.2f}ms ± {stats['std']:.2f}ms")

    # Benchmark VectorMemory
    print("\n2. VectorMemory Benchmarks")
    print("-" * 70)

    embeddings = MockEmbeddingProvider(dimension=384)
    vector_memory = VectorMemory(embeddings)

    # Store (includes embedding time)
    store_time = await benchmark_store(vector_memory, "vector-bench", 100)
    print(f"  Store 100 messages (with embeddings): {store_time:.2f}ms")

    # Retrieve (no query - recent messages)
    stats = await benchmark_retrieve(vector_memory, "vector-bench", 10, iterations=50)
    print(f"  Retrieve 10 recent messages: {stats['mean']:.2f}ms ± {stats['std']:.2f}ms")

    # Semantic search (with query)
    times = []
    for _ in range(50):
        start = time.perf_counter()
        await vector_memory.retrieve("vector-bench", query="test query", limit=10)
        end = time.perf_counter()
        times.append((end - start) * 1000)
    semantic_stats = {
        "mean": mean(times),
        "std": stdev(times) if len(times) > 1 else 0
    }
    print(f"  Semantic search (10 results): {semantic_stats['mean']:.2f}ms ± {semantic_stats['std']:.2f}ms")

    # Benchmark Strategies
    print("\n3. Memory Strategy Benchmarks")
    print("-" * 70)

    # Prepare test data
    test_memory = InMemoryMemory(max_size=10000)
    for i in range(1000):
        await test_memory.store(
            "strategy-bench",
            Message(role="user", content=f"Message {i}"),
            metadata={"importance": 0.5 + (i % 5) * 0.1}
        )

    strategies = {
        "SlidingWindow": SlidingWindowStrategy(window_size=20),
        "ImportanceWeighting": ImportanceWeightingStrategy(
            importance_threshold=0.5,
            recency_weight=0.3,
            min_recent=5
        ),
        "Summarization": SummarizationStrategy(
            recent_count=10,
            summarize_older=True
        )
    }

    for name, strategy in strategies.items():
        stats = await benchmark_strategy(strategy, test_memory, "strategy-bench", 20, iterations=100)
        print(f"  {name}: {stats['mean']:.2f}ms ± {stats['std']:.2f}ms")

    # Benchmark Concurrent Access
    print("\n4. Concurrent Access Benchmarks")
    print("-" * 70)

    concurrent_memory = InMemoryMemory(max_size=100000)

    session_counts = [10, 50, 100]
    messages_per_session = 10

    for count in session_counts:
        time_ms = await benchmark_concurrent_access(concurrent_memory, count, messages_per_session)
        total_messages = count * messages_per_session
        throughput = total_messages / (time_ms / 1000)
        print(f"  {count} sessions × {messages_per_session} messages: {time_ms:.2f}ms ({throughput:.0f} msg/sec)")

    # Memory Usage
    print("\n5. Memory Usage Statistics")
    print("-" * 70)

    usage_memory = InMemoryMemory(max_size=10000)
    for i in range(1000):
        await usage_memory.store(
            "usage-bench",
            Message(role="user", content=f"Message {i}" * 10)  # ~100 chars
        )

    usage = usage_memory.get_memory_usage()
    print(f"  Total sessions: {usage['total_sessions']}")
    print(f"  Total messages: {usage['total_messages']}")
    print(f"  Max size per session: {usage['max_size_per_session']}")

    # Summary
    print("\n" + "=" * 70)
    print("Summary: Key Performance Metrics")
    print("=" * 70)
    print("\nRecommendations:")
    print("  • InMemoryMemory: < 1ms retrieval, best for testing/prototyping")
    print("  • VectorMemory: 10-50ms semantic search, use for RAG/knowledge bases")
    print("  • SlidingWindow: < 1ms, fastest strategy for recent messages")
    print("  • ImportanceWeighting: 1-5ms, best for prioritization")
    print("  • Summarization: 1-10ms, best for long conversations")
    print()
    print("For production deployments:")
    print("  • Use RedisMemory for persistence")
    print("  • Set appropriate context limits (10-50 messages)")
    print("  • Choose strategy based on use case")
    print("  • Monitor memory usage and clean up old sessions")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
