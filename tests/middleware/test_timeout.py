"""Tests for timeout middleware."""

import asyncio
import pytest
from agenkit.interfaces import Agent, Message
from agenkit.middleware import (
    TimeoutConfig,
    TimeoutDecorator,
    TimeoutError,
)


class FastAgent(Agent):
    """Agent that responds quickly."""

    def __init__(self, delay: float = 0.01):
        """Initialize fast agent.

        Args:
            delay: Small delay in seconds (default 0.01s = 10ms)
        """
        self.delay = delay

    @property
    def name(self) -> str:
        return "fast-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(self.delay)
        return Message(role="agent", content=f"Processed: {message.content}")


class SlowAgent(Agent):
    """Agent that takes a long time to respond."""

    def __init__(self, delay: float = 5.0):
        """Initialize slow agent.

        Args:
            delay: Long delay in seconds (default 5s)
        """
        self.delay = delay

    @property
    def name(self) -> str:
        return "slow-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(self.delay)
        return Message(role="agent", content=f"Processed after {self.delay}s: {message.content}")


class StreamingAgent(Agent):
    """Agent that streams responses."""

    def __init__(self, chunk_count: int = 3, chunk_delay: float = 0.1):
        """Initialize streaming agent.

        Args:
            chunk_count: Number of chunks to stream
            chunk_delay: Delay between chunks in seconds
        """
        self.chunk_count = chunk_count
        self.chunk_delay = chunk_delay

    @property
    def name(self) -> str:
        return "streaming-agent"

    @property
    def capabilities(self) -> list[str]:
        return ["streaming"]

    async def process(self, message: Message) -> Message:
        return Message(role="agent", content=f"Processed: {message.content}")

    async def stream(self, message: Message):
        """Stream responses."""
        for i in range(self.chunk_count):
            await asyncio.sleep(self.chunk_delay)
            yield Message(role="agent", content=f"Chunk {i+1}/{self.chunk_count}")


class FailingAgent(Agent):
    """Agent that raises errors."""

    @property
    def name(self) -> str:
        return "failing-agent"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        raise ValueError("Intentional failure for testing")


# ============================================
# Configuration Tests
# ============================================


def test_timeout_config_validation():
    """Test timeout configuration validation."""
    # Valid config
    config = TimeoutConfig(timeout=10.0)
    assert config.timeout == 10.0

    # Invalid timeout (negative)
    with pytest.raises(ValueError, match="timeout must be positive"):
        TimeoutConfig(timeout=-1.0)

    # Invalid timeout (zero)
    with pytest.raises(ValueError, match="timeout must be positive"):
        TimeoutConfig(timeout=0.0)


# ============================================
# Success Cases
# ============================================


@pytest.mark.asyncio
async def test_timeout_allows_fast_agent():
    """Test that fast agents complete successfully within timeout."""
    agent = FastAgent(delay=0.01)  # 10ms delay
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))  # 1s timeout

    msg = Message(role="user", content="test")
    response = await timeout_agent.process(msg)

    assert response.content == "Processed: test"

    # Check metrics
    metrics = timeout_agent.metrics
    assert metrics.total_requests == 1
    assert metrics.successful_requests == 1
    assert metrics.timed_out_requests == 0
    assert metrics.failed_requests == 0
    assert metrics.min_duration is not None
    assert metrics.max_duration is not None
    assert metrics.min_duration <= metrics.max_duration


@pytest.mark.asyncio
async def test_timeout_multiple_successful_requests():
    """Test multiple successful requests update metrics correctly."""
    agent = FastAgent(delay=0.01)
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))

    # Send 5 requests
    for i in range(5):
        msg = Message(role="user", content=f"request {i}")
        response = await timeout_agent.process(msg)
        assert response.content == f"Processed: request {i}"

    # Check metrics
    metrics = timeout_agent.metrics
    assert metrics.total_requests == 5
    assert metrics.successful_requests == 5
    assert metrics.timed_out_requests == 0
    assert metrics.failed_requests == 0


# ============================================
# Timeout Cases
# ============================================


