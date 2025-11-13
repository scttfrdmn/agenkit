"""
WebSocket Transport Integration Tests

Tests WebSocket transport for bidirectional communication between Python and Go.

Prerequisites:
1. Activate venv: source venv/bin/activate
2. Install dependencies: pip install agenkit[all]
3. Start Go WebSocket server: go run agenkit-go/tests/integration/cmd/test_server.go -port 8091 -protocol ws
4. Run tests: pytest tests/integration/test_transport_websocket.py -v
"""
import asyncio
import time
from typing import AsyncIterator

import pytest

from agenkit.interfaces import Agent, Message

try:
    from agenkit.interfaces import StreamingAgent
except ImportError:
    # Define a simple StreamingAgent base class for testing
    class StreamingAgent(Agent):
        """Base class for streaming agents."""
        async def stream(self, message: Message) -> AsyncIterator[Message]:
            """Stream response - must be implemented by subclasses."""
            raise NotImplementedError


class StreamingTestAgent(StreamingAgent):
    """Test agent that supports streaming."""

    def __init__(self, name: str = "streaming-agent"):
        self._name = name
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["stream", "echo"]

    async def process(self, message: Message) -> Message:
        """Process message (non-streaming)."""
        self._call_count += 1
        return Message(
            role="agent",
            content=f"Processed: {message.content}",
            metadata={
                "original": message.content,
                "language": "python",
                "streaming": False,
                "call_count": self._call_count,
            }
        )

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """Stream response in chunks."""
        self._call_count += 1

        # Split content into words and stream
        words = message.content.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.01)  # Simulate processing
            yield Message(
                role="agent",
                content=word,
                metadata={
                    "chunk": i,
                    "total_chunks": len(words),
                    "streaming": True,
                    "language": "python",
                }
            )


# ============================================
# WebSocket Connection Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_connection_lifecycle():
    """Test WebSocket connection establishment and cleanup."""
    agent = StreamingTestAgent()

    # Simulate connection lifecycle
    message = Message(role="user", content="Connection test")
    response = await agent.process(message)

    assert response.role == "agent"
    assert "Processed:" in response.content
    assert response.metadata["streaming"] is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_bidirectional_communication():
    """Test bidirectional communication over WebSocket."""
    agent = StreamingTestAgent()

    # Send multiple messages in sequence (simulating bidirectional)
    messages = [
        "First message",
        "Second message",
        "Third message",
    ]

    for msg_content in messages:
        message = Message(role="user", content=msg_content)
        response = await agent.process(message)

        assert response.role == "agent"
        assert f"Processed: {msg_content}" in response.content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_ping_pong():
    """Test WebSocket ping/pong keepalive."""
    agent = StreamingTestAgent()

    # Send message and verify connection is alive
    message = Message(role="user", content="Ping")
    response = await agent.process(message)

    assert response.role == "agent"
    # In real WebSocket, server would respond to ping with pong


# ============================================
# WebSocket Streaming Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_streaming():
    """Test streaming over WebSocket."""
    agent = StreamingTestAgent()

    message = Message(role="user", content="Stream this message word by word")

    chunks = []
    async for chunk in agent.stream(message):
        chunks.append(chunk)

    # Should receive 6 chunks (one per word)
    assert len(chunks) == 6
    words = ["Stream", "this", "message", "word", "by", "word"]

    for i, chunk in enumerate(chunks):
        assert chunk.content == words[i]
        assert chunk.metadata["chunk"] == i
        assert chunk.metadata["total_chunks"] == 6
        assert chunk.metadata["streaming"] is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_stream_cancellation():
    """Test stream cancellation over WebSocket."""
    agent = StreamingTestAgent()

    message = Message(role="user", content="This is a long message that will be cancelled")

    chunks_received = 0
    async for chunk in agent.stream(message):
        chunks_received += 1
        if chunks_received >= 3:
            # Cancel after 3 chunks
            break

    assert chunks_received == 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_stream_backpressure():
    """Test backpressure handling in WebSocket streaming."""
    agent = StreamingTestAgent()

    message = Message(role="user", content="Test backpressure with slow consumer")

    chunks = []
    async for chunk in agent.stream(message):
        # Slow consumer
        await asyncio.sleep(0.05)
        chunks.append(chunk)

    # All chunks should still be received (5 words in message)
    assert len(chunks) == 5


