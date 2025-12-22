"""
Plan-and-Solve Reasoning Example

Demonstrates how to use Plan-and-Solve prompting to separate planning
(devising a strategy) from solving (executing the strategy).

This example shows:
- Basic planning and execution
- Plan validation before execution
- Custom planner and solver functions
- Replanning when validation fails
- Comparison with direct problem-solving

Requirements:
    pip install agenkit
"""

import asyncio

from agenkit import Message
from agenkit.techniques.reasoning import Plan, PlanAndSolve, PlanStep


# Mock LLM for demonstration
class MockLLM:
    """Simple mock LLM for demonstration."""

    def __init__(self):
        self.call_count = 0

    async def complete(self, prompt: str) -> str:
        """Return mock responses based on prompt type."""
        self.call_count += 1

        # Planning prompts
        if "Plan" in prompt or "plan" in prompt:
            if "birthday party" in prompt:
                return """1. Choose date and venue
2. Create guest list
3. Send invitations
4. Order cake and food
5. Prepare decorations"""

            if "vacation" in prompt:
                return """1. Research destinations
2. Check budget and dates
3. Book flights
4. Reserve accommodation
5. Plan daily itinerary"""

            if "3*4 + 2*5" in prompt:
                return """1. Calculate 3*4
2. Calculate 2*5
3. Add the results"""

            return "1. Understand problem\n2. Develop solution\n3. Verify result"

        # Validation prompts
        if "valid" in prompt.lower() or "review" in prompt.lower():
            if "missing" in prompt or "insufficient" in prompt:
                return "INVALID - The plan is missing important details"
            return "VALID - The plan is complete and feasible"

        # Execution prompts
        if "Choose date" in prompt:
            return "Saturday, June 15th at Central Park"
        if "Create guest list" in prompt:
            return "20 people: family and close friends"
        if "Send invitations" in prompt:
            return "Digital invitations sent via email"
        if "Order cake" in prompt:
            return "Chocolate cake for 25 ordered from local bakery"
        if "Prepare decorations" in prompt:
            return "Balloons, banners, and table settings ready"

        if "Calculate 3*4" in prompt:
            return "12"
        if "Calculate 2*5" in prompt:
            return "10"
        if "Add the results" in prompt:
            return "22"

        if "Research destinations" in prompt:
            return "Paris, France selected for history and culture"
        if "Check budget" in prompt:
            return "$3000 budget, traveling June 1-10"
        if "Book flights" in prompt:
            return "Round-trip flights booked, departing June 1"
        if "Reserve accommodation" in prompt:
            return "Hotel in Marais district for 9 nights"
        if "Plan daily itinerary" in prompt:
            return "Daily schedule: museums, landmarks, restaurants"

        return "Solution step completed"


async def basic_example():
    """Basic Plan-and-Solve with validation."""
    print("=" * 60)
    print("Example 1: Basic Plan-and-Solve (Birthday Party)")
    print("=" * 60)

    llm = MockLLM()
    agent = PlanAndSolve(llm=llm, validate_plan=True)

    problem = "Plan a surprise birthday party for 20 people"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")
    print(f"\n📋 Generated Plan ({len(response.metadata['plan_steps'])} steps):")
    for i, step in enumerate(response.metadata["plan_steps"], 1):
        print(f"  {i}. {step}")

    print(f"\n✓ Plan Validated: {response.metadata['validated']}")
    print(f"  Validation: {response.metadata['validation_notes']}")

    print("\n⚙️  Execution Results:")
    for i, (step, result) in enumerate(
        zip(response.metadata["plan_steps"], response.metadata["execution_steps"], strict=False), 1
    ):
        print(f"  {i}. {step}")
        print(f"     → {result}")

    print(f"\n🎯 Final Result: {response.content}")


