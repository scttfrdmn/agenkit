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


@dataclass
class AutonomousConfig:
    """
    Configuration for AutonomousAgent.

    This config-based approach provides:
    - Cross-language API consistency (matches Go/C++/Rust/TypeScript/Zig)
    - Better documentation (all parameters in one place)
    - Type safety and IDE autocomplete
    - Extensibility without breaking changes

    Attributes:
        objective: High-level objective the agent should pursue
        max_iterations: Maximum iterations before stopping (default: 10)
        stop_condition: Optional callable that returns True when agent should stop

    Example:
        >>> from agenkit.patterns import AutonomousAgent, AutonomousConfig
        >>> config = AutonomousConfig(
        ...     objective="Research and summarize AI trends",
        ...     max_iterations=20
        ... )
        >>> agent = AutonomousAgent(config)
    """

    objective: str
    max_iterations: int = 10
    stop_condition: Callable | None = None

    def __post_init__(self):
        """Validate configuration."""
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")


class AutonomousAgent(Agent):
    """
    Agent that operates autonomously toward objectives.

    Example (recommended config-based API):
        ```python
        from agenkit.patterns import AutonomousAgent, AutonomousConfig

        config = AutonomousConfig(
            objective="Research and summarize AI trends",
            max_iterations=10
        )
        agent = AutonomousAgent(config)

        result = await agent.run()
        # Agent operates independently until complete
        ```

    Example (deprecated direct parameters):
        ```python
        # This API is deprecated and will be removed in v2.0
        agent = AutonomousAgent(
            objective="Research and summarize AI trends",
            max_iterations=10
        )
        ```

    Args:
        config: Configuration object (recommended, matches other languages)
        objective: (Deprecated) High-level objective the agent should pursue
        max_iterations: (Deprecated) Maximum iterations before stopping
        stop_condition: (Deprecated) Optional callable to determine when to stop
    """

    def __init__(
        self,
        config: AutonomousConfig | None = None,
        *,
        # Deprecated parameters (kept for backward compatibility)
        objective: str | None = None,
        max_iterations: int = 10,
        stop_condition: Callable | None = None,
    ):
        """
        Initialize AutonomousAgent.

        Args:
            config: Configuration object (recommended, matches other languages)
            objective: (Deprecated) High-level objective
            max_iterations: (Deprecated) Maximum iterations
            stop_condition: (Deprecated) Optional stop condition callable

        Examples:
            >>> # Recommended: config-based (matches all other languages)
            >>> config = AutonomousConfig(objective="Research AI", max_iterations=15)
            >>> agent = AutonomousAgent(config)
            >>>
            >>> # Deprecated: direct parameters (will be removed in v2.0)
            >>> agent = AutonomousAgent(objective="Research AI", max_iterations=15)

        Migration:
            Old code:
                agent = AutonomousAgent(
                    objective="Research AI trends",
                    max_iterations=20,
                    stop_condition=my_stop_fn
                )

            New code:
                config = AutonomousConfig(
                    objective="Research AI trends",
                    max_iterations=20,
                    stop_condition=my_stop_fn
                )
                agent = AutonomousAgent(config)
        """
        import warnings

        if config is not None:
            # New config-based API (recommended)
            self.objective = config.objective
            self.max_iterations = config.max_iterations
            self.stop_condition = config.stop_condition
        elif objective is not None:
            # Old direct-parameter API (deprecated)
            warnings.warn(
                "Direct parameters for AutonomousAgent are deprecated and will be removed in v2.0. "
                "Use AutonomousConfig instead: "
                "AutonomousAgent(AutonomousConfig(objective=...)). "
                "See migration guide for details.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.objective = objective
            self.max_iterations = max_iterations
            self.stop_condition = stop_condition
        else:
            raise ValueError(
                "Either 'config' or 'objective' must be provided. "
                "Recommended: Use AutonomousConfig for cross-language API consistency."
            )

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