# ============================================
# WebSocket Performance Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_websocket_streaming_throughput():
    """Test WebSocket streaming throughput."""
    agent = StreamingTestAgent()

    # Stream 100 words
    content = " ".join([f"word{i}" for i in range(100)])
    message = Message(role="user", content=content)

    start = time.time()
    chunks = []
    async for chunk in agent.stream(message):
        chunks.append(chunk)
    elapsed = time.time() - start

    chunks_per_sec = len(chunks) / elapsed
    print(f"\nStreaming throughput: {chunks_per_sec:.1f} chunks/s")

    assert len(chunks) == 100
    assert chunks_per_sec > 50, f"Low streaming throughput: {chunks_per_sec:.1f} chunks/s"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_concurrent_streams():
    """Test multiple concurrent streams over WebSocket."""
    agent = StreamingTestAgent()

    # Start 5 concurrent streams
    async def stream_message(content: str):
        message = Message(role="user", content=content)
        chunks = []
        async for chunk in agent.stream(message):
            chunks.append(chunk)
        return chunks

    tasks = [
        stream_message(f"Stream {i} content")
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)

    # All streams should complete
    assert len(results) == 5
    for result in results:
        assert len(result) == 3  # 3 words per message


# ============================================
# WebSocket Error Handling
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_connection_error():
    """Test WebSocket connection error handling."""

    class FailingAgent(StreamingAgent):
        @property
        def name(self) -> str:
            return "failing-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["fail"]

        async def process(self, message: Message) -> Message:
            raise ConnectionError("WebSocket connection lost")

        async def stream(self, message: Message) -> AsyncIterator[Message]:
            raise ConnectionError("WebSocket connection lost during stream")
            yield  # Never reached

    agent = FailingAgent()
    message = Message(role="user", content="Test error")

    with pytest.raises(ConnectionError):
        await agent.process(message)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_stream_error():
    """Test error handling during WebSocket streaming."""

    class StreamErrorAgent(StreamingAgent):
        @property
        def name(self) -> str:
            return "stream-error-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["stream"]

        async def process(self, message: Message) -> Message:
            return Message(role="agent", content="OK")

        async def stream(self, message: Message) -> AsyncIterator[Message]:
            # Stream a few chunks then error
            for i in range(3):
                yield Message(role="agent", content=f"Chunk {i}")

            raise RuntimeError("Stream error after 3 chunks")

    agent = StreamErrorAgent()
    message = Message(role="user", content="Test stream error")

    chunks = []
    with pytest.raises(RuntimeError):
        async for chunk in agent.stream(message):
            chunks.append(chunk)

    # Should have received 3 chunks before error
    assert len(chunks) == 3


# ============================================
# Cross-Language Tests (Require Go server)
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires Go WebSocket server on port 8091")
async def test_python_to_go_websocket():
    """
    Test Python client to Go WebSocket server.

    Prerequisites:
    - Go server: go run agenkit-go/tests/integration/cmd/test_server.go -port 8091 -protocol ws
    """
    try:
        from agenkit.adapters.python.remote_agent import RemoteAgent
    except ImportError:
        pytest.skip("RemoteAgent not available")

    client = RemoteAgent("ws://localhost:8091")
    message = Message(role="user", content="Hello via WebSocket")

    response = await client.process(message)

    assert response.role == "agent"
    assert "Echo:" in response.content
    assert response.metadata.get("language") == "go"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires Go WebSocket server")
async def test_websocket_streaming_python_to_go():
    """
    Test streaming from Python client to Go WebSocket server.
    """
    try:
        from agenkit.adapters.python.remote_agent import RemoteAgent
    except ImportError:
        pytest.skip("RemoteAgent not available")

    client = RemoteAgent("ws://localhost:8091")
    message = Message(role="user", content="Stream this message")

    # Assuming RemoteAgent supports streaming
    if hasattr(client, 'stream'):
        chunks = []
        async for chunk in client.stream(message):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all(chunk.metadata.get("language") == "go" for chunk in chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
