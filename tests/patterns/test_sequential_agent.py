"""
Tests for SequentialAgent pattern - pipeline-style agent composition.
"""

import pytest

from agenkit import Message
from agenkit.patterns import SequentialAgent

# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, name="mock", response="Success", capabilities=None):
        self._name = name
        self.response = response
        self._capabilities = capabilities or []
        self.call_count = 0
        self.last_message = None

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return self._capabilities

    async def process(self, message: Message) -> Message:
        """Process message and return response."""
        self.call_count += 1
        self.last_message = message

        # Append agent name to content for pipeline tracking
        if isinstance(message.content, str):
            new_content = f"{message.content} -> {self._name}"
        else:
            new_content = self.response

        return Message(
            role="assistant",
            content=new_content,
            metadata={"agent": self._name, "call_count": self.call_count},
        )


class FailingAgent:
    """Agent that raises an error."""

    def __init__(self, name="failing", error_message="Agent failed"):
        self._name = name
        self.error_message = error_message

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        """Always raises an error."""
        raise RuntimeError(self.error_message)


# ============================================================================
# Creation Tests
# ============================================================================


def test_sequential_creation():
    """Test basic sequential agent creation."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialAgent(agents=[agent1, agent2])

    assert seq._agents == [agent1, agent2]
    assert seq.name == "SequentialAgent"


def test_sequential_empty_agents_raises():
    """Test that empty agents list raises ValueError."""
    with pytest.raises(ValueError, match="at least one agent is required"):
        SequentialAgent(agents=[])


def test_sequential_single_agent():
    """Test sequential agent with single agent."""
    agent = MockAgent("single")
    seq = SequentialAgent(agents=[agent])

    assert len(seq._agents) == 1
    assert seq._agents[0] is agent


def test_sequential_multiple_agents():
    """Test sequential agent with multiple agents."""
    agents = [MockAgent(f"agent{i}") for i in range(5)]
    seq = SequentialAgent(agents=agents)

    assert len(seq._agents) == 5
    for i, agent in enumerate(seq._agents):
        assert agent.name == f"agent{i}"


# ============================================================================
# Capabilities Tests
# ============================================================================


def test_sequential_capabilities_combined():
    """Test that capabilities are combined from all agents."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["write", "format"])

    seq = SequentialAgent(agents=[agent1, agent2])
    caps = seq.capabilities()

    # Should have all unique capabilities plus sequential/pipeline
    assert "search" in caps
    assert "read" in caps
    assert "write" in caps
    assert "format" in caps
    assert "sequential" in caps
    assert "pipeline" in caps


def test_sequential_capabilities_deduplication():
    """Test that duplicate capabilities are deduplicated."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["search", "write"])

    seq = SequentialAgent(agents=[agent1, agent2])
    caps = seq.capabilities()

    # "search" should appear only once
    assert caps.count("search") == 1


# ============================================================================
# Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_basic_processing():
    """Test basic sequential processing."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    agent3 = MockAgent("agent3")

    seq = SequentialAgent(agents=[agent1, agent2, agent3])

    message = Message(role="user", content="input")
    result = await seq.process(message)

    # Content should show pipeline progression
    assert result.content == "input -> agent1 -> agent2 -> agent3"

    # All agents should have been called
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert agent3.call_count == 1


@pytest.mark.asyncio
async def test_sequential_message_flow():
    """Test that message flows through pipeline correctly."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialAgent(agents=[agent1, agent2])

    message = Message(role="user", content="start")
    await seq.process(message)

    # Agent1 should receive original message
    assert agent1.last_message.content == "start"

    # Agent2 should receive agent1's output
    assert agent2.last_message.content == "start -> agent1"


@pytest.mark.asyncio
async def test_sequential_pipeline_metadata():
    """Test that pipeline metadata is added to result."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialAgent(agents=[agent1, agent2])

    message = Message(role="user", content="input")
    result = await seq.process(message)

    # Should have pipeline metadata
    assert "pipeline_stages" in result.metadata
    assert "pipeline_length" in result.metadata
    assert result.metadata["pipeline_length"] == 2

    # Check stage metadata
    stages = result.metadata["pipeline_stages"]
    assert len(stages) == 2
    assert stages[0]["agent"] == "agent1"
    assert stages[0]["stage"] == 0
    assert stages[1]["agent"] == "agent2"
    assert stages[1]["stage"] == 1


