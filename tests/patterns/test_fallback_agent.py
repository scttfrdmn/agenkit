"""
Tests for FallbackAgent pattern - sequential retry with automatic failover.
"""

import pytest

from agenkit import Message
from agenkit.patterns import FallbackAgent

# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, name="mock", response="Success"):
        self._name = name
        self.response = response
        self.call_count = 0

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return []

    async def process(self, message: Message) -> Message:
        """Process message."""
        self.call_count += 1
        return Message(role="assistant", content=f"{self._name}: {self.response}")


class FailingAgent:
    """Agent that always fails."""

    def __init__(self, name="failing", error_msg="Failed"):
        self._name = name
        self.error_msg = error_msg
        self.call_count = 0

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return []

    async def process(self, message: Message) -> Message:
        """Always raises an error."""
        self.call_count += 1
        raise RuntimeError(self.error_msg)


# ============================================================================
# Creation Tests
# ============================================================================


def test_fallback_creation():
    """Test basic fallback agent creation."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    fallback = FallbackAgent(agents=[agent1, agent2])

    assert fallback._agents == [agent1, agent2]
    assert fallback.name == "FallbackAgent"


def test_fallback_empty_agents_raises():
    """Test that empty agents list raises ValueError."""
    with pytest.raises(ValueError, match="at least one agent is required"):
        FallbackAgent(agents=[])


def test_fallback_capabilities():
    """Test that capabilities are combined."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    fallback = FallbackAgent(agents=[agent1, agent2])
    caps = fallback.capabilities()

    assert "fallback" in caps
    assert "retry" in caps
    assert "high-availability" in caps


# ============================================================================
# Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_fallback_first_succeeds():
    """Test fallback when first agent succeeds."""
    agent1 = MockAgent("agent1", response="Success")
    agent2 = MockAgent("agent2", response="Backup")

    fallback = FallbackAgent(agents=[agent1, agent2])

    message = Message(role="user", content="input")
    result = await fallback.process(message)

    # First agent should succeed
    assert agent1.call_count == 1
    assert agent2.call_count == 0  # Never tried
    assert "agent1: Success" in result.content


@pytest.mark.asyncio
async def test_fallback_second_succeeds():
    """Test fallback when first fails, second succeeds."""
    agent1 = FailingAgent("agent1")
    agent2 = MockAgent("agent2", response="Success")

    fallback = FallbackAgent(agents=[agent1, agent2])

    message = Message(role="user", content="input")
    result = await fallback.process(message)

    # Both agents should be tried
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert "agent2: Success" in result.content


@pytest.mark.asyncio
async def test_fallback_all_fail():
    """Test fallback when all agents fail."""
    agent1 = FailingAgent("agent1", "Error 1")
    agent2 = FailingAgent("agent2", "Error 2")

    fallback = FallbackAgent(agents=[agent1, agent2])

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match=r"all .* agents failed"):
        await fallback.process(message)

    # All agents should have been tried
    assert agent1.call_count == 1
    assert agent2.call_count == 1


@pytest.mark.asyncio
async def test_fallback_metadata():
    """Test that fallback metadata is added."""
    agent1 = FailingAgent("agent1")
    agent2 = MockAgent("agent2", response="Success")

    fallback = FallbackAgent(agents=[agent1, agent2])

    message = Message(role="user", content="input")
    result = await fallback.process(message)

    # Should have fallback metadata
    assert "fallback_attempts" in result.metadata
    assert "fallback_success_index" in result.metadata
    assert "fallback_success_agent" in result.metadata
    assert result.metadata["fallback_attempts"] == 2
    assert result.metadata["fallback_success_index"] == 1
    assert result.metadata["fallback_success_agent"] == "agent2"


@pytest.mark.asyncio
async def test_fallback_failed_attempts_tracked():
    """Test that failed attempts are tracked in metadata."""
    agent1 = FailingAgent("agent1", "Error 1")
    agent2 = FailingAgent("agent2", "Error 2")
    agent3 = MockAgent("agent3", response="Success")

    fallback = FallbackAgent(agents=[agent1, agent2, agent3])

    message = Message(role="user", content="input")
    result = await fallback.process(message)

    # Should track failed attempts
    assert "fallback_failed_attempts" in result.metadata
    failed = result.metadata["fallback_failed_attempts"]
    assert len(failed) == 2
    assert failed[0]["agent"] == "agent1"
    assert failed[1]["agent"] == "agent2"


@pytest.mark.asyncio
async def test_fallback_none_message_raises():
    """Test that None message raises ValueError."""
    agent = MockAgent("agent")
    fallback = FallbackAgent(agents=[agent])

    with pytest.raises(ValueError, match="message cannot be None"):
        await fallback.process(None)  # type: ignore


@pytest.mark.asyncio
async def test_fallback_early_termination():
    """Test that fallback stops after first success."""
    agent1 = MockAgent("agent1", response="Success")
    agent2 = MockAgent("agent2", response="Backup")
    agent3 = MockAgent("agent3", response="Final")

    fallback = FallbackAgent(agents=[agent1, agent2, agent3])

    message = Message(role="user", content="input")
    await fallback.process(message)

    # Only first agent should be called
    assert agent1.call_count == 1
    assert agent2.call_count == 0
    assert agent3.call_count == 0


@pytest.mark.asyncio
async def test_fallback_reuse():
    """Test that fallback agent can be reused."""
    agent1 = FailingAgent("agent1")
    agent2 = MockAgent("agent2", response="Success")

    fallback = FallbackAgent(agents=[agent1, agent2])

    # First call
    message1 = Message(role="user", content="call1")
    await fallback.process(message1)

    # Second call
    message2 = Message(role="user", content="call2")
    await fallback.process(message2)

    # Both agents should have been called twice
    assert agent1.call_count == 2
    assert agent2.call_count == 2
