"""
Tests for InMemoryMemory implementation.
"""

from datetime import datetime, timezone

import pytest

from agenkit.interfaces import Message
from agenkit.memory.in_memory import InMemoryMemory


@pytest.mark.asyncio
async def test_store_and_retrieve():
    """Test basic store and retrieve operations."""
    memory = InMemoryMemory()

    # Store messages
    msg1 = Message(role="user", content="Hello")
    msg2 = Message(role="assistant", content="Hi there!")
    msg3 = Message(role="user", content="How are you?")

    await memory.store("session-1", msg1)
    await memory.store("session-1", msg2)
    await memory.store("session-1", msg3)

    # Retrieve
    messages = await memory.retrieve("session-1", limit=10)

    assert len(messages) == 3
    # Most recent first
    assert messages[0].content == "How are you?"
    assert messages[1].content == "Hi there!"
    assert messages[2].content == "Hello"


@pytest.mark.asyncio
async def test_retrieve_with_limit():
    """Test retrieve with limit."""
    memory = InMemoryMemory()

    # Store 5 messages
    for i in range(5):
        msg = Message(role="user", content=f"Message {i}")
        await memory.store("session-1", msg)

    # Retrieve with limit
    messages = await memory.retrieve("session-1", limit=3)

    assert len(messages) == 3
    # Most recent first
    assert messages[0].content == "Message 4"
    assert messages[1].content == "Message 3"
    assert messages[2].content == "Message 2"


@pytest.mark.asyncio
async def test_lru_eviction():
    """Test LRU eviction when max_size exceeded."""
    memory = InMemoryMemory(max_size=3)

    # Store 5 messages (should evict oldest 2)
    for i in range(5):
        msg = Message(role="user", content=f"Message {i}")
        await memory.store("session-1", msg)

    messages = await memory.retrieve("session-1", limit=10)

    # Should only have last 3 messages
    assert len(messages) == 3
    assert messages[0].content == "Message 4"
    assert messages[1].content == "Message 3"
    assert messages[2].content == "Message 2"


@pytest.mark.asyncio
async def test_multiple_sessions():
    """Test isolation between sessions."""
    memory = InMemoryMemory()

    # Store in different sessions
    await memory.store("session-1", Message(role="user", content="Session 1 msg"))
    await memory.store("session-2", Message(role="user", content="Session 2 msg"))

    messages_1 = await memory.retrieve("session-1", limit=10)
    messages_2 = await memory.retrieve("session-2", limit=10)

    assert len(messages_1) == 1
    assert len(messages_2) == 1
    assert messages_1[0].content == "Session 1 msg"
    assert messages_2[0].content == "Session 2 msg"


@pytest.mark.asyncio
async def test_retrieve_empty_session():
    """Test retrieving from non-existent session."""
    memory = InMemoryMemory()

    messages = await memory.retrieve("non-existent", limit=10)

    assert len(messages) == 0


@pytest.mark.asyncio
async def test_store_with_metadata():
    """Test storing messages with metadata."""
    memory = InMemoryMemory()

    msg = Message(role="user", content="Important message")
    metadata = {"importance": 0.9, "tags": ["critical", "action-required"]}

    await memory.store("session-1", msg, metadata=metadata)

    # Verify storage (internal check)
    session_storage = memory._storage["session-1"]
    _timestamp, stored_msg, stored_metadata = session_storage[0]

    assert stored_msg.content == "Important message"
    assert stored_metadata["importance"] == 0.9
    assert "critical" in stored_metadata["tags"]


@pytest.mark.asyncio
async def test_retrieve_with_importance_threshold():
    """Test retrieving with importance threshold filter."""
    memory = InMemoryMemory()

    # Store messages with different importance
    await memory.store(
        "session-1", Message(role="user", content="Low priority"), metadata={"importance": 0.3}
    )
    await memory.store(
        "session-1", Message(role="user", content="High priority"), metadata={"importance": 0.9}
    )
    await memory.store(
        "session-1", Message(role="user", content="Medium priority"), metadata={"importance": 0.6}
    )

    # Retrieve only high importance
    messages = await memory.retrieve("session-1", limit=10, importance_threshold=0.7)

    assert len(messages) == 1
    assert messages[0].content == "High priority"


@pytest.mark.asyncio
async def test_retrieve_with_tags():
    """Test retrieving with tag filter."""
    memory = InMemoryMemory()

    # Store messages with different tags
    await memory.store(
        "session-1",
        Message(role="user", content="Bug report"),
        metadata={"tags": ["bug", "urgent"]},
    )
    await memory.store(
        "session-1",
        Message(role="user", content="Feature request"),
        metadata={"tags": ["feature", "enhancement"]},
    )
    await memory.store(
        "session-1",
        Message(role="user", content="Critical bug"),
        metadata={"tags": ["bug", "critical"]},
    )

    # Retrieve only bug-tagged messages
    messages = await memory.retrieve("session-1", limit=10, tags=["bug"])

    assert len(messages) == 2
    assert any("Bug report" in msg.content for msg in messages)
    assert any("Critical bug" in msg.content for msg in messages)


