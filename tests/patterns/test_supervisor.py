"""
Tests for SupervisorAgent pattern - hierarchical coordination.

Tests SupervisorAgent, SimplePlanner, and Subtask.
"""

import pytest

from agenkit import Message
from agenkit.patterns.supervisor import SimplePlanner, Subtask, SupervisorAgent

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
        """Process message."""
        self.call_count += 1
        self.last_message = message
        return Message(
            role="assistant",
            content=f"{self._name}: {self.response}",
            metadata={"agent": self._name},
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
# Mock Planners
# ============================================================================


class MockPlanner:
    """Simple mock planner for testing."""

    def __init__(self, subtasks=None, synthesis_response="Synthesized result"):
        self.subtasks = subtasks or []
        self.synthesis_response = synthesis_response
        self.plan_call_count = 0
        self.synthesize_call_count = 0
        self.last_plan_message = None
        self.last_synthesize_original = None
        self.last_synthesize_results = None

    @property
    def name(self):
        return "MockPlanner"

    def capabilities(self):
        return ["planning", "synthesis"]

    async def process(self, message: Message) -> Message:
        """Direct processing (used when no subtasks)."""
        return Message(role="assistant", content="Direct planner response")

    async def plan(self, message: Message) -> list[Subtask]:
        """Return pre-programmed subtasks."""
        self.plan_call_count += 1
        self.last_plan_message = message
        return self.subtasks

    async def synthesize(self, original: Message, results: dict[str, Message]) -> Message:
        """Return pre-programmed synthesis result."""
        self.synthesize_call_count += 1
        self.last_synthesize_original = original
        self.last_synthesize_results = results
        return Message(
            role="assistant", content=self.synthesis_response, metadata={"synthesized": True}
        )


class FailingPlanner:
    """Planner that fails during synthesis."""

    @property
    def name(self):
        return "FailingPlanner"

    def capabilities(self):
        return ["fail"]

    async def process(self, message: Message) -> Message:
        """Process message."""
        return Message(role="assistant", content="response")

    async def plan(self, message: Message) -> list[Subtask]:
        """Return valid subtasks."""
        return [Subtask(type="specialist1", message=Message(role="user", content="task1"))]

    async def synthesize(self, original: Message, results: dict[str, Message]) -> Message:
        """Always raises an error."""
        raise RuntimeError("Synthesis failed")


# ============================================================================
# Subtask Tests
# ============================================================================


def test_subtask_creation():
    """Test basic subtask creation."""
    message = Message(role="user", content="Do something")
    subtask = Subtask(type="coder", message=message)

    assert subtask.type == "coder"
    assert subtask.message is message
    assert subtask.metadata == {}


def test_subtask_with_metadata():
    """Test subtask with custom metadata."""
    message = Message(role="user", content="Do something")
    metadata = {"priority": "high", "timeout": 30}
    subtask = Subtask(type="coder", message=message, metadata=metadata)

    assert subtask.metadata == metadata


# ============================================================================
# SupervisorAgent Creation Tests
# ============================================================================


def test_supervisor_creation():
    """Test basic supervisor creation."""
    planner = MockPlanner()
    specialists = {"coder": MockAgent("coder")}

    supervisor = SupervisorAgent(planner=planner, specialists=specialists)

    assert supervisor._planner is planner
    assert supervisor._specialists == specialists
    assert supervisor.name == "SupervisorAgent"


def test_supervisor_none_planner_raises():
    """Test that None planner raises ValueError."""
    specialists = {"coder": MockAgent("coder")}

    with pytest.raises(ValueError, match=r"Either 'config' or both 'planner' and 'specialists' must be provided"):
        SupervisorAgent(planner=None, specialists=specialists)  # type: ignore


def test_supervisor_empty_specialists_raises():
    """Test that empty specialists dict raises ValueError."""
    planner = MockPlanner()

    with pytest.raises(ValueError, match="at least one specialist is required"):
        SupervisorAgent(planner=planner, specialists={})


def test_supervisor_multiple_specialists():
    """Test supervisor with multiple specialists."""
    planner = MockPlanner()
    specialists = {
        "coder": MockAgent("coder"),
        "tester": MockAgent("tester"),
        "reviewer": MockAgent("reviewer"),
    }

    supervisor = SupervisorAgent(planner=planner, specialists=specialists)

    assert len(supervisor._specialists) == 3


# ============================================================================
# SupervisorAgent Capabilities Tests
# ============================================================================


def test_supervisor_capabilities_combined():
    """Test that capabilities are combined from planner and specialists."""
    planner = MockPlanner()
    coder = MockAgent("coder", capabilities=["code"])
    tester = MockAgent("tester", capabilities=["test"])

    supervisor = SupervisorAgent(planner=planner, specialists={"coder": coder, "tester": tester})
    caps = supervisor.capabilities()

    # Should have planner, specialist, and supervisor-specific capabilities
    assert "planning" in caps
    assert "synthesis" in caps
    assert "code" in caps
    assert "test" in caps
    assert "supervisor" in caps
    assert "hierarchical" in caps
    assert "coordination" in caps


def test_supervisor_capabilities_deduplication():
    """Test that duplicate capabilities are deduplicated."""
    planner = MockPlanner()
    agent1 = MockAgent("agent1", capabilities=["search"])
    agent2 = MockAgent("agent2", capabilities=["search"])

    supervisor = SupervisorAgent(planner=planner, specialists={"agent1": agent1, "agent2": agent2})
    caps = supervisor.capabilities()

    # "search" should appear only once
    assert caps.count("search") == 1


# ============================================================================
# SupervisorAgent Processing Tests - No Subtasks
# ============================================================================


@pytest.mark.asyncio
async def test_supervisor_no_subtasks_direct_processing():
    """Test that supervisor uses direct processing when no subtasks."""
    # Planner returns empty subtasks list
    planner = MockPlanner(subtasks=[])
    specialist = MockAgent("specialist")

    supervisor = SupervisorAgent(planner=planner, specialists={"specialist": specialist})

    message = Message(role="user", content="input")
    result = await supervisor.process(message)

    # Planner should be called for planning
    assert planner.plan_call_count == 1

    # Direct planner processing should be used
    assert result.content == "Direct planner response"

    # Specialist should not be called
    assert specialist.call_count == 0

    # Synthesize should not be called
    assert planner.synthesize_call_count == 0


# ============================================================================
# SupervisorAgent Processing Tests - Single Subtask
# ============================================================================


@pytest.mark.asyncio
async def test_supervisor_single_subtask():
    """Test supervisor with single subtask."""
    subtask_msg = Message(role="user", content="code this")
    subtask = Subtask(type="coder", message=subtask_msg)

    planner = MockPlanner(subtasks=[subtask])
    coder = MockAgent("coder", response="Code complete")

    supervisor = SupervisorAgent(planner=planner, specialists={"coder": coder})

    message = Message(role="user", content="Build a feature")
    result = await supervisor.process(message)

    # Planner should be called
    assert planner.plan_call_count == 1
    assert planner.synthesize_call_count == 1

    # Specialist should be called
    assert coder.call_count == 1
    assert coder.last_message.content == "code this"

    # Result should be synthesized
    assert result.content == "Synthesized result"

    # Metadata should be added
    assert result.metadata["supervisor_subtasks"] == 1
    assert result.metadata["supervisor_specialists"] == 1


@pytest.mark.asyncio
async def test_supervisor_synthesize_receives_results():
    """Test that planner.synthesize receives specialist results."""
    subtask = Subtask(type="coder", message=Message(role="user", content="task"))
    planner = MockPlanner(subtasks=[subtask])
    coder = MockAgent("coder", response="Done")

    supervisor = SupervisorAgent(planner=planner, specialists={"coder": coder})

    message = Message(role="user", content="input")
    await supervisor.process(message)

    # Synthesize should receive results keyed by type_index
    assert "coder_0" in planner.last_synthesize_results
    result_msg = planner.last_synthesize_results["coder_0"]
    assert "Done" in result_msg.content


# ============================================================================
# SupervisorAgent Processing Tests - Multiple Subtasks
# ============================================================================


@pytest.mark.asyncio
async def test_supervisor_multiple_subtasks():
    """Test supervisor with multiple subtasks."""
    subtasks = [
        Subtask(type="coder", message=Message(role="user", content="write code")),
        Subtask(type="tester", message=Message(role="user", content="test code")),
        Subtask(type="reviewer", message=Message(role="user", content="review code")),
    ]

    planner = MockPlanner(subtasks=subtasks)
    specialists = {
        "coder": MockAgent("coder"),
        "tester": MockAgent("tester"),
        "reviewer": MockAgent("reviewer"),
    }

    supervisor = SupervisorAgent(planner=planner, specialists=specialists)

    message = Message(role="user", content="Build feature")
    result = await supervisor.process(message)

    # All specialists should be called
    assert specialists["coder"].call_count == 1
    assert specialists["tester"].call_count == 1
    assert specialists["reviewer"].call_count == 1

    # Metadata should reflect all subtasks
    assert result.metadata["supervisor_subtasks"] == 3


@pytest.mark.asyncio
async def test_supervisor_execution_order_tracked():
    """Test that execution order is tracked in metadata."""
    subtasks = [
        Subtask(type="coder", message=Message(role="user", content="task1")),
        Subtask(type="tester", message=Message(role="user", content="task2")),
    ]

    planner = MockPlanner(subtasks=subtasks)
    specialists = {"coder": MockAgent("coder"), "tester": MockAgent("tester")}

    supervisor = SupervisorAgent(planner=planner, specialists=specialists)

    message = Message(role="user", content="input")
    result = await supervisor.process(message)

    # Execution order should be tracked
    assert "execution_order" in result.metadata
    order = result.metadata["execution_order"]

    assert len(order) == 2
    assert order[0]["index"] == 0
    assert order[0]["type"] == "coder"
    assert order[0]["specialist"] == "coder"
    assert order[1]["index"] == 1
    assert order[1]["type"] == "tester"
    assert order[1]["specialist"] == "tester"


@pytest.mark.asyncio
async def test_supervisor_multiple_same_specialist():
    """Test supervisor using same specialist for multiple subtasks."""
    subtasks = [
        Subtask(type="coder", message=Message(role="user", content="task1")),
        Subtask(type="coder", message=Message(role="user", content="task2")),
    ]

    planner = MockPlanner(subtasks=subtasks)
    coder = MockAgent("coder")

    supervisor = SupervisorAgent(planner=planner, specialists={"coder": coder})

    message = Message(role="user", content="input")
    await supervisor.process(message)

    # Coder should be called twice
    assert coder.call_count == 2

    # Synthesize should receive both results
    assert "coder_0" in planner.last_synthesize_results
    assert "coder_1" in planner.last_synthesize_results


# ============================================================================
# SupervisorAgent Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_supervisor_none_message_raises():
    """Test that None message raises ValueError."""
    planner = MockPlanner()
    specialist = MockAgent("specialist")

    supervisor = SupervisorAgent(planner=planner, specialists={"specialist": specialist})

    with pytest.raises(ValueError, match="message cannot be None"):
        await supervisor.process(None)  # type: ignore


@pytest.mark.asyncio
async def test_supervisor_unknown_specialist_raises():
    """Test that unknown specialist type raises RuntimeError."""
    subtask = Subtask(type="unknown", message=Message(role="user", content="task"))
    planner = MockPlanner(subtasks=[subtask])

    supervisor = SupervisorAgent(planner=planner, specialists={"coder": MockAgent("coder")})

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="unknown specialist type 'unknown'"):
        await supervisor.process(message)


