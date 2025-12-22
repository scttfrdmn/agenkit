"""
Goal Monitoring Composition

A simple wrapper that monitors goal achievement and stops when the goal is reached.
This demonstrates that "goal monitoring" is just a loop with a progress check.

For production autonomous agent systems with complex goal hierarchies,
replanning, and adaptive behavior, use the AutonomousAgent pattern.

This composition is perfect for:
- Simple goal-driven tasks
- Learning goal-oriented agents
- Quick prototypes
- Single-objective optimization

References:
    Pattern: Could be combined with PlanningAgent or AutonomousAgent
    Related: AutonomousAgent in agenkit.patterns.autonomous

Example:
    Basic usage::

        from agenkit.techniques.compositions import GoalMonitor
        from agenkit import Message

        monitor = GoalMonitor(
            agent=my_planning_agent,
            goal_fn=lambda state: state["progress"] >= 100,
            max_iterations=10
        )

        result = await monitor.achieve_goal(
            initial_message=Message(role="user", content="Build a web app")
        )

        print(f"Goal reached: {result.metadata['goal_reached']}")
"""

from collections.abc import Callable
from typing import Any

from agenkit import Agent, Message


class GoalMonitor(Agent):
    """
    Goal monitoring composition.

    Wraps an agent and monitors progress toward a goal, stopping when
    the goal is achieved or max iterations reached.

    This is a simple composition (~60 LOC) showing that goal monitoring
    is just a loop with a check function.

    For production autonomous systems, use AutonomousAgent pattern which provides:
    - Goal hierarchies
    - Replanning on failure
    - Adaptive behavior
    - Resource management
    - Multi-objective optimization

    Attributes:
        name: Agent name (always "goal_monitor")
        agent: Base agent to monitor
        goal_fn: Function to check if goal is achieved
        max_iterations: Maximum iterations before stopping
    """

    def __init__(
        self,
        agent: Agent,
        goal_fn: Callable[[dict[str, Any]], bool],
        max_iterations: int = 10,
        extract_state_fn: Callable[[Message], dict[str, Any]] | None = None,
    ):
        """
        Initialize goal monitor.

        Args:
            agent: Base agent to wrap with goal monitoring.
                Should be a planning or reasoning agent.
            goal_fn: Function that takes agent state and returns True
                if goal is achieved. State is extracted from message metadata.
            max_iterations: Maximum iterations before giving up. Default 10.
            extract_state_fn: Optional function to extract state from message.
                If None, uses message.metadata as state.

        Example:
            >>> def goal_check(state: dict) -> bool:
            ...     return state.get("tasks_completed", 0) >= 5
            >>>
            >>> monitor = GoalMonitor(
            ...     agent=my_agent,
            ...     goal_fn=goal_check,
            ...     max_iterations=20
            ... )
        """
        self.agent = agent
        self.goal_fn = goal_fn
        self.max_iterations = max_iterations
        self.extract_state_fn = extract_state_fn or self._default_extract_state

    @property
    def name(self) -> str:
        """Return agent name."""
        return "goal_monitor"

    def _default_extract_state(self, message: Message) -> dict[str, Any]:
        """
        Default state extraction from message metadata.

        Args:
            message: Message to extract state from

        Returns:
            State dictionary
        """
        return message.metadata if message.metadata else {}

    async def achieve_goal(
        self, initial_message: Message, context: dict[str, Any] | None = None
    ) -> Message:
        """
        Run agent until goal is achieved or max iterations reached.

        Args:
            initial_message: Initial message to start with
            context: Optional context dictionary to track across iterations

        Returns:
            Final message from agent. Metadata includes:
                - goal_reached: Whether goal was achieved
                - iterations: Number of iterations taken
                - technique: Always "goal_monitoring"

        Example:
            >>> result = await monitor.achieve_goal(
            ...     initial_message=Message(
            ...         role="user",
            ...         content="Build a calculator app"
            ...     )
            ... )
            >>> if result.metadata['goal_reached']:
            ...     print(f"Success in {result.metadata['iterations']} steps")
        """
        current_message = initial_message
        iteration = 0
        goal_reached = False

        # Track history
        history = []

        if context is None:
            context = {}

        while iteration < self.max_iterations:
            iteration += 1

            # Process with agent
            response = await self.agent.process(current_message)
            history.append(response)

            # Extract state
            state = self.extract_state_fn(response)
            state.update(context)  # Merge with context

            # Check goal
            if self.goal_fn(state):
                goal_reached = True
                break

            # Prepare next iteration
            # Add progress feedback to next message
            progress_feedback = self._generate_progress_feedback(
                iteration=iteration, max_iterations=self.max_iterations, state=state
            )

            current_message = Message(
                role="user", content=f"{response.content}\n\n{progress_feedback}"
            )

        # Get final response
        final_response = history[-1] if history else initial_message

        # Build metadata
        metadata = {
            "technique": "goal_monitoring",
            "goal_reached": goal_reached,
            "iterations": iteration,
            "max_iterations": self.max_iterations,
            "history": history,
        }

        if final_response.metadata:
            metadata.update(final_response.metadata)

        return Message(role=final_response.role, content=final_response.content, metadata=metadata)

    def _generate_progress_feedback(
        self, iteration: int, max_iterations: int, state: dict[str, Any]
    ) -> str:
        """
        Generate feedback about progress toward goal.

        Args:
            iteration: Current iteration number
            max_iterations: Maximum iterations
            state: Current state

        Returns:
            Feedback string
        """
        remaining = max_iterations - iteration

        feedback = f"\nProgress Update (Iteration {iteration}/{max_iterations}):\n"
        feedback += f"- Iterations remaining: {remaining}\n"

        # Add state summary if available
        if state:
            feedback += "- Current state: "
            summary = ", ".join([f"{k}={v}" for k, v in state.items() if k != "history"])
            feedback += summary

        feedback += "\n\nContinue working toward the goal."

        return feedback

    async def process(self, message: Message) -> Message:
        """
        Process message with goal monitoring (alias for achieve_goal).

        Args:
            message: Input message

        Returns:
            Message with goal monitoring results
        """
        return await self.achieve_goal(message)

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        base_caps = self.agent.capabilities if hasattr(self.agent, "capabilities") else []
        return [*base_caps, "goal_monitoring", "progress_tracking", "iterative_execution"]
