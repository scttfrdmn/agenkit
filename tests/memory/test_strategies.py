"""
Tests for memory strategies.
"""

import pytest

from agenkit.interfaces import Message
from agenkit.memory import InMemoryMemory
from agenkit.memory.strategies import (ImportanceWeightingStrategy,
                                       SlidingWindowStrategy,
                                       SummarizationStrategy)


@pytest.fixture
async def populated_memory():
    """Create memory with test messages."""
    memory = InMemoryMemory()

    # Add 10 messages with varying importance
    for i in range(10):
        importance = 0.1 * (i + 1)  # 0.1, 0.2, ..., 1.0
        await memory.store(
            "test-session",
            Message(role="user", content=f"Message {i}"),
            metadata={"importance": importance},
        )

    return memory


# ===== SlidingWindowStrategy Tests =====


@pytest.mark.asyncio
async def test_sliding_window_basic(populated_memory):
    """Test basic sliding window strategy."""
    strategy = SlidingWindowStrategy(window_size=5)

    messages = await strategy.select(
        memory=populated_memory, session_id="test-session", context_limit=10
    )

    # Should get 5 most recent messages
    assert len(messages) == 5

    # Check that we got the most recent ones (Message 5-9)
    contents = [msg.content for msg in messages]
    assert "Message 9" in contents
    assert "Message 8" in contents
    assert "Message 0" not in contents  # Too old


@pytest.mark.asyncio
async def test_sliding_window_respects_context_limit(populated_memory):
    """Test that sliding window respects context limit."""
    strategy = SlidingWindowStrategy(window_size=10)

    messages = await strategy.select(
        memory=populated_memory,
        session_id="test-session",
        context_limit=3,  # Smaller than window_size
    )

    # Should respect context_limit (min of window_size and context_limit)
    assert len(messages) == 3


@pytest.mark.asyncio
async def test_sliding_window_empty_session():
    """Test sliding window with empty session."""
    memory = InMemoryMemory()
    strategy = SlidingWindowStrategy(window_size=5)

    messages = await strategy.select(memory=memory, session_id="empty-session", context_limit=10)

    assert len(messages) == 0


# ===== ImportanceWeightingStrategy Tests =====


@pytest.mark.asyncio
async def test_importance_weighting_basic(populated_memory):
    """Test basic importance weighting strategy."""
    strategy = ImportanceWeightingStrategy(
        importance_threshold=0.5,
        recency_weight=0.0,  # Disable recency for predictable results
        min_recent=0,  # Disable auto-include recent
    )

    messages = await strategy.select(
        memory=populated_memory, session_id="test-session", context_limit=5
    )

    # Should get messages with importance >= 0.5
    # That's Message 5-9 (importance 0.6-1.0)
    assert len(messages) <= 5

    # All messages should have importance >= 0.5
    for msg in messages:
        content_num = int(msg.content.split()[-1])
        expected_importance = 0.1 * (content_num + 1)
        assert expected_importance >= 0.5


@pytest.mark.asyncio
async def test_importance_weighting_always_includes_recent(populated_memory):
    """Test that importance weighting always includes most recent messages."""
    strategy = ImportanceWeightingStrategy(
        importance_threshold=0.9,  # Very high threshold
        recency_weight=0.0,
        min_recent=3,  # Always include 3 most recent
    )

    messages = await strategy.select(
        memory=populated_memory, session_id="test-session", context_limit=10
    )

    # Should include at least the 3 most recent (Message 7, 8, 9)
    contents = [msg.content for msg in messages]
    assert "Message 9" in contents
    assert "Message 8" in contents
    assert "Message 7" in contents


@pytest.mark.asyncio
async def test_importance_weighting_with_recency_bonus(populated_memory):
    """Test importance weighting with recency bonus."""
    strategy = ImportanceWeightingStrategy(
        importance_threshold=0.0,
        recency_weight=0.5,  # Significant recency bonus
        min_recent=0,
    )

    messages = await strategy.select(
        memory=populated_memory, session_id="test-session", context_limit=5
    )

    # Should prefer more recent messages due to recency bonus
    assert len(messages) == 5

    # Most recent messages should be included
    contents = [msg.content for msg in messages]
    assert "Message 9" in contents


@pytest.mark.asyncio
async def test_importance_weighting_custom_scorer():
    """Test importance weighting with custom scorer."""
    memory = InMemoryMemory()

    # Add messages without importance metadata
    for i in range(5):
        await memory.store("test-session", Message(role="user", content=f"Message {i}"))

    # Custom scorer: prefer messages with even numbers
    def custom_scorer(msg: Message) -> float:
        num = int(msg.content.split()[-1])
        return 1.0 if num % 2 == 0 else 0.0

    strategy = ImportanceWeightingStrategy(
        importance_threshold=0.5, recency_weight=0.0, min_recent=0
    )

    messages = await strategy.select(
        memory=memory, session_id="test-session", context_limit=10, custom_scorer=custom_scorer
    )

    # Should prefer even-numbered messages
    for msg in messages:
        num = int(msg.content.split()[-1])
        # Even numbers or very recent (might be included despite score)
        assert num % 2 == 0 or num >= 3


# ===== SummarizationStrategy Tests =====


