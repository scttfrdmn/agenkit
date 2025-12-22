"""
Tests for Memory Hierarchy Pattern.

Coverage:
- MemoryEntry data structure
- WorkingMemory (in-context memory)
- ShortTermMemory (recent sessions with TTL)
- LongTermMemory (persistent semantic memory)
- MemoryHierarchy (multi-tier system)
- Cross-tier retrieval and deduplication
- Eviction and promotion logic
"""

from datetime import datetime, timedelta, timezone

import pytest

from agenkit.patterns import (
    LongTermMemory,
    MemoryEntry,
    MemoryHierarchy,
    ShortTermMemory,
    WorkingMemory,
)

# Tests for MemoryEntry


def test_memory_entry_creation():
    """Test MemoryEntry creation."""
    entry = MemoryEntry(
        id="test-1",
        content="Test memory",
        metadata={"category": "test"},
        timestamp=datetime.now(timezone.utc),
        importance=0.8,
    )

    assert entry.id == "test-1"
    assert entry.content == "Test memory"
    assert entry.metadata["category"] == "test"
    assert entry.importance == 0.8
    assert entry.access_count == 0


def test_memory_entry_to_dict():
    """Test MemoryEntry.to_dict() serialization."""
    timestamp = datetime.now(timezone.utc)
    entry = MemoryEntry(
        id="test-1",
        content="Test content",
        metadata={"key": "value"},
        timestamp=timestamp,
        importance=0.5,
    )

    entry_dict = entry.to_dict()

    assert entry_dict["id"] == "test-1"
    assert entry_dict["content"] == "Test content"
    assert entry_dict["metadata"]["key"] == "value"
    assert entry_dict["timestamp"] == timestamp.isoformat()
    assert entry_dict["importance"] == 0.5
    assert entry_dict["access_count"] == 0


# Tests for WorkingMemory


@pytest.mark.asyncio
async def test_working_memory_basic():
    """Test basic WorkingMemory operation."""
    memory = WorkingMemory(max_messages=10)

    entry = MemoryEntry(
        id="test-1",
        content="Test message",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )

    await memory.store(entry)

    assert len(memory) == 1
    assert entry in memory.get_all()


