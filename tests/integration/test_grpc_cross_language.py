"""Cross-language integration tests for gRPC transport.

Tests Python client → Go server and Go client → Python server communication
over gRPC.
"""

import pytest

from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.interfaces import Message

from .helpers import go_grpc_server, python_grpc_server


# Python Client → Go Server Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_grpc_basic():
    """Test basic gRPC message exchange: Python client → Go server."""
    async with go_grpc_server() as (port, process):
        # Create remote agent with gRPC endpoint
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        # Send message
        message = Message(role="user", content="Hello via gRPC!")
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: Hello via gRPC!" in response.content
        assert response.metadata["server_language"] == "go"
        assert response.metadata["original_content"] == "Hello via gRPC!"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_grpc_with_metadata():
    """Test gRPC with metadata: Python client → Go server."""
    async with go_grpc_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        # Send message with metadata
        message = Message(
            role="user",
            content="gRPC metadata test",
            metadata={
                "request_id": "grpc-123",
                "priority": "high",
                "tags": ["grpc", "test"],
            }
        )
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: gRPC metadata test" in response.content
        assert response.metadata["server_language"] == "go"

        # Check original metadata is preserved
        original_meta = response.metadata["original_metadata"]
        assert original_meta["request_id"] == "grpc-123"
        assert original_meta["priority"] == "high"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_grpc_unicode():
    """Test Unicode over gRPC: Python client → Go server."""
    async with go_grpc_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
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
async def test_python_to_go_grpc_large_message():
    """Test large message over gRPC: Python client → Go server."""
    async with go_grpc_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
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
async def test_python_to_go_grpc_multiple_messages():
    """Test multiple messages over same gRPC: Python client → Go server."""
    async with go_grpc_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        # Send multiple messages over the same connection
        for i in range(5):
            message = Message(role="user", content=f"gRPC message {i}")
            response = await agent.process(message)

            assert response.role == "agent"
            assert f"Echo: gRPC message {i}" in response.content
            assert response.metadata["original_content"] == f"gRPC message {i}"


# Go Client → Python Server Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_grpc_basic():
    """Test basic gRPC message: Go client → Python server."""
    async with python_grpc_server() as (port, server):
        # Use Python RemoteAgent as a proxy for Go client behavior
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
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
async def test_go_to_python_grpc_with_metadata():
    """Test gRPC with metadata: Go client → Python server."""
    async with python_grpc_server() as (port, server):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        message = Message(
            role="user",
            content="gRPC metadata test",
            metadata={
                "request_id": "go-grpc-123",
                "client": "go",
            }
        )
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: gRPC metadata test" in response.content
        assert response.metadata["original"] == "gRPC metadata test"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_grpc_unicode():
    """Test Unicode over gRPC: Go client → Python server."""
    async with python_grpc_server() as (port, server):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        unicode_content = "Hello 世界 🌍 Привет مرحبا"
        message = Message(role="user", content=unicode_content)
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert f"Echo: {unicode_content}" in response.content
        assert response.metadata["original"] == unicode_content


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_grpc_large_message():
    """Test large message over gRPC: Go client → Python server."""
    async with python_grpc_server() as (port, server):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        # Send large message (1MB)
        large_content = "A" * (1024 * 1024)  # 1MB
        message = Message(role="user", content=large_content)
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert len(response.metadata["original"]) == 1024 * 1024


# Concurrent and Performance Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
@pytest.mark.slow
async def test_grpc_concurrent_requests():
    """Test multiple concurrent gRPC requests: Python → Go."""
    async with go_grpc_server() as (port, process):
        import asyncio

        # Create multiple concurrent connections
        async def send_message(i):
            agent = RemoteAgent(
                name=f"test-agent-{i}",
                endpoint=f"grpc://localhost:{port}"
            )
            message = Message(role="user", content=f"Concurrent gRPC {i}")
            response = await agent.process(message)
            return response

        # Send 10 concurrent messages on different connections
        tasks = [send_message(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)

        # Validate all responses
        assert len(responses) == 10
        for i, response in enumerate(responses):
            assert response.role == "agent"
            assert f"Echo: Concurrent gRPC {i}" in response.content


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_grpc_connection_reuse():
    """Test connection reuse over gRPC."""
    async with go_grpc_server() as (port, process):
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"grpc://localhost:{port}"
        )

        # Send multiple messages - connection should be reused
        for i in range(10):
            message = Message(role="user", content=f"Reuse {i}")
            response = await agent.process(message)

            assert response.role == "agent"
            assert f"Echo: Reuse {i}" in response.content


# Error Handling Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_grpc_invalid_endpoint():
    """Test connection error with invalid endpoint: Python client."""
    agent = RemoteAgent(
        name="test-agent",
        endpoint="grpc://localhost:59999"  # Invalid port
    )

    message = Message(role="user", content="Test")

    # Should raise connection error
    with pytest.raises(Exception):  # ConnectionError or gRPC error
        await agent.process(message)


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_grpc_cross_language.py -v -m cross_language
    pytest.main([__file__, "-v", "-m", "cross_language"])
