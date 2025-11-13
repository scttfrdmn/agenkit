"""
Basic integration tests that can run without external dependencies.

These tests validate core integration functionality like message serialization
and agent behavior consistency.
"""
import json
import pytest

from agenkit.interfaces import Agent, Message


class SimpleEchoAgent(Agent):
    """Simple echo agent for testing."""

    @property
    def name(self) -> str:
        return "simple-echo"

    @property
    def capabilities(self) -> list[str]:
        return ["echo"]

    async def process(self, message: Message) -> Message:
        """Echo the message back."""
        return Message(
            role="agent",
            content=f"Echo: {message.content}",
            metadata={
                "original": message.content,
                "language": "python",
                "agent": self.name
            }
        )


@pytest.mark.asyncio
async def test_message_creation():
    """Test message creation and basic properties."""
    msg = Message(
        role="user",
        content="Hello",
        metadata={"test": True}
    )

    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.metadata["test"] is True
    assert msg.timestamp is not None


@pytest.mark.asyncio
async def test_message_serialization():
    """Test that messages can be serialized to JSON and back."""
    original = Message(
        role="user",
        content="Test message",
        metadata={
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "nested": {"key": "value"},
            "list": [1, 2, 3]
        }
    )

    # Serialize to dict (simulating JSON transport)
    serialized = {
        "role": original.role,
        "content": original.content,
        "metadata": original.metadata,
        "timestamp": original.timestamp.isoformat() if original.timestamp else None
    }

    # Verify JSON serialization works
    json_str = json.dumps(serialized)
    assert isinstance(json_str, str)

    # Deserialize
    deserialized_dict = json.loads(json_str)

    # Validate
    assert deserialized_dict["role"] == "user"
    assert deserialized_dict["content"] == "Test message"
    assert deserialized_dict["metadata"]["string"] == "value"
    assert deserialized_dict["metadata"]["number"] == 42
    assert deserialized_dict["metadata"]["float"] == 3.14
    assert deserialized_dict["metadata"]["bool"] is True
    assert deserialized_dict["metadata"]["nested"]["key"] == "value"
    assert deserialized_dict["metadata"]["list"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_agent_basic_processing():
    """Test basic agent processing."""
    agent = SimpleEchoAgent()

    assert agent.name == "simple-echo"
    assert "echo" in agent.capabilities

    msg = Message(role="user", content="Hello")
    response = await agent.process(msg)

    assert response.role == "agent"
    assert "Echo: Hello" in response.content
    assert response.metadata["original"] == "Hello"
    assert response.metadata["language"] == "python"


@pytest.mark.asyncio
async def test_agent_metadata_preservation():
    """Test that agent metadata is properly set."""
    agent = SimpleEchoAgent()

    msg = Message(
        role="user",
        content="Test",
        metadata={"request_id": "123"}
    )

    response = await agent.process(msg)

    # Agent adds its own metadata
    assert response.metadata["original"] == "Test"
    assert response.metadata["language"] == "python"
    assert response.metadata["agent"] == "simple-echo"


@pytest.mark.asyncio
async def test_multiple_sequential_requests():
    """Test multiple sequential requests to same agent."""
    agent = SimpleEchoAgent()

    messages = [
        Message(role="user", content=f"Message {i}")
        for i in range(5)
    ]

    responses = []
    for msg in messages:
        response = await agent.process(msg)
        responses.append(response)

    # Validate all responses
    assert len(responses) == 5
    for i, response in enumerate(responses):
        assert f"Echo: Message {i}" in response.content
        assert response.metadata["original"] == f"Message {i}"


@pytest.mark.asyncio
async def test_agent_with_complex_metadata():
    """Test agent handling of complex nested metadata."""
    agent = SimpleEchoAgent()

    complex_metadata = {
        "trace_id": "abc-123",
        "user": {
            "id": 42,
            "name": "Test User",
            "preferences": {
                "language": "en",
                "timezone": "UTC"
            }
        },
        "tags": ["test", "integration", "metadata"],
        "counts": [1, 2, 3, 4, 5]
    }

    msg = Message(
        role="user",
        content="Complex test",
        metadata=complex_metadata
    )

    response = await agent.process(msg)

    # Response should have agent metadata
    assert response.metadata["original"] == "Complex test"
    assert response.metadata["language"] == "python"


@pytest.mark.asyncio
async def test_message_immutability():
    """Test that original messages are not modified by agents."""
    agent = SimpleEchoAgent()

    original_content = "Original message"
    original_metadata = {"key": "value"}

    msg = Message(
        role="user",
        content=original_content,
        metadata=original_metadata.copy()
    )

    # Store original values
    original_msg_content = msg.content
    original_msg_metadata = dict(msg.metadata)

    # Process message
    await agent.process(msg)

    # Original message should be unchanged
    assert msg.content == original_msg_content
    assert msg.metadata == original_msg_metadata


@pytest.mark.asyncio
async def test_agent_consistency():
    """Test that agent produces consistent results for same input."""
    agent = SimpleEchoAgent()

    msg = Message(role="user", content="Consistency test")

    # Process same message multiple times
    results = []
    for _ in range(3):
        response = await agent.process(msg)
        results.append(response.content)

    # All results should be identical
    assert len(set(results)) == 1  # Only one unique result
    assert results[0] == "Echo: Consistency test"


@pytest.mark.asyncio
async def test_empty_content_handling():
    """Test agent handling of empty content."""
    agent = SimpleEchoAgent()

    msg = Message(role="user", content="")
    response = await agent.process(msg)

    assert response.role == "agent"
    assert response.content == "Echo: "
    assert response.metadata["original"] == ""


@pytest.mark.asyncio
async def test_unicode_content_handling():
    """Test agent handling of Unicode content."""
    agent = SimpleEchoAgent()

    unicode_content = "Hello 世界 🌍 Привет"
    msg = Message(role="user", content=unicode_content)
    response = await agent.process(msg)

    assert f"Echo: {unicode_content}" in response.content
    assert response.metadata["original"] == unicode_content


if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/test_basic_integration.py -v
    pytest.main([__file__, "-v"])
