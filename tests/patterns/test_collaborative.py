"""
Tests for CollaborativeAgent pattern - peer-to-peer collaboration.

Tests CollaborativeAgent, consensus functions, and merge functions.
"""

import pytest

from agenkit import Message
from agenkit.patterns.collaborative import (CollaborativeAgent,
                                            CollaborativeConfig, RoundResult,
                                            default_consensus_funcs,
                                            default_merge_funcs)

# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, name="mock", responses=None, capabilities=None):
        self._name = name
        self.responses = responses or ["Response"]
        self._capabilities = capabilities or []
        self.call_count = 0
        self.last_message = None

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return self._capabilities

    async def process(self, message: Message) -> Message:
        """Process message, returning responses in sequence."""
        self.call_count += 1
        self.last_message = message

        # Use responses list cyclically
        response_idx = (self.call_count - 1) % len(self.responses)
        content = self.responses[response_idx]

        return Message(
            role="assistant",
            content=content,
            metadata={"agent": self._name, "call_count": self.call_count},
        )


class FailingAgent:
    """Agent that always fails."""

    def __init__(self, name="failing"):
        self._name = name

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        """Always raises an error."""
        raise RuntimeError(f"{self._name} failed")


# ============================================================================
# RoundResult Tests
# ============================================================================


def test_round_result_creation():
    """Test RoundResult dataclass creation."""
    msg1 = Message(role="assistant", content="Response 1")
    msg2 = Message(role="assistant", content="Response 2")

    result = RoundResult(round=0, responses=[msg1, msg2], consensus=False)

    assert result.round == 0
    assert len(result.responses) == 2
    assert result.consensus is False


# ============================================================================
# CollaborativeConfig Tests
# ============================================================================


def test_collaborative_config_creation():
    """Test CollaborativeConfig creation."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate
    )

    assert len(config.agents) == 2
    assert config.max_rounds == 3  # default
    assert config.consensus_func is None
    assert config.merge_func is not None


def test_collaborative_config_custom_rounds():
    """Test CollaborativeConfig with custom max_rounds."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=5
    )

    assert config.max_rounds == 5


def test_collaborative_config_with_consensus():
    """Test CollaborativeConfig with consensus function."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2],
        merge_func=default_merge_funcs.vote,
        consensus_func=default_consensus_funcs.exact_match,
    )

    assert config.consensus_func is not None


# ============================================================================
# CollaborativeAgent Creation Tests
# ============================================================================


def test_collaborative_creation():
    """Test basic collaborative agent creation."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate
    )
    collab = CollaborativeAgent(config)

    assert collab._agents == [agent1, agent2]
    assert collab._max_rounds == 3
    assert collab.name == "CollaborativeAgent"


def test_collaborative_none_config_raises():
    """Test that None config raises ValueError."""
    with pytest.raises(ValueError, match="config is required"):
        CollaborativeAgent(None)  # type: ignore


def test_collaborative_single_agent_raises():
    """Test that less than 2 agents raises ValueError."""
    agent = MockAgent("agent")
    config = CollaborativeConfig(agents=[agent], merge_func=default_merge_funcs.concatenate)

    with pytest.raises(ValueError, match="at least two agents are required"):
        CollaborativeAgent(config)


def test_collaborative_none_merge_func_raises():
    """Test that None merge_func raises ValueError."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    config = CollaborativeConfig(agents=[agent1, agent2], merge_func=None)  # type: ignore

    with pytest.raises(ValueError, match="merge function is required"):
        CollaborativeAgent(config)


def test_collaborative_zero_max_rounds_defaults():
    """Test that zero or negative max_rounds defaults to 3."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=0
    )

    collab = CollaborativeAgent(config)
    assert collab._max_rounds == 3


# ============================================================================
# CollaborativeAgent Capabilities Tests
# ============================================================================


