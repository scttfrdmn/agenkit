"""
Autonomous Agent Pattern

An agent that operates independently with minimal human intervention:
- Sets its own goals based on high-level objectives
- Makes decisions about actions to take
- Monitors progress and adapts strategy
- Continues until objective is met or stopped

This pattern is useful for:
- Long-running tasks
- Self-directed research
- Continuous improvement systems
- Automated workflows
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agenkit import Agent, Message


@dataclass
class Goal:
    """A goal the autonomous agent is pursuing."""

    description: str
    priority: int = 1
    status: str = "active"  # active, completed, abandoned
    progress: float = 0.0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class AutonomousAgent(Agent):
    """
    Agent that operates autonomously toward objectives.

    Example:
        ```python
        from agenkit.patterns import AutonomousAgent

        agent = AutonomousAgent(
            objective="Research and summarize AI trends",
            max_iterations=10
        )

        result = await agent.run()
        # Agent operates independently until complete
        ```
    """

    def __init__(
        self, objective: str, max_iterations: int = 10, stop_condition: Callable | None = None
    ):
        self.objective = objective
        self.max_iterations = max_iterations
        self.stop_condition = stop_condition
        self.goals: list[Goal] = []
        self.iteration_count = 0
        self.is_running = False

    @property
    def name(self) -> str:
        return "AutonomousAgent"

    async def process(self, message: Message) -> Message:
        """Process a message (autonomous agents don't need messages)."""
        return Message(role="assistant", content=f"Autonomous agent working on: {self.objective}")

    def add_goal(self, description: str, priority: int = 1) -> Goal:
        """Add a goal for the agent to pursue."""
        goal = Goal(description=description, priority=priority)
        self.goals.append(goal)
        return goal

    async def run(self) -> dict[str, Any]:
        """Run the autonomous agent."""
        self.is_running = True
        results = []

        while self.iteration_count < self.max_iterations and self.is_running:
            self.iteration_count += 1

            # Check stop condition
            if self.stop_condition and self.stop_condition():
                break

            # Select next action (simplified)
            active_goals = [g for g in self.goals if g.status == "active"]
            if not active_goals:
                break

            # Work on highest priority goal
            goal = max(active_goals, key=lambda g: g.priority)
            result = await self._work_on_goal(goal)
            results.append(result)

            # Update progress
            goal.progress += 0.2
            if goal.progress >= 1.0:
                goal.status = "completed"

        self.is_running = False

        return {
            "objective": self.objective,
            "iterations": self.iteration_count,
            "goals_completed": len([g for g in self.goals if g.status == "completed"]),
            "results": results,
        }

    async def _work_on_goal(self, goal: Goal) -> str:
        """Work on a specific goal."""
        # Mock implementation
        return f"Progress on: {goal.description}"

    def stop(self) -> None:
        """Stop the autonomous agent."""
        self.is_running = False

    def get_progress(self) -> float:
        """Get overall progress."""
        if not self.goals:
            return 0.0

        total_progress = sum(g.progress for g in self.goals)
        return (total_progress / len(self.goals)) * 100