@pytest.mark.asyncio
async def test_retrieve_with_time_range():
    """Test retrieving with time range filter."""
    memory = InMemoryMemory()

    # Store messages
    await memory.store("session-1", Message(role="user", content="Old message"))

    # Wait a bit and record time
    import asyncio

    await asyncio.sleep(0.1)
    cutoff_time = datetime.now(timezone.utc)
    await asyncio.sleep(0.1)

    await memory.store("session-1", Message(role="user", content="New message"))

    # Retrieve only messages after cutoff
    messages = await memory.retrieve(
        "session-1", limit=10, time_range=(cutoff_time, datetime.now(timezone.utc))
    )

    assert len(messages) == 1
    assert messages[0].content == "New message"


@pytest.mark.asyncio
async def test_summarize():
    """Test summarization."""
    memory = InMemoryMemory()

    # Store some messages
    for i in range(5):
        await memory.store(
            "session-1", Message(role="user", content=f"Message {i} with some content")
        )

    summary = await memory.summarize("session-1")

    assert summary.role == "system"
    assert "5 messages" in summary.content
    assert "Message" in summary.content


@pytest.mark.asyncio
async def test_summarize_empty_session():
    """Test summarization of empty session."""
    memory = InMemoryMemory()

    summary = await memory.summarize("non-existent")

    assert summary.role == "system"
    assert "No messages" in summary.content


@pytest.mark.asyncio
async def test_clear():
    """Test clearing session memory."""
    memory = InMemoryMemory()

    # Store messages
    await memory.store("session-1", Message(role="user", content="Message 1"))
    await memory.store("session-1", Message(role="user", content="Message 2"))

    # Verify stored
    messages = await memory.retrieve("session-1", limit=10)
    assert len(messages) == 2

    # Clear
    await memory.clear("session-1")

    # Verify cleared
    messages = await memory.retrieve("session-1", limit=10)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_capabilities():
    """Test capabilities property."""
    memory = InMemoryMemory()

    capabilities = memory.capabilities

    assert "basic_retrieval" in capabilities
    assert "time_filtering" in capabilities
    assert "importance_filtering" in capabilities
    assert "tag_filtering" in capabilities


@pytest.mark.asyncio
async def test_get_session_count():
    """Test get_session_count utility method."""
    memory = InMemoryMemory()

    # Empty session
    assert memory.get_session_count("session-1") == 0

    # Add messages
    for i in range(3):
        await memory.store("session-1", Message(role="user", content=f"Message {i}"))

    assert memory.get_session_count("session-1") == 3


@pytest.mark.asyncio
async def test_get_all_sessions():
    """Test get_all_sessions utility method."""
    memory = InMemoryMemory()

    # No sessions initially
    assert len(memory.get_all_sessions()) == 0

    # Add to multiple sessions
    await memory.store("session-1", Message(role="user", content="Msg 1"))
    await memory.store("session-2", Message(role="user", content="Msg 2"))
    await memory.store("session-3", Message(role="user", content="Msg 3"))

    sessions = memory.get_all_sessions()
    assert len(sessions) == 3
    assert "session-1" in sessions
    assert "session-2" in sessions
    assert "session-3" in sessions


@pytest.mark.asyncio
async def test_get_memory_usage():
    """Test get_memory_usage utility method."""
    memory = InMemoryMemory(max_size=100)

    # Initial usage
    usage = memory.get_memory_usage()
    assert usage["total_sessions"] == 0
    assert usage["total_messages"] == 0
    assert usage["max_size_per_session"] == 100

    # Add messages to multiple sessions
    for i in range(3):
        await memory.store("session-1", Message(role="user", content=f"Msg {i}"))
    for i in range(2):
        await memory.store("session-2", Message(role="user", content=f"Msg {i}"))

    usage = memory.get_memory_usage()
    assert usage["total_sessions"] == 2
    assert usage["total_messages"] == 5
    assert usage["max_size_per_session"] == 100


@pytest.mark.asyncio
async def test_concurrent_access():
    """Test concurrent access to memory."""
    import asyncio

    memory = InMemoryMemory()

    async def store_messages(session_id: str, count: int):
        for i in range(count):
            msg = Message(role="user", content=f"{session_id} - Message {i}")
            await memory.store(session_id, msg)

    # Store concurrently to multiple sessions
    await asyncio.gather(
        store_messages("session-1", 5),
        store_messages("session-2", 5),
        store_messages("session-3", 5),
    )

    # Verify all messages stored correctly
    assert memory.get_session_count("session-1") == 5
    assert memory.get_session_count("session-2") == 5
    assert memory.get_session_count("session-3") == 5


@pytest.mark.asyncio
async def test_combined_filters():
    """Test combining multiple filters."""
    memory = InMemoryMemory()

    # Store messages with various metadata
    await memory.store(
        "session-1",
        Message(role="user", content="Important bug"),
        metadata={"importance": 0.9, "tags": ["bug", "urgent"]},
    )
    await memory.store(
        "session-1",
        Message(role="user", content="Minor bug"),
        metadata={"importance": 0.3, "tags": ["bug", "minor"]},
    )
    await memory.store(
        "session-1",
        Message(role="user", content="Important feature"),
        metadata={"importance": 0.8, "tags": ["feature", "urgent"]},
    )

    # Retrieve with combined filters (urgent + high importance)
    messages = await memory.retrieve(
        "session-1", limit=10, importance_threshold=0.7, tags=["urgent"]
    )

    # Should get both urgent + important messages
    assert len(messages) == 2
    contents = [msg.content for msg in messages]
    assert "Important bug" in contents
    assert "Important feature" in contents
