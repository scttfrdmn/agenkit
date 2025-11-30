"""
Supervisor Agent Pattern

Supervisor pattern implements hierarchical coordination where a central
supervisor agent plans task decomposition, delegates to specialist agents,
and synthesizes their results into a final response.

Key concepts:
- Central planner/supervisor for coordination
- Specialist agents for domain-specific tasks
- Task decomposition and delegation
- Result synthesis from specialist outputs

Performance characteristics:
- Time: O(planning + max(specialist) + synthesis)
- Memory: O(n specialists * message size)
- Hierarchical execution model
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from agenkit import Agent, Message


@dataclass
class Subtask:
    """
    Represents a decomposed task for a specialist agent.

    Attributes:
        type: Identifies which specialist should handle this subtask
        message: Input for the specialist
        metadata: Additional task information
    """

    type: str
    message: Message
    metadata: dict[str, Any] = field(default_factory=dict)


class PlannerAgent(Protocol):
    """
    Protocol for agents responsible for task decomposition and result synthesis.

    The planner receives the initial message and breaks it down into subtasks
    for specialist agents. After specialists complete their work, the planner
    synthesizes their results into a final response.
    """

    @property
    def name(self) -> str:
        """Return the agent's name."""
        ...

    def capabilities(self) -> list[str]:
        """Return the agent's capabilities."""
        ...

    async def process(self, message: Message) -> Message:
        """Process a message."""
        ...

    async def plan(self, message: Message) -> list[Subtask]:
        """
        Decompose a message into subtasks for specialists.

        Args:
            message: Original message to decompose

        Returns:
            List of subtasks for specialist agents
        """
        ...

    async def synthesize(
        self, original: Message, results: dict[str, Message]
    ) -> Message:
        """
        Combine specialist results into final response.

        Args:
            original: Original input message
            results: Map of specialist results keyed by subtask identifier

        Returns:
            Synthesized final message
        """
        ...


class SupervisorAgent(Agent):
    """
    Coordinates specialist agents through hierarchical planning.

    The supervisor uses a planner agent to decompose complex tasks into subtasks,
    delegates each subtask to an appropriate specialist, and synthesizes the
    specialist results into a coherent final response.

    Example use cases:
    - Software development: planner coordinates coder, tester, reviewer
    - Research: planner coordinates searcher, analyzer, writer
    - Data processing: planner coordinates extractor, transformer, validator
    - Customer service: planner coordinates billing, technical, account specialists

    The supervisor pattern is ideal when tasks have clear domain boundaries
    and benefit from specialized expertise.

    Example:
        ```python
        from agenkit.patterns import SupervisorAgent, SimplePlanner

        # Create specialists
        specialists = {
            "coder": coding_agent,
            "tester": testing_agent,
            "reviewer": review_agent
        }

        # Create supervisor
        planner = SimplePlanner(llm_agent)
        supervisor = SupervisorAgent(planner=planner, specialists=specialists)

        result = await supervisor.process(
            Message(role="user", content="Build a REST API")
        )
        ```
    """

    def __init__(
        self,
        planner: PlannerAgent,
        specialists: dict[str, Agent],
    ) -> None:
        """
        Create a new supervisor agent.

        Args:
            planner: Agent responsible for planning and synthesis
            specialists: Map of specialist agents keyed by their domain/type

        Raises:
            ValueError: If planner is None or specialists is empty

        The planner's plan method should return subtasks with type values that
        match keys in the specialists map.
        """
        if planner is None:
            raise ValueError("planner is required")
        if not specialists:
            raise ValueError("at least one specialist is required")

        self._planner = planner
        self._specialists = specialists

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return "SupervisorAgent"

    def capabilities(self) -> list[str]:
        """Return the combined capabilities of planner and specialists."""
        cap_set = set()

        # Add planner capabilities
        cap_set.update(self._planner.capabilities())

        # Add specialist capabilities
        for specialist in self._specialists.values():
            cap_set.update(specialist.capabilities())

        capabilities = list(cap_set)
        capabilities.extend(["supervisor", "hierarchical", "coordination"])

        return capabilities

    async def process(self, message: Message) -> Message:
        """
        Execute the supervisor pattern: plan, delegate, synthesize.

        The process follows these steps:
        1. Planning: Planner decomposes the task into subtasks
        2. Delegation: Each subtask is routed to appropriate specialist
        3. Execution: Specialists process their assigned subtasks
        4. Synthesis: Planner combines specialist results into final response

        If any subtask references an unknown specialist type, an error is raised.
        If any specialist fails, the error is raised immediately.

        The final message includes metadata about the planning and delegation process.

        Args:
            message: Input message to process

        Returns:
            Synthesized message from planner combining specialist results

        Raises:
            ValueError: If message is None
            RuntimeError: If subtask references unknown specialist or specialist fails
        """
        if message is None:
            raise ValueError("message cannot be None")

        # Step 1: Plan - decompose task into subtasks
        subtasks = await self._planner.plan(message)

        if not subtasks:
            # No subtasks - let planner handle directly
            return await self._planner.process(message)

        # Step 2: Validate specialist availability
        for i, subtask in enumerate(subtasks):
            if subtask.type not in self._specialists:
                available_types = ", ".join(self._specialists.keys())
                raise RuntimeError(
                    f"subtask {i} references unknown specialist type '{subtask.type}' "
                    f"(available: {available_types})"
                )

        # Step 3: Execute subtasks with specialists
        results: dict[str, Message] = {}
        execution_order: list[dict[str, Any]] = []

        for i, subtask in enumerate(subtasks):
            specialist = self._specialists[subtask.type]

            # Execute subtask
            try:
                result = await specialist.process(subtask.message)
            except Exception as e:
                raise RuntimeError(
                    f"specialist '{subtask.type}' failed on subtask {i}: {e}"
                ) from e

            # Store result keyed by specialist type and index for synthesis
            result_key = f"{subtask.type}_{i}"
            results[result_key] = result

            # Track execution order
            execution_order.append({
                "index": i,
                "type": subtask.type,
                "specialist": specialist.name,
            })

        # Step 4: Synthesize - combine specialist results
        try:
            final = await self._planner.synthesize(message, results)
        except Exception as e:
            raise RuntimeError(f"synthesis failed: {e}") from e

        # Add supervisor metadata
        if final.metadata is None:
            final.metadata = {}
        final.metadata["supervisor_subtasks"] = len(subtasks)
        final.metadata["supervisor_specialists"] = len(self._specialists)
        final.metadata["execution_order"] = execution_order

        return final


