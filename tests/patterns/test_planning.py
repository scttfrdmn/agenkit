"""
Tests for Planning Agent pattern.
"""

import pytest

from agenkit import Message
from agenkit.patterns import Plan, PlanningAgent, PlanningConfig, PlanStep, StepStatus


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


# ============================================================================
# ErrorTracker integration tests (#653)
# ============================================================================


class MixedOutcomeExecutor:
    """Step executor that fails on specific 0-indexed step numbers.

    Used to exercise ErrorTracker with a known, reproducible mix of
    successes and failures.
    """

    def __init__(self, fail_on_steps: set[int]):
        self.fail_on_steps = fail_on_steps

    async def execute(self, step, context):
        if step.step_number in self.fail_on_steps:
            raise RuntimeError(f"step {step.step_number} failed")
        return f"Completed: {step.description}"


@pytest.mark.asyncio
async def test_planning_agent_error_tracking_disabled_by_default():
    """When enable_error_tracking is absent (default), no tracker is
    populated on the result metadata and record_step is never called
    (behavior unchanged from before #653)."""
    mock_planner = MockPlanningAgent(
        plan_text="""Goal: Test
Steps:
1. Step one
2. Step two
3. Step three"""
    )

    agent = PlanningAgent(PlanningConfig(planner=mock_planner))
    agent.executor = MixedOutcomeExecutor(fail_on_steps={1})

    result = await agent.process(Message(role="user", content="Test"))

    assert "error_tracker" not in result.metadata
    assert agent.error_tracker.enabled is False
    assert agent.error_tracker.total_steps == 0
    assert agent.error_tracker.per_step_error_rate() == 0.0


@pytest.mark.asyncio
async def test_planning_agent_error_tracking_enabled_mixed_outcomes():
    """When enable_error_tracking=True, a multi-step run with a mix of
    successes and failures produces a tracker whose per_step_error_rate()
    matches manual expectation for that specific step sequence."""
    mock_planner = MockPlanningAgent(
        plan_text="""Goal: Test
Steps:
1. Step one
2. Step two
3. Step three
4. Step four"""
    )

    agent = PlanningAgent(PlanningConfig(planner=mock_planner, enable_error_tracking=True))
    # Steps 1 and 3 (0-indexed) fail -> 2 failures out of 4 steps -> p_a = 0.5.
    agent.executor = MixedOutcomeExecutor(fail_on_steps={1, 3})

    result = await agent.process(Message(role="user", content="Test"))

    tracker = result.metadata["error_tracker"]
    assert tracker is agent.error_tracker
    assert tracker.total_steps == 4
    assert tracker.failed_steps == 2
    assert tracker.per_step_error_rate() == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_planning_agent_error_tracking_resets_between_runs():
    """error_tracker is reset at the start of each process() call."""
    mock_planner = MockPlanningAgent(
        plan_text="""Goal: Test
Steps:
1. Step one
2. Step two"""
    )

    agent = PlanningAgent(PlanningConfig(planner=mock_planner, enable_error_tracking=True))
    agent.executor = MixedOutcomeExecutor(fail_on_steps={0})

    await agent.process(Message(role="user", content="First run"))
    assert agent.error_tracker.total_steps == 2
    assert agent.error_tracker.failed_steps == 1

    # Second run: no failures this time.
    agent.executor = MixedOutcomeExecutor(fail_on_steps=set())
    await agent.process(Message(role="user", content="Second run"))

    assert agent.error_tracker.total_steps == 2
    assert agent.error_tracker.failed_steps == 0
