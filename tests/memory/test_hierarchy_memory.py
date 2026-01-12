"""
Tests for HierarchyMemory backward compatibility adapter.
"""

from datetime import datetime, timedelta, timezone

import pytest

from agenkit.interfaces import Message
from agenkit.memory.hierarchy_memory import HierarchyMemory


@pytest.mark.asyncio
async def test_store_and_retrieve():
    """Test basic store and retrieve operations."""
    memory = HierarchyMemory()

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
    # Check all messages are retrieved
    contents = [msg.content for msg in messages]
    assert "Hello" in contents
    assert "Hi there!" in contents
    assert "How are you?" in contents


@pytest.mark.asyncio
async def test_retrieve_with_limit():
    """Test retrieve with limit."""
    memory = HierarchyMemory()

    # Store 5 messages
    for i in range(5):
        msg = Message(role="user", content=f"Message {i}")
        await memory.store("session-1", msg)

    # Retrieve with limit
    messages = await memory.retrieve("session-1", limit=3)

    assert len(messages) == 3
    # Should get 3 messages from session
    contents = [msg.content for msg in messages]
    for content in contents:
        assert "Message" in content


@pytest.mark.asyncio
async def test_session_isolation():
    """Test isolation between sessions."""
    memory = HierarchyMemory()

    # Store in different sessions
    await memory.store("session-1", Message(role="user", content="Session 1 msg"))
    await memory.store("session-2", Message(role="user", content="Session 2 msg"))
    await memory.store("session-1", Message(role="user", content="Session 1 msg 2"))

    messages_1 = await memory.retrieve("session-1", limit=10)
    messages_2 = await memory.retrieve("session-2", limit=10)

    assert len(messages_1) == 2
    assert len(messages_2) == 1

    # Check contents
    contents_1 = [msg.content for msg in messages_1]
    assert "Session 1 msg" in contents_1
    assert "Session 1 msg 2" in contents_1
    assert "Session 2 msg" not in contents_1

    contents_2 = [msg.content for msg in messages_2]
    assert "Session 2 msg" in contents_2
    assert "Session 1 msg" not in contents_2


@pytest.mark.asyncio
async def test_importance_routing():
    """Test importance-based routing to tiers."""
    memory = HierarchyMemory(
        working_capacity=5, short_term_capacity=10, long_term_min_importance=0.7
    )

    # Store low importance (working + short-term only)
    await memory.store(
        "session-1",
        Message(role="system", content="Low importance"),
        metadata={"importance": 0.3},
    )

    # Store medium importance (working + short-term only)
    await memory.store(
        "session-1",
        Message(role="user", content="Medium importance"),
        metadata={"importance": 0.5},
    )

    # Store high importance (all tiers including long-term)
    await memory.store(
        "session-1",
        Message(role="user", content="High importance"),
        metadata={"importance": 0.9},
    )

    # All should be retrievable
    messages = await memory.retrieve("session-1", limit=10)
    assert len(messages) == 3

    # Check stats to verify tier distribution
    stats = memory.get_stats()
    assert stats["working"]["size"] == 3  # All in working
    assert stats["short_term"]["size"] == 3  # All in short-term
    assert stats["long_term"]["size"] == 1  # Only high importance in long-term


@pytest.mark.asyncio
async def test_default_importance_by_role():
    """Test default importance assignment by message role."""
    memory = HierarchyMemory(long_term_min_importance=0.7)

    # System: 0.3 (not in long-term)
    await memory.store("session-1", Message(role="system", content="System msg"))

    # User: 0.5 (not in long-term)
    await memory.store("session-1", Message(role="user", content="User msg"))

    # Assistant: 0.4 (not in long-term)
    await memory.store("session-1", Message(role="assistant", content="Assistant msg"))

    # None should reach long-term (threshold is 0.7)
    stats = memory.get_stats()
    assert stats["long_term"]["size"] == 0


@pytest.mark.asyncio
async def test_clear_session():
    """Test clearing a session removes all entries."""
    memory = HierarchyMemory()

    # Store messages in two sessions
    await memory.store("session-1", Message(role="user", content="Session 1 msg 1"))
    await memory.store("session-1", Message(role="user", content="Session 1 msg 2"))
    await memory.store("session-2", Message(role="user", content="Session 2 msg 1"))

    # Clear session 1
    await memory.clear("session-1")

    # Session 1 should be empty
    messages_1 = await memory.retrieve("session-1", limit=10)
    assert len(messages_1) == 0

    # Session 2 should still have messages
    messages_2 = await memory.retrieve("session-2", limit=10)
    assert len(messages_2) == 1