@pytest.mark.asyncio
async def test_timeout_stops_slow_agent():
    """Test that slow agents are timed out."""
    agent = SlowAgent(delay=5.0)  # 5s delay
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=0.1))  # 100ms timeout

    msg = Message(role="user", content="test")

    with pytest.raises(TimeoutError, match="timed out after 0.1s"):
        await timeout_agent.process(msg)

    # Check metrics
    metrics = timeout_agent.metrics
    assert metrics.total_requests == 1
    assert metrics.successful_requests == 0
    assert metrics.timed_out_requests == 1
    assert metrics.failed_requests == 0


@pytest.mark.asyncio
async def test_timeout_reports_agent_name():
    """Test that timeout error includes agent name."""
    agent = SlowAgent(delay=5.0)
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=0.1))

    msg = Message(role="user", content="test")

    with pytest.raises(TimeoutError, match="slow-agent.*timed out"):
        await timeout_agent.process(msg)


@pytest.mark.asyncio
async def test_timeout_boundary_case():
    """Test timeout at boundary (agent completes just at timeout)."""
    # Agent takes 0.1s, timeout is 0.15s - should succeed
    agent = FastAgent(delay=0.1)
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=0.15))

    msg = Message(role="user", content="test")
    response = await timeout_agent.process(msg)

    assert response.content == "Processed: test"
    assert timeout_agent.metrics.successful_requests == 1


@pytest.mark.asyncio
async def test_timeout_mixed_requests():
    """Test metrics with mix of successful and timed out requests."""
    # Agent that alternates between fast and slow
    class VariableAgent(Agent):
        def __init__(self):
            self.counter = 0

        @property
        def name(self) -> str:
            return "variable-agent"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            self.counter += 1
            # Odd requests are fast, even requests are slow
            delay = 0.01 if self.counter % 2 == 1 else 5.0
            await asyncio.sleep(delay)
            return Message(role="agent", content=f"Response {self.counter}")

    agent = VariableAgent()
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=0.1))

    # Request 1: Fast (succeeds)
    response1 = await timeout_agent.process(Message(role="user", content="1"))
    assert response1.content == "Response 1"

    # Request 2: Slow (times out)
    with pytest.raises(TimeoutError):
        await timeout_agent.process(Message(role="user", content="2"))

    # Request 3: Fast (succeeds)
    response3 = await timeout_agent.process(Message(role="user", content="3"))
    assert response3.content == "Response 3"

    # Check metrics
    metrics = timeout_agent.metrics
    assert metrics.total_requests == 3
    assert metrics.successful_requests == 2
    assert metrics.timed_out_requests == 1
    assert metrics.failed_requests == 0


# ============================================
# Error Handling
# ============================================


@pytest.mark.asyncio
async def test_timeout_preserves_other_errors():
    """Test that non-timeout errors are preserved."""
    agent = FailingAgent()
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))

    msg = Message(role="user", content="test")

    with pytest.raises(ValueError, match="Intentional failure"):
        await timeout_agent.process(msg)

    # Check metrics
    metrics = timeout_agent.metrics
    assert metrics.total_requests == 1
    assert metrics.successful_requests == 0
    assert metrics.timed_out_requests == 0
    assert metrics.failed_requests == 1


@pytest.mark.asyncio
async def test_timeout_with_agent_that_fails_fast():
    """Test timeout with agent that fails quickly (before timeout)."""
    agent = FailingAgent()
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=5.0))

    msg = Message(role="user", content="test")

    # Should get the agent's error, not a timeout
    with pytest.raises(ValueError, match="Intentional failure"):
        await timeout_agent.process(msg)

    # Metrics should show failed request, not timeout
    metrics = timeout_agent.metrics
    assert metrics.timed_out_requests == 0
    assert metrics.failed_requests == 1


# ============================================
# Streaming Tests
# ============================================


@pytest.mark.asyncio
async def test_timeout_streaming_success():
    """Test streaming with chunks arriving within timeout."""
    agent = StreamingAgent(chunk_count=3, chunk_delay=0.01)
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))

    msg = Message(role="user", content="test")

    chunks = []
    async for chunk in timeout_agent.stream(msg):
        chunks.append(chunk.content)

    assert len(chunks) == 3
    assert chunks[0] == "Chunk 1/3"
    assert chunks[1] == "Chunk 2/3"
    assert chunks[2] == "Chunk 3/3"

    # Check metrics
    metrics = timeout_agent.metrics
    assert metrics.successful_requests == 1
    assert metrics.timed_out_requests == 0


