"""
Parallel Agent Pattern

Parallel pattern enables concurrent execution of multiple agents with
result aggregation. This is ideal for ensemble methods, multi-perspective
analysis, or parallelizing independent tasks.

Key concepts:
- Concurrent agent execution using asyncio
- Custom aggregation function for combining results
- All agents receive the same input message
- Results collected and aggregated after all complete

Performance characteristics:
- Time: O(max agent time) - parallel execution
- Memory: O(n * message size) for concurrent processing
- Thread-safe with proper async coordination
"""

import asyncio
from collections.abc import Callable
from typing import Any

from agenkit import Agent, Message

# Type alias for aggregator functions
AggregatorFunc = Callable[[list[Message]], Message]


class ParallelAgent(Agent):
    """
    Executes multiple agents concurrently and aggregates results.

    All agents receive the same input message and execute concurrently.
    Results are collected and passed to the aggregator function which
    produces the final output.

    Example use cases:
    - Multi-model ensemble for improved accuracy
    - Parallel document analysis (sentiment, entities, topics)
    - A/B testing different agent implementations
    - Redundant processing for reliability

    If any agent fails, the error is collected but other agents continue.
    The aggregator receives all successful results.

    Example:
        ```python
        from agenkit.patterns import ParallelAgent, default_aggregators

        # Create a parallel agent
        agent = ParallelAgent(
            agents=[model1, model2, model3],
            aggregator=default_aggregators.majority_vote
        )

        result = await agent.process(Message(role="user", content="Analyze sentiment"))
        ```
    """

    def __init__(
        self,
        agents: list[Agent],
        aggregator: AggregatorFunc,
    ) -> None:
        """
        Create a new parallel execution agent.

        Args:
            agents: List of agents to execute concurrently (must have at least one)
            aggregator: Function to combine agent results into final output

        Raises:
            ValueError: If agents list is empty or aggregator is None

        The aggregator function is called with all successful agent responses
        and must return a single aggregated message.
        """
        if not agents:
            raise ValueError("at least one agent is required")
        if aggregator is None:
            raise ValueError("aggregator function is required")

        self._agents = agents
        self._aggregator = aggregator

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return "ParallelAgent"

    def capabilities(self) -> list[str]:
        """Return the combined capabilities of all agents."""
        cap_set = set()
        for agent in self._agents:
            cap_set.update(agent.capabilities())

        capabilities = list(cap_set)
        capabilities.extend(["parallel", "ensemble"])

        return capabilities

    async def process(self, message: Message) -> Message:
        """
        Execute all agents concurrently and aggregate results.

        All agents receive the same input message and execute in parallel using
        asyncio.gather. Results are collected as they complete. Once all agents finish
        (or fail), successful results are passed to the aggregator function.

        If all agents fail, an error is raised. If some agents succeed, their
        results are aggregated and any errors are recorded in metadata.

        The final message includes metadata about:
        - Total agents executed
        - Successful agent results
        - Any errors that occurred

        Args:
            message: Input message to process

        Returns:
            Aggregated message from successful agent results

        Raises:
            ValueError: If message is None
            RuntimeError: If all agents failed
        """
        if message is None:
            raise ValueError("message cannot be None")

        # Launch all agents concurrently
        tasks = [agent.process(message) for agent in self._agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successes and errors
        successes: list[Message] = []
        errors: list[dict[str, Any]] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append({
                    "agent": self._agents[i].name,
                    "error": str(result),
                })
            else:
                successes.append(result)

        # Check if all agents failed
        if not successes:
            raise RuntimeError(f"all agents failed: {errors}")

        # Aggregate successful results
        aggregated = self._aggregator(successes)

        # Add parallel execution metadata
        if aggregated.metadata is None:
            aggregated.metadata = {}
        aggregated.metadata["parallel_agents"] = len(self._agents)
        aggregated.metadata["successful_agents"] = len(successes)
        if errors:
            aggregated.metadata["errors"] = errors

        return aggregated


class DefaultAggregators:
    """Default aggregation strategies for parallel agents."""

    @staticmethod
    def first(messages: list[Message]) -> Message:
        """
        Return the first successful result.

        Args:
            messages: List of messages from successful agents

        Returns:
            The first message in the list
        """
        if not messages:
            return Message(role="assistant", content="No results to aggregate")
        return messages[0]

    @staticmethod
    def concatenate(messages: list[Message]) -> Message:
        """
        Combine all responses with separator.

        Args:
            messages: List of messages from successful agents

        Returns:
            Message with all contents concatenated
        """
        if not messages:
            return Message(role="assistant", content="No results to aggregate")

        combined = "\n\n---\n\n".join(msg.content for msg in messages)
        return Message(role="assistant", content=combined)

    @staticmethod
    def majority_vote(messages: list[Message]) -> Message:
        """
        Return the most common response.

        Args:
            messages: List of messages from successful agents

        Returns:
            Message with the most common content, with vote counts in metadata
        """
        if not messages:
            return Message(role="assistant", content="No results to aggregate")

        # Count occurrences of each response
        votes: dict[str, int] = {}
        msg_by_content: dict[str, Message] = {}

        for msg in messages:
            votes[msg.content] = votes.get(msg.content, 0) + 1
            msg_by_content[msg.content] = msg

        # Find most common response
        winner = max(votes.items(), key=lambda x: x[1])
        winner_content, max_votes = winner

        result = msg_by_content[winner_content]
        if result.metadata is None:
            result.metadata = {}
        result.metadata["votes"] = max_votes
        result.metadata["total_agents"] = len(messages)

        return result


# Singleton instance for convenience
default_aggregators = DefaultAggregators()
