"""Tests for Plan-and-Solve reasoning technique."""

from typing import Any

import pytest

from agenkit import Message
from agenkit.techniques.reasoning import Plan, PlanAndSolve, PlanStep


class MockLLM:
    """Mock LLM for testing Plan-and-Solve."""

    def __init__(self, responses=None):
        """Initialize with predefined responses."""
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        prompt = "\n".join(m.content for m in messages)
        return Message(role="agent", content=self._respond(prompt))

    def _respond(self, prompt: str) -> str:
        """Return mock response based on call count."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        return "Default response"


@pytest.mark.asyncio
async def test_pas_basic():
    """Test basic Plan-and-Solve functionality."""
    llm = MockLLM(
        responses=[
            "1. Step 1\n2. Step 2\n3. Step 3",  # Planning
            "VALID",  # Validation
            "Result 1",  # Execute step 1
            "Result 2",  # Execute step 2
            "Result 3",  # Execute step 3
        ]
    )

    agent = PlanAndSolve(llm=llm, validate_plan=True)
    response = await agent.process(Message(role="user", content="Test problem"))

    assert response.content == "Result 3"  # Last step result
    assert response.metadata["technique"] == "plan_and_solve"
    assert response.metadata["num_steps"] == 3
    assert response.metadata["validated"]


@pytest.mark.asyncio
async def test_pas_planning_phase():
    """Test plan creation."""
    llm = MockLLM(responses=["1. First step\n2. Second step", "VALID", "Result 1", "Result 2"])

    agent = PlanAndSolve(llm=llm)
    response = await agent.process(Message(role="user", content="Problem"))

    plan_steps = response.metadata["plan_steps"]
    assert len(plan_steps) == 2
    assert "First step" in plan_steps[0]
    assert "Second step" in plan_steps[1]


@pytest.mark.asyncio
async def test_pas_validation():
    """Test plan validation."""
    llm = MockLLM(
        responses=["1. Step A\n2. Step B", "VALID - plan is complete", "Result A", "Result B"]
    )

    agent = PlanAndSolve(llm=llm, validate_plan=True)
    response = await agent.process(Message(role="user", content="Problem"))

    assert response.metadata["validated"]
    assert "VALID" in response.metadata["validation_notes"]


@pytest.mark.asyncio
async def test_pas_no_validation():
    """Test without plan validation."""
    llm = MockLLM(responses=["1. Step 1\n2. Step 2", "Result 1", "Result 2"])

    agent = PlanAndSolve(llm=llm, validate_plan=False)
    response = await agent.process(Message(role="user", content="Problem"))

    # Should not validate
    assert not response.metadata["validated"]
    assert response.metadata["num_steps"] == 2


@pytest.mark.asyncio
async def test_pas_execution_phase():
    """Test step-by-step execution."""
    llm = MockLLM(responses=["1. Add 2+2\n2. Multiply by 3", "VALID", "4", "12"])

    agent = PlanAndSolve(llm=llm)
    response = await agent.process(Message(role="user", content="Calculate"))

    execution_steps = response.metadata["execution_steps"]
    assert len(execution_steps) == 2
    assert execution_steps[0] == "4"
    assert execution_steps[1] == "12"


@pytest.mark.asyncio
async def test_pas_custom_planner():
    """Test with custom planner function."""

    def custom_planner(problem: str) -> Plan:
        steps = [
            PlanStep(description="Custom step 1", order=0),
            PlanStep(description="Custom step 2", order=1),
        ]
        return Plan(steps=steps, problem=problem, validated=True)

    llm = MockLLM(responses=["Result 1", "Result 2"])

    agent = PlanAndSolve(llm=llm, planner=custom_planner, validate_plan=False)
    response = await agent.process(Message(role="user", content="Problem"))

    plan_steps = response.metadata["plan_steps"]
    assert "Custom step 1" in plan_steps[0]
    assert "Custom step 2" in plan_steps[1]


@pytest.mark.asyncio
async def test_pas_custom_solver():
    """Test with custom solver function."""

    def custom_solver(step: PlanStep, previous: list) -> str:
        return f"Custom result for: {step.description}"

    llm = MockLLM(responses=["1. Step A\n2. Step B", "VALID"])

    agent = PlanAndSolve(llm=llm, solver=custom_solver)
    response = await agent.process(Message(role="user", content="Problem"))

    execution_steps = response.metadata["execution_steps"]
    assert "Custom result" in execution_steps[0]
    assert "Step A" in execution_steps[0]


@pytest.mark.asyncio
async def test_pas_replanning():
    """Test replanning when validation fails."""
    llm = MockLLM(
        responses=[
            "1. Bad step",  # Initial plan
            "INVALID - missing details",  # Validation fails
            "1. Better step 1\n2. Better step 2",  # Replan
            "VALID",  # Validation passes
            "Result 1",
            "Result 2",
        ]
    )

    agent = PlanAndSolve(llm=llm, validate_plan=True, allow_replanning=True)
    response = await agent.process(Message(role="user", content="Problem"))

    # Should have replanned and executed
    assert response.metadata["allow_replanning"]
    assert response.metadata["num_steps"] >= 1


@pytest.mark.asyncio
async def test_pas_plan_dataclass():
    """Test Plan dataclass."""
    steps = [PlanStep(description="Step 1", order=0), PlanStep(description="Step 2", order=1)]
    plan = Plan(steps=steps, problem="Test problem", validated=True)

    assert len(plan.steps) == 2
    assert plan.problem == "Test problem"
    assert plan.validated


@pytest.mark.asyncio
async def test_pas_planstep_dataclass():
    """Test PlanStep dataclass."""
    step = PlanStep(description="Test step", order=0, dependencies=[], estimated_complexity=3)

    assert step.description == "Test step"
    assert step.order == 0
    assert step.estimated_complexity == 3
    assert not step.executed
    assert step.result is None


@pytest.mark.asyncio
async def test_pas_metadata():
    """Test metadata completeness."""
    llm = MockLLM(responses=["1. Step X\n2. Step Y", "VALID", "Result X", "Result Y"])

    agent = PlanAndSolve(llm=llm)
    response = await agent.process(Message(role="user", content="Problem"))

    metadata = response.metadata

    # Check all required metadata fields
    assert "technique" in metadata
    assert "plan" in metadata
    assert "plan_steps" in metadata
    assert "execution_steps" in metadata
    assert "num_steps" in metadata
    assert "validated" in metadata
    assert "validation_notes" in metadata
    assert "allow_replanning" in metadata

    # Check types
    assert isinstance(metadata["plan"], Plan)
    assert isinstance(metadata["plan_steps"], list)
    assert isinstance(metadata["execution_steps"], list)
    assert len(metadata["plan_steps"]) == metadata["num_steps"]


@pytest.mark.asyncio
async def test_pas_capabilities():
    """Test agent capabilities reporting."""
    llm = MockLLM()
    agent = PlanAndSolve(llm=llm)

    caps = agent.capabilities

    assert "reasoning" in caps
    assert "planning" in caps
    assert "plan_and_solve" in caps
    assert "strategic_thinking" in caps


@pytest.mark.asyncio
async def test_pas_name():
    """Test agent name."""
    llm = MockLLM()
    agent = PlanAndSolve(llm=llm)

    assert agent.name == "plan_and_solve"


@pytest.mark.asyncio
async def test_pas_with_agent_interface():
    """Test with LLM that uses Agent.process() interface."""

    class MockLLMAgent:
        async def process(self, message: Message) -> Message:
            if "Plan" in message.content or "plan" in message.content:
                return Message(role="assistant", content="1. A\n2. B")
            if "VALID" in message.content or "valid" in message.content:
                return Message(role="assistant", content="VALID")
            return Message(role="assistant", content="Solution")

    llm = MockLLMAgent()
    agent = PlanAndSolve(llm=llm)

    response = await agent.process(Message(role="user", content="Problem"))

    assert response.content
    assert response.metadata["num_steps"] >= 1


@pytest.mark.asyncio
async def test_pas_empty_plan():
    """Test handling of empty plan."""
    llm = MockLLM(
        responses=[
            "",  # Empty plan
            "VALID",
            "Direct solution",
        ]
    )

    agent = PlanAndSolve(llm=llm)
    response = await agent.process(Message(role="user", content="Simple problem"))

    # Should handle gracefully
    assert response.metadata["num_steps"] == 0


@pytest.mark.asyncio
async def test_pas_single_step():
    """Test with single-step plan."""
    llm = MockLLM(responses=["1. Only step", "VALID", "Result"])

    agent = PlanAndSolve(llm=llm)
    response = await agent.process(Message(role="user", content="Simple problem"))

    assert response.content == "Result"
    assert response.metadata["num_steps"] == 1


@pytest.mark.asyncio
async def test_pas_numbering_formats():
    """Test parsing various numbering formats."""
    llm = MockLLM(
        responses=[
            "1) First\n2) Second\n3) Third",  # Parentheses
            "VALID",
            "1",
            "2",
            "3",
        ]
    )

    agent = PlanAndSolve(llm=llm)
    response = await agent.process(Message(role="user", content="Problem"))

    plan_steps = response.metadata["plan_steps"]
    assert len(plan_steps) == 3
    assert "First" in plan_steps[0]
    assert "Second" in plan_steps[1]
    assert "Third" in plan_steps[2]


@pytest.mark.asyncio
async def test_pas_step_dependencies():
    """Test plan steps with dependencies."""
    step1 = PlanStep(description="Step 1", order=0)
    step2 = PlanStep(description="Step 2", order=1, dependencies=[0])
    step3 = PlanStep(description="Step 3", order=2, dependencies=[0, 1])

    Plan(steps=[step1, step2, step3], problem="Test")

    assert len(step2.dependencies) == 1
    assert len(step3.dependencies) == 2
    assert 0 in step3.dependencies


@pytest.mark.asyncio
async def test_pas_step_execution_tracking():
    """Test that step execution is tracked."""
    llm = MockLLM(responses=["1. Step A\n2. Step B", "VALID", "Result A", "Result B"])

    agent = PlanAndSolve(llm=llm)
    response = await agent.process(Message(role="user", content="Problem"))

    plan = response.metadata["plan"]

    # All steps should be marked as executed
    for step in plan.steps:
        assert step.executed
        assert step.result is not None
