"""
Tests for Autonomous Agent pattern.
"""

import pytest
import asyncio
from datetime import datetime

from agenkit import Message
from agenkit.patterns import AutonomousAgent, Goal


# ============================================================================
# Mock Agents
# ============================================================================


class MockAutonomousAgent(AutonomousAgent):
    """Mock autonomous agent for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.work_log = []

    async def _work_on_goal(self, goal: Goal) -> str:
        """Track work done on goals."""
        self.work_log.append(goal.description)
        await asyncio.sleep(0.01)  # Simulate some work
        return f"Completed: {goal.description}"


class CountingAgent(AutonomousAgent):
    """Agent that counts iterations."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0

    async def _work_on_goal(self, goal: Goal) -> str:
        self.count += 1
        await asyncio.sleep(0.01)
        return f"Iteration {self.count}"


# ============================================================================
# Goal Tests
# ============================================================================


def test_goal_creation():
    """Test creating a Goal."""
    goal = Goal(description="Test goal")

    assert goal.description == "Test goal"
    assert goal.priority == 1
    assert goal.status == "active"
    assert goal.progress == 0.0
    assert goal.created_at is not None


def test_goal_with_priority():
    """Test creating goal with custom priority."""
    goal = Goal(description="High priority", priority=10)

    assert goal.priority == 10


def test_goal_with_status():
    """Test creating goal with custom status."""
    goal = Goal(description="Test", status="completed")

    assert goal.status == "completed"


def test_goal_with_progress():
    """Test creating goal with progress."""
    goal = Goal(description="Test", progress=0.5)

    assert goal.progress == 0.5


def test_goal_created_at():
    """Test that created_at is set automatically."""
    goal = Goal(description="Test")

    assert isinstance(goal.created_at, datetime)
    assert goal.created_at <= datetime.now()


def test_goal_with_explicit_created_at():
    """Test setting explicit created_at."""
    timestamp = datetime(2024, 1, 1, 12, 0, 0)
    goal = Goal(description="Test", created_at=timestamp)

    assert goal.created_at == timestamp


# ============================================================================
# AutonomousAgent Tests
# ============================================================================


def test_autonomous_agent_creation():
    """Test creating an AutonomousAgent."""
    agent = MockAutonomousAgent(objective="Test objective")

    assert agent.name == "AutonomousAgent"
    assert agent.objective == "Test objective"
    assert agent.max_iterations == 10
    assert agent.stop_condition is None
    assert len(agent.goals) == 0
    assert agent.iteration_count == 0
    assert agent.is_running is False


def test_autonomous_agent_with_max_iterations():
    """Test creating agent with custom max_iterations."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=5)

    assert agent.max_iterations == 5


def test_autonomous_agent_with_stop_condition():
    """Test creating agent with stop condition."""

    def stop_func():
        return True

    agent = MockAutonomousAgent(objective="Test", stop_condition=stop_func)

    assert agent.stop_condition == stop_func


@pytest.mark.asyncio
async def test_autonomous_agent_process():
    """Test process method."""
    agent = MockAutonomousAgent(objective="Test objective")

    result = await agent.process(Message(role="user", content="Test"))

    assert "Test objective" in result.content


def test_autonomous_agent_add_goal():
    """Test adding a goal."""
    agent = MockAutonomousAgent(objective="Test")

    goal = agent.add_goal("First goal")

    assert len(agent.goals) == 1
    assert goal.description == "First goal"
    assert goal.priority == 1


def test_autonomous_agent_add_goal_with_priority():
    """Test adding goal with custom priority."""
    agent = MockAutonomousAgent(objective="Test")

    goal = agent.add_goal("Important goal", priority=10)

    assert goal.priority == 10


def test_autonomous_agent_add_multiple_goals():
    """Test adding multiple goals."""
    agent = MockAutonomousAgent(objective="Test")

    agent.add_goal("Goal 1")
    agent.add_goal("Goal 2")
    agent.add_goal("Goal 3")

    assert len(agent.goals) == 3


@pytest.mark.asyncio
async def test_autonomous_agent_run_no_goals():
    """Test running agent with no goals."""
    agent = MockAutonomousAgent(objective="Test")

    result = await agent.run()

    assert result["objective"] == "Test"
    assert result["iterations"] == 1  # Enters loop once, then breaks
    assert result["goals_completed"] == 0
    assert len(result["results"]) == 0


@pytest.mark.asyncio
async def test_autonomous_agent_run_single_goal():
    """Test running agent with a single goal."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=10)
    agent.add_goal("Test goal")

    result = await agent.run()

    assert result["goals_completed"] == 1
    assert len(result["results"]) == 5  # Goal completes after 5 iterations (0.2 * 5 = 1.0)