@pytest.mark.asyncio
async def test_summarization_basic(populated_memory):
    """Test basic summarization strategy."""
    strategy = SummarizationStrategy(recent_count=3, summarize_older=True)

    messages = await strategy.select(
        memory=populated_memory, session_id="test-session", context_limit=10
    )

    # Should have summary + 3 recent messages = 4 total
    assert len(messages) == 4

    # First message should be summary
    assert messages[0].role == "system"
    assert "summary" in messages[0].content.lower()

    # Rest should be recent messages in chronological order
    # (Message 7, 8, 9 - reversed from most recent)
    assert messages[1].content == "Message 7"
    assert messages[2].content == "Message 8"
    assert messages[3].content == "Message 9"


@pytest.mark.asyncio
async def test_summarization_no_summary(populated_memory):
    """Test summarization with summary disabled."""
    strategy = SummarizationStrategy(
        recent_count=5,
        summarize_older=False,  # Don't include summary
    )

    messages = await strategy.select(
        memory=populated_memory, session_id="test-session", context_limit=10
    )

    # Should only have recent messages (no summary)
    assert len(messages) == 5

    # Should not have system summary message
    assert all(msg.role != "system" for msg in messages)

    # Messages should be in chronological order (oldest to newest)
    assert messages[0].content == "Message 5"
    assert messages[4].content == "Message 9"


@pytest.mark.asyncio
async def test_summarization_respects_context_limit(populated_memory):
    """Test that summarization respects context limit."""
    strategy = SummarizationStrategy(recent_count=10, summarize_older=True)

    messages = await strategy.select(
        memory=populated_memory,
        session_id="test-session",
        context_limit=5,  # Limit total messages
    )

    # Should have at most 5 messages (1 summary + 4 recent)
    assert len(messages) <= 5


@pytest.mark.asyncio
async def test_summarization_empty_session():
    """Test summarization with empty session."""
    memory = InMemoryMemory()
    strategy = SummarizationStrategy(recent_count=5, summarize_older=True)

    messages = await strategy.select(memory=memory, session_id="empty-session", context_limit=10)

    assert len(messages) == 0


@pytest.mark.asyncio
async def test_summarization_few_messages():
    """Test summarization when there are fewer messages than recent_count."""
    memory = InMemoryMemory()

    # Only add 3 messages
    for i in range(3):
        await memory.store("test-session", Message(role="user", content=f"Message {i}"))

    strategy = SummarizationStrategy(
        recent_count=10,  # More than available
        summarize_older=True,
    )

    messages = await strategy.select(memory=memory, session_id="test-session", context_limit=10)

    # Should have summary + all 3 messages
    # Or just 3 messages if no older messages to summarize
    assert len(messages) >= 3
    assert len(messages) <= 4  # At most summary + 3


# ===== Integration Tests =====


@pytest.mark.asyncio
async def test_strategy_switching():
    """Test switching between different strategies."""
    memory = InMemoryMemory()

    # Add messages
    for i in range(10):
        await memory.store(
            "test-session",
            Message(role="user", content=f"Message {i}"),
            metadata={"importance": 0.5},
        )

    # Try different strategies on same memory
    sliding = SlidingWindowStrategy(window_size=5)
    importance = ImportanceWeightingStrategy()
    summarization = SummarizationStrategy(recent_count=5)

    messages_sliding = await sliding.select(memory, "test-session", context_limit=10)
    messages_importance = await importance.select(memory, "test-session", context_limit=10)
    messages_summarization = await summarization.select(memory, "test-session", context_limit=10)

    # All should return valid results
    assert len(messages_sliding) > 0
    assert len(messages_importance) > 0
    assert len(messages_summarization) > 0

    # Results may differ between strategies
    # (This is expected - different strategies make different choices)


@pytest.mark.asyncio
async def test_strategies_with_real_conversation():
    """Test strategies with realistic conversation flow."""
    memory = InMemoryMemory()

    # Simulate a conversation
    conversation = [
        ("user", "Hello", 0.3),
        ("assistant", "Hi! How can I help?", 0.3),
        ("user", "I need help with a critical bug", 0.9),
        ("assistant", "What's the bug?", 0.8),
        ("user", "The app crashes on startup", 0.9),
        ("assistant", "Let me investigate", 0.7),
        ("user", "Thanks", 0.2),
        ("assistant", "Found the issue - null pointer in config", 0.9),
        ("user", "Can you fix it?", 0.8),
        ("assistant", "Yes, fixing now", 0.8),
    ]

    for role, content, importance in conversation:
        await memory.store(
            "conversation", Message(role=role, content=content), metadata={"importance": importance}
        )

    # Test importance strategy - should prioritize bug discussion
    importance_strategy = ImportanceWeightingStrategy(importance_threshold=0.7, min_recent=2)

    important_messages = await importance_strategy.select(memory, "conversation", context_limit=6)

    # Should include important bug-related messages
    # Note: The exact messages depend on strategy implementation
    # At minimum, should include recent messages
    contents = [msg.content for msg in important_messages]
    assert len(contents) >= 2  # At least min_recent messages

    # Should include some high-importance or recent messages
    assert any(content in ["Can you fix it?", "Yes, fixing now"] for content in contents)
