"""
Autonomous Agent Example

Demonstrates how autonomous agents operate independently with minimal human
intervention. These agents:
- Set and manage their own goals
- Make decisions about what actions to take
- Monitor progress and adapt their approach
- Continue until objectives are met or stopped

The Autonomous pattern is useful for:
- Long-running tasks that don't need constant supervision
- Self-directed research and exploration
- Continuous improvement systems
- Automated workflows and maintenance

This example uses mock implementations for demonstration.
"""

import asyncio
from typing import Any

from agenkit.patterns import AutonomousAgent, Goal

# ============================================================================
# Example 1: Basic Autonomous Operation
# ============================================================================


class BasicResearchAgent(AutonomousAgent):
    """Simple autonomous agent that conducts research."""

    async def _work_on_goal(self, goal: Goal) -> str:
        """Execute work on a specific goal."""
        # Simulate research work
        await asyncio.sleep(0.1)
        return f"Researched: {goal.description}"


async def basic_autonomous_example():
    """Demonstrate basic autonomous agent operation."""
    print("=" * 60)
    print("Example 1: Basic Autonomous Operation")
    print("=" * 60)

    # Create agent with an objective
    agent = BasicResearchAgent(objective="Research AI trends in 2024", max_iterations=5)

    # Add goals for the agent to pursue
    agent.add_goal("Review latest AI papers", priority=3)
    agent.add_goal("Analyze industry trends", priority=2)
    agent.add_goal("Summarize findings", priority=1)

    print(f"\nObjective: {agent.objective}")
    print(f"Goals: {len(agent.goals)}")

    # Run the agent
    print("\nStarting autonomous operation...")
    result = await agent.run()

    print("\nCompleted!")
    print(f"Iterations: {result['iterations']}")
    print(f"Goals completed: {result['goals_completed']}/{len(agent.goals)}")
    print(f"Progress: {agent.get_progress():.1f}%")


# ============================================================================
# Example 2: Goal Priority and Management
# ============================================================================


async def goal_priority_example():
    """Demonstrate goal prioritization."""
    print("\n" + "=" * 60)
    print("Example 2: Goal Priority Management")
    print("=" * 60)

    agent = BasicResearchAgent(objective="Complete multiple tasks", max_iterations=10)

    # Add goals with different priorities
    agent.add_goal("High priority task", priority=10)
    agent.add_goal("Medium priority task", priority=5)
    agent.add_goal("Low priority task", priority=1)
    agent.add_goal("Another high priority", priority=10)

    print("\nGoals in order of priority:")
    sorted_goals = sorted(agent.goals, key=lambda g: g.priority, reverse=True)
    for goal in sorted_goals:
        print(f"  Priority {goal.priority}: {goal.description}")

    print("\nRunning agent...")
    result = await agent.run()

    print("\nExecution order (by priority):")
    for i, res in enumerate(result["results"], 1):
        print(f"  {i}. {res}")


# ============================================================================
# Example 3: Progress Tracking
# ============================================================================


async def progress_tracking_example():
    """Demonstrate progress tracking."""
    print("\n" + "=" * 60)
    print("Example 3: Progress Tracking")
    print("=" * 60)

    agent = BasicResearchAgent(objective="Long-running task", max_iterations=20)

    agent.add_goal("Phase 1: Data collection", priority=3)
    agent.add_goal("Phase 2: Analysis", priority=2)
    agent.add_goal("Phase 3: Report generation", priority=1)

    print("\nTracking progress in real-time...\n")

    # Start agent in background
    task = asyncio.create_task(agent.run())

    # Monitor progress
    last_progress = 0
    last_iteration = 0
    while not task.done():
        progress = agent.get_progress()
        iteration = agent.iteration_count

        if progress != last_progress or iteration != last_iteration:
            status = "Running" if agent.is_running else "Stopped"
            print(f"Status: {status} | Iteration: {iteration} | Progress: {progress:.1f}%")
            last_progress = progress
            last_iteration = iteration

        await asyncio.sleep(0.05)

    result = await task
    print(f"\nFinal status: Completed {result['iterations']} iterations")


# ============================================================================
# Example 4: Stop Conditions
# ============================================================================


async def stop_condition_example():
    """Demonstrate custom stop conditions."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Stop Conditions")
    print("=" * 60)

    # Track external condition
    class Context:
        items_processed = 0
        target = 5

    def stop_when_target_reached():
        """Stop when we've processed enough items."""
        return Context.items_processed >= Context.target

    class CustomAgent(AutonomousAgent):
        """Agent that increments counter."""

        async def _work_on_goal(self, goal: Goal) -> str:
            Context.items_processed += 1
            await asyncio.sleep(0.05)
            return f"Processed item {Context.items_processed}"

    agent = CustomAgent(
        objective="Process items until target reached",
        max_iterations=100,  # High limit
        stop_condition=stop_when_target_reached,
    )

    agent.add_goal("Process items", priority=1)

    print(f"Target: Process {Context.target} items")
    print(f"Max iterations: {agent.max_iterations}")
    print("\nRunning agent with stop condition...")

    result = await agent.run()

    print(f"\nStopped after {result['iterations']} iterations")
    print(f"Items processed: {Context.items_processed}")
    print("Stop condition triggered successfully!")