async def no_validation_example():
    """Example without plan validation."""
    print("\n" + "=" * 60)
    print("Example 2: Without Validation (Faster)")
    print("=" * 60)

    llm = MockLLM()
    agent = PlanAndSolve(llm=llm, validate_plan=False)

    problem = "Calculate 3*4 + 2*5"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")
    print("\n📋 Plan (skip validation for speed):")
    for i, step in enumerate(response.metadata["plan_steps"], 1):
        print(f"  {i}. {step}")

    print("\n⚙️  Execution:")
    for i, result in enumerate(response.metadata["execution_steps"], 1):
        print(f"  Step {i} → {result}")

    print(f"\n🎯 Answer: {response.content}")
    print("\n💡 Set validate_plan=False for simple problems or when speed matters")


async def custom_planner_example():
    """Example with custom planner function."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Planner Function")
    print("=" * 60)

    def domain_specific_planner(problem: str) -> Plan:
        """Custom planner for vacation planning."""
        if "vacation" in problem.lower():
            steps = [
                PlanStep(description="Determine budget", order=0, estimated_complexity=1),
                PlanStep(description="Research destinations", order=1, estimated_complexity=3),
                PlanStep(
                    description="Book transportation",
                    order=2,
                    dependencies=[0, 1],
                    estimated_complexity=2,
                ),
                PlanStep(
                    description="Book accommodation",
                    order=3,
                    dependencies=[2],
                    estimated_complexity=2,
                ),
                PlanStep(
                    description="Create itinerary",
                    order=4,
                    dependencies=[3],
                    estimated_complexity=3,
                ),
            ]
            return Plan(steps=steps, problem=problem, validated=True, strategy="vacation_planning")
        return Plan(steps=[], problem=problem)

    llm = MockLLM()
    agent = PlanAndSolve(llm=llm, planner=domain_specific_planner, validate_plan=False)

    problem = "Plan a vacation to Europe"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")
    print("\n📋 Custom Domain Plan:")
    for step in response.metadata["plan"].steps:
        deps = f" (depends on: {step.dependencies})" if step.dependencies else ""
        complexity = "⭐" * step.estimated_complexity
        print(f"  {step.order + 1}. {step.description} {complexity}{deps}")

    print("\n💡 Custom planners enable:")
    print("   - Domain-specific planning strategies")
    print("   - Dependency tracking between steps")
    print("   - Complexity estimation")
    print("   - Avoiding LLM calls for planning")


async def custom_solver_example():
    """Example with custom solver function."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Solver Function")
    print("=" * 60)

    execution_log = []

    def logging_solver(step: PlanStep, previous_results: list) -> str:
        """Custom solver that logs execution."""
        execution_log.append(f"Executing: {step.description}")

        # Simple simulation based on step description
        if "Calculate" in step.description:
            if "3*4" in step.description:
                return "12"
            if "2*5" in step.description:
                return "10"
            if "Add" in step.description:
                return "22"

        return f"Completed: {step.description}"

    llm = MockLLM()
    agent = PlanAndSolve(llm=llm, solver=logging_solver, validate_plan=False)

    problem = "Calculate 3*4 + 2*5"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")
    print("\n📋 Plan:")
    for i, step in enumerate(response.metadata["plan_steps"], 1):
        print(f"  {i}. {step}")

    print("\n📝 Execution Log:")
    for log_entry in execution_log:
        print(f"  • {log_entry}")

    print(f"\n🎯 Result: {response.content}")
    print("\n💡 Custom solvers enable:")
    print("   - Execution logging and monitoring")
    print("   - Integration with external systems")
    print("   - Custom step execution logic")