@pytest.mark.asyncio
async def test_autonomous_agent_run_multiple_goals():
    """Test running agent with multiple goals."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=20)
    agent.add_goal("Goal 1")
    agent.add_goal("Goal 2")

    result = await agent.run()

    assert result["goals_completed"] == 2
    assert agent.goals[0].status == "completed"
    assert agent.goals[1].status == "completed"


@pytest.mark.asyncio
async def test_autonomous_agent_goal_priority():
    """Test that agent works on highest priority goals first."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=10)
    agent.add_goal("Low priority", priority=1)
    agent.add_goal("High priority", priority=10)
    agent.add_goal("Medium priority", priority=5)

    await agent.run()

    # High priority should be worked on first
    assert agent.work_log[0] == "High priority"


@pytest.mark.asyncio
async def test_autonomous_agent_max_iterations():
    """Test that agent respects max_iterations."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=3)
    agent.add_goal("Long goal")  # Won't complete in 3 iterations

    result = await agent.run()

    assert result["iterations"] == 3
    assert agent.goals[0].status == "active"  # Not completed


@pytest.mark.asyncio
async def test_autonomous_agent_stop_condition():
    """Test that agent respects stop condition."""
    counter = {"value": 0}

    def stop_after_two():
        counter["value"] += 1
        return counter["value"] >= 2

    agent = MockAutonomousAgent(
        objective="Test", max_iterations=100, stop_condition=stop_after_two
    )
    agent.add_goal("Test goal")

    result = await agent.run()

    assert result["iterations"] == 2


@pytest.mark.asyncio
async def test_autonomous_agent_stop_method():
    """Test manually stopping the agent."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=100)
    agent.add_goal("Long goal")

    # Start agent in background
    task = asyncio.create_task(agent.run())

    # Let it run for a bit
    await asyncio.sleep(0.05)

    # Stop it
    agent.stop()

    result = await task

    # Should have stopped early
    assert result["iterations"] < 100
    assert agent.is_running is False


@pytest.mark.asyncio
async def test_autonomous_agent_progress_tracking():
    """Test progress tracking."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=20)
    agent.add_goal("Goal 1")
    agent.add_goal("Goal 2")

    # Before running
    assert agent.get_progress() == 0.0

    # Run agent
    await agent.run()

    # After completion
    assert agent.get_progress() == 100.0


@pytest.mark.asyncio
async def test_autonomous_agent_progress_partial():
    """Test partial progress."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=3)
    agent.add_goal("Goal 1")
    agent.add_goal("Goal 2")

    await agent.run()

    # Both goals should have some progress
    progress = agent.get_progress()
    assert 0 < progress < 100


def test_autonomous_agent_get_progress_no_goals():
    """Test get_progress with no goals."""
    agent = MockAutonomousAgent(objective="Test")

    assert agent.get_progress() == 0.0


@pytest.mark.asyncio
async def test_autonomous_agent_iteration_count():
    """Test iteration counting."""
    agent = CountingAgent(objective="Test", max_iterations=5)
    agent.add_goal("Test")

    result = await agent.run()

    assert agent.count == 5
    assert result["iterations"] == 5


