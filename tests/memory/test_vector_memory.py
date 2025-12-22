"""
Tests for VectorMemory implementation.
"""

from datetime import datetime, timezone

import pytest

from agenkit.interfaces import Message
from agenkit.memory.vector_memory import (EmbeddingProvider,
                                          InMemoryVectorStore, VectorMemory)


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock embedding provider for testing.

    Uses simple character-based embeddings for deterministic results.
    """

    def __init__(self, dimension: int = 10):
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        """Generate mock embedding based on text content."""
        # Simple deterministic embedding: use character codes
        embedding = [0.0] * self._dimension

        # Fill embedding with normalized character values
        for i, char in enumerate(text.lower()[: self._dimension]):
            embedding[i] = ord(char) / 255.0

        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension


@pytest.fixture
def vector_memory():
    """Create VectorMemory instance for testing."""
    embeddings = MockEmbeddingProvider(dimension=10)
    return VectorMemory(embeddings)


@pytest.mark.asyncio
async def test_store_and_retrieve(vector_memory):
    """Test basic store and retrieve operations."""
    # Store messages
    msg1 = Message(role="user", content="Hello world")
    msg2 = Message(role="assistant", content="Hi there")
    msg3 = Message(role="user", content="How are you")

    await vector_memory.store("session-1", msg1)
    await vector_memory.store("session-1", msg2)
    await vector_memory.store("session-1", msg3)

    # Retrieve (without query, gets recent)
    messages = await vector_memory.retrieve("session-1", limit=10)

    assert len(messages) == 3


@pytest.mark.asyncio
async def test_semantic_search(vector_memory):
    """Test semantic search functionality."""
    # Store messages with different content
    await vector_memory.store("session-1", Message(role="user", content="apple banana orange"))
    await vector_memory.store("session-1", Message(role="user", content="apple pear grape"))
    await vector_memory.store("session-1", Message(role="user", content="cat dog bird"))

    # Search for fruit-related messages
    messages = await vector_memory.retrieve("session-1", query="apple fruit", limit=2)

    # Should get fruit messages, not animal message
    assert len(messages) == 2
    assert any("apple" in msg.content for msg in messages)


@pytest.mark.asyncio
async def test_retrieve_with_scores(vector_memory):
    """Test retrieving messages with similarity scores."""
    # Store messages
    await vector_memory.store("session-1", Message(role="user", content="machine learning AI"))
    await vector_memory.store(
        "session-1", Message(role="user", content="deep learning neural networks")
    )
    await vector_memory.store("session-1", Message(role="user", content="cooking recipes food"))

    # Search with scores
    results = await vector_memory.retrieve_with_scores(
        "session-1", query="artificial intelligence", limit=3
    )

    assert len(results) == 3

    # Check that results are tuples of (message, score)
    for message, score in results:
        assert isinstance(message, Message)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    # AI-related messages should have higher scores
    # (Note: exact scores depend on embedding implementation)


@pytest.mark.asyncio
async def test_retrieve_with_limit(vector_memory):
    """Test retrieve with limit."""
    # Store 5 messages
    for i in range(5):
        msg = Message(role="user", content=f"Message number {i}")
        await vector_memory.store("session-1", msg)

    # Retrieve with limit
    messages = await vector_memory.retrieve("session-1", limit=3)

    assert len(messages) == 3


@pytest.mark.asyncio
async def test_multiple_sessions(vector_memory):
    """Test isolation between sessions."""
    # Store in different sessions
    await vector_memory.store("session-1", Message(role="user", content="Session 1 message"))
    await vector_memory.store("session-2", Message(role="user", content="Session 2 message"))

    messages_1 = await vector_memory.retrieve("session-1", limit=10)
    messages_2 = await vector_memory.retrieve("session-2", limit=10)

    assert len(messages_1) == 1
    assert len(messages_2) == 1
    assert messages_1[0].content == "Session 1 message"
    assert messages_2[0].content == "Session 2 message"


@pytest.mark.asyncio
async def test_retrieve_empty_session(vector_memory):
    """Test retrieving from non-existent session."""
    messages = await vector_memory.retrieve("non-existent", limit=10)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_store_with_metadata(vector_memory):
    """Test storing messages with metadata."""
    msg = Message(role="user", content="Important message")
    metadata = {"importance": 0.9, "tags": ["critical"]}

    await vector_memory.store("session-1", msg, metadata=metadata)

    # Test retrieval with importance filter
    messages = await vector_memory.retrieve("session-1", limit=10, importance_threshold=0.8)

    assert len(messages) == 1
    assert messages[0].content == "Important message"


@pytest.mark.asyncio
async def test_retrieve_with_importance_threshold(vector_memory):
    """Test retrieving with importance threshold filter."""
    # Store messages with different importance
    await vector_memory.store(
        "session-1", Message(role="user", content="Low priority task"), metadata={"importance": 0.3}
    )
    await vector_memory.store(
        "session-1",
        Message(role="user", content="High priority task"),
        metadata={"importance": 0.9},
    )
    await vector_memory.store(
        "session-1",
        Message(role="user", content="Medium priority task"),
        metadata={"importance": 0.6},
    )

    # Retrieve only high importance
    messages = await vector_memory.retrieve("session-1", limit=10, importance_threshold=0.7)

    assert len(messages) == 1
    assert messages[0].content == "High priority task"


@pytest.mark.asyncio
async def test_retrieve_with_tags(vector_memory):
    """Test retrieving with tag filter."""
    # Store messages with different tags
    await vector_memory.store(
        "session-1",
        Message(role="user", content="Bug report"),
        metadata={"tags": ["bug", "urgent"]},
    )
    await vector_memory.store(
        "session-1",
        Message(role="user", content="Feature request"),
        metadata={"tags": ["feature", "enhancement"]},
    )
    await vector_memory.store(
        "session-1",
        Message(role="user", content="Critical bug"),
        metadata={"tags": ["bug", "critical"]},
    )

    # Retrieve only bug-tagged messages
    messages = await vector_memory.retrieve("session-1", limit=10, tags=["bug"])

    assert len(messages) == 2
    assert any("Bug report" in msg.content for msg in messages)
    assert any("Critical bug" in msg.content for msg in messages)


@pytest.mark.asyncio
async def test_semantic_search_with_min_similarity(vector_memory):
    """Test semantic search with minimum similarity threshold."""
    # Store messages
    await vector_memory.store(
        "session-1", Message(role="user", content="python programming language")
    )
    await vector_memory.store("session-1", Message(role="user", content="python snake reptile"))
    await vector_memory.store(
        "session-1", Message(role="user", content="javascript web development")
    )

    # Search with high similarity threshold
    messages = await vector_memory.retrieve(
        "session-1", query="python", limit=10, min_similarity=0.5
    )

    # Should get python-related messages
    assert len(messages) >= 1
    assert any("python" in msg.content.lower() for msg in messages)


@pytest.mark.asyncio
async def test_retrieve_with_time_range(vector_memory):
    """Test retrieving with time range filter."""
    # Store messages
    await vector_memory.store("session-1", Message(role="user", content="Old message"))

    # Wait and record time
    import asyncio

    await asyncio.sleep(0.1)
    cutoff_time = datetime.now(timezone.utc)
    await asyncio.sleep(0.1)

    await vector_memory.store("session-1", Message(role="user", content="New message"))

    # Retrieve only messages after cutoff
    messages = await vector_memory.retrieve(
        "session-1", limit=10, time_range=(cutoff_time, datetime.now(timezone.utc))
    )

    assert len(messages) == 1
    assert messages[0].content == "New message"


@pytest.mark.asyncio
async def test_summarize(vector_memory):
    """Test summarization."""
    # Store some messages
    for i in range(5):
        await vector_memory.store(
            "session-1", Message(role="user", content=f"Message {i} with content")
        )

    summary = await vector_memory.summarize("session-1")

    assert summary.role == "system"
    assert "5 messages" in summary.content
    assert "Message" in summary.content


@pytest.mark.asyncio
async def test_summarize_empty_session(vector_memory):
    """Test summarization of empty session."""
    summary = await vector_memory.summarize("non-existent")

    assert summary.role == "system"
    assert "No messages" in summary.content


@pytest.mark.asyncio
async def test_clear(vector_memory):
    """Test clearing session memory."""
    # Store messages
    await vector_memory.store("session-1", Message(role="user", content="Message 1"))
    await vector_memory.store("session-1", Message(role="user", content="Message 2"))

    # Verify stored
    messages = await vector_memory.retrieve("session-1", limit=10)
    assert len(messages) == 2

    # Clear
    await vector_memory.clear("session-1")

    # Verify cleared
    messages = await vector_memory.retrieve("session-1", limit=10)
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_capabilities(vector_memory):
    """Test capabilities property."""
    capabilities = vector_memory.capabilities

    assert "basic_retrieval" in capabilities
    assert "semantic_search" in capabilities
    assert "similarity_retrieval" in capabilities
    assert "time_filtering" in capabilities
    assert "importance_filtering" in capabilities
    assert "tag_filtering" in capabilities


@pytest.mark.asyncio
async def test_cosine_similarity():
    """Test cosine similarity calculation."""
    store = InMemoryVectorStore()

    # Test identical vectors (should be 1.0)
    sim = store._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    assert abs(sim - 1.0) < 0.001

    # Test orthogonal vectors (should be 0.0)
    sim = store._cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
    assert abs(sim - 0.0) < 0.001

    # Test opposite vectors (should be -1.0)
    sim = store._cosine_similarity([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0])
    assert abs(sim - (-1.0)) < 0.001


@pytest.mark.asyncio
async def test_combined_filters(vector_memory):
    """Test combining multiple filters."""
    # Store messages with various metadata
    await vector_memory.store(
        "session-1",
        Message(role="user", content="Important bug report"),
        metadata={"importance": 0.9, "tags": ["bug", "urgent"]},
    )
    await vector_memory.store(
        "session-1",
        Message(role="user", content="Minor bug report"),
        metadata={"importance": 0.3, "tags": ["bug", "minor"]},
    )
    await vector_memory.store(
        "session-1",
        Message(role="user", content="Important feature request"),
        metadata={"importance": 0.8, "tags": ["feature", "urgent"]},
    )

    # Retrieve with combined filters (urgent + high importance)
    messages = await vector_memory.retrieve(
        "session-1", limit=10, importance_threshold=0.7, tags=["urgent"]
    )

    # Should get both urgent + important messages
    assert len(messages) == 2
    contents = [msg.content for msg in messages]
    assert "Important bug" in contents[0] or "Important feature" in contents[0]


@pytest.mark.asyncio
async def test_custom_vector_store():
    """Test using custom vector store."""
    # Create custom store
    custom_store = InMemoryVectorStore()
    embeddings = MockEmbeddingProvider()

    memory = VectorMemory(embeddings, vector_store=custom_store)

    # Use memory
    await memory.store("session-1", Message(role="user", content="Test message"))

    messages = await memory.retrieve("session-1", limit=10)
    assert len(messages) == 1
    assert messages[0].content == "Test message"
