"""
Collaborative Agent Pattern

Collaborative pattern implements peer-to-peer agent collaboration with
iterative refinement. Multiple agents work together, each contributing
their perspective and refining the collective output through rounds.

Key concepts:
- Peer-to-peer collaboration (no hierarchy)
- Iterative refinement through rounds
- Consensus detection or max rounds limit
- Each agent sees all previous responses

Performance characteristics:
- Time: O(rounds * n agents) worst case
- Memory: O(rounds * n agents * message size)
- Early termination on consensus
"""

from collections.abc import Callable
from dataclasses import dataclass

from agenkit import Agent, Message

# Type aliases for callback functions
ConsensusFunc = Callable[[list[Message]], bool]
MergeFunc = Callable[[list[Message]], Message]


@dataclass
class CollaborativeConfig:
    """
    Configuration for a CollaborativeAgent.

    Attributes:
        agents: Agents participating in collaboration
        max_rounds: Limits iteration (default: 3)
        consensus_func: Detects agreement (optional)
        merge_func: Combines responses (required)
    """

    agents: list[Agent]
    merge_func: MergeFunc
    max_rounds: int = 3
    consensus_func: ConsensusFunc | None = None


@dataclass
class RoundResult:
    """Holds responses from a single collaboration round."""

    round: int
    responses: list[Message]
    consensus: bool


class CollaborativeAgent(Agent):
    """
    Enables peer collaboration with iterative refinement.

    Agents work together in rounds, each seeing previous responses and
    contributing refinements. The process continues until consensus is
    reached or maximum rounds are exhausted.

    Example use cases:
    - Code review: multiple reviewers provide feedback
    - Document editing: iterative improvements from editors
    - Decision making: collaborative analysis and consensus
    - Creative writing: multiple perspectives and refinement
    - Research: peer review and iteration

    The collaborative pattern is ideal when multiple perspectives improve
    output quality through discussion and refinement.

    Example:
        ```python
        from agenkit.patterns import CollaborativeAgent, CollaborativeConfig
        from agenkit.patterns.collaborative import default_merge_funcs

        config = CollaborativeConfig(
            agents=[reviewer1, reviewer2, reviewer3],
            max_rounds=3,
            merge_func=default_merge_funcs.vote
        )

        agent = CollaborativeAgent(config)
        result = await agent.process(
            Message(role="user", content="Review this code")
        )
        ```
    """

    def __init__(self, config: CollaborativeConfig) -> None:
        """
        Create a new collaborative agent.

        Args:
            config: Configuration with agents and collaboration settings

        Raises:
            ValueError: If config is None, less than 2 agents, or merge_func is None

        If no consensus function is provided, collaboration continues for all rounds.
        The merge function is required and determines how responses are combined.
        """
        if config is None:
            raise ValueError("config is required")
        if len(config.agents) < 2:
            raise ValueError("at least two agents are required for collaboration")
        if config.merge_func is None:
            raise ValueError("merge function is required")

        self._agents = config.agents
        self._max_rounds = config.max_rounds if config.max_rounds > 0 else 3
        self._consensus_func = config.consensus_func
        self._merge_func = config.merge_func

    @property
    def name(self) -> str:
        """Return the agent's identifier."""
        return "CollaborativeAgent"

    def capabilities(self) -> list[str]:
        """Return the combined capabilities of all agents."""
        cap_set = set()

        for agent in self._agents:
            cap_set.update(agent.capabilities())

        capabilities = list(cap_set)
        capabilities.extend(["collaborative", "iterative", "consensus"])

        return capabilities

    async def process(self, message: Message) -> Message:
        """
        Execute collaborative refinement through multiple rounds.

        The process follows these steps for each round:
        1. Each agent processes the current context (original + previous responses)
        2. All responses are collected
        3. Consensus is checked (if function provided)
        4. If consensus or max rounds, merge and return
        5. Otherwise, prepare next round with all responses as context

        The final message includes metadata about rounds, consensus, and participation.

        Args:
            message: Input message to process

        Returns:
            Merged final message after collaboration

        Raises:
            ValueError: If message is None
            RuntimeError: If any agent fails during collaboration
        """
        if message is None:
            raise ValueError("message cannot be None")

        rounds: list[RoundResult] = []
        current_context: list[Message] = [message]

        for round_num in range(self._max_rounds):
            # Collect responses from all agents
            responses: list[Message] = []

            for agent in self._agents:
                # Build context message with conversation history
                context_msg = self._build_context_message(
                    current_context, round_num, agent.name
                )

                # Get agent response
                try:
                    response = await agent.process(context_msg)
                except Exception as e:
                    raise RuntimeError(
                        f"agent {agent.name} failed in round {round_num}: {e}"
                    ) from e

                responses.append(response)

            # Check for consensus
            has_consensus = False
            if self._consensus_func is not None:
                has_consensus = self._consensus_func(responses)

            # Record round
            rounds.append(
                RoundResult(
                    round=round_num,
                    responses=responses,
                    consensus=has_consensus,
                )
            )

            # Stop if consensus reached
            if has_consensus:
                return self._build_final_result(rounds, "consensus")

            # Prepare next round context
            current_context.extend(responses)

        # Max rounds reached
        return self._build_final_result(rounds, "max_rounds")

    def _build_context_message(
        self, context: list[Message], round_num: int, agent_name: str
    ) -> Message:
        """Create a message with full conversation context."""
        parts = [
            f"=== Collaboration Round {round_num} ===",
            f"Agent: {agent_name}\n",
        ]

        if round_num == 0:
            parts.append("Original Request:")
            parts.append(context[0].content)
        else:
            parts.append("Original Request:")
            parts.append(context[0].content)
            parts.append("\n--- Previous Responses ---\n")

            for i, msg in enumerate(context[1:], 1):
                parts.append(f"Response {i}:")
                parts.append(f"{msg.content}\n")

            parts.append("--- Your Turn ---")
            parts.append(
                "Please review the above responses and provide your refined contribution."
            )

        content = "\n".join(parts)
        return Message(role="user", content=content)

    def _build_final_result(
        self, rounds: list[RoundResult], stop_reason: str
    ) -> Message:
        """Merge all responses and add metadata."""
        # Collect all responses from final round
        final_round = rounds[-1]
        merged = self._merge_func(final_round.responses)

        # Add collaboration metadata
        if merged.metadata is None:
            merged.metadata = {}

        merged.metadata["collaboration_rounds"] = len(rounds)
        merged.metadata["collaboration_agents"] = len(self._agents)
        merged.metadata["stop_reason"] = stop_reason

        # Add round details
        round_details = [
            {
                "round": r.round,
                "responses": len(r.responses),
                "consensus": r.consensus,
            }
            for r in rounds
        ]
        merged.metadata["rounds"] = round_details

        return merged