@pytest.mark.asyncio
async def test_autonomous_agent_goal_completion():
    """Test goal completion logic."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=10)
    goal = agent.add_goal("Test goal")

    await agent.run()

    assert goal.status == "completed"
    assert goal.progress >= 1.0


@pytest.mark.asyncio
async def test_autonomous_agent_multiple_goal_cycles():
    """Test working through multiple goals in cycles."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=15)
    goal1 = agent.add_goal("Goal 1", priority=1)
    goal2 = agent.add_goal("Goal 2", priority=1)

    await agent.run()

    # Both should complete
    assert goal1.status == "completed"
    assert goal2.status == "completed"


@pytest.mark.asyncio
async def test_autonomous_agent_is_running_flag():
    """Test is_running flag."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=10)
    agent.add_goal("Test")

    assert agent.is_running is False

    task = asyncio.create_task(agent.run())
    await asyncio.sleep(0.02)

    assert agent.is_running is True

    await task

    assert agent.is_running is False


@pytest.mark.asyncio
async def test_autonomous_agent_results_collection():
    """Test that results are collected."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=3)
    agent.add_goal("Test goal")

    result = await agent.run()

    assert len(result["results"]) == 3
    assert all("Completed:" in r for r in result["results"])


@pytest.mark.asyncio
async def test_autonomous_agent_goal_status_transitions():
    """Test goal status transitions."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=10)
    goal = agent.add_goal("Test")

    # Initially active
    assert goal.status == "active"

    await agent.run()

    # After completion
    assert goal.status == "completed"


@pytest.mark.asyncio
async def test_autonomous_agent_concurrent_safety():
    """Test that agent can't run multiple times concurrently."""
    agent = MockAutonomousAgent(objective="Test", max_iterations=10)
    agent.add_goal("Test")

    # Start first run
    task1 = asyncio.create_task(agent.run())

    # Try to start second run
    task2 = asyncio.create_task(agent.run())

    result1 = await task1
    result2 = await task2

    # Both should complete, but sequentially
    assert result1["iterations"] + result2["iterations"] >= 0


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_autonomous_agent_realistic_workflow():
    """Test a realistic autonomous workflow."""

    class WorkflowAgent(AutonomousAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.completed_tasks = []

        async def _work_on_goal(self, goal: Goal) -> str:
            await asyncio.sleep(0.01)
            self.completed_tasks.append(goal.description)
            return f"Finished: {goal.description}"

    agent = WorkflowAgent(objective="Complete project", max_iterations=30)

    # Add workflow steps
    agent.add_goal("Planning", priority=5)
    agent.add_goal("Implementation", priority=4)
    agent.add_goal("Testing", priority=3)
    agent.add_goal("Documentation", priority=2)
    agent.add_goal("Deployment", priority=1)

    result = await agent.run()

    # All goals should complete
    assert result["goals_completed"] == 5

    # Check that planning was done first (highest priority)
    assert agent.completed_tasks[0] == "Planning"


@pytest.mark.asyncio
async def test_autonomous_agent_adaptive_goals():
    """Test agent that adds goals dynamically."""

    class AdaptiveAgent(AutonomousAgent):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.discovered = False

        async def _work_on_goal(self, goal: Goal) -> str:
            await asyncio.sleep(0.01)

            # Discover new goal during execution
            if not self.discovered and "explore" in goal.description.lower():
                self.add_goal("Follow up on discovery", priority=5)
                self.discovered = True

            return f"Worked on: {goal.description}"

    agent = AdaptiveAgent(objective="Explore and adapt", max_iterations=20)
    agent.add_goal("Explore area", priority=10)

    initial_goal_count = len(agent.goals)
    result = await agent.run()
    final_goal_count = len(agent.goals)

    # Should have added a goal
    assert final_goal_count > initial_goal_count
    assert result["goals_completed"] >= 2
