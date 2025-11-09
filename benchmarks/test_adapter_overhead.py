"""Benchmark adapter overhead.

This benchmark measures the overhead of the protocol adapter compared to direct
local agent calls. Target: <5% overhead as specified in Issue #2.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from agenkit import Agent, Message
from agenkit.adapters.python import LocalAgent, RemoteAgent


class SimpleAgent(Agent):
    """Minimal agent for benchmarking."""

    @property
    def name(self) -> str:
        return "simple"

    async def process(self, message: Message) -> Message:
        # Minimal processing to isolate adapter overhead
        return Message(role="agent", content=f"Processed: {message.content}")


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for module scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def remote_agent_setup(event_loop):
    """Set up remote agent for benchmarking."""
    agent = SimpleAgent()

    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "bench.sock"
        endpoint = f"unix://{socket_path}"

        # Start server
        server = LocalAgent(agent, endpoint=endpoint)
        await server.start()

        # Create client
        remote = RemoteAgent("simple", endpoint=endpoint)

        yield agent, remote

        await server.stop()


@pytest.mark.benchmark(group="adapter-overhead")
def test_baseline_direct_agent_call(benchmark):
    """Baseline: Direct local agent call (no adapter)."""
    agent = SimpleAgent()
    message = Message(role="user", content="test")

    async def process_direct():
        return await agent.process(message)

    result = benchmark(lambda: asyncio.run(process_direct()))
    assert "Processed" in result.content


@pytest.mark.benchmark(group="adapter-overhead")
def test_remote_agent_call(benchmark, remote_agent_setup):
    """Remote agent call through adapter."""
    _, remote = asyncio.run(remote_agent_setup.__anext__())
    message = Message(role="user", content="test")

    async def process_remote():
        return await remote.process(message)

    result = benchmark(lambda: asyncio.run(process_remote()))
    assert "Processed" in result.content


# Additional benchmarks for different message sizes

@pytest.mark.benchmark(group="message-size")
def test_baseline_small_message(benchmark):
    """Baseline: Small message (100 bytes)."""
    agent = SimpleAgent()
    message = Message(role="user", content="x" * 100)

    result = benchmark(lambda: asyncio.run(agent.process(message)))
    assert "Processed" in result.content


@pytest.mark.benchmark(group="message-size")
def test_remote_small_message(benchmark, remote_agent_setup):
    """Remote: Small message (100 bytes)."""
    _, remote = asyncio.run(remote_agent_setup.__anext__())
    message = Message(role="user", content="x" * 100)

    result = benchmark(lambda: asyncio.run(remote.process(message)))
    assert "Processed" in result.content


@pytest.mark.benchmark(group="message-size")
def test_baseline_medium_message(benchmark):
    """Baseline: Medium message (10KB)."""
    agent = SimpleAgent()
    message = Message(role="user", content="x" * 10240)

    result = benchmark(lambda: asyncio.run(agent.process(message)))
    assert "Processed" in result.content


@pytest.mark.benchmark(group="message-size")
def test_remote_medium_message(benchmark, remote_agent_setup):
    """Remote: Medium message (10KB)."""
    _, remote = asyncio.run(remote_agent_setup.__anext__())
    message = Message(role="user", content="x" * 10240)

    result = benchmark(lambda: asyncio.run(remote.process(message)))
    assert "Processed" in result.content


@pytest.mark.benchmark(group="message-size")
def test_baseline_large_message(benchmark):
    """Baseline: Large message (1MB)."""
    agent = SimpleAgent()
    message = Message(role="user", content="x" * (1024 * 1024))

    result = benchmark(lambda: asyncio.run(agent.process(message)))
    assert "Processed" in result.content


@pytest.mark.benchmark(group="message-size")
def test_remote_large_message(benchmark, remote_agent_setup):
    """Remote: Large message (1MB)."""
    _, remote = asyncio.run(remote_agent_setup.__anext__())
    message = Message(role="user", content="x" * (1024 * 1024))

    result = benchmark(lambda: asyncio.run(remote.process(message)))
    assert "Processed" in result.content


# Throughput benchmark

@pytest.mark.benchmark(group="throughput")
def test_baseline_throughput(benchmark):
    """Baseline: Multiple sequential requests."""
    agent = SimpleAgent()
    messages = [Message(role="user", content=f"test{i}") for i in range(10)]

    async def process_batch():
        results = []
        for msg in messages:
            result = await agent.process(msg)
            results.append(result)
        return results

    results = benchmark(lambda: asyncio.run(process_batch()))
    assert len(results) == 10


@pytest.mark.benchmark(group="throughput")
def test_remote_throughput(benchmark, remote_agent_setup):
    """Remote: Multiple sequential requests."""
    _, remote = asyncio.run(remote_agent_setup.__anext__())
    messages = [Message(role="user", content=f"test{i}") for i in range(10)]

    async def process_batch():
        results = []
        for msg in messages:
            result = await remote.process(msg)
            results.append(result)
        return results

    results = benchmark(lambda: asyncio.run(process_batch()))
    assert len(results) == 10
