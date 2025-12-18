"""
Multi-Agent Collaboration Pattern

Enables multiple agents to work together on complex tasks through:
- Coordination: Agents working on different parts simultaneously
- Delegation: Agents delegating subtasks to specialists
- Consensus: Agents reaching agreement through discussion

This pattern is useful for:
- Complex tasks requiring diverse expertise
- Parallelizable workflows
- Problems benefiting from multiple perspectives
"""

from dataclasses import dataclass
from typing import Any

from agenkit import Agent, Message


@dataclass
class AgentTask:
    """A task assigned to an agent."""

    agent_name: str
    description: str
    result: Any = None
    status: str = "pending"  # pending, in_progress, completed, failed
    error: str | None = None


@dataclass
class MultiAgentConfig:
    """
    Configuration for MultiAgentOrchestrator.

    This config-based approach provides:
    - Cross-language API consistency (matches Go/C++/Rust/TypeScript/Zig)
    - Better documentation (all parameters in one place)
    - Type safety and IDE autocomplete
    - Extensibility without breaking changes

    Attributes:
        strategy: Execution strategy - "sequential", "parallel", or "delegate" (default: "sequential")
        agents: Optional initial agents to register (default: empty dict)

    Example:
        >>> from agenkit.patterns import MultiAgentOrchestrator, MultiAgentConfig
        >>> config = MultiAgentConfig(
        ...     strategy="parallel",
        ...     agents={"researcher": research_agent, "writer": writing_agent}
        ... )
        >>> orchestrator = MultiAgentOrchestrator(config)
    """

    strategy: str = "sequential"
    agents: dict[str, Agent] | None = None

    def __post_init__(self):
        """Validate configuration."""
        valid_strategies = {"sequential", "parallel", "delegate"}
        if self.strategy not in valid_strategies:
            raise ValueError(f"strategy must be one of {valid_strategies}")
        if self.agents is None:
            self.agents = {}


@dataclass
class ConsensusConfig:
    """
    Configuration for ConsensusAgent.

    This config-based approach provides:
    - Cross-language API consistency (matches Go/C++/Rust/TypeScript/Zig)
    - Better documentation (all parameters in one place)
    - Type safety and IDE autocomplete
    - Extensibility without breaking changes

    Attributes:
        voting_strategy: Strategy for reaching consensus - "majority", "unanimous", etc. (default: "majority")
        agents: Optional initial agents to add (default: empty list)

    Example:
        >>> from agenkit.patterns import ConsensusAgent, ConsensusConfig
        >>> config = ConsensusConfig(
        ...     voting_strategy="unanimous",
        ...     agents=[agent1, agent2, agent3]
        ... )
        >>> consensus = ConsensusAgent(config)
    """

    voting_strategy: str = "majority"
    agents: list[Agent] | None = None

    def __post_init__(self):
        """Validate configuration."""
        if self.agents is None:
            self.agents = []