class SimplePlanner:
    """
    Basic planner implementation for simple use cases.

    This planner uses an LLM agent to handle both planning and synthesis.
    For planning, it prompts the LLM to decompose the task. For synthesis,
    it prompts the LLM to combine results.

    For production use, consider implementing a custom PlannerAgent with
    domain-specific planning and synthesis logic.

    Example:
        ```python
        from agenkit.patterns import SimplePlanner

        planner = SimplePlanner(llm_agent)
        ```
    """

    def __init__(self, agent: Agent) -> None:
        """
        Create a basic planner using an LLM agent.

        Args:
            agent: Underlying agent to use for planning and synthesis
        """
        self._agent = agent

    @property
    def name(self) -> str:
        """Return the planner's identifier."""
        return "SimplePlanner"

    def capabilities(self) -> list[str]:
        """Return the planner's capabilities."""
        caps = self._agent.capabilities()
        return [*caps, "planning", "synthesis"]

    async def process(self, message: Message) -> Message:
        """Handle direct message processing (delegates to underlying agent)."""
        return await self._agent.process(message)

    async def plan(self, message: Message) -> list[Subtask]:
        """
        Use the LLM to decompose tasks (simplified implementation).

        Note: This is a basic implementation. Production code should parse
        the LLM response and create proper Subtask structures.

        Args:
            message: Message to decompose

        Returns:
            Empty list (triggers direct processing)
        """
        # In a real implementation, this would prompt the LLM to create a plan
        # and parse the response into Subtask structures.
        # For now, return empty to trigger direct processing.
        return []

    async def synthesize(
        self, original: Message, results: dict[str, Message]
    ) -> Message:
        """
        Combine specialist results (simplified implementation).

        Args:
            original: Original input message
            results: Map of specialist results

        Returns:
            Combined message with all specialist results
        """
        # Combine all results
        combined_parts = ["Synthesis of specialist results:\n"]

        for key, result in results.items():
            combined_parts.append(f"\nResult from {key}:\n{result.content}\n")

        combined = "".join(combined_parts)
        return Message(role="assistant", content=combined)
