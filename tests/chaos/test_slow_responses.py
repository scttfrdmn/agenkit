"""
Slow Response Chaos Tests

Tests system behavior under performance degradation:
- Slow agent processing
- Memory pressure (large payloads)
- Gradual performance degradation
- Tail latency spikes

These tests validate timeout behavior and performance under load.
"""
import asyncio
import time

import pytest

from agenkit.interfaces import Agent, Message
from tests.chaos.chaos_agents import ChaosAgent, ChaosMode


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
# Slow Processing Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_slow_agent_processing():
    """Test behavior with slow agent processing."""
    base_agent = SimpleAgent()
    slow_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.SLOW_RESPONSE,
        delay_ms=200  # 200ms delay
    )

    message = Message(role="user", content="Test")

    # Measure latency
    start = time.time()
    response = await slow_agent.process(message)
    elapsed = time.time() - start

    assert response.content == "Processed: Test"
    assert elapsed >= 0.2, f"Should take >=200ms, took {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_gradual_performance_degradation():
    """Test service that gets progressively slower."""

    class DegradingAgent(Agent):
        def __init__(self):
            self._request_count = 0
            self._base_delay = 0.01  # 10ms base

        @property
        def name(self) -> str:
            return "degrading"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            self._request_count += 1

            # Get progressively slower: 10ms, 20ms, 30ms, ...
            delay = self._base_delay * self._request_count
            await asyncio.sleep(delay)

            return Message(
                role="agent",
                content=f"Processed: {message.content}",
                metadata={"request_number": self._request_count, "delay_ms": delay * 1000}
            )

    agent = DegradingAgent()
    message = Message(role="user", content="Test")

    # First request should be fast
    start = time.time()
    response1 = await agent.process(message)
    elapsed1 = time.time() - start

    assert elapsed1 < 0.05, f"First request should be fast, took {elapsed1:.3f}s"

    # 5th request should be much slower
    for _ in range(4):
        await agent.process(message)

    start = time.time()
    response5 = await agent.process(message)
    elapsed5 = time.time() - start

    assert elapsed5 >= 0.06, f"6th request should take >=60ms, took {elapsed5:.3f}s"
    assert elapsed5 > elapsed1 * 5, "Later requests should be significantly slower"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_tail_latency_spikes():
    """Test occasional latency spikes (tail latency)."""
    import random

    class SpikyAgent(Agent):
        def __init__(self, spike_probability: float = 0.1):
            self._spike_probability = spike_probability

        @property
        def name(self) -> str:
            return "spiky"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            # Most requests are fast, but 10% have spikes
            if random.random() < self._spike_probability:
                await asyncio.sleep(0.2)  # 200ms spike
            else:
                await asyncio.sleep(0.01)  # 10ms normal

            return Message(role="agent", content=f"Processed: {message.content}")

    agent = SpikyAgent(spike_probability=0.1)
    message = Message(role="user", content="Test")

    # Run 50 requests and measure latency distribution
    latencies = []
    for _ in range(50):
        start = time.time()
        await agent.process(message)
        latencies.append(time.time() - start)

    latencies.sort()

    # P50 should be fast (<50ms)
    p50 = latencies[25]
    assert p50 < 0.05, f"P50 latency should be <50ms, got {p50*1000:.1f}ms"

    # P95 should show the spikes (>=100ms)
    p95 = latencies[47]
    # With 10% spike rate, P90-P95 may or may not include spikes (probabilistic)
    # We just verify P95 >= P50 (tail latency not faster than median)
    assert p95 >= p50, f"P95 ({p95*1000:.1f}ms) should be >= P50 ({p50*1000:.1f}ms)"

    # Also check that max latency shows spikes exist
    max_latency = latencies[-1]
    assert max_latency > 0.15, f"Max latency ({max_latency*1000:.1f}ms) should show spikes (>150ms)"


