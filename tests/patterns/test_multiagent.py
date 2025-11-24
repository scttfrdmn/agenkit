"""
Tests for Multi-Agent Collaboration patterns.
"""

import pytest

from agenkit import Agent, Message
from agenkit.patterns import (
    AgentTask,
    ConsensusAgent,
    MultiAgentOrchestrator,
)

# ============================================================================
# Mock Agents
# ============================================================================


class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(self, agent_name: str, response: str = "Mock response"):
        self._name = agent_name
        self.response = response
        self.call_count = 0
        self.last_message = None

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        self.call_count += 1
        self.last_message = message
        return Message(role="assistant", content=self.response)


class FailingAgent(Agent):
    """Agent that always fails."""

    @property
    def name(self) -> str:
        return "FailingAgent"

    async def process(self, message: Message) -> Message:
        raise RuntimeError("Simulated failure")


# ============================================================================
# AgentTask Tests
# ============================================================================


def test_agent_task_creation():
    """Test creating an AgentTask."""
    task = AgentTask(agent_name="test_agent", description="Test task")

    assert task.agent_name == "test_agent"
    assert task.description == "Test task"
    assert task.status == "pending"
    assert task.result is None
    assert task.error is None


def test_agent_task_with_result():
    """Test AgentTask with result."""
    task = AgentTask(
        agent_name="test_agent",
        description="Test task",
        result="Task result",
        status="completed",
    )

    assert task.result == "Task result"
    assert task.status == "completed"


def test_agent_task_with_error():
    """Test AgentTask with error."""
    task = AgentTask(
        agent_name="test_agent",
        description="Test task",
        error="Error message",
        status="failed",
    )

    assert task.error == "Error message"
    assert task.status == "failed"


# ============================================================================
# MultiAgentOrchestrator Tests
# ============================================================================


def test_orchestrator_creation():
    """Test creating a MultiAgentOrchestrator."""
    orchestrator = MultiAgentOrchestrator()

    assert orchestrator.name == "MultiAgentOrchestrator"
    assert orchestrator.strategy == "sequential"
    assert len(orchestrator.agents) == 0
    assert len(orchestrator.tasks) == 0


def test_orchestrator_with_strategy():
    """Test creating orchestrator with custom strategy."""
    orchestrator = MultiAgentOrchestrator(strategy="parallel")

    assert orchestrator.strategy == "parallel"


def test_orchestrator_register_agent():
    """Test registering an agent."""
    orchestrator = MultiAgentOrchestrator()
    agent = MockAgent("test_agent")

    orchestrator.register_agent("test", agent)

    assert "test" in orchestrator.agents
    assert orchestrator.agents["test"] == agent
    assert len(orchestrator.list_agents()) == 1


def test_orchestrator_register_multiple_agents():
    """Test registering multiple agents."""
    orchestrator = MultiAgentOrchestrator()
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    orchestrator.register_agent("first", agent1)
    orchestrator.register_agent("second", agent2)

    assert len(orchestrator.agents) == 2
    assert "first" in orchestrator.list_agents()
    assert "second" in orchestrator.list_agents()


def test_orchestrator_unregister_agent():
    """Test unregistering an agent."""
    orchestrator = MultiAgentOrchestrator()
    agent = MockAgent("test_agent")

    orchestrator.register_agent("test", agent)
    assert "test" in orchestrator.agents

    orchestrator.unregister_agent("test")
    assert "test" not in orchestrator.agents


def test_orchestrator_unregister_nonexistent_agent():
    """Test unregistering an agent that doesn't exist."""
    orchestrator = MultiAgentOrchestrator()

    # Should not raise an error
    orchestrator.unregister_agent("nonexistent")


@pytest.mark.asyncio
async def test_orchestrator_process_single_agent():
    """Test processing with a single agent."""
    orchestrator = MultiAgentOrchestrator()
    agent = MockAgent("test_agent", "Agent response")

    orchestrator.register_agent("test", agent)

    result = await orchestrator.process(Message(role="user", content="Test message"))

    assert "Agent response" in result.content
    assert agent.call_count == 1
    assert agent.last_message.content == "Test message"


