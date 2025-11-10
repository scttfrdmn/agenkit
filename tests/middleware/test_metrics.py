"""Tests for metrics middleware."""

import asyncio
import pytest

from agenkit.interfaces import Agent, Message
from agenkit.middleware import MetricsDecorator


class SimpleAgent(Agent):
    """Simple agent for testing."""

    def __init__(self, response: str = "response", delay: float = 0):
        self._response = response
        self._delay = delay

    @property
    def name(self) -> str:
        return "simple"

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def process(self, message: Message) -> Message:
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        return Message(role="agent", content=self._response)


class ErrorAgent(Agent):
    """Agent that always raises an error."""

    @property
    def name(self) -> str:
        return "error"

    @property
    def capabilities(self) -> list[str]:
        return []

    async def process(self, message: Message) -> Message:
        raise Exception("test error")


@pytest.mark.asyncio
async def test_metrics_basic():
    """Test basic metrics collection."""
    agent = SimpleAgent()
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")
    response = await metrics_agent.process(msg)

    assert response.content == "response"

    metrics = metrics_agent.get_metrics()
    assert metrics.total_requests == 1
    assert metrics.success_requests == 1
    assert metrics.error_requests == 0
    assert metrics.in_flight_requests == 0
    assert metrics.min_latency > 0
    assert metrics.max_latency > 0


@pytest.mark.asyncio
async def test_metrics_multiple_requests():
    """Test metrics across multiple requests."""
    agent = SimpleAgent()
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")
    for _ in range(5):
        await metrics_agent.process(msg)

    metrics = metrics_agent.get_metrics()
    assert metrics.total_requests == 5
    assert metrics.success_requests == 5
    assert metrics.error_requests == 0


@pytest.mark.asyncio
async def test_metrics_error_tracking():
    """Test error metrics tracking."""
    agent = ErrorAgent()
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")

    for _ in range(3):
        with pytest.raises(Exception):
            await metrics_agent.process(msg)

    metrics = metrics_agent.get_metrics()
    assert metrics.total_requests == 3
    assert metrics.success_requests == 0
    assert metrics.error_requests == 3
    assert metrics.error_rate() == 1.0


@pytest.mark.asyncio
async def test_metrics_mixed_success_error():
    """Test metrics with mixed success and errors."""

    class ConditionalAgent(Agent):
        def __init__(self):
            self.count = 0

        @property
        def name(self) -> str:
            return "conditional"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            self.count += 1
            if self.count % 2 == 0:
                raise Exception("error")
            return Message(role="agent", content="success")

    agent = ConditionalAgent()
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")

    for _ in range(4):
        try:
            await metrics_agent.process(msg)
        except Exception:
            pass

    metrics = metrics_agent.get_metrics()
    assert metrics.total_requests == 4
    assert metrics.success_requests == 2
    assert metrics.error_requests == 2
    assert metrics.error_rate() == 0.5


@pytest.mark.asyncio
async def test_metrics_latency():
    """Test latency tracking."""
    agent = SimpleAgent(delay=0.1)
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")
    await metrics_agent.process(msg)

    metrics = metrics_agent.get_metrics()
    assert metrics.min_latency >= 0.09  # Allow some tolerance
    assert metrics.max_latency >= 0.09
    assert metrics.average_latency() >= 0.09


@pytest.mark.asyncio
async def test_metrics_min_max_latency():
    """Test min/max latency tracking across requests."""

    class VariableLatencyAgent(Agent):
        def __init__(self):
            self.delays = [0.05, 0.1, 0.02, 0.15]
            self.count = 0

        @property
        def name(self) -> str:
            return "variable"

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            delay = self.delays[self.count % len(self.delays)]
            self.count += 1
            await asyncio.sleep(delay)
            return Message(role="agent", content="success")

    agent = VariableLatencyAgent()
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")
    for _ in range(4):
        await metrics_agent.process(msg)

    metrics = metrics_agent.get_metrics()
    assert metrics.min_latency >= 0.01  # Should be ~0.02
    assert metrics.max_latency >= 0.14  # Should be ~0.15
    assert 0.01 < metrics.min_latency < metrics.max_latency


@pytest.mark.asyncio
async def test_metrics_average_latency():
    """Test average latency calculation."""
    agent = SimpleAgent(delay=0.1)
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")
    for _ in range(3):
        await metrics_agent.process(msg)

    metrics = metrics_agent.get_metrics()
    avg = metrics.average_latency()
    assert avg >= 0.09  # Each request takes ~0.1s


@pytest.mark.asyncio
async def test_metrics_error_rate():
    """Test error rate calculation."""
    agent = SimpleAgent()
    metrics_agent = MetricsDecorator(agent)

    # Empty metrics
    metrics = metrics_agent.get_metrics()
    assert metrics.error_rate() == 0.0

    # After successful request
    msg = Message(role="user", content="test")
    await metrics_agent.process(msg)
    metrics = metrics_agent.get_metrics()
    assert metrics.error_rate() == 0.0


@pytest.mark.asyncio
async def test_metrics_reset():
    """Test metrics reset."""
    agent = SimpleAgent()
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")
    await metrics_agent.process(msg)

    metrics = metrics_agent.get_metrics()
    assert metrics.total_requests == 1

    await metrics.reset()

    assert metrics.total_requests == 0
    assert metrics.success_requests == 0
    assert metrics.error_requests == 0
    assert metrics.total_latency == 0.0
    assert metrics.min_latency == 0.0
    assert metrics.max_latency == 0.0


@pytest.mark.asyncio
async def test_metrics_concurrent_requests():
    """Test metrics with concurrent requests."""
    agent = SimpleAgent(delay=0.05)
    metrics_agent = MetricsDecorator(agent)

    msg = Message(role="user", content="test")

    # Launch concurrent requests
    tasks = [metrics_agent.process(msg) for _ in range(5)]
    await asyncio.gather(*tasks)

    metrics = metrics_agent.get_metrics()
    assert metrics.total_requests == 5
    assert metrics.success_requests == 5
    assert metrics.in_flight_requests == 0


@pytest.mark.asyncio
async def test_metrics_decorator_passthrough():
    """Test that decorator passes through name and capabilities."""
    agent = SimpleAgent()
    metrics_agent = MetricsDecorator(agent)

    assert metrics_agent.name == "simple"
    assert "test" in metrics_agent.capabilities