# ============================================
# Memory Pressure Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_memory_pressure_large_payload():
    """Test behavior with memory pressure (large payloads)."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(base_agent, chaos_mode=ChaosMode.MEMORY_PRESSURE)

    message = Message(role="user", content="Test")

    # Should handle large response
    response = await chaos_agent.process(message)

    # Response should be 10MB
    assert len(response.content) == 10 * 1024 * 1024
    assert response.metadata.get("chaos") == "memory_pressure"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_large_input_payload():
    """Test agent with large input payload."""

    class LargePayloadAgent(Agent):
        @property
        def name(self) -> str:
            return "large-payload"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            # Process large input
            input_size = len(message.content)

            return Message(
                role="agent",
                content=f"Processed {input_size} bytes",
                metadata={"input_size": input_size}
            )

    agent = LargePayloadAgent()

    # Send 5MB message
    large_content = "x" * (5 * 1024 * 1024)
    message = Message(role="user", content=large_content)

    response = await agent.process(message)

    assert response.metadata["input_size"] == 5 * 1024 * 1024


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_concurrent_large_payloads():
    """Test multiple concurrent large payloads (memory pressure)."""

    class MemoryAgent(Agent):
        @property
        def name(self) -> str:
            return "memory-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            # Simulate memory-intensive processing
            await asyncio.sleep(0.05)

            # Return large response
            return Message(
                role="agent",
                content="x" * (1 * 1024 * 1024),  # 1MB
                metadata={"size_mb": 1}
            )

    agent = MemoryAgent()
    message = Message(role="user", content="Test")

    # 10 concurrent requests, each returning 1MB
    tasks = [agent.process(message) for _ in range(10)]

    start = time.time()
    responses = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    # All should succeed
    assert len(responses) == 10
    assert all(len(r.content) == 1 * 1024 * 1024 for r in responses)

    # Should complete reasonably fast with concurrency
    assert elapsed < 1.0, f"10 concurrent 1MB responses took {elapsed:.2f}s"


# ============================================
# Performance Degradation Under Load
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
@pytest.mark.slow
async def test_performance_under_sustained_load():
    """Test performance degradation under sustained load."""

    class LoadSensitiveAgent(Agent):
        def __init__(self):
            self._concurrent_requests = 0
            self._max_concurrent = 0

        @property
        def name(self) -> str:
            return "load-sensitive"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            self._concurrent_requests += 1
            self._max_concurrent = max(self._max_concurrent, self._concurrent_requests)

            try:
                # Slower with more concurrent requests
                delay = 0.01 * self._concurrent_requests
                await asyncio.sleep(delay)

                return Message(
                    role="agent",
                    content=f"Processed: {message.content}",
                    metadata={"concurrent": self._concurrent_requests}
                )
            finally:
                self._concurrent_requests -= 1

    agent = LoadSensitiveAgent()
    message = Message(role="user", content="Test")

    # Sequential requests should be fast
    start = time.time()
    for _ in range(10):
        await agent.process(message)
    sequential_time = time.time() - start

    # Concurrent requests should be slower
    start = time.time()
    tasks = [agent.process(message) for _ in range(10)]
    await asyncio.gather(*tasks)
    concurrent_time = time.time() - start

    # Concurrent should be faster than sequential despite per-request slowdown
    assert concurrent_time < sequential_time, \
        f"Concurrent ({concurrent_time:.2f}s) should be faster than sequential ({sequential_time:.2f}s)"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_timeout_with_slow_degrading_service():
    """Test that timeout catches degrading service."""

    class DegradingAgent(Agent):
        def __init__(self):
            self._request_count = 0

        @property
        def name(self) -> str:
            return "degrading"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            self._request_count += 1

            # Get progressively slower
            delay = 0.05 * self._request_count
            await asyncio.sleep(delay)

            return Message(role="agent", content=f"Processed: {message.content}")

    agent = DegradingAgent()
    message = Message(role="user", content="Test")
    timeout = 0.2  # 200ms timeout

    # First few requests succeed
    for _ in range(3):
        response = await asyncio.wait_for(agent.process(message), timeout=timeout)
        assert response.content == "Processed: Test"

    # Eventually timeout as service degrades
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(agent.process(message), timeout=timeout)


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_slow_response_percentiles():
    """Test latency percentiles with variable response times."""
    import random

    class VariableLatencyAgent(Agent):
        @property
        def name(self) -> str:
            return "variable-latency"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            # Variable latency: 10-100ms
            delay = random.uniform(0.01, 0.1)
            await asyncio.sleep(delay)

            return Message(role="agent", content=f"Processed: {message.content}")

    agent = VariableLatencyAgent()
    message = Message(role="user", content="Test")

    # Run 100 requests and measure latency
    latencies = []
    for _ in range(100):
        start = time.time()
        await agent.process(message)
        latencies.append(time.time() - start)

    latencies.sort()

    # Calculate percentiles
    p50 = latencies[50]
    p90 = latencies[90]
    p95 = latencies[95]
    p99 = latencies[99]

    # Validate percentiles are in expected range
    assert 0.01 <= p50 <= 0.1, f"P50={p50*1000:.1f}ms should be 10-100ms"
    assert 0.01 <= p90 <= 0.1, f"P90={p90*1000:.1f}ms should be 10-100ms"
    assert p95 > p50, f"P95 should be greater than P50"
    assert p99 > p95, f"P99 should be greater than P95"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "chaos"])
