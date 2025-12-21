"""
Plan-and-Solve Prompting Technique

Explicitly separates planning (devising a solution strategy) from solving
(executing the strategy). Creates more structured reasoning than pure CoT
by forcing an upfront planning phase.

This technique is particularly effective for complex problems that benefit
from strategic planning before execution.

References:
    - Paper: https://arxiv.org/abs/2305.04091
    - "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning"
    - Effective for math word problems, commonsense reasoning, symbolic reasoning

Example:
    Basic usage::

        from agenkit.techniques.reasoning import PlanAndSolve
        from agenkit import Message

        agent = PlanAndSolve(llm=my_llm, validate_plan=True)

        response = await agent.process(Message(
            role="user",
            content="Plan a surprise birthday party for 20 people"
        ))

        # Access plan and execution details
        print(response.metadata['plan'])
        print(response.metadata['execution_steps'])
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from agenkit import Agent, Message


@dataclass
class PlanStep:
    """Represents a single step in a plan."""

    description: str
    order: int
    dependencies: list[int] = field(default_factory=list)
    estimated_complexity: int = 1  # 1-5 scale
    result: str | None = None
    executed: bool = False


@dataclass
class Plan:
    """Represents a complete solution plan."""

    steps: list[PlanStep]
    problem: str
    strategy: str | None = None
    validated: bool = False
    validation_notes: str | None = None

    def __post_init__(self):
        if not self.steps:
            self.steps = []


class PlanAndSolve(Agent):
    """
    Plan-and-Solve prompting technique.

    Separates the reasoning process into two distinct phases:
    1. Planning: Devise a detailed solution strategy upfront
    2. Solving: Execute the plan step-by-step

    This technique is particularly effective for:
    - Complex multi-step problems
    - Problems requiring strategic thinking
    - Tasks where planning improves execution quality
    - Math word problems and reasoning tasks

    Attributes:
        name: Agent name (always "plan_and_solve")
        llm: LLM client for generating responses
        planner: Custom planning function
        solver: Custom solver function
        validate_plan: Whether to validate plans before execution
        allow_replanning: Whether to replan on execution failure
    """

    def __init__(
        self,
        llm,  # LLMClient - type hint omitted for flexibility
        planner: Callable[[str], Plan] | None = None,
        solver: Callable[[PlanStep, list[str]], str] | None = None,
        validate_plan: bool = True,
        allow_replanning: bool = False,
    ):
        """
        Initialize Plan-and-Solve agent.

        Args:
            llm: LLM client for generating responses. Must have a `complete()`
                or `process()` method that returns text.
            planner: Optional custom function to create plans (str -> Plan).
                If None, uses LLM to generate plans.
            solver: Optional custom function to execute plan steps
                (PlanStep, List[str] -> str). If None, uses LLM.
            validate_plan: Whether to validate plans before execution.
                Default True.
            allow_replanning: Whether to allow replanning if execution fails.
                Default False.

        Example:
            >>> agent = PlanAndSolve(
            ...     llm=my_llm,
            ...     validate_plan=True,
            ...     allow_replanning=False
            ... )
        """
        self.llm = llm
        self.planner = planner
        self.solver = solver
        self.validate_plan_flag = validate_plan
        self.allow_replanning = allow_replanning

    @property
    def name(self) -> str:
        """Return agent name."""
        return "plan_and_solve"

    async def _llm_call(self, prompt: str) -> str:
        """
        Call LLM with prompt.

        Args:
            prompt: Prompt to send to LLM

        Returns:
            LLM response text
        """
        if hasattr(self.llm, "complete"):
            return await self.llm.complete(prompt)
        elif hasattr(self.llm, "process"):
            response = await self.llm.process(Message(role="user", content=prompt))
            return response.content
        else:
            raise AttributeError("LLM must have either complete() or process() method")

    async def create_plan(self, problem: str) -> Plan:
        """
        Create a solution plan for the problem.

        Args:
            problem: Problem to create plan for

        Returns:
            Plan object with steps ordered for execution
        """
        if self.planner:
            # Use custom planner
            return self.planner(problem)

        # Use LLM to create plan
        planning_prompt = f"""Create a detailed step-by-step plan to solve this problem.
List each step on a separate line, numbered 1, 2, 3, etc.
Focus on WHAT needs to be done, not HOW to do it yet.

Problem: {problem}