# ============================================================================
# Example 5: Manual Control
# ============================================================================


async def manual_control_example():
    """Demonstrate manual stop control."""
    print("\n" + "=" * 60)
    print("Example 5: Manual Stop Control")
    print("=" * 60)

    agent = BasicResearchAgent(objective="Continuous task", max_iterations=100)

    agent.add_goal("Continuous monitoring", priority=1)

    print("\nStarting agent (will run for 3 iterations, then stop)...")

    # Start agent in background
    task = asyncio.create_task(agent.run())

    # Let it run for a bit
    await asyncio.sleep(0.3)

    # Stop it manually
    print("Stopping agent manually...")
    agent.stop()

    result = await task

    print(f"\nAgent stopped after {result['iterations']} iterations")
    print("Manual control successful!")


# ============================================================================
# Example 6: Adaptive Goal Management
# ============================================================================


async def adaptive_goals_example():
    """Demonstrate dynamic goal management."""
    print("\n" + "=" * 60)
    print("Example 6: Adaptive Goal Management")
    print("=" * 60)

    class AdaptiveAgent(AutonomousAgent):
        """Agent that adds new goals based on discoveries."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.discoveries = []

        async def _work_on_goal(self, goal: Goal) -> str:
            """Work on goal and potentially discover new goals."""
            await asyncio.sleep(0.05)

            # Simulate discovery
            if "explore" in goal.description.lower() and len(self.discoveries) < 2:
                new_goal_desc = f"Follow up on discovery {len(self.discoveries) + 1}"
                self.add_goal(new_goal_desc, priority=5)
                self.discoveries.append(new_goal_desc)
                return f"Completed: {goal.description} (discovered new goal!)"

            return f"Completed: {goal.description}"

    agent = AdaptiveAgent(objective="Explore and adapt", max_iterations=15)

    agent.add_goal("Explore area A", priority=10)
    agent.add_goal("Explore area B", priority=10)

    print(f"Initial goals: {len(agent.goals)}")
    print("\nRunning adaptive agent...")

    result = await agent.run()

    print(f"\nTotal goals created: {len(agent.goals)}")
    print(f"Goals completed: {result['goals_completed']}")
    print(f"Discoveries made: {len(agent.discoveries)}")

    print("\nAll goals:")
    for _i, goal in enumerate(agent.goals, 1):
        status_icon = {"active": "○", "completed": "✓", "abandoned": "✗"}.get(goal.status, "?")
        print(f"  {status_icon} {goal.description} (priority: {goal.priority})")


# ============================================================================
# Example 7: Multi-Goal Coordination
# ============================================================================


async def multi_goal_coordination_example():
    """Demonstrate coordinating multiple related goals."""
    print("\n" + "=" * 60)
    print("Example 7: Multi-Goal Coordination")
    print("=" * 60)

    class CoordinatedAgent(AutonomousAgent):
        """Agent that tracks goal relationships."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.goal_results: dict[str, Any] = {}

        async def _work_on_goal(self, goal: Goal) -> str:
            """Work on goal and store results."""
            await asyncio.sleep(0.05)

            result = f"Result for: {goal.description}"
            self.goal_results[goal.description] = result

            # Check if we've completed all phases
            completed_goals = [g for g in self.goals if g.status == "completed"]
            progress_msg = f"({len(completed_goals)}/{len(self.goals)} complete)"

            return f"{result} {progress_msg}"

    agent = CoordinatedAgent(objective="Multi-phase project", max_iterations=20)

    # Add related goals
    agent.add_goal("Phase 1: Planning", priority=3)
    agent.add_goal("Phase 2: Implementation", priority=2)
    agent.add_goal("Phase 3: Testing", priority=1)
    agent.add_goal("Phase 4: Deployment", priority=0)

    print("Multi-phase project with coordinated goals\n")

    await agent.run()

    print("\nProject phases completed:")
    for goal in agent.goals:
        status = goal.status
        progress = int(goal.progress * 100)
        status_icon = {"active": "○", "completed": "✓", "abandoned": "✗"}.get(status, "?")
        print(f"  {status_icon} {goal.description}: {progress}% ({status})")

    print(f"\nOverall progress: {agent.get_progress():.1f}%")


async def main():
    """Run all examples."""
    await basic_autonomous_example()
    await goal_priority_example()
    await progress_tracking_example()
    await stop_condition_example()
    await manual_control_example()
    await adaptive_goals_example()
    await multi_goal_coordination_example()

    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. Autonomous agents operate independently toward objectives")
    print("2. Goals can be prioritized and managed dynamically")
    print("3. Progress can be tracked in real-time")
    print("4. Custom stop conditions provide flexible control")
    print("5. Agents can be stopped manually when needed")
    print("6. Goals can be added dynamically based on discoveries")
    print("7. Multi-goal coordination enables complex workflows")
    print("\nNext Steps:")
    print("- Integrate with LLMs for intelligent goal generation")
    print("- Add planning capabilities for goal sequencing")
    print("- Implement learning from past executions")
    print("- Add collaboration with other agents")
    print("- Create domain-specific autonomous agents")


if __name__ == "__main__":
    asyncio.run(main())
