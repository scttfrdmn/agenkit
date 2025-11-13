"""
Core orchestration patterns for agenkit.

Patterns are reusable ways to compose agents:
- Sequential: Execute agents one after another (pipeline)
- Parallel: Execute agents concurrently (fan-out)
- Router: Route to one agent based on condition (dispatch)

Design principles:
- Simple, obvious implementations
- No magic, no surprises
- Composable (patterns can contain patterns)
- Observable (hooks for monitoring)
"""

import asyncio
from collections.abc import Callable

from agenkit.interfaces import Agent, Message

__all__ = ["ParallelPattern", "RouterPattern", "SequentialPattern"]


class SequentialPattern(Agent):
    """
    Execute agents sequentially - output of one becomes input of next.

    This is the simplest and most common pattern: agent1 → agent2 → agent3

    Performance characteristics:
    - No overhead vs calling agents directly
    - Agents execute in order (no parallelism)
    - Short-circuits on error (stops at first failure)

    Usage:
        >>> pipeline = SequentialPattern([agent1, agent2, agent3])
        >>> result = await pipeline.process(Message(role="user", content="input"))
    """

    def __init__(
        self,
        agents: list[Agent],
        name: str = "sequential",
        before_agent: Callable[[Agent, Message], None] | None = None,
        after_agent: Callable[[Agent, Message], None] | None = None,
    ) -> None:
        """
        Create a sequential execution pattern.

        Args:
            agents: List of agents to execute in order
            name: Pattern name (for identification)
            before_agent: Optional hook called before each agent
            after_agent: Optional hook called after each agent

        Raises:
            ValueError: If agents list is empty
        """
        if not agents:
            raise ValueError("Sequential pattern requires at least one agent")

        self._agents = agents
        self._name = name
        self._before_agent = before_agent
        self._after_agent = after_agent

    @property
    def name(self) -> str:
        """Pattern name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """
        Combined capabilities of all agents.

        Returns:
            List of unique capabilities across all agents
        """
        caps: set[str] = set()
        for agent in self._agents:
            caps.update(agent.capabilities)
        return list(caps)

    async def process(self, message: Message) -> Message:
        """
        Execute agents sequentially.

        Args:
            message: Initial input message

        Returns:
            Final message after all agents have processed

        Raises:
            Exception: Any exception raised by agents propagates
        """
        # Cache attributes as locals (faster than self.attr lookups)
        agents = self._agents
        before_hook = self._before_agent
        after_hook = self._after_agent

        current = message

        for agent in agents:
            # Hook: before agent
            if before_hook is not None:
                before_hook(agent, current)

            # Process
            current = await agent.process(current)

            # Hook: after agent
            if after_hook is not None:
                after_hook(agent, current)

        return current

    def unwrap(self) -> list[Agent]:
        """
        Get underlying agents list.

        Returns:
            List of agents in execution order
        """
        return self._agents.copy()


class ParallelPattern(Agent):
    """
    Execute agents in parallel and aggregate results.

    All agents receive the same input, execute concurrently, results are combined.

    Performance characteristics:
    - True parallelism (uses asyncio.gather)
    - Bounded by slowest agent
    - Memory: O(n) where n = number of agents

    Usage:
        >>> parallel = ParallelPattern(
        ...     [agent1, agent2, agent3],
        ...     aggregator=lambda results: combine_results(results)
        ... )
        >>> result = await parallel.process(Message(role="user", content="input"))
    """

    def __init__(
        self,
        agents: list[Agent],
        aggregator: Callable[[list[Message]], Message] | None = None,
        name: str = "parallel",
    ) -> None:
        """
        Create a parallel execution pattern.

        Args:
            agents: List of agents to execute concurrently
            aggregator: Function to combine results (default: takes first)
            name: Pattern name (for identification)

        Raises:
            ValueError: If agents list is empty
        """
        if not agents:
            raise ValueError("Parallel pattern requires at least one agent")

        self._agents = agents
        self._aggregator = aggregator or self._default_aggregator
        self._name = name

    @staticmethod
    def _default_aggregator(messages: list[Message]) -> Message:
        """
        Default aggregation: combine all content into metadata, return first.

        Args:
            messages: Results from all agents

        Returns:
            First message with all results in metadata
        """
        if not messages:
            raise ValueError("No messages to aggregate")

        first = messages[0]
        # Put all results in metadata for inspection
        all_results = [
            {"role": msg.role, "content": msg.content, "metadata": msg.metadata}
            for msg in messages
        ]

        return Message(
            role=first.role,
            content=first.content,
            metadata={**first.metadata, "parallel_results": all_results},
        )

    @property
    def name(self) -> str:
        """Pattern name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """
        Combined capabilities of all agents.

        Returns:
            List of unique capabilities across all agents
        """
        caps: set[str] = set()
        for agent in self._agents:
            caps.update(agent.capabilities)
        return list(caps)

    async def process(self, message: Message) -> Message:
        """
        Execute agents in parallel and aggregate results.

        Args:
            message: Input message (sent to all agents)

        Returns:
            Aggregated message from all agents

        Raises:
            Exception: If any agent raises, all are cancelled and exception propagates
        """
        # Execute all agents concurrently
        tasks = [agent.process(message) for agent in self._agents]
        results = await asyncio.gather(*tasks)

        # Aggregate results
        return self._aggregator(results)

    def unwrap(self) -> list[Agent]:
        """
        Get underlying agents list.

        Returns:
            List of agents (no particular order)
        """
        return self._agents.copy()