@pytest.mark.asyncio
async def test_supervisor_specialist_failure_raises():
    """Test that specialist failure raises RuntimeError."""
    subtask = Subtask(type="failing", message=Message(role="user", content="task"))
    planner = MockPlanner(subtasks=[subtask])
    failing = FailingAgent("failing")

    supervisor = SupervisorAgent(planner=planner, specialists={"failing": failing})

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="specialist 'failing' failed"):
        await supervisor.process(message)


@pytest.mark.asyncio
async def test_supervisor_synthesis_failure_raises():
    """Test that synthesis failure raises RuntimeError."""
    planner = FailingPlanner()
    specialist = MockAgent("specialist1")

    supervisor = SupervisorAgent(planner=planner, specialists={"specialist1": specialist})

    message = Message(role="user", content="input")

    with pytest.raises(RuntimeError, match="synthesis failed"):
        await supervisor.process(message)


# ============================================================================
# SimplePlanner Tests
# ============================================================================


def test_simple_planner_creation():
    """Test SimplePlanner creation."""
    agent = MockAgent("base")
    planner = SimplePlanner(agent)

    assert planner._agent is agent
    assert planner.name == "SimplePlanner"


def test_simple_planner_capabilities():
    """Test SimplePlanner combines agent capabilities with planning/synthesis."""
    agent = MockAgent("base", capabilities=["llm", "reasoning"])
    planner = SimplePlanner(agent)

    caps = planner.capabilities()

    # Should have agent capabilities plus planning/synthesis
    assert "llm" in caps
    assert "reasoning" in caps
    assert "planning" in caps
    assert "synthesis" in caps


