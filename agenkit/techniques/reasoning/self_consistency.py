"""
Self-Consistency Reasoning Technique

Generates multiple independent reasoning paths and selects the most consistent
answer through voting or aggregation strategies.

This technique improves reliability by sampling multiple times and using
consensus, particularly effective when multiple valid reasoning approaches exist.

References:
    - Paper: https://arxiv.org/abs/2203.11171 (Wang et al., 2022)
    - "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
    - Works best combined with CoT or other reasoning techniques

Example:
    Basic usage::

        from agenkit.techniques.reasoning import ChainOfThought, SelfConsistency
        from agenkit import Message

        # Wrap CoT with Self-Consistency
        cot = ChainOfThought(llm=my_llm)
        sc = SelfConsistency(
            agent=cot,
            num_samples=5,
            voting_strategy="majority"
        )

        response = await sc.process(Message(
            role="user",
            content="What is 15 * 24?"
        ))

        # Access consensus info
        print(f"Consensus answer: {response.content}")
        print(f"Consistency score: {response.metadata['consistency_score']}")
"""

import asyncio
import re
from collections import Counter
from collections.abc import Callable

from agenkit import Agent, Message


class SelfConsistency(Agent):
    """
    Self-Consistency reasoning technique.

    Wraps a base agent, samples multiple times, and uses voting to determine
    the most consistent answer. Improves reliability by leveraging consensus
    across diverse reasoning paths.

    This technique is particularly effective for:
    - Tasks with multiple valid solution approaches
    - Improving answer reliability and confidence
    - Reducing impact of individual reasoning errors
    - Tasks where consistency indicates correctness

    Attributes:
        name: Agent name (always "self_consistency")
        agent: Base agent to sample from
        num_samples: Number of independent samples to generate
        voting_strategy: Strategy for aggregating answers
        temperature: Sampling temperature for diversity
        answer_extractor: Function to extract final answer from response
    """

    def __init__(
        self,
        agent: Agent,
        num_samples: int = 5,
        voting_strategy: str = "majority",
        temperature: float | None = None,
        answer_extractor: Callable[[str], str] | None = None,
    ):
        """
        Initialize Self-Consistency agent.

        Args:
            agent: Base agent to sample from. Can be any Agent (CoT, ToT, etc.)
            num_samples: Number of independent reasoning paths to generate.
                Higher values improve reliability but increase cost. Default is 5.
            voting_strategy: How to aggregate multiple answers:
                - "majority": Select most common answer (default)
                - "weighted": Weight by answer confidence/length
                - "first": Use first answer (no voting, for debugging)
            temperature: Optional temperature for sampling diversity. If provided,
                passed to agent if it supports temperature parameter.
            answer_extractor: Custom function to extract final answer from
                response text (str -> str). If None, uses default extraction
                that looks for common answer patterns.

        Example:
            >>> from agenkit.techniques.reasoning import ChainOfThought
            >>> cot = ChainOfThought(llm=my_llm)
            >>> sc = SelfConsistency(
            ...     agent=cot,
            ...     num_samples=7,
            ...     voting_strategy="majority"
            ... )
        """
        self.agent = agent
        self.num_samples = num_samples
        self.voting_strategy = voting_strategy
        self.temperature = temperature
        self.answer_extractor = answer_extractor or self._default_answer_extractor

    @property
    def name(self) -> str:
        """Return agent name."""
        return "self_consistency"

    def _default_answer_extractor(self, text: str) -> str:
        """
        Extract final answer from response text.

        Looks for common answer patterns:
        - "Therefore, X" / "Thus, X" / "So, X"
        - "The answer is X"
        - "= X" (for math)
        - Last sentence/line (fallback)

        Args:
            text: Response text to extract answer from

        Returns:
            Extracted answer string
        """
        # Try explicit answer markers
        answer_patterns = [
            r"(?:therefore|thus|so),?\s+(?:the answer is\s+)?(.+?)(?:\.|$)",
            r"(?:the answer is|answer:)\s+(.+?)(?:\.|$)",
            r"=\s*(.+?)(?:\n|$)",
            r"(?:conclusion|result):\s*(.+?)(?:\.|$)",
        ]

        for pattern in answer_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        # Fallback: use last non-empty line
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            return lines[-1]

        return text.strip()

    async def _sample_once(self, message: Message) -> tuple[str, str]:
        """
        Generate one sample from base agent.

        Args:
            message: Input message

        Returns:
            Tuple of (full_response, extracted_answer)
        """
        # TODO: If temperature supported, pass it to agent
        response = await self.agent.process(message)
        full_response = response.content
        answer = self.answer_extractor(full_response)
        return (full_response, answer)

    async def _generate_samples(self, message: Message) -> list[tuple[str, str]]:
        """
        Generate multiple samples in parallel.

        Args:
            message: Input message

        Returns:
            List of (full_response, extracted_answer) tuples
        """
        # Generate samples in parallel for performance
        tasks = [self._sample_once(message) for _ in range(self.num_samples)]
        samples = await asyncio.gather(*tasks)
        return samples

    def _vote_majority(self, answers: list[str]) -> tuple[str, float]:
        """
        Majority voting: select most common answer.

        Args:
            answers: List of extracted answers

        Returns:
            Tuple of (winning_answer, consistency_score)
        """
        if not answers:
            return ("", 0.0)

        # Count answer occurrences (case-insensitive)
        answer_counts = Counter(answer.lower().strip() for answer in answers)

        # Get most common
        most_common = answer_counts.most_common(1)[0]
        winning_answer_lower = most_common[0]
        winning_count = most_common[1]

        # Find original case version
        winning_answer = next(
            (ans for ans in answers if ans.lower().strip() == winning_answer_lower),
            winning_answer_lower,
        )

        # Consistency score = fraction that agree
        consistency_score = winning_count / len(answers)

        return (winning_answer, consistency_score)

    def _vote_weighted(self, answers: list[str], responses: list[str]) -> tuple[str, float]:
        """
        Weighted voting: weight by response length (proxy for detail/confidence).

        Args:
            answers: List of extracted answers
            responses: List of full response texts

        Returns:
            Tuple of (winning_answer, consistency_score)
        """
        if not answers:
            return ("", 0.0)

        # Group answers by normalized form
        answer_groups = {}
        for answer, response in zip(answers, responses, strict=False):
            answer_key = answer.lower().strip()
            if answer_key not in answer_groups:
                answer_groups[answer_key] = {"original": answer, "weight": 0, "count": 0}
            # Weight by response length
            answer_groups[answer_key]["weight"] += len(response)
            answer_groups[answer_key]["count"] += 1

        # Find highest weighted answer
        winning_key = max(answer_groups, key=lambda k: answer_groups[k]["weight"])
        winning_answer = answer_groups[winning_key]["original"]
        winning_weight = answer_groups[winning_key]["weight"]
        total_weight = sum(group["weight"] for group in answer_groups.values())

        # Consistency score = weight fraction
        consistency_score = winning_weight / total_weight if total_weight > 0 else 0.0

        return (winning_answer, consistency_score)

    def _vote_first(self, answers: list[str]) -> tuple[str, float]:
        """
        First answer (no voting): use first sample.

        Args:
            answers: List of extracted answers

        Returns:
            Tuple of (first_answer, 1.0)
        """
        if not answers:
            return ("", 0.0)
        return (answers[0], 1.0)

    async def process(self, message: Message) -> Message:
        """
        Process message with Self-Consistency.

        Generates multiple independent samples, extracts answers, and uses
        voting to determine the most consistent answer.

        Args:
            message: Input message with query content

        Returns:
            Message with consensus answer and metadata. Metadata includes:
                - samples: List of all full responses
                - extracted_answers: List of extracted answers
                - consistency_score: Agreement score (0.0-1.0)
                - num_samples: Number of samples generated
                - voting_strategy: Strategy used
                - answer_counts: Dict of answer frequencies
                - technique: Always "self_consistency"

        Example:
            >>> response = await sc.process(Message(role="user", content="What is 2+2?"))
            >>> print(f"Consensus: {response.content}")
            >>> print(f"Consistency: {response.metadata['consistency_score']:.2f}")
        """
        # Generate multiple samples
        samples = await self._generate_samples(message)
        full_responses = [resp for resp, _ in samples]
        extracted_answers = [ans for _, ans in samples]

        # Vote for consensus answer
        if self.voting_strategy == "majority":
            consensus_answer, consistency_score = self._vote_majority(extracted_answers)
        elif self.voting_strategy == "weighted":
            consensus_answer, consistency_score = self._vote_weighted(
                extracted_answers, full_responses
            )
        elif self.voting_strategy == "first":
            consensus_answer, consistency_score = self._vote_first(extracted_answers)
        else:
            raise ValueError(f"Invalid voting strategy: {self.voting_strategy}")

        # Count answer occurrences for metadata
        answer_counts = Counter(ans.lower().strip() for ans in extracted_answers)

        return Message(
            role="assistant",
            content=consensus_answer,
            metadata={
                "technique": "self_consistency",
                "num_samples": self.num_samples,
                "voting_strategy": self.voting_strategy,
                "consistency_score": consistency_score,
                "samples": full_responses,
                "extracted_answers": extracted_answers,
                "answer_counts": dict(answer_counts),
                "base_agent": self.agent.name if hasattr(self.agent, "name") else "unknown",
            },
        )

    @property
    def capabilities(self) -> list[str]:
        """
        Return agent capabilities.

        Returns:
            List of capability strings describing what this agent can do
        """
        return ["reasoning", "self_consistency", "majority_voting", "reliability", "consensus"]
