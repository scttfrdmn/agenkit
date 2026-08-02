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
import random
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
            role="agent", content=f"Processed: {message.content}", metadata={"agent": self.name}
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
        delay_ms=200,  # 200ms delay
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
@pytest.mark.timeout(60)
@pytest.mark.xdist_group("chaos")
async def test_gradual_performance_degradation():
    """Test service that gets progressively slower."""

    # 50ms rather than 10ms. The 2x ratio asserted below compares two wall-clock
    # measurements, and at a 10ms base the smaller one sat *below* the scheduling
    # noise floor: under xdist load a 10ms sleep was observed taking 38ms, which
    # made `elapsed5 > elapsed1 * 2` demand >76ms from a request whose nominal
    # cost is 60ms -- unsatisfiable by construction, not merely tight. Worse, the
    # `elapsed1 < 0.05` guard *permitted* that: it allowed up to 50ms, at which
    # point the ratio would need the 6th request to exceed 100ms, which it can
    # never do. The two assertions were inconsistent over part of the range the
    # first one allowed. At a 50ms base the ratio tolerates up to 100ms of jitter
    # on the first request, and the guard below is derived rather than guessed.
    base_delay = 0.05

    class DegradingAgent(Agent):
        def __init__(self):
            self._request_count = 0
            self._base_delay = base_delay

        @property
        def name(self) -> str:
            return "degrading"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            self._request_count += 1

            # Get progressively slower: 50ms, 100ms, 150ms, ...
            delay = self._base_delay * self._request_count
            await asyncio.sleep(delay)

            return Message(
                role="agent",
                content=f"Processed: {message.content}",
                metadata={"request_number": self._request_count, "delay_ms": delay * 1000},
            )

    agent = DegradingAgent()
    message = Message(role="user", content="Test")

    elapsed: list[float] = []
    responses: list[Message] = []
    for _ in range(6):
        start = time.time()
        responses.append(await agent.process(message))
        elapsed.append(time.time() - start)

    elapsed1, elapsed6 = elapsed[0], elapsed[-1]

    # The delay the agent *intended* is exact and load-independent, so assert
    # monotonic degradation against that. This is the property the test is named
    # for; wall-clock can only ever corroborate it.
    intended = [r.metadata["delay_ms"] for r in responses]
    assert intended == sorted(intended), f"delay did not increase monotonically: {intended}"
    assert intended[-1] == pytest.approx(intended[0] * 6), (
        f"6th delay should be 6x the first, got {intended[0]} -> {intended[-1]}"
    )

    # Wall clock: each request must take at least its nominal delay. A sleep can
    # overshoot under load but never undershoot, so this direction has no upper
    # noise term and is safe to assert per-request.
    for i, e in enumerate(elapsed, start=1):
        assert e >= base_delay * i * 0.9, (
            f"request {i} took {e:.3f}s, below its {base_delay * i:.3f}s nominal delay"
        )

    # Derived rather than guessed: for `elapsed6 > elapsed1 * 2` to be reachable,
    # elapsed1 must stay under half the 6th request's nominal cost. Asserting the
    # precondition separately means an overloaded machine reports "the baseline
    # measurement was too noisy" instead of a misleading degradation failure.
    ratio_ceiling = (base_delay * 6) / 2
    assert elapsed1 < ratio_ceiling, (
        f"baseline request took {elapsed1:.3f}s, above the {ratio_ceiling:.3f}s at which "
        f"the 2x ratio below becomes unsatisfiable -- machine too loaded to time this"
    )
    assert elapsed6 > elapsed1 * 2, (
        f"6th request ({elapsed6:.3f}s) should be > 2x first request ({elapsed1:.3f}s)"
    )


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_tail_latency_spikes():
    """Test occasional latency spikes (tail latency).

    Rewritten in #787. The original had three assertions and each was unsound in a
    different way:

    * `p50 < 0.05` was an *upper* bound on wall clock only 5x above a nominal 10ms
      sleep. Wall clock overshoots under load -- a 10ms sleep has been measured at
      38ms on this suite -- so this was a timing flake with no relation to the
      behaviour being tested.
    * `p95 >= p50` is `latencies[47] >= latencies[25]` on a list that was just
      sorted. Vacuously true; it could never fail, whatever the agent did.
    * `max_latency > 0.15` needed at least one spike in 50 draws at p=0.1, which
      is 0.5% -- unlikely but not negligible, and unreproducible unseeded.

    The rewrite seeds the RNG and asserts on *classification* rather than raw
    durations: with a known seed the exact number of spikes is known ahead of time,
    so every request can be checked to land on the correct side of a threshold
    midway between the 10ms and 200ms tiers. Sleeps overshoot but never undershoot,
    so a 200ms spike stays above the threshold and a 10ms request would have to be
    15x over budget to cross it.
    """
    spike_delay = 0.2
    normal_delay = 0.01
    # Halfway between the two tiers in log terms: a 10ms request needs a 15x
    # overshoot to reach it, and a 200ms spike would need to finish early.
    threshold = 0.15

    class SpikyAgent(Agent):
        def __init__(self, spike_probability: float = 0.1, seed: int | None = None):
            self._spike_probability = spike_probability
            self._rng = random.Random(seed)

        @property
        def name(self) -> str:
            return "spiky"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            spiked = self._rng.random() < self._spike_probability
            await asyncio.sleep(spike_delay if spiked else normal_delay)
            return Message(
                role="agent", content=f"Processed: {message.content}", metadata={"spiked": spiked}
            )

    requests = 50
    seed = 787
    # Precompute what the agent will do, from the same seed. This is what makes the
    # assertions below exact rather than probabilistic: `expected_spikes` is 7 for
    # this seed, so a spike count that drifts means the injection changed, not that
    # the dice fell differently.
    oracle = random.Random(seed)
    expected_spikes = sum(1 for _ in range(requests) if oracle.random() < 0.1)
    assert expected_spikes > 0, "chosen seed must produce at least one spike to measure a tail"

    agent = SpikyAgent(spike_probability=0.1, seed=seed)
    message = Message(role="user", content="Test")

    latencies = []
    reported_spikes = 0
    for _ in range(requests):
        start = time.time()
        response = await agent.process(message)
        latencies.append(time.time() - start)
        reported_spikes += bool(response.metadata["spiked"])

    assert reported_spikes == expected_spikes, (
        f"agent spiked {reported_spikes} times, expected {expected_spikes} from seed {seed}"
    )

    measured_spikes = sum(1 for latency in latencies if latency >= threshold)
    assert measured_spikes == expected_spikes, (
        f"{measured_spikes} requests measured over {threshold * 1000:.0f}ms but "
        f"{expected_spikes} were injected -- the two tiers are no longer separable "
        f"(latencies in ms: {sorted(round(latency * 1000) for latency in latencies)})"
    )

    latencies.sort()

    # The median must be a fast request, and the tail must be a spike. This is the
    # property "most requests are fast, a few are much slower" stated so that it can
    # actually fail: if the fast path regressed to the spike duration the median
    # crosses the threshold, and if spikes stopped being injected the tail drops
    # below it.
    p50 = latencies[requests // 2]
    assert p50 < threshold, (
        f"P50 ({p50 * 1000:.1f}ms) should be a fast request, below {threshold * 1000:.0f}ms"
    )

    max_latency = latencies[-1]
    assert max_latency >= threshold, (
        f"max latency ({max_latency * 1000:.1f}ms) should show a spike (>={threshold * 1000:.0f}ms)"
    )
    # And the tail must be *materially* slower than the median, not merely sorted
    # after it -- the original `p95 >= p50` check was true by construction.
    assert max_latency > p50 * 5, (
        f"max latency ({max_latency * 1000:.1f}ms) should be far above P50 ({p50 * 1000:.1f}ms)"
    )


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
                metadata={"input_size": input_size},
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
                metadata={"size_mb": 1},
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
    """Test performance degradation under sustained load.

    This test demonstrates that concurrent requests complete faster overall
    even though individual requests may take longer due to contention.
    """

    class LoadSensitiveAgent(Agent):
        def __init__(self):
            self._request_count = 0
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
            self._request_count += 1
            self._max_concurrent = max(self._max_concurrent, self._concurrent_requests)

            try:
                # Fixed delay per request to make timing predictable
                # In production, this would be actual CPU/IO work
                await asyncio.sleep(0.05)  # 50ms per request

                return Message(
                    role="agent",
                    content=f"Processed: {message.content}",
                    metadata={"concurrent": self._concurrent_requests},
                )
            finally:
                self._concurrent_requests -= 1

    agent = LoadSensitiveAgent()
    message = Message(role="user", content="Test")

    # Sequential: 10 requests x 50ms each = 500ms
    start = time.time()
    for _ in range(10):
        await agent.process(message)
    sequential_time = time.time() - start

    # Concurrent: All 10 run in parallel = ~50ms total
    start = time.time()
    tasks = [agent.process(message) for _ in range(10)]
    await asyncio.gather(*tasks)
    concurrent_time = time.time() - start

    # Concurrent should be significantly faster (at least 3x faster)
    # Sequential: ~0.50s, Concurrent: ~0.05s
    # Use conservative 2x threshold to handle timing variance
    assert concurrent_time * 2 < sequential_time, (
        f"Concurrent ({concurrent_time:.2f}s) should be <50% of sequential ({sequential_time:.2f}s)"
    )

    # Verify concurrent execution actually happened
    assert agent._max_concurrent >= 5, (
        f"Should have seen significant concurrency, got max={agent._max_concurrent}"
    )


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
    """Test latency percentiles with variable response times.

    Reworked in #787 for the same reason as test_tail_latency_spikes: the original
    asserted `p90 <= 0.1` on *measured* wall clock against a nominal p90 of 91ms,
    leaving a 9ms budget for scheduling overhead. On an idle machine overshoot here
    is ~2ms, but under a loaded `make test` it has been measured at 28ms, at which
    point the assertion cannot pass however correctly the agent behaves.

    The split below is the general fix for timing assertions in this file:
      * upper bounds and ordering go on the *intended* delays, which are exact
        because the RNG is seeded;
      * measured wall clock only ever gets *lower* bounds, because sleeps overshoot
        but never undershoot.
    """
    low, high = 0.01, 0.1

    class VariableLatencyAgent(Agent):
        def __init__(self, seed: int | None = None):
            self._rng = random.Random(seed)

        @property
        def name(self) -> str:
            return "variable-latency"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            delay = self._rng.uniform(low, high)
            await asyncio.sleep(delay)
            return Message(
                role="agent", content=f"Processed: {message.content}", metadata={"delay": delay}
            )

    agent = VariableLatencyAgent(seed=787)
    message = Message(role="user", content="Test")

    requests = 100
    latencies = []
    intended = []
    for _ in range(requests):
        start = time.time()
        response = await agent.process(message)
        latencies.append(time.time() - start)
        intended.append(response.metadata["delay"])

    # Every request took at least as long as it asked to sleep for. This is the only
    # direction wall clock can be trusted in, and it is what proves the delays were
    # actually applied rather than just reported.
    for i, (measured, want) in enumerate(zip(latencies, intended, strict=True)):
        assert measured >= want * 0.9, (
            f"request {i} slept {want * 1000:.1f}ms but returned in {measured * 1000:.1f}ms"
        )

    intended.sort()
    p50, p90, p95, p99 = (intended[50], intended[90], intended[95], intended[99])

    # Exact, not probabilistic: the generator is seeded, so these percentiles are a
    # fixed property of the distribution's declared range.
    assert low <= p50 <= high, f"P50={p50 * 1000:.1f}ms should be 10-100ms"
    assert low <= p90 <= high, f"P90={p90 * 1000:.1f}ms should be 10-100ms"
    assert p95 > p50, "P95 should be greater than P50"
    assert p99 > p95, "P99 should be greater than P95"

    # The spread must be real. `p95 > p50` on a sorted list is nearly free, so pin
    # the shape of the distribution too. Note the modest ratio: for uniform(10ms,
    # 100ms) the median is ~55ms and the 99th percentile ~99ms, so p99/p50 is only
    # about 1.8 (1.67 for this seed) -- a ratio like 2x would be *unsatisfiable*
    # against a correct generator, which is the same mistake the wall-clock bounds
    # above made. 1.4 leaves headroom while still failing if the generator collapses
    # to a constant or narrows to a fraction of its declared range.
    assert p99 > p50 * 1.4, (
        f"P99 ({p99 * 1000:.1f}ms) should be well above P50 ({p50 * 1000:.1f}ms); "
        f"latency does not appear to vary across the declared "
        f"{low * 1000:.0f}-{high * 1000:.0f}ms range"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "chaos"])
