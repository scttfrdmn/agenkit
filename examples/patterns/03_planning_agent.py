"""
Planning Agent Example

Demonstrates how to use PlanningAgent to break down complex tasks into
manageable steps and execute them systematically.

The Planning pattern is useful for:
- Multi-step tasks requiring coordination
- Tasks where order and dependencies matter
- Complex workflows that need tracking
- Tasks that may need replanning on failures

This example uses mock implementations for demonstration.
"""

import asyncio
from typing import List, Dict, Any

from agenkit import Message
from agenkit.patterns import (
    PlanningAgent,
    Plan,
    PlanStep,
    StepStatus,
    StepExecutor,
)


# ============================================================================
# Mock LLM for Planning
# ============================================================================


class MockPlanningLLM:
    """Mock LLM that generates plans."""

    async def chat(self, messages: List[Message]) -> Message:
        """Generate mock plans based on the task."""
        user_message = [msg for msg in messages if msg.role == "user"][-1].content

        if "organize" in user_message.lower() and "event" in user_message.lower():
            return Message(
                role="assistant",
                content="""Goal: Organize a successful team event

Steps:
1. Choose date and venue
2. Create invitation list
3. Send invitations
4. Arrange catering
5. Confirm attendees""",
            )

        elif "deploy" in user_message.lower() or "website" in user_message.lower():
            return Message(
                role="assistant",
                content="""Goal: Deploy website to production

Steps:
1. Run tests
2. Build production assets
3. Create database backup
4. Deploy to staging
5. Run smoke tests
6. Deploy to production""",
            )

        elif "research" in user_message.lower():
            return Message(
                role="assistant",
                content="""Goal: Complete research project

Steps:
1. Review existing literature
2. Design research methodology
3. Collect data
4. Analyze results
5. Write report""",
            )

        # Default plan
        return Message(
            role="assistant",
            content="""Goal: Complete the task

Steps:
1. Break down the task
2. Execute each part
3. Verify results""",
        )


# ============================================================================
# Custom Step Executors
# ============================================================================


class MockStepExecutor:
    """Mock executor with custom logic."""

    def __init__(self, fail_steps: List[int] = None):
        self.fail_steps = fail_steps or []
        self.execution_log = []

    async def execute(self, step: PlanStep, context: Dict[str, Any]) -> str:
        """Execute a step with optional failures."""
        self.execution_log.append(f"Executing step {step.step_number}: {step.description}")

        # Simulate failures for testing
        if step.step_number in self.fail_steps:
            raise RuntimeError(f"Step {step.step_number} failed (simulated)")

        # Simulate execution delay
        await asyncio.sleep(0.1)

        return f"Completed: {step.description}"


# ============================================================================
# Example Functions
# ============================================================================


async def basic_planning_example():
    """Demonstrate basic planning functionality."""
    print("=" * 60)
    print("Example 1: Basic Planning")
    print("=" * 60)

    llm = MockPlanningLLM()
    agent = PlanningAgent(llm_client=llm, max_steps=10)

    print("\nTask: Organize a team event")
    result = await agent.process(Message(role="user", content="Organize a team event"))

    print(f"\n{result.content}")

    # Show the plan details
    plan = agent.get_plan()
    if plan:
        print(f"\nPlan created with {len(plan.steps)} steps")
        print(f"Progress: {plan.get_progress():.0f}%")


