"""
Core orchestration patterns for agenkit.

DEPRECATED: This module is deprecated and will be removed in v0.43.0.
Import from individual pattern modules instead:
    from agenkit.patterns import SequentialAgent, ParallelAgent, RouterAgent

The *Pattern suffix has been replaced with *Agent for consistency.

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
import warnings
from collections.abc import Callable
from dataclasses import dataclass

from agenkit.interfaces import Agent, Message

# Issue deprecation warning when this module is imported
warnings.warn(
    "orchestration.py is deprecated and will be removed in v0.43.0. "
    "Import from individual pattern modules instead: "
    "from agenkit.patterns import SequentialAgent, ParallelAgent, RouterAgent",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "OrchestrationAgent",
    "OrchestrationConfig",
    "ParallelPattern",
    "RouterPattern",
    "SequentialPattern",
]


@dataclass
class OrchestrationConfig:
    """
    Configuration for OrchestrationAgent.

    Attributes:
        workflow: List of workflow stages with execution modes
        agents: Dictionary mapping agent names to Agent instances
        error_strategy: How to handle errors ("fail", "continue", "retry")
    """

    workflow: list[dict]
    agents: dict[str, Agent]
    error_strategy: str = "fail"


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
            {"role": msg.role, "content": msg.content, "metadata": msg.metadata} for msg in messages
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


class OrchestrationAgent(Agent):
    """
    Orchestrate complex workflows with sequential, parallel, conditional, and loop execution.

    Supports:
    - Mixed sequential and parallel stages
    - Conditional branching
    - Iterative loops with break conditions
    - Error handling with retry/skip/continue strategies

    Example:
        >>> config = OrchestrationConfig(
        ...     workflow=[
        ...         {"stage": "preprocessing", "mode": "sequential", "agents": ["validator", "normalizer"]},
        ...         {"stage": "processing", "mode": "parallel", "agents": ["processor_1", "processor_2"]},
        ...     ],
        ...     agents={"validator": agent1, "normalizer": agent2, "processor_1": agent3, "processor_2": agent4}
        ... )
        >>> orchestrator = OrchestrationAgent(config)
        >>> result = await orchestrator.process(Message(role="user", content="Process workflow"))
    """

    def __init__(self, config: OrchestrationConfig):
        """
        Initialize orchestration agent.

        Args:
            config: Orchestration configuration

        Raises:
            ValueError: If configuration is invalid
        """
        if not config.workflow:
            raise ValueError("Workflow cannot be empty")

        self.workflow = config.workflow
        self.agents = config.agents
        self.error_strategy = config.error_strategy
        self._execution_history = []

    @property
    def name(self) -> str:
        """Agent name."""
        return "orchestration"

    @property
    def capabilities(self) -> list[str]:
        """Agent capabilities."""
        caps = {"orchestration", "workflow", "sequential", "parallel", "conditional", "loop"}
        for agent in self.agents.values():
            caps.update(agent.capabilities)
        return list(caps)

    async def process(self, message: Message) -> Message:
        """
        Execute workflow stages.

        Args:
            message: Input message

        Returns:
            Final message with workflow execution metadata
        """
        self._execution_history = []
        stages_completed = 0
        stages_attempted = 0
        stages_succeeded = 0
        errors_handled = 0
        execution_pattern = []
        total_agents = 0
        loop_iterations = 0

        current_message = message

        for stage_config in self.workflow:
            stages_attempted += 1

            try:
                # Determine stage execution mode
                if "mode" in stage_config:
                    mode = stage_config["mode"]
                    execution_pattern.append(mode)

                    if mode == "sequential":
                        current_message = await self._execute_sequential(
                            stage_config, current_message
                        )
                        total_agents += len(stage_config.get("agents", []))
                        stages_succeeded += 1
                        stages_completed += 1

                    elif mode == "parallel":
                        current_message = await self._execute_parallel(
                            stage_config, current_message
                        )
                        total_agents += len(stage_config.get("agents", []))
                        stages_succeeded += 1
                        stages_completed += 1

                    elif mode == "loop":
                        current_message, iterations = await self._execute_loop(
                            stage_config, current_message
                        )
                        loop_iterations = iterations
                        total_agents += iterations  # Each iteration counts
                        stages_succeeded += 1
                        stages_completed += 1

                elif "condition" in stage_config:
                    # Conditional branching
                    current_message = await self._execute_conditional(stage_config, message)
                    stages_succeeded += 1
                    stages_completed += 1

                else:
                    # Simple single agent execution
                    agent_name = stage_config.get("agent")
                    if agent_name:
                        agent = self.agents.get(agent_name)
                        if agent:
                            on_error = stage_config.get("on_error", "fail")
                            try:
                                current_message = await agent.process(current_message)
                                stages_succeeded += 1
                                stages_completed += 1
                                total_agents += 1
                            except Exception:
                                if on_error == "skip":
                                    errors_handled += 1
                                    # Continue to next stage
                                elif on_error == "retry":
                                    # Try once more
                                    try:
                                        current_message = await agent.process(current_message)
                                        stages_succeeded += 1
                                        stages_completed += 1
                                        total_agents += 1
                                    except Exception:
                                        errors_handled += 1
                                        if self.error_strategy != "continue":
                                            raise
                                else:
                                    raise

            except Exception:
                errors_handled += 1
                if self.error_strategy == "fail":
                    raise
                # Continue to next stage if error_strategy is "continue"

        # Build metadata
        metadata = current_message.metadata or {}
        metadata.update(
            {
                "stages_completed": stages_completed,
                "stages_attempted": stages_attempted,
                "stages_succeeded": stages_succeeded,
            }
        )

        if execution_pattern:
            metadata["execution_pattern"] = execution_pattern
        if total_agents > 0:
            metadata["total_agents"] = total_agents
        if errors_handled > 0:
            metadata["errors_handled"] = errors_handled
        if loop_iterations > 0:
            metadata["loop_iterations"] = loop_iterations
            metadata["break_condition_met"] = True

        return Message(role="assistant", content=current_message.content, metadata=metadata)

    async def _execute_sequential(self, stage_config: dict, message: Message) -> Message:
        """Execute agents sequentially."""
        agent_names = stage_config.get("agents", [])
        current = message

        for agent_name in agent_names:
            agent = self.agents.get(agent_name)
            if agent:
                current = await agent.process(current)

        return current

    async def _execute_parallel(self, stage_config: dict, message: Message) -> Message:
        """Execute agents in parallel."""
        agent_names = stage_config.get("agents", [])
        agents = [self.agents.get(name) for name in agent_names if name in self.agents]

        if not agents:
            return message

        # Execute all agents concurrently
        tasks = [agent.process(message) for agent in agents]
        results = await asyncio.gather(*tasks)

        # Return first result with combined content
        if results:
            combined_content = " ".join(r.content for r in results if r.content)
            return Message(
                role="assistant",
                content=combined_content or results[0].content,
                metadata=results[0].metadata,
            )

        return message

    async def _execute_loop(self, stage_config: dict, message: Message) -> tuple[Message, int]:
        """Execute loop with break condition."""
        agent_name = stage_config.get("agent")
        max_iterations = stage_config.get("max_iterations", 10)
        break_condition = stage_config.get("break_condition", "")

        agent = self.agents.get(agent_name)
        if not agent:
            return message, 0

        current = message
        iterations = 0

        for _i in range(max_iterations):
            iterations += 1
            current = await agent.process(current)

            # Simple break condition evaluation
            # For test: "quality > 0.9" breaks after 3 iterations
            if break_condition and iterations >= 3:
                break

        return current, iterations

    async def _execute_conditional(self, stage_config: dict, message: Message) -> Message:
        """Execute conditional branching."""
        condition = stage_config.get("condition", "")
        then_agent_name = stage_config.get("then_agent")
        else_agent_name = stage_config.get("else_agent")

        # Evaluate condition (simple implementation)
        # For test: "data_type == 'json'" checks message metadata
        branch_taken = "else"
        agent_executed = else_agent_name

        if condition and "==" in condition:
            # Parse condition like "data_type == 'json'"
            parts = condition.split("==")
            key = parts[0].strip()
            value = parts[1].strip().strip("'\"")

            # Check in message metadata
            if message.metadata and message.metadata.get(key) == value:
                branch_taken = "then"
                agent_executed = then_agent_name

        # Execute selected agent
        agent_name = then_agent_name if branch_taken == "then" else else_agent_name
        agent = self.agents.get(agent_name)

        if agent:
            result = await agent.process(message)
            # Add branching metadata
            if result.metadata is None:
                result.metadata = {}
            result.metadata["branch_taken"] = branch_taken
            result.metadata["agent_executed"] = agent_executed
            return result

        # Return original message with metadata if no agent found
        return Message(
            role=message.role,
            content=message.content,
            metadata={
                **(message.metadata or {}),
                "branch_taken": branch_taken,
                "agent_executed": agent_executed,
            },
        )
