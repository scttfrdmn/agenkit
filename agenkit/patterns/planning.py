"""
Planning Agent Pattern

Implements agents that create plans to accomplish complex tasks by breaking
them down into smaller, manageable steps.

A planning agent:
1. Analyzes the task
2. Creates a step-by-step plan
3. Executes each step
4. Adapts the plan if needed
5. Returns the final result

This pattern is useful for:
- Complex multi-step tasks
- Tasks requiring coordination
- Tasks where order matters
- Tasks needing dynamic replanning
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from agenkit import Agent, Message


class StepStatus(Enum):
    """Status of a plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """
    A single step in a plan.

    Attributes:
        description: What this step should accomplish
        dependencies: Step indices that must complete before this step
        status: Current status of the step
        result: Result from executing the step (if completed)
        error: Error message if step failed
        step_number: Position in the plan (0-indexed)
    """

    description: str
    dependencies: list[int] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str | None = None
    step_number: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now())

    def can_execute(self, completed_steps: list[int]) -> bool:
        """Check if this step's dependencies are met."""
        return all(dep in completed_steps for dep in self.dependencies)


@dataclass
class Plan:
    """
    A plan consisting of multiple steps.

    Attributes:
        goal: The overall goal the plan aims to achieve
        steps: List of steps in the plan
        created_at: When the plan was created
        metadata: Additional plan metadata
    """

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_next_steps(self) -> list[PlanStep]:
        """
        Get all steps that can be executed now.

        Returns steps that are pending and have their dependencies met.
        """
        completed = [i for i, step in enumerate(self.steps) if step.status == StepStatus.COMPLETED]

        next_steps = []
        for step in self.steps:
            if step.status == StepStatus.PENDING and step.can_execute(completed):
                next_steps.append(step)

        return next_steps

    def is_complete(self) -> bool:
        """Check if all steps are completed or skipped."""
        return all(step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for step in self.steps)

    def has_failures(self) -> bool:
        """Check if any steps failed."""
        return any(step.status == StepStatus.FAILED for step in self.steps)

    def get_progress(self) -> float:
        """Get completion progress as a percentage."""
        if not self.steps:
            return 0.0

        completed = sum(
            1 for step in self.steps if step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        )
        return (completed / len(self.steps)) * 100


class LLMClient(Protocol):
    """Protocol for LLM clients that can be used with PlanningAgent."""

    async def chat(self, messages: list[Message]) -> Message:
        """Generate a response given conversation history."""
        ...


class StepExecutor(Protocol):
    """Protocol for executing individual plan steps."""

    async def execute(self, step: PlanStep, context: dict[str, Any]) -> Any:
        """
        Execute a plan step.

        Args:
            step: The step to execute
            context: Context from previous steps

        Returns:
            Result of the step execution
        """
        ...


