"""
Tests for RedisMemory implementation.

Note: These tests require a running Redis server.
They will be skipped if Redis is not available.
"""

from datetime import UTC, datetime

import pytest

from agenkit.interfaces import Message

# Try to import RedisMemory
try:
    import redis.asyncio  # noqa: F401  # availability probe; RedisMemory import below is what's used

    from agenkit.memory.redis_memory import RedisMemory

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")


@pytest.fixture
async def redis_memory():
    """Create RedisMemory instance for testing."""
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available")

    memory = RedisMemory(
        redis_url="redis://localhost:6379",
        ttl=60,  # 60 seconds for tests
        key_prefix="agenkit:test",
    )

    # Check if Redis is running
    try:
        client = await memory._get_client()
        await client.ping()
    except Exception:
        pytest.skip("Redis server not running")

    yield memory

    # Cleanup: clear all test keys
    try:
        sessions = await memory.get_all_sessions()
        for session_id in sessions:
            await memory.clear(session_id)
        await memory.close()
    except Exception:
        pass  # Cleanup code - silent failure acceptable for teardown


@pytest.mark.asyncio
async def test_store_and_retrieve(redis_memory):
    """Test basic store and retrieve operations."""
    # Store messages
    msg1 = Message(role="user", content="Hello")
    msg2 = Message(role="assistant", content="Hi there!")
    msg3 = Message(role="user", content="How are you?")

    await redis_memory.store("test-session-1", msg1)
    await redis_memory.store("test-session-1", msg2)
    await redis_memory.store("test-session-1", msg3)

    # Retrieve
    messages = await redis_memory.retrieve("test-session-1", limit=10)

    assert len(messages) == 3
    # Most recent first
    assert messages[0].content == "How are you?"
    assert messages[1].content == "Hi there!"
    assert messages[2].content == "Hello"


@pytest.mark.asyncio
async def test_retrieve_with_limit(redis_memory):
    """Test retrieve with limit."""
    # Store 5 messages
    for i in range(5):
        msg = Message(role="user", content=f"Message {i}")
        await redis_memory.store("test-session-2", msg)

    # Retrieve with limit
    messages = await redis_memory.retrieve("test-session-2", limit=3)

    assert len(messages) == 3
    # Most recent first
    assert messages[0].content == "Message 4"
    assert messages[1].content == "Message 3"
    assert messages[2].content == "Message 2"


@pytest.mark.asyncio
async def test_multiple_sessions(redis_memory):
    """Test isolation between sessions."""
    # Store in different sessions
    await redis_memory.store("test-session-3a", Message(role="user", content="Session 3a msg"))
    await redis_memory.store("test-session-3b", Message(role="user", content="Session 3b msg"))

    messages_a = await redis_memory.retrieve("test-session-3a", limit=10)
    messages_b = await redis_memory.retrieve("test-session-3b", limit=10)

    assert len(messages_a) == 1
    assert len(messages_b) == 1
    assert messages_a[0].content == "Session 3a msg"
    assert messages_b[0].content == "Session 3b msg"


@pytest.mark.asyncio
async def test_retrieve_empty_session(redis_memory):
    """Test retrieving from non-existent session."""
    messages = await redis_memory.retrieve("non-existent", limit=10)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_store_with_metadata(redis_memory):
    """Test storing messages with metadata."""
    msg = Message(role="user", content="Important message")
    metadata = {"importance": 0.9, "tags": ["critical", "action-required"]}

    await redis_memory.store("test-session-4", msg, metadata=metadata)

    # Retrieve and verify (metadata filtering tests this implicitly)
    messages = await redis_memory.retrieve("test-session-4", limit=10, importance_threshold=0.8)

    assert len(messages) == 1
    assert messages[0].content == "Important message"


@pytest.mark.asyncio
async def test_retrieve_with_importance_threshold(redis_memory):
    """Test retrieving with importance threshold filter."""
    # Store messages with different importance
    await redis_memory.store(
        "test-session-5", Message(role="user", content="Low priority"), metadata={"importance": 0.3}
    )
    await redis_memory.store(
        "test-session-5",
        Message(role="user", content="High priority"),
        metadata={"importance": 0.9},
    )
    await redis_memory.store(
        "test-session-5",
        Message(role="user", content="Medium priority"),
        metadata={"importance": 0.6},
    )

    # Retrieve only high importance
    messages = await redis_memory.retrieve("test-session-5", limit=10, importance_threshold=0.7)

    assert len(messages) == 1
    assert messages[0].content == "High priority"


@pytest.mark.asyncio
async def test_retrieve_with_tags(redis_memory):
    """Test retrieving with tag filter."""
    # Store messages with different tags
    await redis_memory.store(
        "test-session-6",
        Message(role="user", content="Bug report"),
        metadata={"tags": ["bug", "urgent"]},
    )
    await redis_memory.store(
        "test-session-6",
        Message(role="user", content="Feature request"),
        metadata={"tags": ["feature", "enhancement"]},
    )
    await redis_memory.store(
        "test-session-6",
        Message(role="user", content="Critical bug"),
        metadata={"tags": ["bug", "critical"]},
    )

    # Retrieve only bug-tagged messages
    messages = await redis_memory.retrieve("test-session-6", limit=10, tags=["bug"])

    assert len(messages) == 2
    assert any("Bug report" in msg.content for msg in messages)
    assert any("Critical bug" in msg.content for msg in messages)


