"""
Sequential Agent Pattern

Sequential pattern enables pipeline-style agent composition where each agent
processes the output of the previous agent. This is ideal for multi-stage
processing workflows.

Key concepts:
- Linear processing pipeline
- Output of agent N becomes input of agent N+1
- Early termination on errors
- Preserves metadata across pipeline stages

Performance characteristics:
- Time: O(sum of agent times) - sequential execution
- Memory: O(1) for message passing (no accumulation)
- Each agent sees only previous agent's output
"""

from typing import Any

from agenkit import Agent, Message


class SequentialAgent(Agent):
    """
    Executes a pipeline of agents in order.

    Each agent receives the output of the previous agent as input.
    The final agent's output is returned as the result.

    Example use cases:
    - Document processing: extract -> translate -> summarize
    - Data pipeline: validate -> transform -> enrich
    - Content generation: draft -> review -> format

    The pipeline stops immediately if any agent returns an error.

    Example:
        ```python
        from agenkit.patterns import SequentialAgent

        # Create a pipeline of agents
        agent = SequentialAgent(agents=[extractor, translator, summarizer])

        # Process through the pipeline
        result = await agent.process(Message(role="user", content="Extract and translate"))
        ```
    """

    def __init__(self, agents: list[Agent]) -> None:
        """
        Create a new sequential pipeline agent.

        Args:
            agents: List of agents to execute in order (must have at least one)

        Raises:
            ValueError: If agents list is empty

        The agents will be executed in the order provided. Each agent's output
        becomes the input for the next agent.
        """
        if not agents:
            raise ValueError("at least one agent is required")

        self._agents = agents

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return "SequentialAgent"

    @property
    def capabilities(self) -> list[str]:
        """Return the combined capabilities of all agents in the pipeline."""
        cap_set = set()
        for agent in self._agents:
            cap_set.update(agent.capabilities)

        capabilities = list(cap_set)
        capabilities.extend(["sequential", "pipeline"])

        return capabilities

    async def process(self, message: Message) -> Message:
        """
        Execute the agent pipeline sequentially.

        The message is passed through each agent in order. Each agent's output
        becomes the input for the next agent. If any agent returns an error,
        the pipeline stops and the error is raised immediately.

        Metadata from each agent is preserved in the final message under the
        "pipeline_stages" key, allowing inspection of intermediate results.

        Args:
            message: Input message to process through the pipeline

        Returns:
            Final message from the last agent in the pipeline

        Raises:
            ValueError: If message is None
            Exception: If any agent in the pipeline fails
        """
        if message is None:
            raise ValueError("message cannot be None")

        # Track pipeline stages for observability
        stages: list[dict[str, Any]] = []

        # Pass message through each agent
        current = message
        for i, agent in enumerate(self._agents):
            # Process with current agent
            try:
                result = await agent.process(current)
            except Exception as e:
                raise RuntimeError(f"agent {i} ({agent.name}) failed: {e}") from e

            # Record stage metadata
            stage_info: dict[str, Any] = {
                "agent": agent.name,
                "stage": i,
            }
            if result.metadata:
                stage_info["metadata"] = result.metadata

            stages.append(stage_info)

            # Use result as input for next agent
            current = result

        # Add pipeline metadata to final result (Message.metadata is always
        # a dict, never None -- normalized at construction, #919)
        current.metadata["pipeline_stages"] = stages
        current.metadata["pipeline_length"] = len(self._agents)

        return current
