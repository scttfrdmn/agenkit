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

from agenkit import Message
from agenkit.patterns import (
    Plan,
    PlanningAgent,
    PlanStep,
    StepStatus,
)

# ============================================================================
# Mock Agent for Planning
# ============================================================================


class MockPlanningAgent:
    """
    Mock Agent that generates plans based on tasks.

    In production, replace with real LLM-based agent:
    - OpenAI: from openai import AsyncOpenAI
    - Anthropic: from anthropic import AsyncAnthropic
    - LiteLLM: from litellm import acompletion
    """

    def __init__(self):
        self.call_count = 0
        self.name = "MockPlanningAgent"

    async def process(self, message: Message) -> Message:
        """Generate mock plans based on the task."""
        self.call_count += 1

        # Extract the task from the message content
        content = message.content.lower()

        if "organize" in content and "event" in content:
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

        elif "deploy" in content or "website" in content:
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

        elif "research" in content:
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
# Example Functions
# ============================================================================


async def basic_planning_example():
    """Demonstrate basic planning functionality."""
    print("=" * 60)
    print("Example 1: Basic Planning")
    print("=" * 60)

    planner = MockPlanningAgent()
    agent = PlanningAgent(planner=planner, max_steps=10)

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


async def deployment_plan_example():
    """Demonstrate a deployment planning workflow."""
    print("\n" + "=" * 60)
    print("Example 3: Deployment Planning")
    print("=" * 60)

    planner = MockPlanningAgent()
    agent = PlanningAgent(planner=planner, max_steps=10)

    print("\nTask: Deploy website to production")
    result = await agent.process(Message(role="user", content="Deploy website"))

    print(f"\n{result.content}")

    # Show the plan structure
    plan = agent.get_plan()
    if plan:
        print("\nPlan steps:")
        for step in plan.steps:
            status_icon = {
                StepStatus.COMPLETED: "✓",
                StepStatus.FAILED: "✗",
                StepStatus.PENDING: "○",
                StepStatus.SKIPPED: "⊘",
            }.get(step.status, "?")
            print(f"  {status_icon} Step {step.step_number + 1}: {step.description}")


async def research_plan_example():
    """Demonstrate a research planning workflow."""
    print("\n" + "=" * 60)
    print("Example 4: Research Planning")
    print("=" * 60)

    planner = MockPlanningAgent()
    agent = PlanningAgent(planner=planner, max_steps=10)

    print("\nTask: Complete research project")
    result = await agent.process(Message(role="user", content="Complete research project"))

    print(f"\n{result.content}")

    # Show plan details
    plan = agent.get_plan()
    if plan:
        print(f"\nResearch plan has {len(plan.steps)} phases")
        print(f"All steps completed: {plan.is_complete()}")
        print(f"Progress: {plan.get_progress():.0f}%")


async def progress_tracking_example():
    """Demonstrate progress tracking."""
    print("\n" + "=" * 60)
    print("Example 5: Progress Tracking")
    print("=" * 60)

    planner = MockPlanningAgent()
    agent = PlanningAgent(planner=planner, max_steps=10)

    print("\nTask: Organize team event")
    print("Tracking progress...\n")

    # Start execution in background
    task = asyncio.create_task(agent.process(Message(role="user", content="Organize team event")))

    # Monitor progress
    last_progress = 0
    while not task.done():
        progress = agent.get_progress()
        if progress != last_progress:
            print(f"Progress: {progress:.0f}%")
            last_progress = progress
        await asyncio.sleep(0.05)

    await task
    print(f"\nCompleted! Final progress: {agent.get_progress():.0f}%")


async def main():
    """Run all examples."""
    await basic_planning_example()
    await plan_structure_example()
    await deployment_plan_example()
    await research_plan_example()
    await progress_tracking_example()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. PlanningAgent breaks complex tasks into steps")
    print("2. Plans support dependencies between steps")
    print("3. Step execution is handled automatically")
    print("4. Progress can be monitored in real-time")
    print("5. Plans track completion status for each step")
    print("\nNext Steps:")
    print("- Replace MockPlanningAgent with real LLM-based agent")
    print("- Add custom step executors for domain-specific tasks")
    print("- Implement replanning logic for adaptive plans")
    print("- Integrate with ReActAgent for tool-using steps")
    print("- Add parallel execution for independent steps")


if __name__ == "__main__":
    asyncio.run(main())