def test_collaborative_capabilities_combined():
    """Test that capabilities are combined from all agents."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["write", "format"])

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate
    )
    collab = CollaborativeAgent(config)
    caps = collab.capabilities()

    # Should have all agent capabilities plus collaborative-specific
    assert "search" in caps
    assert "read" in caps
    assert "write" in caps
    assert "format" in caps
    assert "collaborative" in caps
    assert "iterative" in caps
    assert "consensus" in caps


def test_collaborative_capabilities_deduplication():
    """Test that duplicate capabilities are deduplicated."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["search", "write"])

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate
    )
    collab = CollaborativeAgent(config)
    caps = collab.capabilities()

    # "search" should appear only once
    assert caps.count("search") == 1


# ============================================================================
# CollaborativeAgent Processing Tests - Basic
# ============================================================================


@pytest.mark.asyncio
async def test_collaborative_basic_processing():
    """Test basic collaborative processing."""
    agent1 = MockAgent("agent1", responses=["A1", "A1-refined"])
    agent2 = MockAgent("agent2", responses=["A2", "A2-refined"])

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=2
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    result = await collab.process(message)

    # Both agents should be called for 2 rounds
    assert agent1.call_count == 2
    assert agent2.call_count == 2

    # Result should contain both agents' final responses
    assert "A1-refined" in result.content
    assert "A2-refined" in result.content


@pytest.mark.asyncio
async def test_collaborative_all_rounds_executed():
    """Test that all rounds are executed when no consensus."""
    agent1 = MockAgent("agent1", responses=["R1-1", "R1-2", "R1-3"])
    agent2 = MockAgent("agent2", responses=["R2-1", "R2-2", "R2-3"])

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=3
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    result = await collab.process(message)

    # All rounds should execute
    assert agent1.call_count == 3
    assert agent2.call_count == 3

    # Metadata should reflect all rounds
    assert result.metadata["collaboration_rounds"] == 3
    assert result.metadata["stop_reason"] == "max_rounds"


@pytest.mark.asyncio
async def test_collaborative_metadata():
    """Test that collaboration metadata is added."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=2
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    result = await collab.process(message)

    # Should have collaboration metadata
    assert "collaboration_rounds" in result.metadata
    assert "collaboration_agents" in result.metadata
    assert "stop_reason" in result.metadata
    assert "rounds" in result.metadata

    assert result.metadata["collaboration_agents"] == 2
    assert result.metadata["collaboration_rounds"] == 2


# ============================================================================
# CollaborativeAgent Processing Tests - Consensus
# ============================================================================


@pytest.mark.asyncio
async def test_collaborative_consensus_early_stop():
    """Test that collaboration stops early on consensus."""
    # Both agents return same response
    agent1 = MockAgent("agent1", responses=["Same"])
    agent2 = MockAgent("agent2", responses=["Same"])

    config = CollaborativeConfig(
        agents=[agent1, agent2],
        merge_func=default_merge_funcs.concatenate,
        max_rounds=5,
        consensus_func=default_consensus_funcs.exact_match,
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    result = await collab.process(message)

    # Should stop after first round due to consensus
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert result.metadata["collaboration_rounds"] == 1
    assert result.metadata["stop_reason"] == "consensus"


@pytest.mark.asyncio
async def test_collaborative_consensus_later_round():
    """Test consensus reached in later round."""
    # Agents converge to same response in round 2
    agent1 = MockAgent("agent1", responses=["Different1", "Converged"])
    agent2 = MockAgent("agent2", responses=["Different2", "Converged"])

    config = CollaborativeConfig(
        agents=[agent1, agent2],
        merge_func=default_merge_funcs.concatenate,
        max_rounds=5,
        consensus_func=default_consensus_funcs.exact_match,
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    result = await collab.process(message)

    # Should stop after second round
    assert agent1.call_count == 2
    assert agent2.call_count == 2
    assert result.metadata["collaboration_rounds"] == 2
    assert result.metadata["stop_reason"] == "consensus"


@pytest.mark.asyncio
async def test_collaborative_no_consensus_all_rounds():
    """Test that all rounds execute when consensus never reached."""
    # Agents never agree
    agent1 = MockAgent("agent1", responses=["A1", "A2", "A3"])
    agent2 = MockAgent("agent2", responses=["B1", "B2", "B3"])

    config = CollaborativeConfig(
        agents=[agent1, agent2],
        merge_func=default_merge_funcs.concatenate,
        max_rounds=3,
        consensus_func=default_consensus_funcs.exact_match,
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    result = await collab.process(message)

    # All rounds should execute
    assert agent1.call_count == 3
    assert agent2.call_count == 3
    assert result.metadata["stop_reason"] == "max_rounds"


# ============================================================================
# CollaborativeAgent Processing Tests - Context Building
# ============================================================================


@pytest.mark.asyncio
async def test_collaborative_context_includes_previous_responses():
    """Test that agents see previous round responses."""
    agent1 = MockAgent("agent1", responses=["Round1", "Round2"])
    agent2 = MockAgent("agent2", responses=["Round1", "Round2"])

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=2
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="original input")
    await collab.process(message)

    # Check that agent1's second call includes previous responses
    last_msg = agent1.last_message
    assert "original input" in last_msg.content
    assert "Previous Responses" in last_msg.content
    assert "Round1" in last_msg.content  # Should see round 1 responses


@pytest.mark.asyncio
async def test_collaborative_first_round_no_previous():
    """Test that first round doesn't show previous responses."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=1
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    await collab.process(message)

    # First round should not mention previous responses
    assert "Previous Responses" not in agent1.last_message.content


