"""
Tests for ParallelAgent pattern - concurrent execution with result aggregation.
"""

import asyncio

import pytest

from agenkit import Message
from agenkit.patterns import ParallelAgent, default_aggregators

# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent:
    """Simple mock agent for testing."""

    def __init__(self, name="mock", response="Success", delay=0, capabilities=None):
        self._name = name
        self.response = response
        self.delay = delay
        self._capabilities = capabilities or []
        self.call_count = 0
        self.last_message = None

    @property
    def name(self):
        return self._name

    def capabilities(self):
        return self._capabilities

    async def process(self, message: Message) -> Message:
        """Process message with optional delay."""
        self.call_count += 1
        self.last_message = message

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        return Message(role="assistant", content=self.response, metadata={"agent": self._name})


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
# Aggregator Functions
# ============================================================================


def simple_first_aggregator(messages: list[Message]) -> Message:
    """Simple aggregator that returns first message."""
    return messages[0] if messages else Message(role="assistant", content="No results")


def count_aggregator(messages: list[Message]) -> Message:
    """Aggregator that counts results."""
    return Message(
        role="assistant",
        content=f"Aggregated {len(messages)} results",
        metadata={"count": len(messages)},
    )


# ============================================================================
# Creation Tests
# ============================================================================


def test_parallel_creation():
    """Test basic parallel agent creation."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)

    assert parallel._agents == [agent1, agent2]
    assert parallel._aggregator is simple_first_aggregator
    assert parallel.name == "ParallelAgent"


def test_parallel_empty_agents_raises():
    """Test that empty agents list raises ValueError."""
    with pytest.raises(ValueError, match="at least one agent is required"):
        ParallelAgent(agents=[], aggregator=simple_first_aggregator)


def test_parallel_none_aggregator_raises():
    """Test that None aggregator raises ValueError."""
    agent = MockAgent("agent")

    with pytest.raises(ValueError, match="aggregator function is required"):
        ParallelAgent(agents=[agent], aggregator=None)  # type: ignore


def test_parallel_single_agent():
    """Test parallel agent with single agent."""
    agent = MockAgent("single")
    parallel = ParallelAgent(agents=[agent], aggregator=simple_first_aggregator)

    assert len(parallel._agents) == 1


# ============================================================================
# Capabilities Tests
# ============================================================================


def test_parallel_capabilities_combined():
    """Test that capabilities are combined from all agents."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["write", "format"])

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)
    caps = parallel.capabilities()

    # Should have all unique capabilities plus parallel/ensemble
    assert "search" in caps
    assert "read" in caps
    assert "write" in caps
    assert "format" in caps
    assert "parallel" in caps
    assert "ensemble" in caps


def test_parallel_capabilities_deduplication():
    """Test that duplicate capabilities are deduplicated."""
    agent1 = MockAgent("agent1", capabilities=["search", "read"])
    agent2 = MockAgent("agent2", capabilities=["search", "write"])

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)
    caps = parallel.capabilities()

    # "search" should appear only once
    assert caps.count("search") == 1


# ============================================================================
# Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_basic_processing():
    """Test basic parallel processing."""
    agent1 = MockAgent("agent1", response="Response1")
    agent2 = MockAgent("agent2", response="Response2")
    agent3 = MockAgent("agent3", response="Response3")

    parallel = ParallelAgent(agents=[agent1, agent2, agent3], aggregator=simple_first_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # All agents should have been called
    assert agent1.call_count == 1
    assert agent2.call_count == 1
    assert agent3.call_count == 1

    # Result should be from first agent
    assert result.content == "Response1"


@pytest.mark.asyncio
async def test_parallel_same_input_to_all():
    """Test that all agents receive the same input."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)

    message = Message(role="user", content="shared_input")
    await parallel.process(message)

    # All agents should receive same message
    assert agent1.last_message.content == "shared_input"
    assert agent2.last_message.content == "shared_input"


@pytest.mark.asyncio
async def test_parallel_concurrent_execution():
    """Test that agents execute concurrently."""
    # Agents with delays - if sequential, would take 0.3s total
    agent1 = MockAgent("agent1", delay=0.1)
    agent2 = MockAgent("agent2", delay=0.1)
    agent3 = MockAgent("agent3", delay=0.1)

    parallel = ParallelAgent(agents=[agent1, agent2, agent3], aggregator=simple_first_aggregator)

    message = Message(role="user", content="input")

    start = asyncio.get_event_loop().time()
    await parallel.process(message)
    elapsed = asyncio.get_event_loop().time() - start

    # Should complete in ~0.1s (parallel) not 0.3s (sequential)
    # Allow some margin for overhead
    assert elapsed < 0.25


@pytest.mark.asyncio
async def test_parallel_metadata():
    """Test that parallel execution metadata is added."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # Should have parallel metadata
    assert "parallel_agents" in result.metadata
    assert "successful_agents" in result.metadata
    assert result.metadata["parallel_agents"] == 2
    assert result.metadata["successful_agents"] == 2


# ============================================================================
# Aggregator Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_custom_aggregator():
    """Test parallel agent with custom aggregator."""
    agent1 = MockAgent("agent1", response="A")
    agent2 = MockAgent("agent2", response="B")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=count_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    assert result.content == "Aggregated 2 results"
    assert result.metadata["count"] == 2


@pytest.mark.asyncio
async def test_parallel_default_aggregator_first():
    """Test default first aggregator."""
    agent1 = MockAgent("agent1", response="First")
    agent2 = MockAgent("agent2", response="Second")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=default_aggregators.first)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    assert result.content == "First"