@pytest.mark.asyncio
async def test_working_memory_eviction():
    """Test FIFO eviction when capacity exceeded."""
    memory = WorkingMemory(max_messages=3)

    # Add 3 entries (at capacity)
    for i in range(3):
        entry = MemoryEntry(
            id=f"test-{i}",
            content=f"Message {i}",
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        await memory.store(entry)

    assert len(memory) == 3

    # Add 4th entry (should evict first)
    entry4 = MemoryEntry(
        id="test-3",
        content="Message 3",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    await memory.store(entry4)

    assert len(memory) == 3
    all_entries = memory.get_all()
    assert all_entries[0].id == "test-1"  # First was evicted
    assert all_entries[-1].id == "test-3"


@pytest.mark.asyncio
async def test_working_memory_retrieve():
    """Test WorkingMemory retrieval."""
    memory = WorkingMemory(max_messages=10)

    # Add entries
    for i in range(5):
        entry = MemoryEntry(
            id=f"test-{i}",
            content=f"Message {i}",
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        await memory.store(entry)

    # Retrieve all
    results = await memory.retrieve("", limit=10)
    assert len(results) == 5

    # Retrieve with limit
    results = await memory.retrieve("", limit=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_working_memory_delete():
    """Test deleting specific entry."""
    memory = WorkingMemory(max_messages=10)

    entry1 = MemoryEntry(
        id="test-1", content="Message 1", metadata={}, timestamp=datetime.now(timezone.utc)
    )
    entry2 = MemoryEntry(
        id="test-2", content="Message 2", metadata={}, timestamp=datetime.now(timezone.utc)
    )

    await memory.store(entry1)
    await memory.store(entry2)

    assert len(memory) == 2

    await memory.delete("test-1")

    assert len(memory) == 1
    assert memory.get_all()[0].id == "test-2"


@pytest.mark.asyncio
async def test_working_memory_clear():
    """Test clearing all working memory."""
    memory = WorkingMemory(max_messages=10)

    for i in range(5):
        entry = MemoryEntry(
            id=f"test-{i}",
            content=f"Message {i}",
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        await memory.store(entry)

    assert len(memory) == 5

    memory.clear()

    assert len(memory) == 0


def test_working_memory_validation():
    """Test WorkingMemory parameter validation."""
    with pytest.raises(ValueError, match="max_messages must be at least 1"):
        WorkingMemory(max_messages=0)


# Tests for ShortTermMemory


@pytest.mark.asyncio
async def test_short_term_memory_basic():
    """Test basic ShortTermMemory operation."""
    memory = ShortTermMemory(max_messages=100, ttl_seconds=3600)

    entry = MemoryEntry(
        id="test-1",
        content="Recent memory",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )

    await memory.store(entry)

    assert len(memory) == 1


@pytest.mark.asyncio
async def test_short_term_memory_ttl_expiration():
    """Test TTL-based expiration."""
    memory = ShortTermMemory(max_messages=100, ttl_seconds=1)  # 1 second TTL

    # Add entry with old timestamp
    old_entry = MemoryEntry(
        id="test-old",
        content="Old memory",
        metadata={},
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=2),  # 2 seconds ago
    )

    memory._messages.append(old_entry)  # Add directly to bypass timestamp

    # Add fresh entry
    fresh_entry = MemoryEntry(
        id="test-fresh",
        content="Fresh memory",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )

    await memory.store(fresh_entry)

    # Should have cleaned expired entry
    assert len(memory) == 1
    assert memory._messages[0].id == "test-fresh"


@pytest.mark.asyncio
async def test_short_term_memory_lru_eviction():
    """Test LRU eviction when capacity exceeded."""
    memory = ShortTermMemory(max_messages=3, ttl_seconds=3600)

    # Add 3 entries
    for i in range(3):
        entry = MemoryEntry(
            id=f"test-{i}",
            content=f"Message {i}",
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        await memory.store(entry)

    # Access first entry (make it recently used)
    results = await memory.retrieve("", limit=1)
    assert results[0].id == "test-2"  # Most recent

    # Add 4th entry (should evict least recently used)
    entry4 = MemoryEntry(
        id="test-3",
        content="Message 3",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    await memory.store(entry4)

    assert len(memory) == 3


@pytest.mark.asyncio
async def test_short_term_memory_retrieve_updates_access():
    """Test that retrieval updates access count and time."""
    memory = ShortTermMemory(max_messages=100, ttl_seconds=3600)

    entry = MemoryEntry(
        id="test-1",
        content="Test memory",
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )

    await memory.store(entry)

    assert entry.access_count == 0
    assert entry.last_accessed is None

    # Retrieve
    results = await memory.retrieve("", limit=10)

    assert len(results) == 1
    assert results[0].access_count == 1
    assert results[0].last_accessed is not None


def test_short_term_memory_validation():
    """Test ShortTermMemory parameter validation."""
    with pytest.raises(ValueError, match="max_messages must be at least 1"):
        ShortTermMemory(max_messages=0)

    with pytest.raises(ValueError, match="ttl_seconds must be at least 1"):
        ShortTermMemory(max_messages=10, ttl_seconds=0)


# Tests for LongTermMemory


@pytest.mark.asyncio
async def test_long_term_memory_basic():
    """Test basic LongTermMemory operation."""
    memory = LongTermMemory(min_importance=0.5)

    entry = MemoryEntry(
        id="test-1",
        content="Important memory",
        metadata={},
        timestamp=datetime.now(timezone.utc),
        importance=0.8,
    )

    await memory.store(entry)

    assert len(memory) == 1


@pytest.mark.asyncio
async def test_long_term_memory_importance_threshold():
    """Test importance threshold filtering."""
    memory = LongTermMemory(min_importance=0.7)

    # High importance (should store)
    high_entry = MemoryEntry(
        id="test-high",
        content="High importance",
        metadata={},
        timestamp=datetime.now(timezone.utc),
        importance=0.9,
    )

    await memory.store(high_entry)
    assert len(memory) == 1

    # Low importance (should not store)
    low_entry = MemoryEntry(
        id="test-low",
        content="Low importance",
        metadata={},
        timestamp=datetime.now(timezone.utc),
        importance=0.5,
    )

    await memory.store(low_entry)
    assert len(memory) == 1  # Still only 1


@pytest.mark.asyncio
async def test_long_term_memory_retrieve_keyword():
    """Test keyword-based retrieval."""
    memory = LongTermMemory(min_importance=0.5)

    # Add entries
    entry1 = MemoryEntry(
        id="test-1",
        content="Python programming language",
        metadata={},
        timestamp=datetime.now(timezone.utc),
        importance=0.8,
    )

    entry2 = MemoryEntry(
        id="test-2",
        content="JavaScript programming",
        metadata={},
        timestamp=datetime.now(timezone.utc),
        importance=0.7,
    )

    entry3 = MemoryEntry(
        id="test-3",
        content="Data science",
        metadata={},
        timestamp=datetime.now(timezone.utc),
        importance=0.9,
    )

    await memory.store(entry1)
    await memory.store(entry2)
    await memory.store(entry3)

    # Search for "python"
    results = await memory.retrieve("python", limit=10)

    # Should find entry1 with keyword match
    assert len(results) > 0
    assert any("python" in r.content.lower() for r in results)


@pytest.mark.asyncio
async def test_long_term_memory_delete():
    """Test deleting entries."""
    memory = LongTermMemory(min_importance=0.5)

    entry = MemoryEntry(
        id="test-1",
        content="Test memory",
        metadata={},
        timestamp=datetime.now(timezone.utc),
        importance=0.8,
    )

    await memory.store(entry)
    assert len(memory) == 1

    await memory.delete("test-1")
    assert len(memory) == 0


def test_long_term_memory_validation():
    """Test LongTermMemory parameter validation."""
    with pytest.raises(ValueError, match="min_importance must be between 0.0 and 1.0"):
        LongTermMemory(min_importance=1.5)

    with pytest.raises(ValueError, match="min_importance must be between 0.0 and 1.0"):
        LongTermMemory(min_importance=-0.1)


# Tests for MemoryHierarchy


@pytest.mark.asyncio
async def test_memory_hierarchy_basic():
    """Test basic MemoryHierarchy operation."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100),
        long_term_memory=LongTermMemory(min_importance=0.7),
    )

    # Store memory
    memory_id = await hierarchy.store(
        content="Test memory",
        importance=0.5,
        metadata={"category": "test"},
    )

    assert memory_id is not None


@pytest.mark.asyncio
async def test_memory_hierarchy_tier_routing():
    """Test that memories are routed to appropriate tiers."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100),
        long_term_memory=LongTermMemory(min_importance=0.7),
    )

    # Low importance (working + short-term only)
    await hierarchy.store(content="Low importance", importance=0.5)

    assert len(hierarchy.working) == 1
    assert len(hierarchy.short_term) == 1
    assert len(hierarchy.long_term) == 0

    # High importance (all tiers)
    await hierarchy.store(content="High importance", importance=0.9)

    assert len(hierarchy.working) == 2
    assert len(hierarchy.short_term) == 2
    assert len(hierarchy.long_term) == 1


@pytest.mark.asyncio
async def test_memory_hierarchy_retrieve_all_tiers():
    """Test retrieval searches all tiers."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100),
        long_term_memory=LongTermMemory(min_importance=0.5),
    )

    # Store in different tiers
    await hierarchy.store(content="Working memory item", importance=0.4)
    await hierarchy.store(content="Short-term memory item", importance=0.6)
    await hierarchy.store(content="Long-term memory item", importance=0.8)

    # Retrieve from all tiers
    results = await hierarchy.retrieve("memory", limit=10)

    # Should find entries from multiple tiers
    assert len(results) > 0


@pytest.mark.asyncio
async def test_memory_hierarchy_deduplication():
    """Test deduplication across tiers."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100),
        long_term_memory=LongTermMemory(min_importance=0.5),
    )

    # Store high importance (goes to all tiers with same ID)
    await hierarchy.store(content="Duplicate memory", importance=0.9)

    # Retrieve (should deduplicate)
    results = await hierarchy.retrieve("duplicate", limit=10)

    # Should only get one result despite being in multiple tiers
    unique_ids = {r.id for r in results}
    assert len(unique_ids) == len(results)


@pytest.mark.asyncio
async def test_memory_hierarchy_retrieve_specific_tiers():
    """Test retrieving from specific tiers."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100),
        long_term_memory=LongTermMemory(min_importance=0.7),
    )

    await hierarchy.store(content="Working item", importance=0.5)
    await hierarchy.store(content="Long-term item", importance=0.9)

    # Search only working memory
    working_results = await hierarchy.retrieve("", limit=10, search_tiers=["working"])
    assert len(working_results) > 0

    # Search only long-term memory
    long_term_results = await hierarchy.retrieve("", limit=10, search_tiers=["long_term"])
    assert len(long_term_results) > 0


@pytest.mark.asyncio
async def test_memory_hierarchy_clear_tier():
    """Test clearing specific tier."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100),
    )

    await hierarchy.store(content="Test", importance=0.5)

    assert len(hierarchy.working) > 0

    # Clear working memory
    await hierarchy.clear_tier("working")

    assert len(hierarchy.working) == 0


@pytest.mark.asyncio
async def test_memory_hierarchy_clear_tier_validation():
    """Test clear_tier validation."""
    hierarchy = MemoryHierarchy(working_memory=WorkingMemory(max_messages=10))

    with pytest.raises(ValueError, match="Invalid tier"):
        await hierarchy.clear_tier("invalid_tier")

    with pytest.raises(ValueError, match="not configured"):
        await hierarchy.clear_tier("long_term")


def test_memory_hierarchy_get_stats():
    """Test get_stats method."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100, ttl_seconds=3600),
        long_term_memory=LongTermMemory(min_importance=0.7),
    )

    stats = hierarchy.get_stats()

    assert "working" in stats
    assert stats["working"]["capacity"] == 10

    assert "short_term" in stats
    assert stats["short_term"]["capacity"] == 100
    assert stats["short_term"]["ttl_seconds"] == 3600

    assert "long_term" in stats
    assert stats["long_term"]["min_importance"] == 0.7


@pytest.mark.asyncio
async def test_memory_hierarchy_importance_validation():
    """Test importance parameter validation."""
    hierarchy = MemoryHierarchy(working_memory=WorkingMemory(max_messages=10))

    with pytest.raises(ValueError, match="importance must be between 0.0 and 1.0"):
        await hierarchy.store(content="Test", importance=1.5)

    with pytest.raises(ValueError, match="importance must be between 0.0 and 1.0"):
        await hierarchy.store(content="Test", importance=-0.1)


@pytest.mark.asyncio
async def test_memory_hierarchy_without_optional_tiers():
    """Test hierarchy with only working memory."""
    hierarchy = MemoryHierarchy(working_memory=WorkingMemory(max_messages=10))

    # Should work with only working memory
    memory_id = await hierarchy.store(content="Test", importance=0.5)
    assert memory_id is not None

    results = await hierarchy.retrieve("test", limit=10)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_memory_hierarchy_ranking():
    """Test relevance ranking across tiers."""
    hierarchy = MemoryHierarchy(
        working_memory=WorkingMemory(max_messages=10),
        short_term_memory=ShortTermMemory(max_messages=100),
        long_term_memory=LongTermMemory(min_importance=0.5),
    )

    # Store memories with different characteristics
    await hierarchy.store(
        content="Python programming is great",
        importance=0.9,
        metadata={"topic": "python"},
    )

    await hierarchy.store(
        content="JavaScript is also good",
        importance=0.5,
        metadata={"topic": "javascript"},
    )

    # Search for python
    results = await hierarchy.retrieve("python", limit=10)

    # Should rank by relevance (keyword match, importance, etc.)
    assert len(results) > 0
    # First result should likely be the Python one due to keyword match
    top_result = results[0]
    assert "python" in top_result.content.lower() or top_result.importance > 0.7


@pytest.mark.asyncio
async def test_memory_hierarchy_session_id():
    """Test storing memories with session IDs."""
    hierarchy = MemoryHierarchy(working_memory=WorkingMemory(max_messages=10))

    memory_id = await hierarchy.store(
        content="Session memory",
        importance=0.5,
        session_id="session-123",
    )

    assert memory_id is not None

    # Verify session_id is preserved
    results = await hierarchy.retrieve("session", limit=10)
    assert len(results) > 0
    assert results[0].session_id == "session-123"