# ============================================================================
# CollaborativeAgent Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_collaborative_none_message_raises():
    """Test that None message raises ValueError."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate
    )
    collab = CollaborativeAgent(config)

    with pytest.raises(ValueError, match="message cannot be None"):
        await collab.process(None)  # type: ignore


@pytest.mark.asyncio
async def test_collaborative_agent_failure_raises():
    """Test that agent failure raises RuntimeError."""
    agent1 = MockAgent("agent1")
    failing = FailingAgent("failing")

    config = CollaborativeConfig(
        agents=[agent1, failing], merge_func=default_merge_funcs.concatenate
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="agent failing failed in round 0"):
        await collab.process(message)


# ============================================================================
# DefaultConsensusFuncs Tests
# ============================================================================


def test_consensus_exact_match_all_same():
    """Test exact_match with identical responses."""
    msg1 = Message(role="assistant", content="Same")
    msg2 = Message(role="assistant", content="Same")
    msg3 = Message(role="assistant", content="Same")

    assert default_consensus_funcs.exact_match([msg1, msg2, msg3]) is True


def test_consensus_exact_match_different():
    """Test exact_match with different responses."""
    msg1 = Message(role="assistant", content="Different1")
    msg2 = Message(role="assistant", content="Different2")

    assert default_consensus_funcs.exact_match([msg1, msg2]) is False


def test_consensus_exact_match_single_message():
    """Test exact_match with single message."""
    msg = Message(role="assistant", content="Solo")

    assert default_consensus_funcs.exact_match([msg]) is True


def test_consensus_majority_agreement():
    """Test majority_agreement with majority."""
    msg1 = Message(role="assistant", content="A")
    msg2 = Message(role="assistant", content="A")
    msg3 = Message(role="assistant", content="B")

    # 2 out of 3 agree on "A"
    assert default_consensus_funcs.majority_agreement([msg1, msg2, msg3]) is True


def test_consensus_majority_no_agreement():
    """Test majority_agreement without majority."""
    msg1 = Message(role="assistant", content="A")
    msg2 = Message(role="assistant", content="B")
    msg3 = Message(role="assistant", content="C")

    # No majority
    assert default_consensus_funcs.majority_agreement([msg1, msg2, msg3]) is False


def test_consensus_similarity_threshold():
    """Test similarity_threshold function factory."""
    # Messages with matching prefix (first 20 chars)
    msg1 = Message(role="assistant", content="Hello world this is a response")
    msg2 = Message(role="assistant", content="Hello world this is another response")

    func = default_consensus_funcs.similarity_threshold(0.8)
    # Both contain the first message's prefix
    assert func([msg1, msg2]) is True


# ============================================================================
# DefaultMergeFuncs Tests
# ============================================================================


def test_merge_concatenate():
    """Test concatenate merge function."""
    msg1 = Message(role="assistant", content="Part 1")
    msg2 = Message(role="assistant", content="Part 2")

    result = default_merge_funcs.concatenate([msg1, msg2])

    assert "Part 1" in result.content
    assert "Part 2" in result.content
    assert "---" in result.content


def test_merge_concatenate_empty():
    """Test concatenate with empty list."""
    result = default_merge_funcs.concatenate([])
    assert "No responses" in result.content


def test_merge_vote():
    """Test vote merge function."""
    msg1 = Message(role="assistant", content="A")
    msg2 = Message(role="assistant", content="A")
    msg3 = Message(role="assistant", content="B")

    result = default_merge_funcs.vote([msg1, msg2, msg3])

    # "A" wins with 2 votes
    assert result.content == "A"
    assert result.metadata["votes"] == 2
    assert result.metadata["total"] == 3


def test_merge_vote_empty():
    """Test vote with empty list."""
    result = default_merge_funcs.vote([])
    assert "No responses" in result.content


def test_merge_first():
    """Test first merge function."""
    msg1 = Message(role="assistant", content="First")
    msg2 = Message(role="assistant", content="Second")

    result = default_merge_funcs.first([msg1, msg2])
    assert result.content == "First"


def test_merge_first_empty():
    """Test first with empty list."""
    result = default_merge_funcs.first([])
    assert "No responses" in result.content


def test_merge_last():
    """Test last merge function."""
    msg1 = Message(role="assistant", content="First")
    msg2 = Message(role="assistant", content="Last")

    result = default_merge_funcs.last([msg1, msg2])
    assert result.content == "Last"


def test_merge_last_empty():
    """Test last with empty list."""
    result = default_merge_funcs.last([])
    assert "No responses" in result.content


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_collaborative_full_workflow():
    """Test complete collaborative workflow."""
    # Create agents that converge
    agent1 = MockAgent("agent1", responses=["Initial1", "Refined1", "Final"])
    agent2 = MockAgent("agent2", responses=["Initial2", "Refined2", "Final"])

    config = CollaborativeConfig(
        agents=[agent1, agent2],
        merge_func=default_merge_funcs.vote,
        max_rounds=3,
        consensus_func=default_consensus_funcs.exact_match,
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="Collaborate on this")
    result = await collab.process(message)

    # Should reach consensus in round 3
    assert result.metadata["collaboration_rounds"] == 3
    assert result.metadata["stop_reason"] == "consensus"
    assert result.content == "Final"


@pytest.mark.asyncio
async def test_collaborative_reuse():
    """Test that collaborative agent can be reused."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    config = CollaborativeConfig(
        agents=[agent1, agent2], merge_func=default_merge_funcs.concatenate, max_rounds=2
    )
    collab = CollaborativeAgent(config)

    # First call
    message1 = Message(role="user", content="call1")
    await collab.process(message1)

    # Second call
    message2 = Message(role="user", content="call2")
    await collab.process(message2)

    # Agents should have been called 4 times total (2 rounds x 2 calls)
    assert agent1.call_count == 4
    assert agent2.call_count == 4


@pytest.mark.asyncio
async def test_collaborative_many_agents():
    """Test collaborative with many agents."""
    agents = [MockAgent(f"agent{i}") for i in range(5)]

    config = CollaborativeConfig(
        agents=agents, merge_func=default_merge_funcs.concatenate, max_rounds=2
    )
    collab = CollaborativeAgent(config)

    message = Message(role="user", content="input")
    result = await collab.process(message)

    # All agents should be called
    for agent in agents:
        assert agent.call_count == 2

    # Metadata should reflect all agents
    assert result.metadata["collaboration_agents"] == 5
