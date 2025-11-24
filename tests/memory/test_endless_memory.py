"""Tests for EndlessMemory integration."""

import pytest

from agenkit.interfaces import Message
from agenkit.memory.endless_memory import EndlessMemory


# Mock EndlessClient for testing
class MockEndlessClient:
    """Mock endless client for testing."""

    def __init__(self):
        self.storage: dict[str, list[dict]] = {}

    async def store_context(
        self, session_id: str, messages: list[dict], metadata: dict | None = None
    ) -> None:
        """Store messages in mock storage."""
        if session_id not in self.storage:
            self.storage[session_id] = []
        self.storage[session_id].extend(messages)

    async def retrieve_context(
        self, session_id: str, query: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Retrieve from mock storage."""
        if session_id not in self.storage:
            return []

        messages = self.storage[session_id]

        # Simple query matching (if query provided)
        if query:
            messages = [
                msg for msg in messages if query.lower() in str(msg.get("content", "")).lower()
            ]

        return messages[-limit:] if messages else []

    async def summarize_context(self, session_id: str) -> str:
        """Mock summarization."""
        if session_id not in self.storage:
            return "No messages in session."

        count = len(self.storage[session_id])
        return f"Session summary: {count} messages stored in compressed context."

    async def clear_context(self, session_id: str) -> None:
        """Clear mock storage."""
        if session_id in self.storage:
            del self.storage[session_id]


@pytest.mark.asyncio
async def test_store_and_retrieve():
    """Test basic store and retrieve operations."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    msg = Message(role="user", content="Test message")
    await memory.store("session-1", msg)

    messages = await memory.retrieve("session-1")
    assert len(messages) == 1
    assert messages[0].content == "Test message"
    assert messages[0].role == "user"


@pytest.mark.asyncio
async def test_semantic_retrieval():
    """Test semantic retrieval with query."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    # Store multiple messages
    await memory.store("session-1", Message(role="user", content="What is the pricing?"))
    await memory.store("session-1", Message(role="assistant", content="Pricing is $50/month"))
    await memory.store("session-1", Message(role="user", content="How's the weather?"))

    # Retrieve with query
    messages = await memory.retrieve("session-1", query="pricing")
    assert len(messages) == 2
    assert "pricing" in messages[0].content.lower() or "pricing" in messages[1].content.lower()


@pytest.mark.asyncio
async def test_retrieve_with_limit():
    """Test retrieval with limit."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    # Store 5 messages
    for i in range(5):
        await memory.store("session-1", Message(role="user", content=f"Message {i}"))

    # Retrieve with limit
    messages = await memory.retrieve("session-1", limit=3)
    assert len(messages) == 3
    # Should get most recent 3
    assert messages[0].content == "Message 2"
    assert messages[1].content == "Message 3"
    assert messages[2].content == "Message 4"


@pytest.mark.asyncio
async def test_store_with_metadata():
    """Test storing messages with metadata."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    msg = Message(role="user", content="Important message")
    metadata = {"importance": 0.9, "tags": ["critical"]}

    await memory.store("session-1", msg, metadata=metadata)

    # Verify storage (via client)
    stored = client.storage["session-1"][0]
    assert stored["content"] == "Important message"
    assert stored["metadata"]["importance"] == 0.9


@pytest.mark.asyncio
async def test_summarize():
    """Test summarization."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    # Store messages
    for i in range(10):
        await memory.store("session-1", Message(role="user", content=f"Message {i}"))

    # Get summary
    summary = await memory.summarize("session-1")
    assert summary.role == "system"
    assert "10 messages" in summary.content


@pytest.mark.asyncio
async def test_summarize_empty_session():
    """Test summarization of empty session."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    summary = await memory.summarize("session-1")
    assert summary.role == "system"
    assert "No messages" in summary.content


@pytest.mark.asyncio
async def test_clear():
    """Test clearing session."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    # Store messages
    await memory.store("session-1", Message(role="user", content="Test"))

    # Clear
    await memory.clear("session-1")

    # Verify empty
    messages = await memory.retrieve("session-1")
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_multiple_sessions():
    """Test isolated storage per session."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    # Store in different sessions
    await memory.store("session-1", Message(role="user", content="Session 1 message"))
    await memory.store("session-2", Message(role="user", content="Session 2 message"))

    # Retrieve from each session
    messages_1 = await memory.retrieve("session-1")
    messages_2 = await memory.retrieve("session-2")

    assert len(messages_1) == 1
    assert len(messages_2) == 1
    assert messages_1[0].content == "Session 1 message"
    assert messages_2[0].content == "Session 2 message"


@pytest.mark.asyncio
async def test_retrieve_empty_session():
    """Test retrieving from empty session."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    messages = await memory.retrieve("nonexistent-session")
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_capabilities():
    """Test capabilities reporting."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    caps = memory.capabilities
    assert "infinite_context" in caps
    assert "compression" in caps
    assert "semantic_search" in caps
    assert "cross_session_knowledge" in caps
    assert "automatic_summarization" in caps


@pytest.mark.asyncio
async def test_protocol_compliance():
    """Test that mock client implements required protocol."""
    client = MockEndlessClient()

    # Verify protocol methods exist
    assert hasattr(client, "store_context")
    assert hasattr(client, "retrieve_context")
    assert hasattr(client, "summarize_context")
    assert hasattr(client, "clear_context")

    # Verify they're callable
    assert callable(client.store_context)
    assert callable(client.retrieve_context)
    assert callable(client.summarize_context)
    assert callable(client.clear_context)


@pytest.mark.asyncio
async def test_long_conversation():
    """Test handling of very long conversations (infinite context scenario)."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    # Simulate long conversation (100 messages)
    for i in range(100):
        await memory.store(
            "long-session",
            Message(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}"),
        )

    # Should be able to retrieve with limit
    messages = await memory.retrieve("long-session", limit=20)
    assert len(messages) == 20

    # Summary should work
    summary = await memory.summarize("long-session")
    assert "100 messages" in summary.content


@pytest.mark.asyncio
async def test_message_conversion():
    """Test message to dict and dict to message conversion."""
    client = MockEndlessClient()
    memory = EndlessMemory(client)

    # Create message with complex content
    original = Message(role="assistant", content="This is a test message with special chars: !@#$%")

    # Store and retrieve
    await memory.store("session-1", original)
    retrieved = await memory.retrieve("session-1")

    # Verify conversion preserves data
    assert len(retrieved) == 1
    assert retrieved[0].role == original.role
    assert retrieved[0].content == original.content