@pytest.mark.asyncio
async def test_timeout_streaming_timeout():
    """Test streaming timeout when chunks arrive too slowly."""
    agent = StreamingAgent(chunk_count=5, chunk_delay=0.5)  # 0.5s per chunk
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))  # 1s total timeout

    msg = Message(role="user", content="test")

    with pytest.raises(TimeoutError, match="Streaming.*timed out"):
        chunks = []
        async for chunk in timeout_agent.stream(msg):
            chunks.append(chunk.content)

    # Check metrics
    metrics = timeout_agent.metrics
    assert metrics.timed_out_requests == 1
    assert metrics.successful_requests == 0


@pytest.mark.asyncio
async def test_timeout_streaming_not_supported():
    """Test streaming with agent that doesn't support it."""
    agent = FastAgent()  # Doesn't have stream method
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))

    msg = Message(role="user", content="test")

    with pytest.raises(NotImplementedError, match="does not support streaming"):
        async for chunk in timeout_agent.stream(msg):
            pass


# ============================================
# Metrics Tests
# ============================================


@pytest.mark.asyncio
async def test_timeout_metrics_duration_tracking():
    """Test that metrics correctly track request durations."""
    agent = FastAgent(delay=0.05)  # 50ms delay
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))

    # Send 3 requests
    for i in range(3):
        await timeout_agent.process(Message(role="user", content=f"test {i}"))

    metrics = timeout_agent.metrics
    assert metrics.total_requests == 3
    assert metrics.min_duration is not None
    assert metrics.max_duration is not None
    assert metrics.avg_duration > 0

    # Duration should be approximately 50ms per request
    assert 0.04 < metrics.avg_duration < 0.1  # Allow for timing variance


@pytest.mark.asyncio
async def test_timeout_metrics_tracks_timeout_duration():
    """Test that timeout duration is recorded even for timed-out requests."""
    agent = SlowAgent(delay=10.0)
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=0.1))

    msg = Message(role="user", content="test")

    try:
        await timeout_agent.process(msg)
    except TimeoutError:
        pass

    metrics = timeout_agent.metrics
    assert metrics.timed_out_requests == 1

    # Duration should be approximately the timeout duration
    assert 0.09 < metrics.avg_duration < 0.2  # ~100ms timeout + overhead


# ============================================
# Agent Interface Tests
# ============================================


def test_timeout_decorator_preserves_agent_interface():
    """Test that timeout decorator properly implements Agent interface."""
    agent = FastAgent()
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))

    # Should have correct name
    assert timeout_agent.name == "fast-agent"

    # Should have correct capabilities
    assert timeout_agent.capabilities == []


def test_timeout_decorator_preserves_capabilities():
    """Test that capabilities from underlying agent are preserved."""
    agent = StreamingAgent()
    timeout_agent = TimeoutDecorator(agent, TimeoutConfig(timeout=1.0))

    assert "streaming" in timeout_agent.capabilities


# ============================================
# Default Configuration Tests
# ============================================


@pytest.mark.asyncio
async def test_timeout_default_config():
    """Test that default timeout configuration works."""
    agent = FastAgent(delay=0.01)
    timeout_agent = TimeoutDecorator(agent)  # No config = use defaults

    msg = Message(role="user", content="test")
    response = await timeout_agent.process(msg)

    assert response.content == "Processed: test"
    assert timeout_agent.metrics.successful_requests == 1


@pytest.mark.asyncio
async def test_timeout_default_is_30_seconds():
    """Test that default timeout is 30 seconds."""
    agent = SlowAgent(delay=0.5)
    timeout_agent = TimeoutDecorator(agent)  # Use default 30s timeout

    msg = Message(role="user", content="test")
    response = await timeout_agent.process(msg)

    # Should succeed with 30s timeout
    assert "Processed after 0.5s" in response.content
