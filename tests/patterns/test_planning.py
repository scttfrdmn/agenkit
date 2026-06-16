"""
Tests for Planning Agent pattern.
"""

import pytest

from agenkit import Message
from agenkit.patterns import Plan, PlanningAgent, PlanStep, StepStatus


# Mock Planning Agent
class MockPlanningAgent:
    def __init__(self, plan_text=None):
        self.plan_text = (
            plan_text
            or """Goal: Test goal
Steps:
1. First step
2. Second step
3. Third step"""
        )
        self.call_count = 0
        self.last_message = None
        self.name = "MockPlanningAgent"

    async def process(self, message):
        self.call_count += 1
        self.last_message = message
        return Message(role="assistant", content=self.plan_text)


# ============================================================================
# PlanStep Tests
# ============================================================================


def test_plan_step_can_execute_no_dependencies():
    """Test step can execute when it has no dependencies."""
    step = PlanStep(description="Test", step_number=0)
    assert step.can_execute([])


def test_plan_step_can_execute_met_dependencies():
    """Test step can execute when dependencies are met."""
    step = PlanStep(description="Test", dependencies=[0, 1], step_number=2)
    assert step.can_execute([0, 1, 3])


def test_plan_step_cannot_execute_unmet_dependencies():
    """Test step cannot execute when dependencies are not met."""
    step = PlanStep(description="Test", dependencies=[0, 1], step_number=2)
    assert not step.can_execute([0])


# ============================================================================
# Plan Tests
# ============================================================================


def test_plan_get_next_steps_no_dependencies():
    """Test getting next steps when no dependencies."""
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(description="Step 1", step_number=0),
            PlanStep(description="Step 2", step_number=1),
        ],
    )

    next_steps = plan.get_next_steps()
    assert len(next_steps) == 2


def test_plan_get_next_steps_with_dependencies():
    """Test getting next steps respects dependencies."""
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(description="Step 1", step_number=0),
            PlanStep(description="Step 2", dependencies=[0], step_number=1),
        ],
    )

    next_steps = plan.get_next_steps()
    assert len(next_steps) == 1
    assert next_steps[0].step_number == 0


def test_plan_get_next_steps_after_completion():
    """Test getting next steps after some complete."""
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(description="Step 1", step_number=0, status=StepStatus.COMPLETED),
            PlanStep(description="Step 2", dependencies=[0], step_number=1),
        ],
    )

    next_steps = plan.get_next_steps()
    assert len(next_steps) == 1
    assert next_steps[0].step_number == 1


def test_plan_is_complete_all_completed():
    """Test plan is complete when all steps completed."""
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(description="Step 1", step_number=0, status=StepStatus.COMPLETED),
            PlanStep(description="Step 2", step_number=1, status=StepStatus.COMPLETED),
        ],
    )

    assert plan.is_complete()


def test_plan_is_not_complete_with_pending():
    """Test plan is not complete when steps pending."""
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(description="Step 1", step_number=0, status=StepStatus.COMPLETED),
            PlanStep(description="Step 2", step_number=1, status=StepStatus.PENDING),
        ],
    )

    assert not plan.is_complete()


def test_plan_has_failures():
    """Test detecting failures in plan."""
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(description="Step 1", step_number=0, status=StepStatus.COMPLETED),
            PlanStep(description="Step 2", step_number=1, status=StepStatus.FAILED),
        ],
    )

    assert plan.has_failures()


def test_plan_get_progress():
    """Test calculating plan progress."""
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(description="Step 1", step_number=0, status=StepStatus.COMPLETED),
            PlanStep(description="Step 2", step_number=1, status=StepStatus.PENDING),
            PlanStep(description="Step 3", step_number=2, status=StepStatus.PENDING),
        ],
    )

    progress = plan.get_progress()
    assert abs(progress - 33.33) < 0.1


def test_plan_get_progress_empty():
    """Test progress for empty plan."""
    plan = Plan(goal="Test", steps=[])
    assert plan.get_progress() == 0.0


# ============================================================================
# PlanningAgent Tests
# ============================================================================


@pytest.mark.asyncio
async def test_planning_agent_basic():
    """Test basic planning agent functionality."""
    mock_planner = MockPlanningAgent()

    agent = PlanningAgent(planner=mock_planner, max_steps=10)

    response = await agent.process(Message(role="user", content="Test task"))

    assert "completed" in response.content.lower()
    assert mock_planner.call_count == 1


@pytest.mark.asyncio
async def test_planning_agent_creates_plan():
    """Test that agent creates a plan from planner response."""
    mock_planner = MockPlanningAgent()
    agent = PlanningAgent(planner=mock_planner, max_steps=10)

    await agent.process(Message(role="user", content="Test"))

    plan = agent.get_plan()
    assert plan is not None
    assert plan.goal == "Test goal"
    assert len(plan.steps) == 3


@pytest.mark.asyncio
async def test_planning_agent_executes_steps():
    """Test that agent executes all steps."""
    mock_planner = MockPlanningAgent()

    agent = PlanningAgent(planner=mock_planner)

    await agent.process(Message(role="user", content="Test"))

    plan = agent.get_plan()
    completed = [s for s in plan.steps if s.status == StepStatus.COMPLETED]
    assert len(completed) == 3


@pytest.mark.asyncio
async def test_planning_agent_max_steps():
    """Test max_steps limit."""
    mock_planner = MockPlanningAgent(
        plan_text="""Goal: Test
Steps:
1. Step 1
2. Step 2
3. Step 3
4. Step 4
5. Step 5"""
    )

    agent = PlanningAgent(planner=mock_planner, max_steps=3)

    await agent.process(Message(role="user", content="Test"))

    plan = agent.get_plan()
    assert len(plan.steps) <= 3


@pytest.mark.asyncio
async def test_planning_agent_get_progress():
    """Test getting progress during execution."""
    mock_planner = MockPlanningAgent()

    agent = PlanningAgent(planner=mock_planner)

    await agent.process(Message(role="user", content="Test"))

    progress = agent.get_progress()
    assert progress == 100.0


@pytest.mark.asyncio
async def test_planning_agent_name_property():
    """Test agent name property."""
    mock_planner = MockPlanningAgent()
    agent = PlanningAgent(planner=mock_planner)

    assert agent.name == "PlanningAgent"


@pytest.mark.asyncio
async def test_planning_agent_custom_system_prompt():
    """Test using custom system prompt."""
    mock_planner = MockPlanningAgent()
    custom_prompt = "Custom planning instructions"

    agent = PlanningAgent(planner=mock_planner, system_prompt=custom_prompt)

    await agent.process(Message(role="user", content="Test"))

    # Check that custom prompt was included in the message
    assert mock_planner.last_message is not None
    assert custom_prompt in mock_planner.last_message.content


def test_plan_step_dataclass():
    """Test PlanStep dataclass."""
    step = PlanStep(
        description="Test step",
        dependencies=[0, 1],
        status=StepStatus.PENDING,
        step_number=2,
    )

    assert step.description == "Test step"
    assert step.dependencies == [0, 1]
    assert step.status == StepStatus.PENDING
    assert step.step_number == 2
    assert step.timestamp is not None


def test_plan_dataclass():
    """Test Plan dataclass."""
    plan = Plan(goal="Test goal", steps=[PlanStep(description="Step", step_number=0)])

    assert plan.goal == "Test goal"
    assert len(plan.steps) == 1
    assert plan.created_at is not None
