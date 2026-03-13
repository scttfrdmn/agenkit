"""
Cost tracking for LLM usage.

Tracks costs per session, per agent, and globally for budget management.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .models import ModelPricing


@dataclass
class Cost:
    """
    Single cost record.

    Attributes:
        session_id: Session identifier
        agent_name: Agent name
        model: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        thinking_tokens: Number of thinking/reasoning tokens (o3, Claude 4 extended)
        input_cost: Cost for input tokens ($)
        output_cost: Cost for output tokens ($)
        thinking_cost: Cost for thinking tokens ($)
        total_cost: Total cost ($)
        timestamp: When cost was recorded
        metadata: Additional metadata
    """

    session_id: str
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    input_cost: float
    output_cost: float
    thinking_cost: float
    total_cost: float
    timestamp: datetime
    metadata: dict

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class Storage:
    """Abstract interface for cost storage backends."""

    async def store(self, cost: Cost) -> None:
        """Store a cost record."""
        raise NotImplementedError

    async def query(
        self,
        session_id: str | None = None,
        agent_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Cost]:
        """Query cost records."""
        raise NotImplementedError


class MemoryStorage(Storage):
    """In-memory storage for cost records."""

    def __init__(self):
        self.costs: list[Cost] = []

    async def store(self, cost: Cost) -> None:
        """Store cost record in memory."""
        self.costs.append(cost)

    async def query(
        self,
        session_id: str | None = None,
        agent_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Cost]:
        """Query cost records from memory."""
        results = []

        for cost in self.costs:
            # Filter by session_id
            if session_id and cost.session_id != session_id:
                continue

            # Filter by agent_name
            if agent_name and cost.agent_name != agent_name:
                continue

            # Filter by time range
            if start_time and cost.timestamp < start_time:
                continue
            if end_time and cost.timestamp > end_time:
                continue

            results.append(cost)

        return results


class CostTracker:
    """
    Track LLM costs per session, agent, and globally.

    Features:
    - Per-session cost tracking
    - Per-agent cost tracking
    - Global cost tracking
    - Cost breakdown by model
    - Time-series cost data

    Example:
        >>> tracker = CostTracker()
        >>> await tracker.record_cost(
        ...     session_id="user-123",
        ...     agent_name="assistant",
        ...     model="claude-sonnet-4",
        ...     input_tokens=1000,
        ...     output_tokens=500
        ... )
        >>> total = await tracker.get_session_cost("user-123")
        >>> print(f"Session cost: ${total:.2f}")
        Session cost: $0.01
    """

    def __init__(self, storage: Storage | None = None):
        """
        Initialize cost tracker.

        Args:
            storage: Storage backend (defaults to in-memory)
        """
        self.storage = storage or MemoryStorage()
        self.model_pricing = ModelPricing()

    async def record_cost(
        self,
        session_id: str,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
        metadata: dict | None = None,
    ) -> Cost:
        """
        Record a cost event.

        Args:
            session_id: Session identifier
            agent_name: Agent name
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            thinking_tokens: Number of thinking/reasoning tokens (default: 0)
            metadata: Optional metadata (message_id, etc.)

        Returns:
            Cost record

        Example:
            >>> tracker = CostTracker()
            >>> cost = await tracker.record_cost(
            ...     "session-1",
            ...     "assistant",
            ...     "claude-sonnet-4",
            ...     1000,
            ...     500,
            ...     thinking_tokens=5000
            ... )
            >>> print(f"${cost.total_cost:.4f}")
            $0.0180
        """
        # Calculate costs
        input_cost = self.model_pricing.calculate(model, input_tokens, "input")
        output_cost = self.model_pricing.calculate(model, output_tokens, "output")

        # Thinking tokens typically use output token pricing
        # (some models may charge differently, but this is a reasonable default)
        thinking_cost = (
            self.model_pricing.calculate(model, thinking_tokens, "output")
            if thinking_tokens > 0
            else 0.0
        )

        total_cost = input_cost + output_cost + thinking_cost

        # Create record
        cost = Cost(
            session_id=session_id,
            agent_name=agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            thinking_cost=thinking_cost,
            total_cost=total_cost,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        # Store
        await self.storage.store(cost)

        return cost

    async def get_session_cost(
        self, session_id: str, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> float:
        """
        Get total cost for session (optionally in time range).

        Args:
            session_id: Session identifier
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            Total cost in dollars

        Example:
            >>> tracker = CostTracker()
            >>> # ... record some costs ...
            >>> total = await tracker.get_session_cost("session-1")
            >>> print(f"${total:.2f}")
            $1.50
        """
        costs = await self.storage.query(
            session_id=session_id, start_time=start_time, end_time=end_time
        )
        return sum(c.total_cost for c in costs)

    async def get_agent_cost(
        self, agent_name: str, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> float:
        """
        Get total cost for agent.

        Args:
            agent_name: Agent name
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            Total cost in dollars
        """
        costs = await self.storage.query(
            agent_name=agent_name, start_time=start_time, end_time=end_time
        )
        return sum(c.total_cost for c in costs)

    async def get_global_cost(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> float:
        """
        Get total global cost.

        Args:
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            Total cost in dollars
        """
        costs = await self.storage.query(start_time=start_time, end_time=end_time)
        return sum(c.total_cost for c in costs)

    async def get_breakdown(
        self, session_id: str | None = None, agent_name: str | None = None
    ) -> dict[str, float]:
        """
        Get cost breakdown by model.

        Args:
            session_id: Optional session filter
            agent_name: Optional agent filter

        Returns:
            Dict mapping model to total cost

        Example:
            >>> tracker = CostTracker()
            >>> # ... record costs ...
            >>> breakdown = await tracker.get_breakdown(session_id="session-1")
            >>> print(breakdown)
            {"claude-sonnet-4": 2.50, "claude-opus-4": 5.75}
        """
        costs = await self.storage.query(session_id=session_id, agent_name=agent_name)

        breakdown = defaultdict(float)
        for cost in costs:
            breakdown[cost.model] += cost.total_cost

        return dict(breakdown)

    async def get_top_sessions(
        self, limit: int = 10, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> list[tuple[str, float]]:
        """
        Get top N sessions by cost.

        Args:
            limit: Number of sessions to return
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            List of (session_id, total_cost) tuples, sorted by cost descending

        Example:
            >>> tracker = CostTracker()
            >>> top = await tracker.get_top_sessions(limit=5)
            >>> for session_id, cost in top:
            ...     print(f"{session_id}: ${cost:.2f}")
            session-1: $10.50
            session-2: $5.25
            ...
        """
        costs = await self.storage.query(start_time=start_time, end_time=end_time)

        session_totals = defaultdict(float)
        for cost in costs:
            session_totals[cost.session_id] += cost.total_cost

        sorted_sessions = sorted(session_totals.items(), key=lambda x: x[1], reverse=True)

        return sorted_sessions[:limit]

    async def get_top_agents(
        self, limit: int = 10, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> list[tuple[str, float]]:
        """
        Get top N agents by cost.

        Args:
            limit: Number of agents to return
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            List of (agent_name, total_cost) tuples
        """
        costs = await self.storage.query(start_time=start_time, end_time=end_time)

        agent_totals = defaultdict(float)
        for cost in costs:
            agent_totals[cost.agent_name] += cost.total_cost

        sorted_agents = sorted(agent_totals.items(), key=lambda x: x[1], reverse=True)

        return sorted_agents[:limit]

    async def get_statistics(
        self, session_id: str | None = None, agent_name: str | None = None
    ) -> dict:
        """
        Get cost statistics.

        Args:
            session_id: Optional session filter
            agent_name: Optional agent filter

        Returns:
            Dict with statistics (total_cost, total_tokens, avg_cost_per_request, etc.)
        """
        costs = await self.storage.query(session_id=session_id, agent_name=agent_name)

        if not costs:
            return {
                "total_cost": 0.0,
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_thinking_tokens": 0,
                "avg_cost_per_request": 0.0,
            }

        total_cost = sum(c.total_cost for c in costs)
        total_input_tokens = sum(c.input_tokens for c in costs)
        total_output_tokens = sum(c.output_tokens for c in costs)
        total_thinking_tokens = sum(c.thinking_tokens for c in costs)

        return {
            "total_cost": total_cost,
            "total_requests": len(costs),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_thinking_tokens": total_thinking_tokens,
            "total_tokens": total_input_tokens + total_output_tokens + total_thinking_tokens,
            "avg_cost_per_request": total_cost / len(costs),
            "avg_tokens_per_request": (
                total_input_tokens + total_output_tokens + total_thinking_tokens
            )
            / len(costs),
        }


# Deprecated alias — use MemoryStorage in new code.
InMemoryStorage = MemoryStorage  # Deprecated: Use MemoryStorage instead.