@pytest.mark.asyncio
async def test_retrieve_with_time_range(redis_memory):
    """Test retrieving with time range filter."""
    # Store messages
    await redis_memory.store("test-session-7", Message(role="user", content="Old message"))

    # Wait and record time
    import asyncio

    await asyncio.sleep(0.1)
    cutoff_time = datetime.now(UTC)
    await asyncio.sleep(0.1)

    await redis_memory.store("test-session-7", Message(role="user", content="New message"))

    # Retrieve only messages after cutoff
    messages = await redis_memory.retrieve(
        "test-session-7", limit=10, time_range=(cutoff_time, datetime.now(UTC))
    )

    assert len(messages) == 1
    assert messages[0].content == "New message"


@pytest.mark.asyncio
async def test_summarize(redis_memory):
    """Test summarization."""
    # Store some messages
    for i in range(5):
        await redis_memory.store(
            "test-session-8", Message(role="user", content=f"Message {i} with some content")
        )

    summary = await redis_memory.summarize("test-session-8")

    assert summary.role == "system"
    assert "5 messages" in summary.content
    assert "Message" in summary.content


@pytest.mark.asyncio
async def test_summarize_empty_session(redis_memory):
    """Test summarization of empty session."""
    summary = await redis_memory.summarize("non-existent")

    assert summary.role == "system"
    assert "No messages" in summary.content


@pytest.mark.asyncio
async def test_clear(redis_memory):
    """Test clearing session memory."""
    # Store messages
    await redis_memory.store("test-session-9", Message(role="user", content="Message 1"))
    await redis_memory.store("test-session-9", Message(role="user", content="Message 2"))

    # Verify stored
    messages = await redis_memory.retrieve("test-session-9", limit=10)
    assert len(messages) == 2

    # Clear
    await redis_memory.clear("test-session-9")

    # Verify cleared
    messages = await redis_memory.retrieve("test-session-9", limit=10)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_capabilities(redis_memory):
    """Test capabilities property."""
    capabilities = redis_memory.capabilities

    assert "basic_retrieval" in capabilities
    assert "persistence" in capabilities
    assert "ttl" in capabilities
    assert "time_filtering" in capabilities
    assert "importance_filtering" in capabilities
    assert "tag_filtering" in capabilities


@pytest.mark.asyncio
async def test_get_session_count(redis_memory):
    """Test get_session_count utility method."""
    # Empty session
    count = await redis_memory.get_session_count("test-session-10")
    assert count == 0

    # Add messages
    for i in range(3):
        await redis_memory.store("test-session-10", Message(role="user", content=f"Message {i}"))

    count = await redis_memory.get_session_count("test-session-10")
    assert count == 3


@pytest.mark.asyncio
async def test_get_all_sessions(redis_memory):
    """Test get_all_sessions utility method."""
    # Add to multiple sessions
    await redis_memory.store("test-session-11a", Message(role="user", content="Msg 1"))
    await redis_memory.store("test-session-11b", Message(role="user", content="Msg 2"))
    await redis_memory.store("test-session-11c", Message(role="user", content="Msg 3"))

    sessions = await redis_memory.get_all_sessions()

    assert "test-session-11a" in sessions
    assert "test-session-11b" in sessions
    assert "test-session-11c" in sessions


@pytest.mark.asyncio
async def test_get_memory_usage(redis_memory):
    """Test get_memory_usage utility method."""
    # Add messages to multiple sessions
    for i in range(3):
        await redis_memory.store("test-session-12a", Message(role="user", content=f"Msg {i}"))
    for i in range(2):
        await redis_memory.store("test-session-12b", Message(role="user", content=f"Msg {i}"))

    usage = await redis_memory.get_memory_usage()

    assert usage["total_sessions"] >= 2  # At least our test sessions
    assert usage["total_messages"] >= 5  # At least our test messages
    assert usage["ttl"] == 60


@pytest.mark.asyncio
async def test_persistence(redis_memory):
    """Test that data persists across connections."""
    # Store message
    await redis_memory.store("test-session-13", Message(role="user", content="Persistent message"))

    # Close connection
    await redis_memory.close()

    # Create new connection
    new_memory = RedisMemory(redis_url="redis://localhost:6379", key_prefix="agenkit:test")

    try:
        # Retrieve message (should still exist)
        messages = await new_memory.retrieve("test-session-13", limit=10)

        assert len(messages) == 1
        assert messages[0].content == "Persistent message"
    finally:
        await new_memory.clear("test-session-13")
        await new_memory.close()


@pytest.mark.asyncio
async def test_context_manager(redis_memory):
    """Test context manager usage."""
    async with RedisMemory(redis_url="redis://localhost:6379", key_prefix="agenkit:test") as memory:
        await memory.store("test-session-14", Message(role="user", content="Context manager test"))

        messages = await memory.retrieve("test-session-14", limit=10)
        assert len(messages) == 1

        # Cleanup
        await memory.clear("test-session-14")

    # Connection should be closed after exiting context