@pytest.mark.asyncio
async def test_sequential_preserves_agent_metadata():
    """Test that agent metadata is preserved in pipeline stages."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialAgent(agents=[agent1, agent2])

    message = Message(role="user", content="input")
    result = await seq.process(message)

    stages = result.metadata["pipeline_stages"]

    # Each stage should have agent metadata
    assert "metadata" in stages[0]
    assert stages[0]["metadata"]["agent"] == "agent1"
    assert stages[0]["metadata"]["call_count"] == 1

    assert "metadata" in stages[1]
    assert stages[1]["metadata"]["agent"] == "agent2"
    assert stages[1]["metadata"]["call_count"] == 1


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_none_message_raises():
    """Test that None message raises ValueError."""
    agent = MockAgent("agent")
    seq = SequentialAgent(agents=[agent])

    with pytest.raises(ValueError, match="message cannot be None"):
        await seq.process(None)  # type: ignore


@pytest.mark.asyncio
async def test_sequential_first_agent_failure():
    """Test that failure in first agent stops pipeline."""
    failing = FailingAgent("failing")
    agent2 = MockAgent("agent2")

    seq = SequentialAgent(agents=[failing, agent2])

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match=r"agent 0 .* failed"):
        await seq.process(message)

    # Agent2 should not have been called
    assert agent2.call_count == 0


@pytest.mark.asyncio
async def test_sequential_middle_agent_failure():
    """Test that failure in middle agent stops pipeline."""
    agent1 = MockAgent("agent1")
    failing = FailingAgent("failing")
    agent3 = MockAgent("agent3")

    seq = SequentialAgent(agents=[agent1, failing, agent3])

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match=r"agent 1 .* failed"):
        await seq.process(message)

    # Agent1 should have been called
    assert agent1.call_count == 1

    # Agent3 should not have been called
    assert agent3.call_count == 0


@pytest.mark.asyncio
async def test_sequential_error_includes_agent_name():
    """Test that error message includes agent name."""
    failing = FailingAgent("problematic_agent", "Something went wrong")

    seq = SequentialAgent(agents=[failing])

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match=r"problematic_agent.*failed"):
        await seq.process(message)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_long_pipeline():
    """Test sequential agent with many stages."""
    # Create a 10-agent pipeline
    agents = [MockAgent(f"agent{i}") for i in range(10)]
    seq = SequentialAgent(agents=agents)

    message = Message(role="user", content="start")
    result = await seq.process(message)

    # All agents should have been called
    for agent in agents:
        assert agent.call_count == 1

    # Pipeline metadata should reflect all stages
    assert result.metadata["pipeline_length"] == 10
    assert len(result.metadata["pipeline_stages"]) == 10


@pytest.mark.asyncio
async def test_sequential_reuse():
    """Test that sequential agent can be reused for multiple calls."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    seq = SequentialAgent(agents=[agent1, agent2])

    # First call
    message1 = Message(role="user", content="call1")
    result1 = await seq.process(message1)
    assert result1.content == "call1 -> agent1 -> agent2"

    # Second call
    message2 = Message(role="user", content="call2")
    result2 = await seq.process(message2)
    assert result2.content == "call2 -> agent1 -> agent2"

    # Call counts should increment
    assert agent1.call_count == 2
    assert agent2.call_count == 2


@pytest.mark.asyncio
async def test_sequential_with_complex_content():
    """Test sequential agent with complex message content."""
    agent1 = MockAgent("agent1", response={"result": "processed"})
    agent2 = MockAgent("agent2", response=["item1", "item2"])

    seq = SequentialAgent(agents=[agent1, agent2])

    message = Message(role="user", content={"input": "data"})
    result = await seq.process(message)

    # Should handle complex content
    assert isinstance(result.content, list)
    assert result.content == ["item1", "item2"]


@pytest.mark.asyncio
async def test_sequential_metadata_initialization():
    """Test that metadata is properly initialized if None."""

    class MinimalAgent:
        """Agent that returns message with no metadata."""

        @property
        def name(self):
            return "minimal"

        def capabilities(self):
            return []

        async def process(self, message: Message) -> Message:
            return Message(role="assistant", content="done")

    agent = MinimalAgent()
    seq = SequentialAgent(agents=[agent])

    message = Message(role="user", content="input")
    result = await seq.process(message)

    # Metadata should be initialized and contain pipeline info
    assert result.metadata is not None
    assert "pipeline_stages" in result.metadata
    assert "pipeline_length" in result.metadata