@pytest.mark.asyncio
async def test_simple_planner_process():
    """Test SimplePlanner direct processing delegates to agent."""
    agent = MockAgent("base", response="Agent response")
    planner = SimplePlanner(agent)

    message = Message(role="user", content="input")
    result = await planner.process(message)

    assert agent.call_count == 1
    assert "Agent response" in result.content


@pytest.mark.asyncio
async def test_simple_planner_plan_returns_empty():
    """Test SimplePlanner.plan returns empty list (basic implementation)."""
    agent = MockAgent("base")
    planner = SimplePlanner(agent)

    message = Message(role="user", content="input")
    subtasks = await planner.plan(message)

    # Basic implementation returns empty
    assert subtasks == []


@pytest.mark.asyncio
async def test_simple_planner_synthesize():
    """Test SimplePlanner.synthesize combines results."""
    agent = MockAgent("base")
    planner = SimplePlanner(agent)

    original = Message(role="user", content="original")
    results = {
        "coder_0": Message(role="assistant", content="Code done"),
        "tester_0": Message(role="assistant", content="Tests pass"),
    }

    result = await planner.synthesize(original, results)

    # Should combine all results
    assert "Synthesis of specialist results" in result.content
    assert "coder_0" in result.content
    assert "Code done" in result.content
    assert "tester_0" in result.content
    assert "Tests pass" in result.content


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_supervisor_full_workflow():
    """Test complete supervisor workflow with SimplePlanner."""
    # Create base agent for planner
    base_agent = MockAgent("base")

    # Create custom planner that returns subtasks
    class WorkflowPlanner(SimplePlanner):
        async def plan(self, message: Message) -> list[Subtask]:
            return [
                Subtask(type="coder", message=Message(role="user", content="write code")),
                Subtask(type="tester", message=Message(role="user", content="test code")),
            ]

    planner = WorkflowPlanner(base_agent)

    # Create specialists
    specialists = {
        "coder": MockAgent("coder", response="Feature implemented"),
        "tester": MockAgent("tester", response="Tests passing"),
    }

    # Create supervisor
    supervisor = SupervisorAgent(planner=planner, specialists=specialists)

    # Execute
    message = Message(role="user", content="Build login feature")
    result = await supervisor.process(message)

    # All specialists should be called
    assert specialists["coder"].call_count == 1
    assert specialists["tester"].call_count == 1

    # Result should be synthesized
    assert "Synthesis of specialist results" in result.content
    assert "Feature implemented" in result.content
    assert "Tests passing" in result.content


@pytest.mark.asyncio
async def test_supervisor_reuse():
    """Test that supervisor can be reused for multiple calls."""
    subtask = Subtask(type="coder", message=Message(role="user", content="task"))
    planner = MockPlanner(subtasks=[subtask])
    coder = MockAgent("coder")

    supervisor = SupervisorAgent(planner=planner, specialists={"coder": coder})

    # First call
    message1 = Message(role="user", content="call1")
    await supervisor.process(message1)

    # Second call
    message2 = Message(role="user", content="call2")
    await supervisor.process(message2)

    # Planner and specialist should have been called twice
    assert planner.plan_call_count == 2
    assert coder.call_count == 2