@pytest.mark.asyncio
async def test_retrieve_empty_session():
    """Test retrieving from non-existent session."""
    memory = HierarchyMemory()

    messages = await memory.retrieve("non-existent", limit=10)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_message_metadata_preserved():
    """Test that message metadata is preserved through storage."""
    memory = HierarchyMemory()

    msg = Message(
        role="user", content="Test message", metadata={"custom_field": "custom_value", "tags": ["important"]}
    )

    await memory.store("session-1", msg)
    messages = await memory.retrieve("session-1", limit=1)

    assert len(messages) == 1
    retrieved = messages[0]
    assert "custom_field" in retrieved.metadata
    assert retrieved.metadata["custom_field"] == "custom_value"
    assert "tags" in retrieved.metadata
    assert "important" in retrieved.metadata["tags"]


@pytest.mark.asyncio
async def test_importance_threshold_filter():
    """Test filtering by importance threshold."""
    memory = HierarchyMemory()

    # Store messages with different importance
    await memory.store(
        "session-1",
        Message(role="user", content="Low importance"),
        metadata={"importance": 0.3},
    )
    await memory.store(
        "session-1",
        Message(role="user", content="High importance"),
        metadata={"importance": 0.9},
    )

    # Filter by importance
    messages = await memory.retrieve("session-1", limit=10, importance_threshold=0.5)

    assert len(messages) == 1
    assert messages[0].content == "High importance"


@pytest.mark.asyncio
async def test_tags_filter():
    """Test filtering by tags."""
    memory = HierarchyMemory()

    # Store messages with different tags
    await memory.store(
        "session-1",
        Message(role="user", content="Tagged message"),
        metadata={"tags": ["important", "urgent"]},
    )
    await memory.store(
        "session-1", Message(role="user", content="Untagged message"), metadata={"tags": []}
    )
    await memory.store(
        "session-1",
        Message(role="user", content="Different tag"),
        metadata={"tags": ["routine"]},
    )

    # Filter by tags
    messages = await memory.retrieve("session-1", limit=10, tags=["important"])

    assert len(messages) == 1
    assert messages[0].content == "Tagged message"


@pytest.mark.asyncio
async def test_time_range_filter():
    """Test filtering by time range using original message timestamps."""
    memory = HierarchyMemory()

    # Store messages with specific timestamps
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=2)
    future = now + timedelta(hours=2)

    # Store old message
    msg1 = Message(role="user", content="Old message", timestamp=past)
    await memory.store("session-1", msg1)

    # Store recent message
    msg2 = Message(role="user", content="Recent message", timestamp=now)
    await memory.store("session-1", msg2)

    # Filter by time range
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=1)
    messages = await memory.retrieve("session-1", limit=10, time_range=(start_time, end_time))

    # Should only get recent message
    assert len(messages) == 1
    assert messages[0].content == "Recent message"


@pytest.mark.asyncio
async def test_summarize():
    """Test summarize functionality."""
    memory = HierarchyMemory()

    # Store several messages
    await memory.store("session-1", Message(role="user", content="Hello"))
    await memory.store("session-1", Message(role="assistant", content="Hi there!"))
    await memory.store("session-1", Message(role="user", content="How are you?"))

    # Get summary
    summary = await memory.summarize("session-1")

    assert summary.role == "system"
    assert "summary" in summary.content.lower()
    assert "3 messages" in summary.content


@pytest.mark.asyncio
async def test_summarize_empty_session():
    """Test summarize on empty session."""
    memory = HierarchyMemory()

    summary = await memory.summarize("non-existent")

    assert summary.role == "system"
    assert "no messages" in summary.content.lower()


@pytest.mark.asyncio
async def test_capabilities():
    """Test capabilities property."""
    memory = HierarchyMemory()

    capabilities = memory.capabilities

    assert "semantic_search" in capabilities
    assert "importance_filtering" in capabilities
    assert "tag_filtering" in capabilities
    assert "time_filtering" in capabilities
    assert "multi_tier" in capabilities
    assert "auto_eviction" in capabilities