@pytest.mark.asyncio
async def test_orchestrator_process_multiple_agents():
    """Test processing with multiple agents."""
    orchestrator = MultiAgentOrchestrator()
    agent1 = MockAgent("agent1", "Response 1")
    agent2 = MockAgent("agent2", "Response 2")

    orchestrator.register_agent("first", agent1)
    orchestrator.register_agent("second", agent2)

    result = await orchestrator.process(Message(role="user", content="Test"))

    assert "Response 1" in result.content
    assert "Response 2" in result.content
    assert agent1.call_count == 1
    assert agent2.call_count == 1


@pytest.mark.asyncio
async def test_orchestrator_task_tracking():
    """Test that tasks are tracked."""
    orchestrator = MultiAgentOrchestrator()
    agent = MockAgent("test_agent")

    orchestrator.register_agent("test", agent)

    await orchestrator.process(Message(role="user", content="Task 1"))
    await orchestrator.process(Message(role="user", content="Task 2"))

    tasks = orchestrator.get_tasks()
    assert len(tasks) == 2
    assert tasks[0].description == "Task 1"
    assert tasks[1].description == "Task 2"


@pytest.mark.asyncio
async def test_orchestrator_task_status_completed():
    """Test that completed tasks have correct status."""
    orchestrator = MultiAgentOrchestrator()
    agent = MockAgent("test_agent", "Success")

    orchestrator.register_agent("test", agent)

    await orchestrator.process(Message(role="user", content="Test"))

    tasks = orchestrator.get_tasks()
    assert len(tasks) == 1
    assert tasks[0].status == "completed"
    assert tasks[0].result == "Success"
    assert tasks[0].error is None


@pytest.mark.asyncio
async def test_orchestrator_handles_agent_failure():
    """Test that orchestrator handles agent failures."""
    orchestrator = MultiAgentOrchestrator()
    failing_agent = FailingAgent()
    good_agent = MockAgent("good_agent", "Success")

    orchestrator.register_agent("failing", failing_agent)
    orchestrator.register_agent("good", good_agent)

    result = await orchestrator.process(Message(role="user", content="Test"))

    # Check that both agents ran
    assert "Failed" in result.content
    assert "Success" in result.content

    # Check task statuses
    tasks = orchestrator.get_tasks()
    assert len(tasks) == 2

    failed_tasks = [t for t in tasks if t.status == "failed"]
    completed_tasks = [t for t in tasks if t.status == "completed"]

    assert len(failed_tasks) == 1
    assert len(completed_tasks) == 1
    assert "Simulated failure" in failed_tasks[0].error


@pytest.mark.asyncio
async def test_orchestrator_empty_agent_list():
    """Test processing with no registered agents."""
    orchestrator = MultiAgentOrchestrator()

    result = await orchestrator.process(Message(role="user", content="Test"))

    # Should return empty result
    assert result.content == ""
    assert len(orchestrator.get_tasks()) == 0


def test_orchestrator_get_tasks_returns_copy():
    """Test that get_tasks returns a copy."""
    orchestrator = MultiAgentOrchestrator()
    task = AgentTask(agent_name="test", description="Test")
    orchestrator.tasks.append(task)

    tasks = orchestrator.get_tasks()
    tasks.append(AgentTask(agent_name="other", description="Other"))

    # Original should be unchanged
    assert len(orchestrator.tasks) == 1


# ============================================================================
# ConsensusAgent Tests
# ============================================================================


def test_consensus_agent_creation():
    """Test creating a ConsensusAgent."""
    consensus = ConsensusAgent()

    assert consensus.name == "ConsensusAgent"
    assert consensus.voting_strategy == "majority"
    assert len(consensus.agents) == 0


def test_consensus_agent_with_strategy():
    """Test creating consensus agent with custom strategy."""
    consensus = ConsensusAgent(voting_strategy="unanimous")

    assert consensus.voting_strategy == "unanimous"


