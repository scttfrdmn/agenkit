"""
Tests for CostTracker.
"""

from datetime import UTC, datetime

import pytest

from agenkit.budget.tracker import CostTracker


@pytest.mark.asyncio
async def test_record_cost():
    """Test recording a cost."""
    tracker = CostTracker()

    cost = await tracker.record_cost(
        session_id="session-1",
        agent_name="assistant",
        model="claude-sonnet-4",
        input_tokens=1000,
        output_tokens=500,
    )

    assert cost.session_id == "session-1"
    assert cost.agent_name == "assistant"
    assert cost.model == "claude-sonnet-4"
    assert cost.input_tokens == 1000
    assert cost.output_tokens == 500
    assert cost.input_cost > 0
    assert cost.output_cost > 0
    assert cost.total_cost == cost.input_cost + cost.output_cost


@pytest.mark.asyncio
async def test_get_session_cost():
    """Test getting total cost for a session."""
    tracker = CostTracker()

    # Record multiple costs
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)
    await tracker.record_cost("session-1", "agent-2", "claude-sonnet-4", 2000, 1000)

    total = await tracker.get_session_cost("session-1")
    assert total > 0

    # Should be sum of both costs
    expected = (1000 + 2000) * 0.003 / 1000 + (500 + 1000) * 0.015 / 1000
    assert abs(total - expected) < 0.001


@pytest.mark.asyncio
async def test_get_agent_cost():
    """Test getting total cost for an agent."""
    tracker = CostTracker()

    # Record costs for different agents
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)
    await tracker.record_cost("session-2", "agent-1", "claude-sonnet-4", 2000, 1000)
    await tracker.record_cost("session-3", "agent-2", "claude-sonnet-4", 1000, 500)

    agent1_cost = await tracker.get_agent_cost("agent-1")
    agent2_cost = await tracker.get_agent_cost("agent-2")

    assert agent1_cost > agent2_cost  # agent-1 has more costs


@pytest.mark.asyncio
async def test_get_global_cost():
    """Test getting total global cost."""
    tracker = CostTracker()

    # Record costs across sessions and agents
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)
    await tracker.record_cost("session-2", "agent-2", "claude-sonnet-4", 2000, 1000)
    await tracker.record_cost("session-3", "agent-3", "claude-sonnet-4", 1500, 750)

    total = await tracker.get_global_cost()

    # Should be sum of all costs
    assert total > 0


@pytest.mark.asyncio
async def test_get_breakdown():
    """Test getting cost breakdown by model."""
    tracker = CostTracker()

    # Record costs with different models
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)
    await tracker.record_cost("session-1", "agent-1", "claude-opus-4", 1000, 500)
    await tracker.record_cost("session-1", "agent-1", "claude-haiku-3", 1000, 500)

    breakdown = await tracker.get_breakdown(session_id="session-1")

    assert "claude-sonnet-4" in breakdown
    assert "claude-opus-4" in breakdown
    assert "claude-haiku-3" in breakdown

    # Opus should be most expensive
    assert breakdown["claude-opus-4"] > breakdown["claude-sonnet-4"]
    assert breakdown["claude-sonnet-4"] > breakdown["claude-haiku-3"]


@pytest.mark.asyncio
async def test_get_top_sessions():
    """Test getting top sessions by cost."""
    tracker = CostTracker()

    # Record costs with different amounts
    await tracker.record_cost(
        "session-1", "agent-1", "claude-sonnet-4", 10000, 5000
    )  # More expensive
    await tracker.record_cost(
        "session-2", "agent-1", "claude-sonnet-4", 1000, 500
    )  # Less expensive
    await tracker.record_cost("session-3", "agent-1", "claude-sonnet-4", 5000, 2500)  # Medium

    top_sessions = await tracker.get_top_sessions(limit=3)

    assert len(top_sessions) == 3

    # Should be ordered by cost (descending)
    assert top_sessions[0][0] == "session-1"  # Most expensive
    assert top_sessions[1][0] == "session-3"  # Medium
    assert top_sessions[2][0] == "session-2"  # Least expensive

    # Verify costs are descending
    assert top_sessions[0][1] > top_sessions[1][1]
    assert top_sessions[1][1] > top_sessions[2][1]


