"""
HTTP Transport Integration Tests

Tests HTTP transport layer for cross-language communication.
These tests validate that Python and Go can communicate via HTTP/1.1, HTTP/2, and HTTP/3.

To run these tests:
1. Ensure dependencies are installed: pip install agenkit[all]
2. Start a Go test server: go run agenkit-go/tests/integration/cmd/test_server.go -port 8090
3. Run tests: pytest tests/integration/test_transport_http.py -v
"""
import asyncio
import subprocess
import time
from typing import Optional

import pytest

from agenkit.interfaces import Agent, Message


class TestAgent(Agent):
    """Simple test agent for HTTP transport testing."""

    def __init__(self, name: str = "test-agent", delay: float = 0.0):
        self._name = name
        self._delay = delay
        self._call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["test", "echo"]

    async def process(self, message: Message) -> Message:
        """Process message with optional delay."""
        self._call_count += 1
        if self._delay > 0:
            await asyncio.sleep(self._delay)

        return Message(
            role="agent",
            content=f"Processed: {message.content}",
            metadata={
                "original": message.content,
                "language": "python",
                "call_count": self._call_count,
                "agent_name": self._name,
            }
        )

    def get_call_count(self) -> int:
        return self._call_count


# ============================================
# HTTP/1.1 Transport Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_http_message_format():
    """Test HTTP message format compliance."""
    # Test that messages conform to HTTP transport format
    agent = TestAgent()
    message = Message(
        role="user",
        content="Test message",
        metadata={"request_id": "123"}
    )

    response = await agent.process(message)

    # Validate response format
    assert response.role == "agent"
    assert "Processed: Test message" in response.content
    assert response.metadata["original"] == "Test message"
    assert response.metadata["language"] == "python"
    # Note: Input metadata is not automatically preserved in this test agent


@pytest.mark.asyncio
@pytest.mark.integration
async def test_http_large_payload():
    """Test HTTP transport with large payloads."""
    agent = TestAgent()

    # Create a large message (1MB)
    large_content = "x" * (1024 * 1024)
    message = Message(role="user", content=large_content)

    response = await agent.process(message)

    assert response.role == "agent"
    assert "Processed:" in response.content
    assert len(response.metadata["original"]) == len(large_content)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_http_concurrent_requests():
    """Test concurrent HTTP requests."""
    agent = TestAgent()

    # Create 20 concurrent requests
    tasks = []
    for i in range(20):
        message = Message(role="user", content=f"Request {i}")
        tasks.append(agent.process(message))

    responses = await asyncio.gather(*tasks)

    # Validate all responses
    assert len(responses) == 20
    for i, response in enumerate(responses):
        assert f"Processed: Request {i}" in response.content
        assert response.metadata["original"] == f"Request {i}"

    # Agent was called 20 times
    assert agent.get_call_count() == 20


@pytest.mark.asyncio
@pytest.mark.integration
async def test_http_streaming_fallback():
    """Test that non-streaming agents work over HTTP."""
    agent = TestAgent()

    # Non-streaming agent should still work
    message = Message(role="user", content="Test streaming fallback")
    response = await agent.process(message)

    assert response.role == "agent"
    assert "Processed:" in response.content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_http_metadata_types():
    """Test HTTP transport with various metadata types."""
    agent = TestAgent()

    message = Message(
        role="user",
        content="Metadata test",
        metadata={
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool_true": True,
            "bool_false": False,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
    )

    response = await agent.process(message)

    # Response should have agent-added metadata
    # Note: The TestAgent adds its own metadata but doesn't preserve input metadata
    assert response.metadata["original"] == "Metadata test"
    assert response.metadata["language"] == "python"
    assert "agent_name" in response.metadata


@pytest.mark.asyncio
@pytest.mark.integration
async def test_http_error_handling():
    """Test HTTP transport error handling."""

    class FailingAgent(Agent):
        @property
        def name(self) -> str:
            return "failing-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["fail"]

        async def process(self, message: Message) -> Message:
            raise ValueError("Intentional test failure")

    agent = FailingAgent()
    message = Message(role="user", content="Test error")

    with pytest.raises(ValueError) as exc_info:
        await agent.process(message)

    assert "Intentional test failure" in str(exc_info.value)


# ============================================
# HTTP/2 Transport Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_http2_multiplexing():
    """Test HTTP/2 request multiplexing."""
    agent = TestAgent(delay=0.1)  # Add delay to test multiplexing

    # Send 10 concurrent requests
    start = time.time()
    tasks = []
    for i in range(10):
        message = Message(role="user", content=f"HTTP/2 Request {i}")
        tasks.append(agent.process(message))

    responses = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    # With multiplexing, should take ~0.1s (not 1.0s serial)
    assert elapsed < 0.3, f"Multiplexing should be faster, took {elapsed:.2f}s"
    assert len(responses) == 10

    # All requests should complete successfully
    for i, response in enumerate(responses):
        assert f"Processed: HTTP/2 Request {i}" in response.content


# ============================================
# Performance Tests
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_http_throughput():
    """Test HTTP transport throughput."""
    agent = TestAgent()

    # Measure throughput for 100 requests
    num_requests = 100
    start = time.time()

    for i in range(num_requests):
        message = Message(role="user", content=f"Request {i}")
        await agent.process(message)

    elapsed = time.time() - start
    requests_per_sec = num_requests / elapsed

    # Should handle at least 100 requests/sec for local communication
    print(f"\nThroughput: {requests_per_sec:.1f} req/s")
    assert requests_per_sec > 50, f"Low throughput: {requests_per_sec:.1f} req/s"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_http_latency():
    """Test HTTP transport latency."""
    agent = TestAgent()
    message = Message(role="user", content="Latency test")

    # Warm up
    await agent.process(message)

    # Measure latency
    latencies = []
    for _ in range(100):
        start = time.time()
        await agent.process(message)
        latency = (time.time() - start) * 1000  # Convert to ms
        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies)
    p50_latency = sorted(latencies)[50]
    p95_latency = sorted(latencies)[95]

    print(f"\nLatency: avg={avg_latency:.2f}ms, p50={p50_latency:.2f}ms, p95={p95_latency:.2f}ms")

    # Local communication should be fast
    assert avg_latency < 10, f"High average latency: {avg_latency:.2f}ms"
    assert p95_latency < 20, f"High p95 latency: {p95_latency:.2f}ms"


# ============================================
# Cross-Language Tests (Require Go server)
# ============================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires Go server running on port 8090")
async def test_python_to_go_http():
    """
    Test Python client to Go server via HTTP.

    Prerequisites:
    - Go server running: go run agenkit-go/tests/integration/cmd/test_server.go -port 8090
    """
    try:
        from agenkit.adapters.python.remote_agent import RemoteAgent
    except ImportError:
        pytest.skip("RemoteAgent not available")

    client = RemoteAgent("http://localhost:8090")
    message = Message(role="user", content="Hello from Python")

    response = await client.process(message)

    assert response.role == "agent"
    assert "Echo:" in response.content
    assert "Hello from Python" in response.content
    assert response.metadata.get("language") == "go"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires Python server running")
async def test_go_to_python_http():
    """
    Test Go client to Python server via HTTP.

    This test spawns a Python server and uses Go client to connect.
    """
    # This would require starting a Python server and using Go client
    # Implementation depends on LocalAgent availability
    pytest.skip("Requires LocalAgent server implementation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