class MultiAgentOrchestrator(Agent):
    """
    Orchestrates multiple agents working together.

    Example (recommended config-based API):
        ```python
        from agenkit.patterns import MultiAgentOrchestrator, MultiAgentConfig

        config = MultiAgentConfig(
            strategy="sequential",
            agents={"researcher": research_agent, "writer": writing_agent}
        )
        orchestrator = MultiAgentOrchestrator(config)

        result = await orchestrator.process(
            Message(role="user", content="Write a research report")
        )
        ```

    Example (deprecated direct parameters):
        ```python
        # This API is deprecated and will be removed in v2.0
        orchestrator = MultiAgentOrchestrator(strategy="sequential")
        orchestrator.register_agent("researcher", research_agent)
        ```

    Args:
        config: Configuration object (recommended, matches other languages)
        strategy: (Deprecated) Execution strategy
    """

    def __init__(
        self,
        config: MultiAgentConfig | None = None,
        *,
        # Deprecated parameters (kept for backward compatibility)
        strategy: str = "sequential",
    ):
        """
        Initialize MultiAgentOrchestrator.

        Args:
            config: Configuration object (recommended, matches other languages)
            strategy: (Deprecated) Execution strategy

        Examples:
            >>> # Recommended: config-based (matches all other languages)
            >>> config = MultiAgentConfig(strategy="parallel", agents={"researcher": agent1})
            >>> orchestrator = MultiAgentOrchestrator(config)
            >>>
            >>> # Deprecated: direct parameters (will be removed in v2.0)
            >>> orchestrator = MultiAgentOrchestrator(strategy="sequential")

        Migration:
            Old code:
                orchestrator = MultiAgentOrchestrator(strategy="parallel")
                orchestrator.register_agent("researcher", research_agent)

            New code:
                config = MultiAgentConfig(
                    strategy="parallel",
                    agents={"researcher": research_agent}
                )
                orchestrator = MultiAgentOrchestrator(config)
        """
        import warnings

        if config is not None:
            # New config-based API (recommended)
            self.strategy = config.strategy
            self.agents = config.agents.copy() if config.agents else {}
        else:
            # Old direct-parameter API (deprecated)
            warnings.warn(
                "Direct parameters for MultiAgentOrchestrator are deprecated and will be removed in v2.0. "
                "Use MultiAgentConfig instead: "
                "MultiAgentOrchestrator(MultiAgentConfig(strategy=...)). "
                "See migration guide for details.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.strategy = strategy
            self.agents = {}

        self.tasks: list[AgentTask] = []

    @property
    def name(self) -> str:
        return "MultiAgentOrchestrator"

    def register_agent(self, name: str, agent: Agent) -> None:
        """Register an agent that can be used."""
        self.agents[name] = agent

    def unregister_agent(self, name: str) -> None:
        """Remove an agent."""
        self.agents.pop(name, None)

    def list_agents(self) -> list[str]:
        """Get list of registered agents."""
        return list(self.agents.keys())

    async def process(self, message: Message) -> Message:
        """Process message by coordinating multiple agents."""
        # Simple implementation: delegate to all agents sequentially
        results = []

        for agent_name, agent in self.agents.items():
            task = AgentTask(agent_name=agent_name, description=message.content)
            task.status = "in_progress"
            self.tasks.append(task)

            try:
                response = await agent.process(message)
                task.result = response.content
                task.status = "completed"
                results.append(f"{agent_name}: {response.content}")
            except Exception as e:
                task.error = str(e)
                task.status = "failed"
                results.append(f"{agent_name}: Failed - {e}")

        combined_result = "\n\n".join(results)
        return Message(role="assistant", content=combined_result)

    def get_tasks(self) -> list[AgentTask]:
        """Get all tasks executed."""
        return self.tasks.copy()


class ConsensusAgent(Agent):
    """
    Reaches consensus among multiple agents.

    Example (recommended config-based API):
        ```python
        from agenkit.patterns import ConsensusAgent, ConsensusConfig

        config = ConsensusConfig(
            voting_strategy="majority",
            agents=[agent1, agent2, agent3]
        )
        consensus = ConsensusAgent(config)

        result = await consensus.process(
            Message(role="user", content="What's the best approach?")
        )
        # Result combines perspectives from all agents
        ```

    Example (deprecated direct parameters):
        ```python
        # This API is deprecated and will be removed in v2.0
        consensus = ConsensusAgent(voting_strategy="majority")
        consensus.add_agent(agent1)
        ```

    Args:
        config: Configuration object (recommended, matches other languages)
        voting_strategy: (Deprecated) Strategy for reaching consensus
    """

    def __init__(
        self,
        config: ConsensusConfig | None = None,
        *,
        # Deprecated parameters (kept for backward compatibility)
        voting_strategy: str = "majority",
    ):
        """
        Initialize ConsensusAgent.

        Args:
            config: Configuration object (recommended, matches other languages)
            voting_strategy: (Deprecated) Strategy for reaching consensus

        Examples:
            >>> # Recommended: config-based (matches all other languages)
            >>> config = ConsensusConfig(voting_strategy="unanimous", agents=[agent1, agent2])
            >>> consensus = ConsensusAgent(config)
            >>>
            >>> # Deprecated: direct parameters (will be removed in v2.0)
            >>> consensus = ConsensusAgent(voting_strategy="majority")

        Migration:
            Old code:
                consensus = ConsensusAgent(voting_strategy="unanimous")
                consensus.add_agent(agent1)
                consensus.add_agent(agent2)

            New code:
                config = ConsensusConfig(
                    voting_strategy="unanimous",
                    agents=[agent1, agent2]
                )
                consensus = ConsensusAgent(config)
        """
        import warnings

        if config is not None:
            # New config-based API (recommended)
            self.voting_strategy = config.voting_strategy
            self.agents = config.agents.copy() if config.agents else []
        else:
            # Old direct-parameter API (deprecated)
            warnings.warn(
                "Direct parameters for ConsensusAgent are deprecated and will be removed in v2.0. "
                "Use ConsensusConfig instead: "
                "ConsensusAgent(ConsensusConfig(voting_strategy=...)). "
                "See migration guide for details.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.voting_strategy = voting_strategy
            self.agents = []

    @property
    def name(self) -> str:
        return "ConsensusAgent"

    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the consensus group."""
        self.agents.append(agent)

    async def process(self, message: Message) -> Message:
        """Get responses from all agents and form consensus."""
        responses = []

        for agent in self.agents:
            response = await agent.process(message)
            responses.append(response.content)

        # Simple consensus: combine all responses
        consensus = f"Consensus from {len(responses)} agents:\n\n"
        consensus += "\n\n".join([f"Agent {i + 1}: {r}" for i, r in enumerate(responses)])

        return Message(role="assistant", content=consensus)
