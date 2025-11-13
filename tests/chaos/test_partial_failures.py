"""
Partial Failure Chaos Tests

Tests system behavior with partial failures:
- Some requests succeed, others fail
- Streaming partial failures (fail mid-stream)
- Batch processing with individual failures
- Mixed timeout scenarios

These tests validate graceful degradation and partial success handling.
"""
import asyncio
import random
import time
from typing import AsyncIterator

import pytest

from agenkit.interfaces import Agent, Message
from tests.chaos.chaos_agents import ChaosAgent, ChaosMode, StreamingChaosAgent

try:
    from agenkit.interfaces import StreamingAgent
except ImportError:
    class StreamingAgent(Agent):
        async def stream(self, message: Message) -> AsyncIterator[Message]:
            raise NotImplementedError


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


class SimpleStreamingAgent(StreamingAgent):
    """Simple streaming agent for testing."""

    def __init__(self, name: str = "streaming-agent"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["stream"]

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """Stream words from message."""
        words = message.content.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.01)
            yield Message(
                role="agent",
                content=word,
                metadata={"chunk": i, "total": len(words)}
            )


# ============================================
# Partial Success Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_some_requests_succeed_others_fail():
    """Test mixed success/failure scenarios."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.5  # 50% failure rate
    )

    message = Message(role="user", content="Test")

    # Run 20 requests
    results = []
    for _ in range(20):
        try:
            response = await chaos_agent.process(message)
            results.append(("success", response))
        except Exception as e:
            results.append(("failure", e))

    # Should have both successes and failures
    successes = [r for r in results if r[0] == "success"]
    failures = [r for r in results if r[0] == "failure"]

    assert len(successes) > 0, "Should have some successes"
    assert len(failures) > 0, "Should have some failures"

    # Roughly 50/50 split (allow variance)
    assert 5 <= len(successes) <= 15, f"Expected ~10 successes, got {len(successes)}"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_partial_failure_with_retry():
    """Test that retry converts partial failures to successes."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.7  # 70% failure rate
    )

    message = Message(role="user", content="Test")

    # Without retry: most requests fail
    successes_no_retry = 0
    for _ in range(20):
        try:
            await chaos_agent.process(message)
            successes_no_retry += 1
        except:
            pass

    # With retry: most requests should eventually succeed
    successes_with_retry = 0
    for _ in range(20):
        # Try up to 5 times
        for attempt in range(5):
            try:
                await chaos_agent.process(message)
                successes_with_retry += 1
                break
            except:
                if attempt < 4:
                    await asyncio.sleep(0.01)

    # Retry should significantly improve success rate
    assert successes_with_retry > successes_no_retry, \
        f"Retry ({successes_with_retry}) should improve success rate over no retry ({successes_no_retry})"

    # With retry, expect >85% success rate (allow some variance due to randomness)
    assert successes_with_retry >= 17, \
        f"Expected >=17 successes with retry, got {successes_with_retry}"


# ============================================
# Streaming Partial Failures
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_stream_fails_mid_stream():
    """Test streaming that fails partway through."""
    base_agent = SimpleStreamingAgent()
    chaos_agent = StreamingChaosAgent(
        base_agent,
        fail_after_chunks=3  # Fail after 3 chunks
    )

    message = Message(role="user", content="one two three four five six")

    chunks = []
    with pytest.raises(ConnectionError) as exc_info:
        async for chunk in chaos_agent.stream(message):
            chunks.append(chunk)

    # Should have received 3 chunks before failure
    assert len(chunks) == 3
    assert "failed after 3 chunks" in str(exc_info.value)

    # Verify chunks are correct
    assert chunks[0].content == "one"
    assert chunks[1].content == "two"
    assert chunks[2].content == "three"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_stream_with_intermittent_failures():
    """Test streaming with random failures during stream."""
    base_agent = SimpleStreamingAgent()
    chaos_agent = StreamingChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.3  # 30% chance of failure per chunk
    )

    message = Message(role="user", content="one two three four five")

    # May succeed or fail partway through
    chunks = []
    failed = False

    try:
        async for chunk in chaos_agent.stream(message):
            chunks.append(chunk)
    except ConnectionError:
        failed = True

    # Either completed all 5 chunks or failed partway
    if failed:
        assert 0 <= len(chunks) < 5, "Should have partial chunks on failure"
    else:
        assert len(chunks) == 5, "Should have all chunks on success"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_stream_slow_chunks():
    """Test streaming with slow chunk delivery."""
    base_agent = SimpleStreamingAgent()
    chaos_agent = StreamingChaosAgent(
        base_agent,
        delay_per_chunk_ms=50  # 50ms delay per chunk
    )

    message = Message(role="user", content="one two three")

    chunks = []
    start = time.time()

    async for chunk in chaos_agent.stream(message):
        chunks.append(chunk)

    elapsed = time.time() - start

    # Should have all 3 chunks
    assert len(chunks) == 3

    # Should take ~150ms (3 chunks × 50ms each)
    assert elapsed >= 0.15, f"Should take >=150ms, took {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_stream_cancellation_cleanup():
    """Test that stream cancellation is handled cleanly."""
    import time

    base_agent = SimpleStreamingAgent()

    message = Message(role="user", content=" ".join([f"word{i}" for i in range(100)]))

    chunks = []
    start = time.time()

    # Cancel after receiving a few chunks
    try:
        async for chunk in base_agent.stream(message):
            chunks.append(chunk)
            if len(chunks) >= 5:
                break  # Cancel stream
    except:
        pass

    elapsed = time.time() - start

    # Should have received exactly 5 chunks
    assert len(chunks) == 5

    # Should be fast (not wait for all 100 chunks)
    assert elapsed < 0.2, f"Should cancel quickly, took {elapsed:.3f}s"