@pytest.mark.asyncio
async def test_parallel_default_aggregator_concatenate():
    """Test default concatenate aggregator."""
    agent1 = MockAgent("agent1", response="Response1")
    agent2 = MockAgent("agent2", response="Response2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=default_aggregators.concatenate)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    assert "Response1" in result.content
    assert "Response2" in result.content
    assert "---" in result.content


@pytest.mark.asyncio
async def test_parallel_default_aggregator_majority_vote():
    """Test default majority vote aggregator."""
    # 2 agents say "Yes", 1 says "No"
    agent1 = MockAgent("agent1", response="Yes")
    agent2 = MockAgent("agent2", response="Yes")
    agent3 = MockAgent("agent3", response="No")

    parallel = ParallelAgent(
        agents=[agent1, agent2, agent3], aggregator=default_aggregators.majority_vote
    )

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # Majority wins
    assert result.content == "Yes"
    assert result.metadata["votes"] == 2
    assert result.metadata["total_agents"] == 3


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_none_message_raises():
    """Test that None message raises ValueError."""
    agent = MockAgent("agent")
    parallel = ParallelAgent(agents=[agent], aggregator=simple_first_aggregator)

    with pytest.raises(ValueError, match="message cannot be None"):
        await parallel.process(None)  # type: ignore


@pytest.mark.asyncio
async def test_parallel_single_agent_failure():
    """Test that single agent failure is recorded."""
    agent1 = MockAgent("agent1", response="Success")
    agent2 = FailingAgent("agent2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # Should still succeed with one agent
    assert result.content == "Success"

    # Error should be recorded in metadata
    assert "errors" in result.metadata
    assert len(result.metadata["errors"]) == 1
    assert result.metadata["errors"][0]["agent"] == "agent2"
    assert result.metadata["successful_agents"] == 1


@pytest.mark.asyncio
async def test_parallel_all_agents_fail():
    """Test that all agents failing raises error."""
    agent1 = FailingAgent("agent1")
    agent2 = FailingAgent("agent2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="all agents failed"):
        await parallel.process(message)


@pytest.mark.asyncio
async def test_parallel_mixed_success_failure():
    """Test parallel with mix of successes and failures."""
    agent1 = MockAgent("agent1", response="Success1")
    agent2 = FailingAgent("agent2")
    agent3 = MockAgent("agent3", response="Success3")
    agent4 = FailingAgent("agent4")

    parallel = ParallelAgent(agents=[agent1, agent2, agent3, agent4], aggregator=count_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # Should succeed with 2 successful agents
    assert result.content == "Aggregated 2 results"
    assert result.metadata["count"] == 2

    # Should have 2 errors recorded
    assert len(result.metadata["errors"]) == 2
    assert result.metadata["successful_agents"] == 2
    assert result.metadata["parallel_agents"] == 4


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_reuse():
    """Test that parallel agent can be reused."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)

    # First call
    message1 = Message(role="user", content="call1")
    await parallel.process(message1)

    # Second call
    message2 = Message(role="user", content="call2")
    await parallel.process(message2)

    # Call counts should increment
    assert agent1.call_count == 2
    assert agent2.call_count == 2


@pytest.mark.asyncio
async def test_parallel_many_agents():
    """Test parallel agent with many agents."""
    agents = [MockAgent(f"agent{i}", response=f"Response{i}") for i in range(10)]
    parallel = ParallelAgent(agents=agents, aggregator=count_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # All agents should have been called
    for agent in agents:
        assert agent.call_count == 1

    # Should have aggregated all results
    assert result.content == "Aggregated 10 results"
    assert result.metadata["count"] == 10


@pytest.mark.asyncio
async def test_parallel_no_errors_when_all_succeed():
    """Test that errors key is not added when all succeed."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    parallel = ParallelAgent(agents=[agent1, agent2], aggregator=simple_first_aggregator)

    message = Message(role="user", content="input")
    result = await parallel.process(message)

    # Should not have errors key
    assert "errors" not in result.metadata
    assert result.metadata["successful_agents"] == 2