async def plan_structure_example():
    """Demonstrate plan structure and step management."""
    print("\n" + "=" * 60)
    print("Example 2: Plan Structure")
    print("=" * 60)

    # Create a plan manually
    plan = Plan(
        goal="Deploy website to production",
        steps=[
            PlanStep(description="Run tests", step_number=0),
            PlanStep(description="Build assets", step_number=1, dependencies=[0]),
            PlanStep(description="Deploy to staging", step_number=2, dependencies=[1]),
            PlanStep(description="Run smoke tests", step_number=3, dependencies=[2]),
            PlanStep(description="Deploy to production", step_number=4, dependencies=[3]),
        ],
    )

    print(f"\nGoal: {plan.goal}")
    print(f"Total steps: {len(plan.steps)}")

    # Show dependencies
    print("\nStep dependencies:")
    for step in plan.steps:
        deps = ", ".join([str(d) for d in step.dependencies]) if step.dependencies else "None"
        print(f"  Step {step.step_number}: {step.description} (depends on: {deps})")

    # Simulate execution
    print("\nSimulating execution...")
    completed = []
    while not plan.is_complete():
        next_steps = plan.get_next_steps()
        if not next_steps:
            break

        for step in next_steps:
            step.status = StepStatus.COMPLETED
            completed.append(step.step_number)
            print(f"  ✓ Completed step {step.step_number}: {step.description}")

    print(f"\nFinal progress: {plan.get_progress():.0f}%")


async def custom_executor_example():
    """Demonstrate using a custom step executor."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Step Executor")
    print("=" * 60)

    llm = MockPlanningLLM()
    executor = MockStepExecutor()

    agent = PlanningAgent(llm_client=llm, step_executor=executor, max_steps=10)

    print("\nTask: Complete research project")
    result = await agent.process(Message(role="user", content="Complete research project"))

    print(f"\n{result.content}")

    # Show execution log
    print("\nExecution log:")
    for log_entry in executor.execution_log:
        print(f"  - {log_entry}")


async def failure_handling_example():
    """Demonstrate handling step failures."""
    print("\n" + "=" * 60)
    print("Example 4: Failure Handling")
    print("=" * 60)

    llm = MockPlanningLLM()
    # Make step 2 fail
    executor = MockStepExecutor(fail_steps=[2])

    agent = PlanningAgent(llm_client=llm, step_executor=executor, max_steps=10)

    print("\nTask: Deploy website (with simulated failure)")
    result = await agent.process(Message(role="user", content="Deploy website"))

    print(f"\n{result.content}")

    # Show which steps failed
    plan = agent.get_plan()
    if plan:
        print("\nStep status:")
        for step in plan.steps:
            status_icon = {
                StepStatus.COMPLETED: "✓",
                StepStatus.FAILED: "✗",
                StepStatus.PENDING: "○",
                StepStatus.SKIPPED: "⊘",
            }.get(step.status, "?")

            print(f"  {status_icon} Step {step.step_number}: {step.description}")
            if step.error:
                print(f"    Error: {step.error}")


async def progress_tracking_example():
    """Demonstrate progress tracking."""
    print("\n" + "=" * 60)
    print("Example 5: Progress Tracking")
    print("=" * 60)

    llm = MockPlanningLLM()
    executor = MockStepExecutor()

    agent = PlanningAgent(llm_client=llm, step_executor=executor, max_steps=10)

    print("\nTask: Organize team event")
    print("Tracking progress...\n")

    # Start execution in background
    task = asyncio.create_task(
        agent.process(Message(role="user", content="Organize team event"))
    )

    # Monitor progress
    last_progress = 0
    while not task.done():
        progress = agent.get_progress()
        if progress != last_progress:
            print(f"Progress: {progress:.0f}%")
            last_progress = progress
        await asyncio.sleep(0.05)

    result = await task
    print(f"\nCompleted! Final progress: {agent.get_progress():.0f}%")


async def main():
    """Run all examples."""
    await basic_planning_example()
    await plan_structure_example()
    await custom_executor_example()
    await failure_handling_example()
    await progress_tracking_example()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. PlanningAgent breaks complex tasks into steps")
    print("2. Plans support dependencies between steps")
    print("3. Custom executors handle actual step execution")
    print("4. Failures can be tracked and handled")
    print("5. Progress can be monitored in real-time")
    print("\nNext Steps:")
    print("- Replace MockPlanningLLM with real LLM")
    print("- Implement custom executors for your domain")
    print("- Add replanning logic for adaptive plans")
    print("- Integrate with ReActAgent for tool-using steps")
    print("- Add parallel execution for independent steps")


if __name__ == "__main__":
    asyncio.run(main())
