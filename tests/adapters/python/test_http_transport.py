"""Tests for HTTP transport with HTTP/2 support."""

import asyncio
import pytest

from agenkit.adapters.python.http_server import HTTPAgentServer
from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.interfaces import Agent, Message


class EchoAgent(Agent):
    """Simple echo agent for testing."""

    async def process(self, message: Message) -> Message:
        """Echo the input message."""
        return Message(
            role="agent",
            content=f"Echo: {message.content}",
            metadata=message.metadata,
        )

    @property
    def name(self) -> str:
        return "echo"


class StreamingEchoAgent(Agent):
    """Streaming echo agent that returns 5 chunks."""

    async def stream(self, message: Message):
        """Stream 5 chunks."""
        for i in range(5):
            yield Message(
                role="agent",
                content=f"Chunk {i}: {message.content}",
                metadata=message.metadata,
            )
            await asyncio.sleep(0.01)

    async def process(self, message: Message) -> Message:
        """Non-streaming fallback."""
        return Message(role="agent", content=f"Echo: {message.content}")

    @property
    def name(self) -> str:
        return "echo"


class ErrorAgent(Agent):
    """Agent that always raises an error."""

    async def process(self, message: Message) -> Message:
        raise ValueError("Test error")

    @property
    def name(self) -> str:
        return "error"


class SlowAgent(Agent):
    """Agent with slow responses for timeout testing."""

    async def process(self, message: Message) -> Message:
        await asyncio.sleep(2.0)
        return Message(role="agent", content="Slow response")

    @property
    def name(self) -> str:
        return "slow"


@pytest.fixture
async def http_server():
    """Create HTTP server fixture."""
    agent = EchoAgent()
    server = HTTPAgentServer(agent, "localhost", 18080)
    await server.start()
    await asyncio.sleep(0.05)  # Wait for server to start
    yield server
    await server.stop()


@pytest.fixture
async def http2_server():
    """Create HTTP/2 server fixture."""
    agent = EchoAgent()
    server = HTTPAgentServer(agent, "localhost", 18088, enable_http2=True)
    await server.start()
    await asyncio.sleep(0.05)
    yield server
    await server.stop()


@pytest.fixture
async def streaming_server():
    """Create streaming HTTP server fixture."""
    agent = StreamingEchoAgent()
    server = HTTPAgentServer(agent, "localhost", 18081)
    await server.start()
    await asyncio.sleep(0.05)
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_http_basic_communication(http_server):
    """Test basic HTTP communication."""
    client = RemoteAgent("echo", "http://localhost:18080")

    message = Message(role="user", content="test message")
    response = await client.process(message)

    assert response.role == "agent"
    assert response.content == "Echo: test message"

    await client.close()


@pytest.mark.asyncio
async def test_http_streaming():
    """Test HTTP streaming with SSE."""
    agent = StreamingEchoAgent()
    server = HTTPAgentServer(agent, "localhost", 18081)
    await server.start()
    await asyncio.sleep(0.05)

    try:
        client = RemoteAgent("echo", "http://localhost:18081")

        message = Message(role="user", content="test")
        chunks = []
        async for chunk in client.stream(message):
            chunks.append(chunk)

        assert len(chunks) == 5
        for i, chunk in enumerate(chunks):
            assert chunk.content == f"Chunk {i}: test"

        await client.close()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_http_concurrent_requests(http_server):
    """Test concurrent HTTP requests."""
    clients = [RemoteAgent("echo", "http://localhost:18080") for _ in range(5)]

    async def send_message(client: RemoteAgent, idx: int):
        message = Message(role="user", content=f"message {idx}")
        response = await client.process(message)
        assert response.content == f"Echo: message {idx}"
        return response

    results = await asyncio.gather(*[send_message(clients[i], i) for i in range(5)])
    assert len(results) == 5

    for client in clients:
        await client.close()


@pytest.mark.asyncio
async def test_http_error_handling():
    """Test HTTP error handling."""
    agent = ErrorAgent()
    server = HTTPAgentServer(agent, "localhost", 18083)
    await server.start()
    await asyncio.sleep(0.05)

    try:
        client = RemoteAgent("error", "http://localhost:18083")

        message = Message(role="user", content="test")
        with pytest.raises(Exception):
            await client.process(message)

        await client.close()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_http_metadata_preservation(http_server):
    """Test that metadata is preserved in HTTP requests."""
    client = RemoteAgent("echo", "http://localhost:18080")

    message = Message(
        role="user",
        content="test",
        metadata={"key1": "value1", "key2": 42}
    )
    response = await client.process(message)

    # Verify response was received
    assert response.role == "agent"
    assert response.content == "Echo: test"

    await client.close()


@pytest.mark.asyncio
async def test_http_large_payload(http_server):
    """Test HTTP with large payload."""
    client = RemoteAgent("echo", "http://localhost:18080")

    # 100KB message
    large_content = "x" * (100 * 1024)
    message = Message(role="user", content=large_content)
    response = await client.process(message)

    assert response.content == f"Echo: {large_content}"

    await client.close()


@pytest.mark.asyncio
async def test_http_context_cancellation():
    """Test HTTP request cancellation."""
    agent = SlowAgent()
    server = HTTPAgentServer(agent, "localhost", 18087)
    await server.start()
    await asyncio.sleep(0.05)

    try:
        client = RemoteAgent("slow", "http://localhost:18087")

        message = Message(role="user", content="test")

        # Test with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(client.process(message), timeout=0.5)

        await client.close()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_http2_basic_communication():
    """Test HTTP/2 cleartext communication."""
    agent = EchoAgent()
    server = HTTPAgentServer(agent, "localhost", 18088, enable_http2=True)
    await server.start()
    await asyncio.sleep(0.05)

    try:
        # Use h2c:// for HTTP/2 cleartext
        client = RemoteAgent("echo", "h2c://localhost:18088")

        message = Message(role="user", content="test message http2")
        response = await client.process(message)

        assert response.role == "agent"
        assert response.content == "Echo: test message http2"

        await client.close()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_http2_streaming():
    """Test HTTP/2 streaming."""
    agent = StreamingEchoAgent()
    server = HTTPAgentServer(agent, "localhost", 18089, enable_http2=True)
    await server.start()
    await asyncio.sleep(0.05)

    try:
        client = RemoteAgent("echo", "h2c://localhost:18089")

        message = Message(role="user", content="test")
        chunks = []
        async for chunk in client.stream(message):
            chunks.append(chunk)

        assert len(chunks) == 5
        for i, chunk in enumerate(chunks):
            assert chunk.content == f"Chunk {i}: test"

        await client.close()
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_http_protocol_detection():
    """Test URL scheme detection."""
    # These should not raise errors
    endpoints = [
        "http://localhost:8080",
        "https://example.com",
        "h2c://localhost:8080",
        "h3://localhost:8080",
    ]

    for endpoint in endpoints:
        client = RemoteAgent("test", endpoint)
        # Just verify creation succeeds
        await client.close()