class DefaultConsensusFuncs:
    """Default consensus detection strategies."""

    @staticmethod
    def exact_match(messages: list[Message]) -> bool:
        """
        Require all responses to be identical.

        Args:
            messages: List of messages from agents

        Returns:
            True if all messages have identical content
        """
        if len(messages) <= 1:
            return True

        first_content = messages[0].content
        return all(msg.content == first_content for msg in messages[1:])

    @staticmethod
    def similarity_threshold(threshold: float = 0.8) -> ConsensusFunc:
        """
        Require responses to be similar (simple string comparison).

        Args:
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            Consensus function with configured threshold
        """
        def check_similarity(messages: list[Message]) -> bool:
            if len(messages) <= 1:
                return True

            # Simple similarity: compare common prefix
            # In production, use proper similarity metrics
            first = messages[0].content.lower()
            prefix_len = min(len(first), 20)

            for msg in messages[1:]:
                current = msg.content.lower()
                if first[:prefix_len] not in current:
                    return False

            return True

        return check_similarity

    @staticmethod
    def majority_agreement(messages: list[Message]) -> bool:
        """
        Require majority of responses to match.

        Args:
            messages: List of messages from agents

        Returns:
            True if any content has majority agreement
        """
        if len(messages) <= 1:
            return True

        # Count identical responses
        content_count: dict[str, int] = {}
        for msg in messages:
            content_count[msg.content] = content_count.get(msg.content, 0) + 1

        # Check if any content has majority
        majority = (len(messages) // 2) + 1
        return any(count >= majority for count in content_count.values())


class DefaultMergeFuncs:
    """Default merge strategies for combining responses."""

    @staticmethod
    def concatenate(messages: list[Message]) -> Message:
        """
        Combine all responses with separators.

        Args:
            messages: List of messages to merge

        Returns:
            Message with all contents concatenated
        """
        if not messages:
            return Message(role="assistant", content="No responses to merge")

        combined = "\n\n---\n\n".join(msg.content for msg in messages)
        return Message(role="assistant", content=combined)

    @staticmethod
    def vote(messages: list[Message]) -> Message:
        """
        Return most common response.

        Args:
            messages: List of messages to merge

        Returns:
            Message with the most common content, with vote counts in metadata
        """
        if not messages:
            return Message(role="assistant", content="No responses to merge")

        # Count votes
        votes: dict[str, int] = {}
        msg_by_content: dict[str, Message] = {}

        for msg in messages:
            votes[msg.content] = votes.get(msg.content, 0) + 1
            msg_by_content[msg.content] = msg

        # Find winner
        winner = max(votes.items(), key=lambda x: x[1])
        winner_content, max_votes = winner

        result = msg_by_content[winner_content]
        if result.metadata is None:
            result.metadata = {}
        result.metadata["votes"] = max_votes
        result.metadata["total"] = len(messages)

        return result

    @staticmethod
    def first(messages: list[Message]) -> Message:
        """
        Return first response.

        Args:
            messages: List of messages to merge

        Returns:
            First message in the list
        """
        if not messages:
            return Message(role="assistant", content="No responses to merge")
        return messages[0]

    @staticmethod
    def last(messages: list[Message]) -> Message:
        """
        Return last response.

        Args:
            messages: List of messages to merge

        Returns:
            Last message in the list
        """
        if not messages:
            return Message(role="assistant", content="No responses to merge")
        return messages[-1]


# Singleton instances for convenience
default_consensus_funcs = DefaultConsensusFuncs()
default_merge_funcs = DefaultMergeFuncs()
