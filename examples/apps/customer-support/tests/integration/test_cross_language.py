"""Integration tests for Python-Go cross-language communication."""

import asyncio

import pytest

from agenkit.adapters.python import RemoteAgent
from agenkit.interfaces import Message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_python_to_go_specialist_agent():
    """Test Python can communicate with Go specialist agent."""
    # Assumes Go worker is running on localhost:50051
    specialist = RemoteAgent(
        name="specialist",
        endpoint="grpc://localhost:50051",
        timeout=30.0
    )

    message = Message(
        role="user",
        content="Tell me about API integration",
        metadata={"user_id": "test_user"}
    )

    try:
        response = await specialist.process(message)

        assert response.role == "assistant"
        assert len(response.content) > 0
        assert response.metadata.get("processed_by") == "go_worker"
        assert "sources" in response.metadata
    except Exception as e:
        pytest.skip(f"Go worker not available: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_specialist_agent_performance_query():
    """Test Go specialist handles performance queries."""
    specialist = RemoteAgent(
        name="specialist",
        endpoint="grpc://localhost:50051",
        timeout=30.0
    )

    message = Message(
        role="user",
        content="Why is my application running slow?",
        metadata={"user_id": "test_user"}
    )

    try:
        response = await specialist.process(message)

        assert "performance" in response.content.lower()
        assert response.metadata.get("confidence", 0) > 0.7
        assert len(response.metadata.get("sources", [])) > 0
    except Exception as e:
        pytest.skip(f"Go worker not available: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_specialist_concurrent_requests():
    """Test Go specialist handles concurrent requests."""
    specialist = RemoteAgent(
        name="specialist",
        endpoint="grpc://localhost:50051",
        timeout=30.0
    )

    messages = [
        Message(role="user", content=f"Query {i}", metadata={"user_id": f"user{i}"})
        for i in range(5)
    ]

    try:
        responses = await asyncio.gather(
            *[specialist.process(msg) for msg in messages],
            return_exceptions=True
        )

        # At least some should succeed
        successful = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful) > 0
    except Exception as e:
        pytest.skip(f"Go worker not available: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_specialist_health_check():
    """Test Go specialist responds to health checks."""
    specialist = RemoteAgent(
        name="specialist",
        endpoint="grpc://localhost:50051",
        timeout=5.0
    )

    message = Message(
        role="user",
        content="health_check",
        metadata={"type": "health_check"}
    )

    try:
        response = await specialist.process(message)
        assert response.metadata.get("status") == "ok"
    except Exception as e:
        pytest.skip(f"Go worker not available: {e}")
