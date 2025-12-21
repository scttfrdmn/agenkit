"""Tests for introspection capability."""

import pytest
from datetime import datetime, timezone

from agenkit import Agent, Message, IntrospectionResult


class SimpleAgent(Agent):
    """Simple test agent."""

    @property
    def name(self) -> str:
        return "simple"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content=f"Processed: {message.content}")

    @property
    def capabilities(self) -> list[str]:
        return ["test", "simple"]


class AgentWithMemory(Agent):
    """Agent with memory state."""

    def __init__(self):
        self.memory = {
            "short_term": ["item1", "item2"],
            "long_term": ["memory1"],
        }
        self.message_count = 0

    @property
    def name(self) -> str:
        return "memory_agent"

    async def process(self, message: Message) -> Message:
        self.message_count += 1
        return Message(role="assistant", content="Processed")

    @property
    def capabilities(self) -> list[str]:
        return ["memory", "stateful"]

    def _get_memory_state(self) -> dict:
        return {
            "short_term_count": len(self.memory["short_term"]),
            "long_term_count": len(self.memory["long_term"]),
        }

    def _get_internal_state(self) -> dict:
        return {
            "message_count": self.message_count,
            "has_memory": True,
        }


def test_introspection_result_creation():
    """Test creating IntrospectionResult."""
    result = IntrospectionResult(
        timestamp=datetime.now(timezone.utc),
        agent_name="test",
        capabilities=["test"],
        memory_state=None,
        internal_state={},
        metadata={},
    )

    assert result.agent_name == "test"
    assert result.capabilities == ["test"]
    assert result.memory_state is None
    assert result.internal_state == {}


def test_introspection_result_validation():
    """Test IntrospectionResult validation."""
    # Empty agent name should raise
    with pytest.raises(ValueError, match="agent_name cannot be empty"):
        IntrospectionResult(
            timestamp=datetime.now(timezone.utc),
            agent_name="",
            capabilities=[],
            memory_state=None,
            internal_state={},
        )

    # Capabilities must be a list
    with pytest.raises(TypeError, match="capabilities must be a list"):
        IntrospectionResult(
            timestamp=datetime.now(timezone.utc),
            agent_name="test",
            capabilities="not a list",  # type: ignore
            memory_state=None,
            internal_state={},
        )

    # Internal state must be a dict
    with pytest.raises(TypeError, match="internal_state must be a dict"):
        IntrospectionResult(
            timestamp=datetime.now(timezone.utc),
            agent_name="test",
            capabilities=[],
            memory_state=None,
            internal_state="not a dict",  # type: ignore
        )


def test_basic_introspection():
    """Test basic agent introspection."""
    agent = SimpleAgent()
    result = agent.introspect()

    assert isinstance(result, IntrospectionResult)
    assert result.agent_name == "simple"
    assert result.capabilities == ["test", "simple"]
    assert result.memory_state is None
    assert result.internal_state == {}
    assert isinstance(result.timestamp, datetime)


def test_introspection_with_memory():
    """Test introspection of agent with memory."""
    agent = AgentWithMemory()
    result = agent.introspect()

    assert result.agent_name == "memory_agent"
    assert result.capabilities == ["memory", "stateful"]
    assert result.memory_state is not None
    assert result.memory_state["short_term_count"] == 2
    assert result.memory_state["long_term_count"] == 1
    assert result.internal_state["message_count"] == 0
    assert result.internal_state["has_memory"] is True


@pytest.mark.asyncio
async def test_introspection_reflects_state_changes():
    """Test that introspection captures state changes."""
    agent = AgentWithMemory()

    # Initial state
    result1 = agent.introspect()
    assert result1.internal_state["message_count"] == 0

    # Process a message
    await agent.process(Message(role="user", content="test"))

    # State should have changed
    result2 = agent.introspect()
    assert result2.internal_state["message_count"] == 1


def test_introspection_immutable():
    """Test that IntrospectionResult is immutable."""
    result = IntrospectionResult(
        timestamp=datetime.now(timezone.utc),
        agent_name="test",
        capabilities=["test"],
        memory_state=None,
        internal_state={},
    )

    # Should not be able to modify
    with pytest.raises(AttributeError):
        result.agent_name = "modified"  # type: ignore

    with pytest.raises(AttributeError):
        result.capabilities = ["modified"]  # type: ignore


def test_introspection_timestamp():
    """Test that introspection timestamp is recent."""
    agent = SimpleAgent()
    before = datetime.now(timezone.utc)
    result = agent.introspect()
    after = datetime.now(timezone.utc)

    assert before <= result.timestamp <= after


def test_introspection_with_metadata():
    """Test introspection with custom metadata."""
    agent = SimpleAgent()
    result = agent.introspect()

    # Default metadata should be empty
    assert result.metadata == {}

    # Can create result with metadata
    custom_result = IntrospectionResult(
        timestamp=datetime.now(timezone.utc),
        agent_name="test",
        capabilities=[],
        memory_state=None,
        internal_state={},
        metadata={"custom": "data"},
    )
    assert custom_result.metadata == {"custom": "data"}


def test_introspection_default_methods():
    """Test default _get_memory_state and _get_internal_state methods."""
    agent = SimpleAgent()

    # Default methods should return expected values
    assert agent._get_memory_state() is None
    assert agent._get_internal_state() == {}