def test_consensus_agent_add_agent():
    """Test adding an agent to consensus group."""
    consensus = ConsensusAgent()
    agent = MockAgent("test_agent")

    consensus.add_agent(agent)

    assert len(consensus.agents) == 1
    assert consensus.agents[0] == agent


def test_consensus_agent_add_multiple_agents():
    """Test adding multiple agents."""
    consensus = ConsensusAgent()
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    agent3 = MockAgent("agent3")

    consensus.add_agent(agent1)
    consensus.add_agent(agent2)
    consensus.add_agent(agent3)

    assert len(consensus.agents) == 3


@pytest.mark.asyncio
async def test_consensus_agent_process_single_agent():
    """Test consensus with a single agent."""
    consensus = ConsensusAgent()
    agent = MockAgent("test_agent", "Single response")

    consensus.add_agent(agent)

    result = await consensus.process(Message(role="user", content="Test"))

    assert "Consensus from 1 agents" in result.content
    assert "Single response" in result.content


@pytest.mark.asyncio
async def test_consensus_agent_process_multiple_agents():
    """Test consensus with multiple agents."""
    consensus = ConsensusAgent()
    agent1 = MockAgent("agent1", "Response 1")
    agent2 = MockAgent("agent2", "Response 2")
    agent3 = MockAgent("agent3", "Response 3")

    consensus.add_agent(agent1)
    consensus.add_agent(agent2)
    consensus.add_agent(agent3)

    result = await consensus.process(Message(role="user", content="Test"))

    assert "Consensus from 3 agents" in result.content
    assert "Response 1" in result.content
    assert "Response 2" in result.content
    assert "Response 3" in result.content


@pytest.mark.asyncio
async def test_consensus_agent_formats_responses():
    """Test that consensus agent formats responses correctly."""
    consensus = ConsensusAgent()
    consensus.add_agent(MockAgent("agent1", "First"))
    consensus.add_agent(MockAgent("agent2", "Second"))

    result = await consensus.process(Message(role="user", content="Test"))

    # Check formatting
    assert "Agent 1:" in result.content
    assert "Agent 2:" in result.content


@pytest.mark.asyncio
async def test_consensus_agent_empty():
    """Test consensus with no agents."""
    consensus = ConsensusAgent()

    result = await consensus.process(Message(role="user", content="Test"))

    assert "Consensus from 0 agents" in result.content


@pytest.mark.asyncio
async def test_consensus_agent_same_message_to_all():
    """Test that all agents receive the same message."""
    consensus = ConsensusAgent()
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    consensus.add_agent(agent1)
    consensus.add_agent(agent2)

    message = Message(role="user", content="Test message")
    await consensus.process(message)

    assert agent1.last_message.content == "Test message"
    assert agent2.last_message.content == "Test message"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_orchestrator_with_consensus():
    """Test using ConsensusAgent within an orchestrator."""
    # Create a consensus agent
    consensus = ConsensusAgent()
    consensus.add_agent(MockAgent("reviewer1", "Looks good"))
    consensus.add_agent(MockAgent("reviewer2", "Approved"))

    # Create orchestrator
    orchestrator = MultiAgentOrchestrator()
    orchestrator.register_agent("consensus", consensus)
    orchestrator.register_agent("writer", MockAgent("writer", "Report written"))

    result = await orchestrator.process(Message(role="user", content="Review report"))

    # Both agents should have run
    assert "Looks good" in result.content
    assert "Approved" in result.content
    assert "Report written" in result.content


@pytest.mark.asyncio
async def test_nested_orchestration():
    """Test orchestrators within orchestrators."""
    # Inner orchestrator
    inner = MultiAgentOrchestrator()
    inner.register_agent("agent1", MockAgent("agent1", "Inner 1"))
    inner.register_agent("agent2", MockAgent("agent2", "Inner 2"))

    # Outer orchestrator
    outer = MultiAgentOrchestrator()
    outer.register_agent("inner_team", inner)
    outer.register_agent("agent3", MockAgent("agent3", "Outer"))

    result = await outer.process(Message(role="user", content="Test"))

    assert "Inner 1" in result.content
    assert "Inner 2" in result.content
    assert "Outer" in result.content