class PlanningAgent(Agent):
    """
    Agent that creates and executes plans for complex tasks.

    The agent uses an LLM to create a plan, then executes each step
    sequentially or in parallel (if dependencies allow).

    Example:
        ```python
        from agenkit.patterns import PlanningAgent

        # Create agent with custom executor
        agent = PlanningAgent(
            llm_client=llm,
            step_executor=my_executor,
            allow_replanning=True
        )

        # Give it a complex task
        result = await agent.process(
            Message(role="user", content="Organize a team event")
        )
        # Agent will create a plan with steps like:
        # 1. Choose date and venue
        # 2. Create invitation list
        # 3. Send invitations
        # 4. Arrange catering
        # etc.
        ```

    Args:
        llm_client: LLM client for plan creation
        step_executor: Executor for individual steps
        max_steps: Maximum steps in a plan (default: 10)
        allow_replanning: Whether to replan on failures (default: False)
        system_prompt: Optional system prompt
    """

    def __init__(
        self,
        llm_client: LLMClient,
        step_executor: StepExecutor | None = None,
        max_steps: int = 10,
        allow_replanning: bool = False,
        system_prompt: str | None = None,
    ):
        self.llm = llm_client
        self.executor = step_executor or DefaultStepExecutor()
        self.max_steps = max_steps
        self.allow_replanning = allow_replanning
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.current_plan: Plan | None = None

    @property
    def name(self) -> str:
        """Return the agent's name."""
        return "PlanningAgent"

    def _default_system_prompt(self) -> str:
        """Generate default system prompt for planning."""
        return f"""You are a planning agent that breaks down complex tasks into steps.

For each task, create a plan with specific, actionable steps.

Format your plan as:
Goal: [overall goal]
Steps:
1. [first step]
2. [second step]
...

Maximum {self.max_steps} steps.

Guidelines:
- Make steps concrete and actionable
- Consider dependencies between steps
- Keep steps focused and achievable
- Include verification steps when appropriate
"""

    async def process(self, message: Message) -> Message:
        """
        Process a task by creating and executing a plan.

        Args:
            message: The task to accomplish

        Returns:
            Message with the final result
        """
        # Create plan
        plan = await self._create_plan(message.content)
        self.current_plan = plan

        # Execute plan
        result = await self._execute_plan(plan)

        return Message(
            role="assistant",
            content=f"Task completed.\n\nGoal: {plan.goal}\n\nSteps completed: {len([s for s in plan.steps if s.status == StepStatus.COMPLETED])}/{len(plan.steps)}\n\nResult: {result}",
        )

    async def _create_plan(self, task: str) -> Plan:
        """
        Create a plan for the given task.

        Args:
            task: The task description

        Returns:
            A Plan object with steps
        """
        # Ask LLM to create a plan
        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=f"Create a plan for: {task}"),
        ]

        response = await self.llm.chat(messages)

        # Parse the plan
        plan = self._parse_plan(response.content, task)

        return plan

    def _parse_plan(self, plan_text: str, goal: str) -> Plan:
        """
        Parse LLM response into a Plan object.

        Expected format:
        Goal: [goal]
        Steps:
        1. [step 1]
        2. [step 2]
        ...
        """
        lines = plan_text.strip().split("\n")

        # Extract goal
        plan_goal = goal
        for line in lines:
            if line.strip().startswith("Goal:"):
                plan_goal = line.split("Goal:", 1)[1].strip()
                break

        # Extract steps
        steps = []
        in_steps_section = False
        step_number = 0

        for line in lines:
            line = line.strip()

            if line.startswith("Steps:"):
                in_steps_section = True
                continue

            if in_steps_section and line:
                # Remove leading numbers and dots
                step_text = line
                for prefix in [
                    f"{step_number + 1}.",
                    f"{step_number + 1})",
                    f"Step {step_number + 1}:",
                ]:
                    if step_text.startswith(prefix):
                        step_text = step_text[len(prefix) :].strip()
                        break

                if step_text and len(steps) < self.max_steps:
                    steps.append(
                        PlanStep(
                            description=step_text,
                            step_number=step_number,
                        )
                    )
                    step_number += 1

        return Plan(goal=plan_goal, steps=steps)

    async def _execute_plan(self, plan: Plan) -> str:
        """
        Execute all steps in the plan.

        Args:
            plan: The plan to execute

        Returns:
            Summary of execution results
        """
        context: dict[str, Any] = {}
        results = []

        while not plan.is_complete():
            # Get next executable steps
            next_steps = plan.get_next_steps()

            if not next_steps:
                # No steps can execute (all blocked or completed)
                if plan.has_failures() and self.allow_replanning:
                    # Try to replan around failures
                    await self._replan(plan)
                    continue
                else:
                    break

            # Execute next steps (for now, sequentially)
            for step in next_steps:
                step.status = StepStatus.IN_PROGRESS

                try:
                    result = await self.executor.execute(step, context)
                    step.result = result
                    step.status = StepStatus.COMPLETED

                    # Add result to context for future steps
                    context[f"step_{step.step_number}_result"] = result
                    results.append(f"Step {step.step_number + 1}: {step.description} ✓")

                except Exception as e:
                    step.error = str(e)
                    step.status = StepStatus.FAILED
                    results.append(f"Step {step.step_number + 1}: {step.description} ✗ ({e})")

        # Generate summary
        summary = "\n".join(results)

        if plan.is_complete():
            summary += f"\n\nPlan completed successfully ({plan.get_progress():.0f}%)"
        elif plan.has_failures():
            summary += f"\n\nPlan failed ({plan.get_progress():.0f}% complete)"
        else:
            summary += f"\n\nPlan partially completed ({plan.get_progress():.0f}%)"

        return summary

    async def _replan(self, failed_plan: Plan) -> None:
        """
        Create a new plan to work around failures.

        Args:
            failed_plan: The plan that has failures
        """
        # Get failed steps
        failed_steps = [step for step in failed_plan.steps if step.status == StepStatus.FAILED]

        if not failed_steps:
            return

        # Ask LLM to create alternative steps
        failed_descriptions = "\n".join(
            [f"- {step.description} (Error: {step.error})" for step in failed_steps]
        )

        messages = [
            Message(role="system", content=self.system_prompt),
            Message(
                role="user",
                content=f"The following steps failed:\n{failed_descriptions}\n\nCreate alternative steps to accomplish the goal: {failed_plan.goal}",
            ),
        ]

        await self.llm.chat(messages)

        # Parse new steps and replace failed ones
        # For simplicity, mark failed steps as skipped
        for step in failed_steps:
            step.status = StepStatus.SKIPPED

    def get_plan(self) -> Plan | None:
        """
        Get the current plan.

        Returns:
            The current Plan, or None if no plan exists
        """
        return self.current_plan

    def get_progress(self) -> float:
        """
        Get current plan progress as a percentage.

        Returns:
            Progress percentage (0-100), or 0 if no plan
        """
        if self.current_plan:
            return self.current_plan.get_progress()
        return 0.0


class DefaultStepExecutor:
    """
    Default step executor that returns mock results.

    In production, replace with an executor that:
    - Uses tools/APIs to accomplish steps
    - Delegates to other agents
    - Interacts with external systems
    """

    async def execute(self, step: PlanStep, context: dict[str, Any]) -> str:
        """Execute a step (mock implementation)."""
        # Mock execution - just return success
        return f"Completed: {step.description}"
