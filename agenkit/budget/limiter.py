"""
Budget limiter middleware for cost enforcement.

Middleware that enforces cost budgets and stops agent execution
when budgets are exceeded.
"""

import functools
import logging
from collections.abc import Callable

from ..interfaces import Agent, Message
from .tracker import CostTracker

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when budget is exceeded."""

    pass


class BudgetLimiter:
    """
    Middleware that enforces cost budgets.

    Stops agent execution when budget exceeded. Supports per-session,
    per-agent, and global budgets.

    Actions on budget exceeded:
    - "error": Raise BudgetExceededError
    - "warning": Log warning and continue
    - "switch_model": Switch to cheaper model (requires model_switcher)

    Example:
        >>> tracker = CostTracker()
        >>> limiter = BudgetLimiter(
        ...     tracker,
        ...     session_budget=10.00,  # $10 per session
        ...     action="error"
        ... )
        >>> wrapped_agent = limiter(my_agent)
        >>> # Agent will raise BudgetExceededError if session exceeds $10
    """

    def __init__(
        self,
        tracker: CostTracker,
        session_budget: float | None = None,  # $ per session
        agent_budget: float | None = None,  # $ per agent
        global_budget: float | None = None,  # $ global
        action: str = "error",  # "error", "warning", "switch_model"
        model_switcher: Callable[[str], str] | None = None,  # For switch_model action
        agent_name: str | None = None,  # Override agent name for tracking
    ):
        """
        Initialize budget limiter.

        Args:
            tracker: CostTracker instance
            session_budget: Max $ per session (None = unlimited)
            agent_budget: Max $ per agent (None = unlimited)
            global_budget: Max $ globally (None = unlimited)
            action: Action when budget exceeded ("error", "warning", "switch_model")
            model_switcher: Function to switch models (str -> str) for switch_model action
            agent_name: Override agent name for tracking (defaults to agent.name if available)
        """
        self.tracker = tracker
        self.session_budget = session_budget
        self.agent_budget = agent_budget
        self.global_budget = global_budget
        self.action = action
        self.model_switcher = model_switcher
        self.agent_name_override = agent_name

        if action not in ("error", "warning", "switch_model"):
            raise ValueError(f"action must be 'error', 'warning', or 'switch_model', got: {action}")

        if action == "switch_model" and model_switcher is None:
            raise ValueError("model_switcher required when action='switch_model'")

    def __call__(self, agent: Agent) -> Agent:
        """
        Wrap agent with budget enforcement.

        Args:
            agent: Agent to wrap

        Returns:
            Wrapped agent with budget enforcement
        """
        # Get agent name
        agent_name = self.agent_name_override or getattr(agent, "name", "unknown")

        # Wrap process method
        original_process = agent.process

        @functools.wraps(original_process)
        async def wrapped_process(message: Message) -> Message:
            # Extract session_id from message metadata
            session_id = message.metadata.get("session_id", "default")

            # Check budgets before processing
            await self._check_budgets(session_id, agent_name)

            # Process message
            response = await original_process(message)

            # Record cost after processing
            await self._record_cost(session_id, agent_name, response)

            return response

        # Replace process method
        agent.process = wrapped_process
        return agent

    async def _check_budgets(self, session_id: str, agent_name: str) -> None:
        """Check all budgets before processing."""

        # Check session budget
        if self.session_budget is not None:
            current_cost = await self.tracker.get_session_cost(session_id)
            if current_cost >= self.session_budget:
                await self._handle_budget_exceeded(
                    f"Session budget ${self.session_budget:.2f} exceeded (current: ${current_cost:.2f})",
                    session_id=session_id,
                )

        # Check agent budget
        if self.agent_budget is not None:
            current_cost = await self.tracker.get_agent_cost(agent_name)
            if current_cost >= self.agent_budget:
                await self._handle_budget_exceeded(
                    f"Agent '{agent_name}' budget ${self.agent_budget:.2f} exceeded (current: ${current_cost:.2f})",
                    agent_name=agent_name,
                )

        # Check global budget
        if self.global_budget is not None:
            current_cost = await self.tracker.get_global_cost()
            if current_cost >= self.global_budget:
                await self._handle_budget_exceeded(
                    f"Global budget ${self.global_budget:.2f} exceeded (current: ${current_cost:.2f})"
                )

    async def _handle_budget_exceeded(
        self, message: str, session_id: str | None = None, agent_name: str | None = None
    ) -> None:
        """Handle budget exceeded based on action."""

        if self.action == "error":
            raise BudgetExceededError(message)

        elif self.action == "warning":
            logger.warning(f"Budget exceeded: {message}")

        elif self.action == "switch_model":
            # Model switching handled by optimizer, just log
            logger.info(f"Budget threshold reached: {message}")

    async def _record_cost(self, session_id: str, agent_name: str, response: Message) -> None:
        """Record cost from response metadata."""

        # Check if response has usage metadata
        if "usage" not in response.metadata:
            logger.debug("No usage metadata in response, skipping cost recording")
            return

        usage = response.metadata["usage"]
        model = response.metadata.get("model", "unknown")

        # Record cost
        await self.tracker.record_cost(
            session_id=session_id,
            agent_name=agent_name,
            model=model,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            metadata={"message_id": response.metadata.get("message_id"), "model": model},
        )

    async def get_remaining_budget(
        self, session_id: str | None = None, agent_name: str | None = None
    ) -> dict[str, float | None]:
        """
        Get remaining budget(s).

        Args:
            session_id: Session identifier for session budget
            agent_name: Agent name for agent budget

        Returns:
            Dict with remaining budgets (None = unlimited)

        Example:
            >>> limiter = BudgetLimiter(tracker, session_budget=10.0)
            >>> remaining = await limiter.get_remaining_budget("session-1")
            >>> print(remaining)
            {"session": 8.50, "agent": None, "global": None}
        """
        remaining = {"session": None, "agent": None, "global": None}

        # Session budget
        if self.session_budget is not None and session_id:
            current = await self.tracker.get_session_cost(session_id)
            remaining["session"] = max(0.0, self.session_budget - current)

        # Agent budget
        if self.agent_budget is not None and agent_name:
            current = await self.tracker.get_agent_cost(agent_name)
            remaining["agent"] = max(0.0, self.agent_budget - current)

        # Global budget
        if self.global_budget is not None:
            current = await self.tracker.get_global_cost()
            remaining["global"] = max(0.0, self.global_budget - current)

        return remaining


class BudgetWarning:
    """
    Budget warning middleware (logs warnings at thresholds).

    Similar to BudgetLimiter but only warns at specified thresholds
    instead of stopping execution.

    Example:
        >>> warning = BudgetWarning(
        ...     tracker,
        ...     session_budget=10.00,
        ...     warning_thresholds=[0.5, 0.75, 0.9]  # Warn at 50%, 75%, 90%
        ... )
    """

    def __init__(
        self,
        tracker: CostTracker,
        session_budget: float | None = None,
        agent_budget: float | None = None,
        global_budget: float | None = None,
        warning_thresholds: list[float] | None = None,  # [0.5, 0.75, 0.9]
        agent_name: str | None = None,
    ):
        """Initialize budget warning middleware."""
        self.tracker = tracker
        self.session_budget = session_budget
        self.agent_budget = agent_budget
        self.global_budget = global_budget
        self.warning_thresholds = warning_thresholds or [0.5, 0.75, 0.9]
        self.agent_name_override = agent_name

        # Track which thresholds have been triggered
        self._session_warnings: dict[str, set[float]] = {}
        self._agent_warnings: dict[str, set[float]] = {}
        self._global_warnings: set[float] = set()

    def __call__(self, agent: Agent) -> Agent:
        """Wrap agent with budget warnings."""
        agent_name = self.agent_name_override or getattr(agent, "name", "unknown")
        original_process = agent.process

        @functools.wraps(original_process)
        async def wrapped_process(message: Message) -> Message:
            session_id = message.metadata.get("session_id", "default")

            # Check and log warnings
            await self._check_warnings(session_id, agent_name)

            # Process
            response = await original_process(message)

            # Record cost
            if "usage" in response.metadata:
                usage = response.metadata["usage"]
                model = response.metadata.get("model", "unknown")
                await self.tracker.record_cost(
                    session_id=session_id,
                    agent_name=agent_name,
                    model=model,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )

            return response

        agent.process = wrapped_process
        return agent

    async def _check_warnings(self, session_id: str, agent_name: str) -> None:
        """Check and log budget warnings."""

        # Session warnings
        if self.session_budget is not None:
            current = await self.tracker.get_session_cost(session_id)
            usage_pct = current / self.session_budget

            if session_id not in self._session_warnings:
                self._session_warnings[session_id] = set()

            for threshold in self.warning_thresholds:
                if usage_pct >= threshold and threshold not in self._session_warnings[session_id]:
                    logger.warning(
                        f"Session {session_id} at {usage_pct * 100:.0f}% of budget "
                        f"(${current:.2f} / ${self.session_budget:.2f})"
                    )
                    self._session_warnings[session_id].add(threshold)

        # Agent warnings
        if self.agent_budget is not None:
            current = await self.tracker.get_agent_cost(agent_name)
            usage_pct = current / self.agent_budget

            if agent_name not in self._agent_warnings:
                self._agent_warnings[agent_name] = set()

            for threshold in self.warning_thresholds:
                if usage_pct >= threshold and threshold not in self._agent_warnings[agent_name]:
                    logger.warning(
                        f"Agent {agent_name} at {usage_pct * 100:.0f}% of budget "
                        f"(${current:.2f} / ${self.agent_budget:.2f})"
                    )
                    self._agent_warnings[agent_name].add(threshold)

        # Global warnings
        if self.global_budget is not None:
            current = await self.tracker.get_global_cost()
            usage_pct = current / self.global_budget

            for threshold in self.warning_thresholds:
                if usage_pct >= threshold and threshold not in self._global_warnings:
                    logger.warning(
                        f"Global cost at {usage_pct * 100:.0f}% of budget "
                        f"(${current:.2f} / ${self.global_budget:.2f})"
                    )
                    self._global_warnings.add(threshold)
