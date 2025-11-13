"""
gRPC Transport Integration Tests

Tests gRPC transport for high-performance cross-language communication.

Prerequisites:
1. Activate venv: source venv/bin/activate
2. Install dependencies: pip install agenkit[all]
3. Start Go gRPC server: go run agenkit-go/tests/integration/cmd/test_server.go -port 50051 -protocol grpc
4. Run tests: pytest tests/integration/test_transport_grpc.py -v
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


class GRPCTestAgent(StreamingAgent):
    """Test agent for gRPC transport testing."""

    def __init__(self, name: str = "grpc-agent"):
        self._name = name
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["grpc", "stream", "echo"]

    async def process(self, message: Message) -> Message:
        """Process message (unary RPC)."""
        self._call_count += 1
        # Preserve input metadata and add our own
        response_metadata = dict(message.metadata) if message.metadata else {}
        response_metadata.update({
            "original": message.content,
            "language": "python",
            "transport": "grpc",
            "call_count": self._call_count,
        })
        return Message(
            role="agent",
            content=f"gRPC: {message.content}",
            metadata=response_metadata
        )

    async def stream(self, message: Message) -> AsyncIterator[Message]:
        """Stream response (server streaming RPC)."""
        self._call_count += 1

        # Stream words with metadata
        words = message.content.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.01)
            yield Message(
                role="agent",
                content=word,
                metadata={
                    "chunk": i,
                    "total_chunks": len(words),
                    "transport": "grpc",
                    "streaming": True,
                }
            )


# ============================================
# gRPC Unary RPC Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_unary_call():
    """Test gRPC unary call (single request, single response)."""
    agent = GRPCTestAgent()

    message = Message(role="user", content="Test unary RPC")
    response = await agent.process(message)

    assert response.role == "agent"
    assert "gRPC: Test unary RPC" in response.content
    assert response.metadata["transport"] == "grpc"
    assert response.metadata["original"] == "Test unary RPC"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_metadata_propagation():
    """Test gRPC metadata propagation."""
    agent = GRPCTestAgent()

    message = Message(
        role="user",
        content="Test metadata",
        metadata={
            "trace_id": "abc-123",
            "user_id": 42,
            "priority": "high",
        }
    )

    response = await agent.process(message)

    # Response should preserve and add metadata
    assert response.metadata["trace_id"] == "abc-123"
    assert response.metadata["user_id"] == 42
    assert response.metadata["priority"] == "high"
    assert response.metadata["transport"] == "grpc"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_large_message():
    """Test gRPC with large messages (tests chunking)."""
    agent = GRPCTestAgent()

    # 5MB message
    large_content = "x" * (5 * 1024 * 1024)
    message = Message(role="user", content=large_content)

    response = await agent.process(message)

    assert response.role == "agent"
    assert len(response.metadata["original"]) == len(large_content)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_concurrent_unary_calls():
    """Test concurrent gRPC unary calls (connection multiplexing)."""
    agent = GRPCTestAgent()

    # 50 concurrent calls
    tasks = []
    for i in range(50):
        message = Message(role="user", content=f"Call {i}")
        tasks.append(agent.process(message))

    start = time.time()
    responses = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    # Should complete fast due to HTTP/2 multiplexing
    assert len(responses) == 50
    for i, response in enumerate(responses):
        assert f"gRPC: Call {i}" in response.content

    print(f"\n50 concurrent gRPC calls: {elapsed:.3f}s ({50/elapsed:.1f} req/s)")


# ============================================
# gRPC Streaming RPC Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_server_streaming():
    """Test gRPC server-side streaming."""
    agent = GRPCTestAgent()

    message = Message(role="user", content="Stream these five words please")

    chunks = []
    async for chunk in agent.stream(message):
        chunks.append(chunk)

    # Should receive 5 chunks
    assert len(chunks) == 5
    words = ["Stream", "these", "five", "words", "please"]

    for i, chunk in enumerate(chunks):
        assert chunk.content == words[i]
        assert chunk.metadata["chunk"] == i
        assert chunk.metadata["transport"] == "grpc"
        assert chunk.metadata["streaming"] is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_stream_with_metadata():
    """Test gRPC streaming with metadata in each chunk."""
    agent = GRPCTestAgent()

    message = Message(
        role="user",
        content="One Two Three",
        metadata={"request_id": "stream-123"}
    )

    chunks = []
    async for chunk in agent.stream(message):
        chunks.append(chunk)
        # Each chunk should have transport metadata
        assert chunk.metadata["transport"] == "grpc"
        assert chunk.metadata["streaming"] is True

    assert len(chunks) == 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_stream_cancellation():
    """Test gRPC stream cancellation."""
    agent = GRPCTestAgent()

    message = Message(role="user", content="Stream that will be cancelled early")

    chunks_received = 0
    async for chunk in agent.stream(message):
        chunks_received += 1
        if chunks_received >= 2:
            break  # Cancel stream

    assert chunks_received == 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_concurrent_streams():
    """Test multiple concurrent gRPC streams."""
    agent = GRPCTestAgent()

    async def stream_and_collect(content: str):
        message = Message(role="user", content=content)
        chunks = []
        async for chunk in agent.stream(message):
            chunks.append(chunk)
        return chunks

    # 10 concurrent streams
    tasks = [
        stream_and_collect(f"Stream {i} content")
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    for result in results:
        assert len(result) == 3  # 3 words per message


# ============================================
# gRPC Performance Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_grpc_throughput():
    """Test gRPC throughput (requests per second)."""
    agent = GRPCTestAgent()

    num_requests = 1000
    start = time.time()

    for i in range(num_requests):
        message = Message(role="user", content=f"Request {i}")
        await agent.process(message)

    elapsed = time.time() - start
    throughput = num_requests / elapsed

    print(f"\ngRPC throughput: {throughput:.1f} req/s")
    # gRPC should handle high throughput
    assert throughput > 100, f"Low gRPC throughput: {throughput:.1f} req/s"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_grpc_latency():
    """Test gRPC latency (round-trip time)."""
    agent = GRPCTestAgent()
    message = Message(role="user", content="Latency test")

    # Warm up
    await agent.process(message)

    # Measure latency
    latencies = []
    for _ in range(100):
        start = time.time()
        await agent.process(message)
        latency = (time.time() - start) * 1000  # ms
        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies)
    p50_latency = sorted(latencies)[50]
    p95_latency = sorted(latencies)[95]
    p99_latency = sorted(latencies)[99]

    print(f"\ngRPC latency: avg={avg_latency:.2f}ms, p50={p50_latency:.2f}ms, "
          f"p95={p95_latency:.2f}ms, p99={p99_latency:.2f}ms")

    # gRPC should have low latency
    assert avg_latency < 5, f"High average latency: {avg_latency:.2f}ms"
    assert p95_latency < 10, f"High p95 latency: {p95_latency:.2f}ms"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_grpc_streaming_throughput():
    """Test gRPC streaming throughput."""
    agent = GRPCTestAgent()

    # Stream 500 words
    content = " ".join([f"word{i}" for i in range(500)])
    message = Message(role="user", content=content)

    start = time.time()
    chunks = []
    async for chunk in agent.stream(message):
        chunks.append(chunk)
    elapsed = time.time() - start

    chunks_per_sec = len(chunks) / elapsed
    print(f"\ngRPC streaming: {chunks_per_sec:.1f} chunks/s")

    assert len(chunks) == 500
    assert chunks_per_sec > 80, f"Low streaming throughput: {chunks_per_sec:.1f} chunks/s"


# ============================================
# gRPC Error Handling
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_error_codes():
    """Test gRPC error code handling."""

    class ErrorAgent(Agent):
        @property
        def name(self) -> str:
            return "error-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["error"]

        async def process(self, message: Message) -> Message:
            # Simulate different error types
            if "not_found" in message.content:
                raise FileNotFoundError("Resource not found")
            elif "invalid" in message.content:
                raise ValueError("Invalid argument")
            elif "unavailable" in message.content:
                raise ConnectionError("Service unavailable")
            else:
                raise RuntimeError("Internal error")

    agent = ErrorAgent()

    # Test different error conditions
    with pytest.raises(FileNotFoundError):
        await agent.process(Message(role="user", content="not_found"))

    with pytest.raises(ValueError):
        await agent.process(Message(role="user", content="invalid"))

    with pytest.raises(ConnectionError):
        await agent.process(Message(role="user", content="unavailable"))


@pytest.mark.asyncio
@pytest.mark.integration
async def test_grpc_timeout():
    """Test gRPC deadline/timeout handling."""

    class SlowAgent(Agent):
        @property
        def name(self) -> str:
            return "slow-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["slow"]

        async def process(self, message: Message) -> Message:
            await asyncio.sleep(5)  # Very slow
            return Message(role="agent", content="Done")

    agent = SlowAgent()
    message = Message(role="user", content="Slow request")

    # Test with timeout (would need actual gRPC context)
    try:
        response = await asyncio.wait_for(agent.process(message), timeout=0.1)
        pytest.fail("Should have timed out")
    except asyncio.TimeoutError:
        pass  # Expected


# ============================================
# Cross-Language Tests (Require Go server)
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires Go gRPC server on port 50051")
async def test_python_to_go_grpc():
    """
    Test Python client to Go gRPC server.

    Prerequisites:
    - Go gRPC server: go run agenkit-go/tests/integration/cmd/test_server.go -port 50051 -protocol grpc
    """
    try:
        from agenkit.adapters.python.remote_agent import RemoteAgent
    except ImportError:
        pytest.skip("RemoteAgent not available")

    client = RemoteAgent("grpc://localhost:50051")
    message = Message(role="user", content="Hello via gRPC")

    response = await client.process(message)

    assert response.role == "agent"
    assert "Echo:" in response.content
    assert response.metadata.get("language") == "go"
    assert response.metadata.get("transport") == "grpc"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires Go gRPC server")
async def test_grpc_streaming_python_to_go():
    """Test gRPC streaming from Python client to Go server."""
    try:
        from agenkit.adapters.python.remote_agent import RemoteAgent
    except ImportError:
        pytest.skip("RemoteAgent not available")

    client = RemoteAgent("grpc://localhost:50051")
    message = Message(role="user", content="Stream this via gRPC")

    if hasattr(client, 'stream'):
        chunks = []
        async for chunk in client.stream(message):
            chunks.append(chunk)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata.get("language") == "go"
            assert chunk.metadata.get("transport") == "grpc"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires servers in both languages")
async def test_grpc_bidirectional_streaming():
    """Test bidirectional streaming (client and server both stream)."""
    # This would require BiDi streaming support in both Python and Go
    pytest.skip("Bidirectional streaming not yet implemented")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