Solution Plan:"""

        response = await self._llm_call(planning_prompt)

        # Parse plan from response
        steps = []
        lines = response.strip().split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Remove numbering (1., 1), etc.)
            import re
            cleaned = re.sub(r'^\d+[\\.)]\\s*', '', line)

            if cleaned:
                steps.append(
                    PlanStep(
                        description=cleaned,
                        order=i,
                        estimated_complexity=1
                    )
                )

        return Plan(steps=steps, problem=problem)

    async def validate(self, plan: Plan) -> Plan:
        """
        Validate that a plan is complete and feasible.

        Args:
            plan: Plan to validate

        Returns:
            Validated plan (may be modified)
        """
        validation_prompt = f"""Review this solution plan for completeness and feasibility.
Is this plan sufficient to solve the problem? Are there any missing steps or issues?

Problem: {plan.problem}

Plan:
{self._format_plan(plan)}

Validation (answer "VALID" or describe issues):"""

        response = await self._llm_call(validation_prompt)

        # Check if plan is valid
        is_valid = "VALID" in response.upper() or "YES" in response.upper()

        plan.validated = is_valid
        plan.validation_notes = response.strip()

        return plan

    def _format_plan(self, plan: Plan) -> str:
        """Format plan for display."""
        lines = []
        for i, step in enumerate(plan.steps, 1):
            status = "✓" if step.executed else "○"
            lines.append(f"{i}. [{status}] {step.description}")
        return "\\n".join(lines)

    async def execute_step(
        self,
        step: PlanStep,
        previous_results: list[str]
    ) -> str:
        """
        Execute a single plan step.

        Args:
            step: Plan step to execute
            previous_results: Results from previous steps

        Returns:
            Result of executing this step
        """
        if self.solver:
            # Use custom solver
            return self.solver(step, previous_results)

        # Use LLM to execute step
        if previous_results:
            context = "\\n".join([
                f"Previous step {i+1} result: {result}"
                for i, result in enumerate(previous_results)
            ])

            prompt = f"""Execute this step of the plan, using previous results as context.

Previous Results:
{context}

Current Step: {step.description}

Execution Result:"""
        else:
            prompt = f"""Execute this step of the plan:

Step: {step.description}

Execution Result:"""

        result = await self._llm_call(prompt)
        return result.strip()

    async def execute_plan(self, plan: Plan) -> list[str]:
        """
        Execute all steps in the plan sequentially.

        Args:
            plan: Plan to execute

        Returns:
            List of results from each step
        """
        results = []

        for step in plan.steps:
            result = await self.execute_step(step, results)
            step.result = result
            step.executed = True
            results.append(result)

        return results

    async def process(self, message: Message) -> Message:
        """
        Process message with Plan-and-Solve prompting.

        Creates a plan first, validates it (if enabled), then executes
        the plan step-by-step.

        Args:
            message: Input message with problem

        Returns:
            Message with final solution and metadata. Metadata includes:
                - plan: The solution plan
                - plan_steps: List of plan step descriptions
                - execution_steps: List of execution results
                - validated: Whether plan was validated
                - strategy: High-level strategy (if identified)
                - technique: Always "plan_and_solve"

        Example:
            >>> response = await agent.process(Message(
            ...     role="user",
            ...     content="Plan a birthday party"
            ... ))
            >>> print(response.metadata['plan_steps'])
            >>> print(response.metadata['execution_steps'])
        """
        problem = message.content

        # Phase 1: Create plan
        plan = await self.create_plan(problem)

        # Phase 2: Validate plan (if enabled)
        if self.validate_plan_flag:
            plan = await self.validate(plan)

            # If validation failed and replanning is allowed
            if not plan.validated and self.allow_replanning:
                # Try to create improved plan based on validation feedback
                improved_prompt = f"""The previous plan had issues. Create an improved plan.

Problem: {problem}

Previous Plan Issues:
{plan.validation_notes}

Improved Plan:"""

                await self._llm_call(improved_prompt)
                plan = await self.create_plan(problem)
                plan = await self.validate(plan)

        # Phase 3: Execute plan
        execution_results = await self.execute_plan(plan)

        # Final solution is the last step's result
        final_solution = execution_results[-1] if execution_results else ""

        return Message(
            role="assistant",
            content=final_solution,
            metadata={
                "technique": "plan_and_solve",
                "plan": plan,
                "plan_steps": [step.description for step in plan.steps],
                "execution_steps": execution_results,
                "num_steps": len(plan.steps),
                "validated": plan.validated,
                "validation_notes": plan.validation_notes,
                "allow_replanning": self.allow_replanning
            }
        )

    @property
    def capabilities(self) -> list[str]:
        """
        Return agent capabilities.

        Returns:
            List of capability strings describing what this agent can do
        """
        return [
            "reasoning",
            "planning",
            "plan_and_solve",
            "strategic_thinking",
            "step_by_step_execution"
        ]