async def replanning_example():
    """Example with replanning on validation failure."""
    print("\n" + "=" * 60)
    print("Example 5: Replanning When Validation Fails")
    print("=" * 60)

    class ReplanningLLM:
        def __init__(self):
            self.plan_attempt = 0

        async def complete(self, prompt: str) -> str:
            if "plan" in prompt.lower() and "Plan" not in prompt:
                self.plan_attempt += 1
                if self.plan_attempt == 1:
                    # First plan is incomplete
                    return "1. Do the thing"
                else:
                    # Improved plan after feedback
                    return """1. Define clear requirements
2. Break into subtasks
3. Execute each subtask
4. Verify results"""

            if "valid" in prompt.lower():
                if self.plan_attempt == 1:
                    return "INVALID - Plan is too vague, missing critical details"
                return "VALID - Improved plan is complete"

            return "Step completed"

    llm = ReplanningLLM()
    agent = PlanAndSolve(llm=llm, validate_plan=True, allow_replanning=True)

    problem = "Solve a complex problem"
    response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")
    print("\n❌ Initial Plan Failed Validation:")
    print(f"   Reason: {response.metadata['validation_notes']}")

    print(f"\n✅ Replanned with {len(response.metadata['plan_steps'])} improved steps:")
    for i, step in enumerate(response.metadata["plan_steps"], 1):
        print(f"  {i}. {step}")

    print("\n💡 Replanning (allow_replanning=True):")
    print("   - Catches incomplete or flawed plans")
    print("   - Automatically improves plan based on validation feedback")
    print("   - Ensures high-quality plans before execution")


async def comparison_example():
    """Compare Plan-and-Solve vs direct solving."""
    print("\n" + "=" * 60)
    print("Example 6: Plan-and-Solve vs Direct Solving")
    print("=" * 60)

    problem = "Organize a team-building event"

    # Direct solving (no planning)
    llm_direct = MockLLM()
    direct_response = await llm_direct.complete(problem)

    # Plan-and-Solve
    llm_planned = MockLLM()
    agent = PlanAndSolve(llm=llm_planned, validate_plan=True)
    planned_response = await agent.process(Message(role="user", content=problem))

    print(f"\nProblem: {problem}")

    print("\n❌ Direct Solving (No Planning):")
    print(f"   Response: {direct_response}")
    print("   Issues:")
    print("   - No clear structure")
    print("   - May miss important steps")
    print("   - Hard to track progress")
    print("   - Difficult to modify mid-execution")

    print("\n✅ Plan-and-Solve:")
    print(f"   {len(planned_response.metadata['plan_steps'])} clear steps:")
    for i, step in enumerate(planned_response.metadata["plan_steps"], 1):
        print(f"   {i}. {step}")

    print("\n   Benefits:")
    print("   - ✓ Structured approach")
    print("   - ✓ All steps identified upfront")
    print("   - ✓ Progress tracking built-in")
    print("   - ✓ Easy to validate before execution")
    print("   - ✓ Can replan if needed")


async def when_to_use():
    """Guidelines on when to use Plan-and-Solve."""
    print("\n" + "=" * 60)
    print("When to Use Plan-and-Solve")
    print("=" * 60)

    print("""
✅ BEST FOR:
  - Complex multi-step problems
  - Projects requiring strategic planning
  - Tasks where planning improves execution quality
  - Problems with clear sequential steps
  - Situations requiring validation before action
  - Tasks where you want to review the plan first

❌ LESS SUITABLE FOR:
  - Simple one-step problems
  - Tasks requiring exploratory reasoning
  - When you need to explore multiple paths (use Tree-of-Thought)
  - Real-time reactive problems
  - When planning overhead isn't justified

⚙️ CONFIGURATION:
  - validate_plan: Enable validation before execution (default True)
  - allow_replanning: Allow replanning on validation failure (default False)
  - planner: Custom planning function for domain-specific logic
  - solver: Custom solver function for specialized execution

🔗 COMBINE WITH:
  - Chain-of-Thought: Use CoT as the LLM for better planning/execution
  - Least-to-Most: Plan-and-Solve for strategy, LtM for decomposition
  - Self-Consistency: Generate multiple plans, vote for best

💡 KEY DIFFERENCES:
  - vs ChainOfThought: Explicit planning phase vs implicit reasoning
  - vs LeastToMost: Strategic planning vs problem decomposition
  - vs TreeOfThought: Single plan vs exploring multiple paths
  - vs PlanningAgent: Prompting technique vs agent orchestration pattern
""")


async def main():
    """Run all examples."""
    await basic_example()
    await no_validation_example()
    await custom_planner_example()
    await custom_solver_example()
    await replanning_example()
    await comparison_example()
    await when_to_use()

    print("\n" + "=" * 60)
    print("Plan-and-Solve Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