# ============================================
# Batch Processing Failures
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_batch_with_individual_failures():
    """Test batch processing where some items fail."""

    class BatchAgent(Agent):
        def __init__(self, failure_indices: set[int]):
            self._failure_indices = failure_indices

        @property
        def name(self) -> str:
            return "batch-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["batch"]

        async def process(self, message: Message) -> Message:
            """Single message process (required by Agent interface)."""
            return Message(role="agent", content=f"Processed: {message.content}")

        async def process_batch(self, messages: list[Message]) -> list[tuple[bool, Message | Exception]]:
            """Process batch, returning success/failure for each item."""
            results = []

            for i, msg in enumerate(messages):
                if i in self._failure_indices:
                    results.append((False, RuntimeError(f"Item {i} failed")))
                else:
                    response = Message(
                        role="agent",
                        content=f"Processed: {msg.content}",
                        metadata={"index": i}
                    )
                    results.append((True, response))

            return results

    # Fail items 2 and 5
    agent = BatchAgent(failure_indices={2, 5})

    # Create batch of 10 messages
    batch = [Message(role="user", content=f"Item {i}") for i in range(10)]

    results = await agent.process_batch(batch)

    # Check results
    assert len(results) == 10

    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]

    assert len(successes) == 8, "8 items should succeed"
    assert len(failures) == 2, "2 items should fail"

    # Verify failed indices
    failed_indices = []
    for i, (success, result) in enumerate(results):
        if not success:
            failed_indices.append(i)

    assert failed_indices == [2, 5], "Items 2 and 5 should have failed"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_batch_with_timeout():
    """Test batch processing where some items timeout."""

    class BatchAgent(Agent):
        @property
        def name(self) -> str:
            return "batch-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["batch"]

        async def process(self, message: Message) -> Message:
            """Single message process (required by Agent interface)."""
            return Message(role="agent", content=f"Processed: {message.content}")

        async def process_batch(self, messages: list[Message], timeout: float = 0.1):
            """Process batch with per-item timeout."""
            results = []

            for i, msg in enumerate(messages):
                try:
                    # Some items are slow
                    delay = 0.05 if i % 3 == 0 else 0.15  # Every 3rd is fast, others slow

                    response = await asyncio.wait_for(
                        self._process_one(msg, delay),
                        timeout=timeout
                    )
                    results.append((True, response))
                except asyncio.TimeoutError:
                    results.append((False, asyncio.TimeoutError(f"Item {i} timed out")))

            return results

        async def _process_one(self, msg: Message, delay: float) -> Message:
            await asyncio.sleep(delay)
            return Message(role="agent", content=f"Processed: {msg.content}")

    agent = BatchAgent()

    # Batch of 6 messages
    batch = [Message(role="user", content=f"Item {i}") for i in range(6)]

    results = await agent.process_batch(batch, timeout=0.1)

    # Items 0 and 3 should succeed (fast), others should timeout
    assert len(results) == 6

    successes = [i for i, (success, _) in enumerate(results) if success]
    timeouts = [i for i, (success, _) in enumerate(results) if not success]

    assert len(successes) == 2, f"2 items should succeed, got {len(successes)}"
    assert len(timeouts) == 4, f"4 items should timeout, got {len(timeouts)}"


# ============================================
# Mixed Timeout Scenarios
# ============================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_some_requests_timeout_others_succeed():
    """Test scenario where some requests timeout, others succeed."""
    import time

    class VariableDelayAgent(Agent):
        def __init__(self):
            self._request_count = 0

        @property
        def name(self) -> str:
            return "variable-delay"

        @property
        def capabilities(self) -> list[str]:
            return ["test"]

        async def process(self, message: Message) -> Message:
            self._request_count += 1

            # Every 3rd request is slow
            delay = 0.3 if self._request_count % 3 == 0 else 0.05

            await asyncio.sleep(delay)

            return Message(role="agent", content=f"Processed: {message.content}")

    agent = VariableDelayAgent()
    message = Message(role="user", content="Test")
    timeout = 0.2  # 200ms timeout

    # Run 9 requests with timeout
    results = []
    for _ in range(9):
        try:
            response = await asyncio.wait_for(agent.process(message), timeout=timeout)
            results.append(("success", response))
        except asyncio.TimeoutError:
            results.append(("timeout", None))

    # Requests 3, 6, 9 should timeout (every 3rd)
    successes = [r for r in results if r[0] == "success"]
    timeouts = [r for r in results if r[0] == "timeout"]

    assert len(successes) == 6, f"6 requests should succeed, got {len(successes)}"
    assert len(timeouts) == 3, f"3 requests should timeout, got {len(timeouts)}"


@pytest.mark.asyncio
@pytest.mark.chaos
async def test_graceful_degradation_with_partial_failures():
    """Test system continues operating despite partial failures."""
    base_agent = SimpleAgent()
    chaos_agent = ChaosAgent(
        base_agent,
        chaos_mode=ChaosMode.INTERMITTENT,
        failure_rate=0.4  # 40% failure rate
    )

    message = Message(role="user", content="Test")

    # System should continue operating despite failures
    total_requests = 50
    successes = 0
    failures = 0

    for _ in range(total_requests):
        try:
            response = await chaos_agent.process(message)
            assert response.content == "Processed: Test"
            successes += 1
        except Exception:
            failures += 1

        # System should remain responsive
        # (no cascading failures causing everything to block)

    assert successes > 0, "System should have some successes"
    assert failures > 0, "System should have some failures"

    # Expect ~60% success rate (allow variance)
    success_rate = successes / total_requests
    assert 0.4 <= success_rate <= 0.8, \
        f"Expected ~60% success rate, got {success_rate:.1%}"

    # All requests completed (no hangs)
    assert successes + failures == total_requests


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "chaos"])
