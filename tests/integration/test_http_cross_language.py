"""Cross-language integration tests for HTTP transport.

Tests Python client → Go server and Go client → Python server communication.
"""

import httpx
import pytest

from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.interfaces import Message

from .helpers import go_http_server, python_http_server


# Python Client → Go Server Tests


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_basic_message():
    """Test basic message exchange: Python client → Go server."""
    async with go_http_server() as (port, process):
        # Create remote agent client
        agent = RemoteAgent(
            name="test-agent",
            endpoint=f"http://localhost:{port}"
        )

        # Send message
        message = Message(role="user", content="Hello from Python!")
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: Hello from Python!" in response.content
        assert response.metadata["server_language"] == "go"
        assert response.metadata["original_content"] == "Hello from Python!"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_with_metadata():
    """Test message with metadata: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(name="test-agent", endpoint=f"http://localhost:{port}")

        # Send message with metadata
        message = Message(
            role="user",
            content="Test message",
            metadata={
                "request_id": "test-123",
                "user": "alice",
                "tags": ["test", "integration"],
            }
        )
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert "Echo: Test message" in response.content
        assert response.metadata["server_language"] == "go"
        assert response.metadata["original_content"] == "Test message"

        # Check original metadata is preserved
        original_meta = response.metadata["original_metadata"]
        assert original_meta["request_id"] == "test-123"
        assert original_meta["user"] == "alice"
        assert original_meta["tags"] == ["test", "integration"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_unicode_content():
    """Test Unicode content handling: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(name="test-agent", endpoint=f"http://localhost:{port}")

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
async def test_python_to_go_empty_content():
    """Test empty content handling: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(name="test-agent", endpoint=f"http://localhost:{port}")

        # Send message with empty content
        message = Message(role="user", content="")
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert response.content == "Echo: "
        assert response.metadata["original_content"] == ""


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_large_message():
    """Test large message handling: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(name="test-agent", endpoint=f"http://localhost:{port}")

        # Send large message (1MB)
        large_content = "A" * (1024 * 1024)  # 1MB
        message = Message(role="user", content=large_content)
        response = await agent.process(message)

        # Validate response
        assert response.role == "agent"
        assert f"Echo: {large_content}" in response.content
        assert len(response.metadata["original_content"]) == 1024 * 1024


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_health_check():
    """Test health check endpoint: Python client → Go server."""
    async with go_http_server() as (port, process):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{port}/health")
            assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_python_to_go_multiple_sequential_requests():
    """Test multiple sequential requests: Python client → Go server."""
    async with go_http_server() as (port, process):
        agent = RemoteAgent(name="test-agent", endpoint=f"http://localhost:{port}")

        # Send multiple messages sequentially
        for i in range(5):
            message = Message(role="user", content=f"Message {i}")
            response = await agent.process(message)

            assert response.role == "agent"
            assert f"Echo: Message {i}" in response.content
            assert response.metadata["original_content"] == f"Message {i}"


# Python Server → Go Client Tests (will be implemented next)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_basic_message():
    """Test basic message exchange: Go client → Python server."""
    async with python_http_server() as (port, server):
        # Use httpx to simulate Go client behavior
        async with httpx.AsyncClient() as client:
            # Create request envelope
            envelope = {
                "id": "test-001",
                "type": "request",
                "version": "1.0",
                "payload": {
                    "message": {
                        "role": "user",
                        "content": "Hello from Go client!",
                        "metadata": None,
                    }
                }
            }

            # Send request
            response = await client.post(
                f"http://localhost:{port}/process",
                json=envelope,
                headers={"Content-Type": "application/json"}
            )

            # Validate response
            assert response.status_code == 200
            response_data = response.json()

            assert response_data["type"] == "response"
            message_data = response_data["payload"]["message"]
            assert message_data["role"] == "agent"
            assert "Echo: Hello from Go client!" in message_data["content"]
            assert message_data["metadata"]["language"] == "python"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.cross_language
async def test_go_to_python_with_metadata():
    """Test message with metadata: Go client → Python server."""
    async with python_http_server() as (port, server):
        async with httpx.AsyncClient() as client:
            envelope = {
                "id": "test-002",
                "type": "request",
                "version": "1.0",
                "payload": {
                    "message": {
                        "role": "user",
                        "content": "Test with metadata",
                        "metadata": {
                            "request_id": "go-123",
                            "priority": "high",
                        }
                    }
                }
            }

            response = await client.post(
                f"http://localhost:{port}/process",
                json=envelope
            )

            assert response.status_code == 200
            response_data = response.json()
            message_data = response_data["payload"]["message"]

            assert message_data["role"] == "agent"
            assert "Echo: Test with metadata" in message_data["content"]
            assert message_data["metadata"]["original"] == "Test with metadata"


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_http_cross_language.py -v -m cross_language
    pytest.main([__file__, "-v", "-m", "cross_language"])