@pytest.mark.asyncio
async def test_get_top_agents():
    """Test getting top agents by cost."""
    tracker = CostTracker()

    # Record costs for different agents
    await tracker.record_cost("session-1", "agent-expensive", "claude-opus-4", 10000, 5000)
    await tracker.record_cost("session-2", "agent-cheap", "claude-haiku-3", 10000, 5000)
    await tracker.record_cost("session-3", "agent-medium", "claude-sonnet-4", 10000, 5000)

    top_agents = await tracker.get_top_agents(limit=3)

    assert len(top_agents) == 3

    # agent-expensive should be first (uses most expensive model)
    assert top_agents[0][0] == "agent-expensive"


@pytest.mark.asyncio
async def test_get_statistics():
    """Test getting cost statistics."""
    tracker = CostTracker()

    # Record some costs
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 2000, 1000)
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1500, 750)

    stats = await tracker.get_statistics(session_id="session-1")

    assert stats["total_requests"] == 3
    assert stats["total_input_tokens"] == 4500
    assert stats["total_output_tokens"] == 2250
    assert stats["total_tokens"] == 6750
    assert stats["total_cost"] > 0
    assert stats["avg_cost_per_request"] > 0
    assert stats["avg_tokens_per_request"] == 2250


@pytest.mark.asyncio
async def test_get_statistics_empty():
    """Test statistics for non-existent session."""
    tracker = CostTracker()

    stats = await tracker.get_statistics(session_id="non-existent")

    assert stats["total_cost"] == 0.0
    assert stats["total_requests"] == 0
    assert stats["total_input_tokens"] == 0
    assert stats["total_output_tokens"] == 0


@pytest.mark.asyncio
async def test_time_range_filtering():
    """Test filtering costs by time range."""
    tracker = CostTracker()

    # Record cost in the past
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)

    # Get current time
    now = datetime.now(UTC)

    # Record cost now
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 2000, 1000)

    # Get costs after the first one
    recent_cost = await tracker.get_session_cost("session-1", start_time=now)

    # Should only include the second cost
    assert recent_cost > 0

    total_cost = await tracker.get_session_cost("session-1")
    assert total_cost > recent_cost  # Total includes both


@pytest.mark.asyncio
async def test_metadata_storage():
    """Test storing and retrieving metadata."""
    tracker = CostTracker()

    cost = await tracker.record_cost(
        "session-1",
        "agent-1",
        "claude-sonnet-4",
        1000,
        500,
        metadata={"message_id": "msg-123", "user": "alice"},
    )

    assert cost.metadata["message_id"] == "msg-123"
    assert cost.metadata["user"] == "alice"


@pytest.mark.asyncio
async def test_cost_to_dict():
    """Test converting cost to dictionary."""
    tracker = CostTracker()

    cost = await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)

    cost_dict = cost.to_dict()

    assert cost_dict["session_id"] == "session-1"
    assert cost_dict["agent_name"] == "agent-1"
    assert cost_dict["model"] == "claude-sonnet-4"
    assert "timestamp" in cost_dict
    assert isinstance(cost_dict["timestamp"], str)  # ISO format


@pytest.mark.asyncio
async def test_multiple_sessions_isolation():
    """Test that session costs are isolated."""
    tracker = CostTracker()

    # Record costs for different sessions
    await tracker.record_cost("session-1", "agent-1", "claude-sonnet-4", 1000, 500)
    await tracker.record_cost("session-2", "agent-1", "claude-sonnet-4", 2000, 1000)

    session1_cost = await tracker.get_session_cost("session-1")
    session2_cost = await tracker.get_session_cost("session-2")

    # Sessions should have different costs
    assert session1_cost != session2_cost
    assert session2_cost > session1_cost  # session-2 has more tokens


@pytest.mark.asyncio
async def test_zero_cost_recording():
    """Test recording zero-cost operations (e.g., cached responses)."""
    tracker = CostTracker()

    cost = await tracker.record_cost(
        "session-1",
        "agent-1",
        "gemini-2.0-flash-exp",  # Free model
        1000,
        500,
    )

    assert cost.total_cost == 0.0
    assert cost.input_cost == 0.0
    assert cost.output_cost == 0.0


@pytest.mark.asyncio
async def test_large_token_counts():
    """Test handling large token counts (30-hour scenario)."""
    tracker = CostTracker()

    # 10M input tokens, 5M output tokens (realistic for 30-hour agent)
    cost = await tracker.record_cost(
        "session-1",
        "agent-1",
        "claude-opus-4",
        10000000,  # 10M input
        5000000,  # 5M output
    )

    # Should be $150 (input) + $375 (output) = $525
    assert abs(cost.total_cost - 525.0) < 1.0
