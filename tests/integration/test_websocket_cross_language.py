"""Cross-language integration tests for WebSocket transport.

Tests Python client → Go server and Go client → Python server communication
over WebSocket.
"""

import pytest

from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.interfaces import Message

from .helpers import go_http_server, python_websocket_server


# Python Client → Go Server Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_websocket_basic():
    """Test basic WebSocket message exchange: Python client → Go server."""
    async with go_http_server() as (port, process):
        # Create remote agent with WebSocket endpoint
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}/ws"
        )

        # Send message
        message = Message(role="user", content="Hello via WebSocket!")
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: Hello via WebSocket!" in response.content
        assert response.metadata["server_language"] == "go"
        assert response.metadata["original_content"] == "Hello via WebSocket!"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_websocket_with_metadata():
    """Test WebSocket with metadata: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}/ws"
        )

        # Send message with metadata
        message = Message(
            role="user",
            content="WebSocket metadata test",
            metadata={
                "request_id": "ws-123",
                "priority": "high",
                "tags": ["websocket", "test"],
            }
        )
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: WebSocket metadata test" in response.content
        assert response.metadata["server_language"] == "go"

        # Check original metadata is preserved
        original_meta = response.metadata["original_metadata"]
        assert original_meta["request_id"] == "ws-123"
        assert original_meta["priority"] == "high"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_websocket_unicode():
    """Test Unicode over WebSocket: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}/ws"
        )

        # Send message with Unicode content
        unicode_content = "Hello 世界 🌍 Привет مرحبا"
        message = Message(role="user", content=unicode_content)
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert f"Echo: {unicode_content}" in response.content
        assert response.metadata["original_content"] == unicode_content


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_websocket_large_message():
    """Test large message over WebSocket: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}/ws"
        )

        # Send large message (1MB)
        large_content = "A" * (1024 * 1024)  # 1MB
        message = Message(role="user", content=large_content)
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert len(response.metadata["original_content"]) == 1024 * 1024


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_websocket_multiple_messages():
    """Test multiple messages over same WebSocket: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}/ws"
        )

        # Send multiple messages over the same connection
        for i in range(5):
            message = Message(role="user", content=f"WebSocket message {i}")
            response = await agent.process(message)

            assert response.role == "agent"
            assert f"Echo: WebSocket message {i}" in response.content
            assert response.metadata["original_content"] == f"WebSocket message {i}"


# Go Client → Python Server Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_websocket_basic():
    """Test basic WebSocket message: Go client → Python server."""
    async with python_websocket_server() as (port, local_agent, task):
        # Use Python RemoteAgent as a proxy for Go client behavior
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}"
        )

        message = Message(role="user", content="Hello from Go!")
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: Hello from Go!" in response.content
        assert response.metadata["language"] == "python"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_websocket_with_metadata():
    """Test WebSocket with metadata: Go client → Python server."""
    async with python_websocket_server() as (port, local_agent, task):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}"
        )

        message = Message(
            role="user",
            content="WebSocket metadata test",
            metadata={
                "request_id": "go-ws-123",
                "client": "go",
            }
        )
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: WebSocket metadata test" in response.content
        assert response.metadata["original"] == "WebSocket metadata test"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_websocket_unicode():
    """Test Unicode over WebSocket: Go client → Python server."""
    async with python_websocket_server() as (port, local_agent, task):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}"
        )

        unicode_content = "Hello 世界 🌍 Привет مرحبا"
        message = Message(role="user", content=unicode_content)
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert f"Echo: {unicode_content}" in response.content
        assert response.metadata["original"] == unicode_content


# Bidirectional and Concurrent Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
@pytest.mark.slow
async def test_websocket_concurrent_connections():
    """Test multiple concurrent WebSocket connections: Python → Go."""
    async with go_http_server() as (port, process):
        import asyncio

        # Create multiple concurrent connections
        async def send_message(i):
            agent = RemoteAgent(
                name=f"test-agent-{i}",
                endpoint=f"ws://localhost:{port}/ws"
            )
            message = Message(role="user", content=f"Concurrent WS {i}")
            response = await agent.process(message)
            return response

        # Send 10 concurrent messages on different connections
        tasks = [send_message(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)

        # Validate all responses
        assert len(responses) == 10
        for i, response in enumerate(responses):
            assert response.role == "agent"
            assert f"Echo: Concurrent WS {i}" in response.content


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_websocket_connection_reuse():
    """Test connection reuse over WebSocket."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"ws://localhost:{port}/ws"
        )

        # Send multiple messages - connection should be reused
        for i in range(10):
            message = Message(role="user", content=f"Reuse {i}")
            response = await agent.process(message)

            assert response.role == "agent"
            assert f"Echo: Reuse {i}" in response.content


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_websocket_cross_language.py -v -m cross_language
    pytest.main([__file__, "-v", "-m", "cross_language"])
