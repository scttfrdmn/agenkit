"""
Fallback Agent Pattern

Fallback pattern implements sequential retry across multiple agents.
If one agent fails, the next agent is tried until one succeeds or
all agents are exhausted.

Key concepts:
- Sequential attempt order
- Automatic failover on errors
- First successful result wins
- Error collection for debugging

Performance characteristics:
- Best case: O(first agent) - immediate success
- Worst case: O(sum of all agents) - all fail
- Early termination on first success
"""

from collections.abc import Callable
from dataclasses import dataclass

from agenkit import Agent, Message


@dataclass
class AttemptResult:
    """Holds the result of a single agent attempt."""

    agent_index: int
    agent_name: str
    success: bool
    message: Message | None
    error: Exception | None


# Type alias for recovery function
RecoveryFunc = Callable[[Message, Exception], Message]


class FallbackAgent(Agent):
    """
    Tries agents in sequence until one succeeds.

    Each agent is attempted in order. The first agent to return a successful
    response wins, and that response is returned immediately. If an agent
    fails, the next agent is tried. If all agents fail, an error combining
    all failure reasons is raised.

    Example use cases:
    - High availability: fallback from primary to backup systems
    - Multi-provider: try different LLM providers until one succeeds
    - Graceful degradation: try advanced model, fallback to simple model
    - Retry with alternatives: different strategies for same task
    - Error recovery: fallback to cached/default responses

    The fallback pattern is ideal when you need resilience and have
    multiple ways to accomplish the same task.

    Example:
        ```python
        from agenkit.patterns import FallbackAgent

        # Create fallback chain
        agent = FallbackAgent(agents=[primary_agent, backup_agent, default_agent])

        # Will try primary, then backup, then default
        result = await agent.process(
            Message(role="user", content="Generate response")
        )
        ```
    """

    def __init__(self, agents: list[Agent]) -> None:
        """
        Create a new fallback agent.

        Args:
            agents: List of agents to try in order (must have at least one)

        Raises:
            ValueError: If agents list is empty

        Agents are tried in the order provided. The first successful response
        is returned immediately without trying remaining agents.
        """
        if not agents:
            raise ValueError("at least one agent is required")

        self._agents = agents

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return "FallbackAgent"

    @property
    def capabilities(self) -> list[str]:
        """Return the combined capabilities of all agents."""
        cap_set = set()

        for agent in self._agents:
            cap_set.update(agent.capabilities)

        capabilities = list(cap_set)
        capabilities.extend(["fallback", "retry", "high-availability"])

        return capabilities

    async def process(self, message: Message) -> Message:
        """
        Try agents sequentially until one succeeds.

        Each agent is attempted in order. If an agent succeeds, its response
        is returned immediately with metadata about the attempt. If an agent
        fails, the next agent is tried.

        If all agents fail, an error is raised that includes information
        about all failed attempts.

        The successful message includes metadata about:
        - Which agent succeeded
        - How many attempts were made
        - Which agents were tried

        Args:
            message: Input message to process

        Returns:
            Response from the first successful agent

        Raises:
            ValueError: If message is None
            RuntimeError: If all agents failed
        """
        if message is None:
            raise ValueError("message cannot be None")

        attempts: list[AttemptResult] = []

        for i, agent in enumerate(self._agents):
            # Try agent
            try:
                result = await agent.process(message)
                error = None
                success = True
            except Exception as e:
                result = None
                error = e
                success = False

            # Record attempt
            attempt = AttemptResult(
                agent_index=i,
                agent_name=agent.name,
                success=success,
                message=result,
                error=error,
            )
            attempts.append(attempt)

            # If successful, return immediately
            if success:
                return self._build_success_result(result, attempts)  # type: ignore

            # Agent failed, try next (if available)
            # Error will be included in final error if all fail

        # All agents failed
        raise self._build_failure_error(attempts)

    def _build_success_result(self, message: Message, attempts: list[AttemptResult]) -> Message:
        """Add fallback metadata to successful response."""
        if message.metadata is None:
            message.metadata = {}

        successful_attempt = attempts[-1]

        message.metadata["fallback_attempts"] = len(attempts)
        message.metadata["fallback_success_index"] = successful_attempt.agent_index
        message.metadata["fallback_success_agent"] = successful_attempt.agent_name
        message.metadata["fallback_total_agents"] = len(self._agents)

        # Include failed attempts for observability
        if len(attempts) > 1:
            failed_attempts = [
                {
                    "index": attempt.agent_index,
                    "agent": attempt.agent_name,
                    "error": str(attempt.error),
                }
                for attempt in attempts[:-1]
            ]
            message.metadata["fallback_failed_attempts"] = failed_attempts

        return message

    def _build_failure_error(self, attempts: list[AttemptResult]) -> RuntimeError:
        """Create a comprehensive error from all failed attempts."""
        error_parts = [f"all {len(attempts)} agents failed:"]

        for attempt in attempts:
            error_parts.append(f"  [{attempt.agent_index}] {attempt.agent_name}: {attempt.error}")

        error_msg = "\n".join(error_parts)
        return RuntimeError(error_msg)