@pytest.mark.asyncio
async def test_get_stats():
    """Test get_stats returns hierarchy statistics."""
    memory = HierarchyMemory(
        working_capacity=10, short_term_capacity=100, long_term_min_importance=0.7
    )

    # Store some messages
    await memory.store("session-1", Message(role="user", content="Message 1"))
    await memory.store("session-1", Message(role="user", content="Message 2"))

    stats = memory.get_stats()

    # Check structure
    assert "working" in stats
    assert "short_term" in stats
    assert "long_term" in stats

    # Check working tier
    assert stats["working"]["size"] == 2
    assert stats["working"]["capacity"] == 10

    # Check short-term tier
    assert stats["short_term"]["size"] == 2
    assert stats["short_term"]["capacity"] == 100


@pytest.mark.asyncio
async def test_get_all_sessions():
    """Test get_all_sessions returns session IDs."""
    memory = HierarchyMemory()

    # Store messages in different sessions
    await memory.store("session-1", Message(role="user", content="Msg 1"))
    await memory.store("session-2", Message(role="user", content="Msg 2"))
    await memory.store("session-1", Message(role="user", content="Msg 3"))

    sessions = memory.get_all_sessions()

    assert len(sessions) == 2
    assert "session-1" in sessions
    assert "session-2" in sessions


@pytest.mark.asyncio
async def test_working_memory_eviction():
    """Test that working memory uses FIFO eviction."""
    memory = HierarchyMemory(working_capacity=3)

    # Store 5 messages (should evict first 2 from working)
    for i in range(5):
        await memory.store("session-1", Message(role="user", content=f"Message {i}"))

    stats = memory.get_stats()

    # Working should have exactly 3 (capacity limit)
    assert stats["working"]["size"] == 3

    # Short-term should have all 5
    assert stats["short_term"]["size"] == 5


@pytest.mark.asyncio
async def test_semantic_retrieval_with_query():
    """Test semantic retrieval with query string."""
    memory = HierarchyMemory()

    # Store messages with different content
    await memory.store("session-1", Message(role="user", content="I love Python programming"))
    await memory.store("session-1", Message(role="user", content="The weather is nice today"))
    await memory.store(
        "session-1", Message(role="user", content="Python is great for data science")
    )

    # Query for Python-related messages
    messages = await memory.retrieve("session-1", query="Python", limit=10)

    # Should prioritize Python-related messages (keyword matching)
    assert len(messages) == 3
    python_count = sum(1 for msg in messages if "Python" in str(msg.content))
    assert python_count == 2


@pytest.mark.asyncio
async def test_backward_compatibility_interface():
    """Test that HierarchyMemory is a drop-in replacement for Memory interface."""
    from agenkit.memory.base import Memory

    memory: Memory = HierarchyMemory()  # Type annotation verifies interface

    # Should have all Memory interface methods
    assert hasattr(memory, "store")
    assert hasattr(memory, "retrieve")
    assert hasattr(memory, "summarize")
    assert hasattr(memory, "clear")

    # Test basic operations work
    msg = Message(role="user", content="Test")
    await memory.store("session-1", msg)
    messages = await memory.retrieve("session-1", limit=10)
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_invalid_parameters():
    """Test validation of initialization parameters."""
    # Test invalid working_capacity
    with pytest.raises(ValueError, match="working_capacity must be at least 1"):
        HierarchyMemory(working_capacity=0)

    # Test invalid short_term_capacity
    with pytest.raises(ValueError, match="short_term_capacity must be at least 1"):
        HierarchyMemory(short_term_capacity=0)

    # Test invalid short_term_ttl_seconds
    with pytest.raises(ValueError, match="short_term_ttl_seconds must be at least 1"):
        HierarchyMemory(short_term_ttl_seconds=0)

    # Test invalid long_term_min_importance
    with pytest.raises(ValueError, match="long_term_min_importance must be between 0.0 and 1.0"):
        HierarchyMemory(long_term_min_importance=1.5)


@pytest.mark.asyncio
async def test_long_term_disabled():
    """Test that long-term memory can be disabled."""
    memory = HierarchyMemory(enable_long_term=False)

    # Store high importance message
    await memory.store(
        "session-1",
        Message(role="user", content="Important"),
        metadata={"importance": 0.9},
    )

    stats = memory.get_stats()

    # Long-term should not exist in stats when disabled
    assert "long_term" not in stats or stats.get("long_term") is None