class RouterPattern(Agent):
    """
    Route message to one agent based on routing function.

    The routing function decides which agent should handle the message.

    Performance characteristics:
    - O(1) routing decision
    - Only one agent executes
    - No overhead vs direct agent call

    Usage:
        >>> def route(msg: Message) -> str:
        ...     if "code" in msg.content:
        ...         return "code_agent"
        ...     return "general_agent"
        >>>
        >>> router = RouterPattern(
        ...     router=route,
        ...     handlers={"code_agent": code_agent, "general_agent": general_agent}
        ... )
        >>> result = await router.process(Message(role="user", content="Write code"))
    """

    def __init__(
        self,
        router: Callable[[Message], str],
        handlers: dict[str, Agent],
        default: Agent | None = None,
        name: str = "router",
    ) -> None:
        """
        Create a routing pattern.

        Args:
            router: Function that returns handler key for a message
            handlers: Map of handler keys to agents
            default: Optional default agent if router returns unknown key
            name: Pattern name (for identification)

        Raises:
            ValueError: If handlers dict is empty
        """
        if not handlers:
            raise ValueError("Router pattern requires at least one handler")

        self._router = router
        self._handlers = handlers
        self._default = default
        self._name = name
        self._has_default = default is not None

    @property
    def name(self) -> str:
        """Pattern name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """
        Combined capabilities of all handlers.

        Returns:
            List of unique capabilities across all handlers
        """
        caps: set[str] = set()
        for agent in self._handlers.values():
            caps.update(agent.capabilities)
        if self._default is not None:
            caps.update(self._default.capabilities)
        return list(caps)

    async def process(self, message: Message) -> Message:
        """
        Route message to appropriate handler and execute.

        Args:
            message: Input message to route

        Returns:
            Message from selected handler

        Raises:
            KeyError: If router returns unknown key and no default handler
            Exception: Any exception from selected agent propagates
        """
        # Cache attributes as locals (faster than self.attr lookups)
        router = self._router
        handlers = self._handlers

        # Get handler key
        handler_key = router(message)

        # Fast path: try/except is faster than .get() for success case
        try:
            handler = handlers[handler_key]
        except KeyError:
            if self._has_default:
                # We know self._default is not None because _has_default is True
                assert self._default is not None
                handler = self._default
            else:
                raise KeyError(
                    f"Router returned unknown key '{handler_key}' and no default handler"
                )

        # Execute handler
        return await handler.process(message)

    def unwrap(self) -> dict[str, Agent]:
        """
        Get underlying handlers dict.

        Returns:
            Dict mapping handler keys to agents
        """
        return self._handlers.copy()