class RecoveryAgent(Agent):
    """
    Wraps an agent with a recovery function.

    This agent tries a primary agent, and if it fails, calls a recovery
    function to generate a fallback response.

    Example:
        ```python
        from agenkit.patterns.fallback import RecoveryAgent, default_recovery

        # Create recovery agent
        agent = RecoveryAgent(
            agent=primary_agent,
            recovery_func=default_recovery.static_message(
                "I'm experiencing technical difficulties. Please try again."
            )
        )
        ```
    """

    def __init__(self, agent: Agent, recovery_func: RecoveryFunc) -> None:
        """
        Create a recovery agent.

        Args:
            agent: Primary agent to execute
            recovery_func: Function to call on failure
        """
        self._agent = agent
        self._recovery_func = recovery_func

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return f"{self._agent.name}+Recovery"

    @property
    def capabilities(self) -> list[str]:
        """Return the agent's capabilities plus recovery."""
        caps = self._agent.capabilities
        return [*caps, "recovery", "error-handling"]

    async def process(self, message: Message) -> Message:
        """Execute the agent with recovery on failure."""
        try:
            return await self._agent.process(message)
        except Exception as e:
            # Primary agent failed, try recovery
            try:
                recovered = self._recovery_func(message, e)
            except Exception as recovery_err:
                raise RuntimeError(
                    f"primary agent failed: {e}; recovery failed: {recovery_err}"
                ) from e

            # Add recovery metadata
            if recovered.metadata is None:
                recovered.metadata = {}
            recovered.metadata["recovery_used"] = True
            recovered.metadata["original_error"] = str(e)

            return recovered


class DefaultRecovery:
    """Default recovery strategies."""

    @staticmethod
    def static_message(content: str) -> RecoveryFunc:
        """
        Return a fixed fallback message.

        Args:
            content: Message content to return on failure

        Returns:
            Recovery function that returns static message

        Example:
            ```python
            recovery = default_recovery.static_message(
                "Service unavailable. Please try again later."
            )
            ```
        """

        def recover(message: Message, error: Exception) -> Message:
            return Message(role="assistant", content=content)

        return recover

    @staticmethod
    def empty_response(message: Message, error: Exception) -> Message:
        """
        Return an empty but valid response.

        Args:
            message: Original message
            error: Error that occurred

        Returns:
            Empty message
        """
        return Message(role="assistant", content="")


# Singleton instance for convenience
default_recovery = DefaultRecovery()


def with_recovery(agent: Agent, recovery_func: RecoveryFunc) -> RecoveryAgent:
    """
    Helper function to wrap an agent with recovery logic.

    Args:
        agent: Agent to wrap
        recovery_func: Recovery function to use

    Returns:
        RecoveryAgent wrapping the provided agent

    Example:
        ```python
        from agenkit.patterns.fallback import with_recovery, default_recovery

        agent = with_recovery(
            primary_agent,
            default_recovery.static_message("Error occurred")
        )
        ```
    """
    return RecoveryAgent(agent=agent, recovery_func=recovery_func)
