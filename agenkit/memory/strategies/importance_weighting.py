"""
Importance weighting memory strategy.

Prioritizes messages by importance score with recency bias.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from .base import MemoryStrategy

if TYPE_CHECKING:
    from ...interfaces import Message
    from ..base import Memory


class ImportanceWeightingStrategy(MemoryStrategy):
    """
    Prioritize messages by importance score.

    Selects messages based on:
    - Importance metadata (if available)
    - Recency (recent messages get bonus)
    - Relevance (optional custom scoring)

    Scoring:
    - Base score = importance (0.0-1.0)
    - Recency bonus = recency_weight * (1 - normalized_age)
    - Final score = base_score + recency_bonus

    Use cases:
    - When some messages more important than others
    - Long conversations with key decisions
    - Tracking action items or commitments

    Example:
        >>> strategy = ImportanceWeightingStrategy(
        ...     importance_threshold=0.5,
        ...     recency_weight=0.3
        ... )
        >>> messages = await strategy.select(
        ...     memory=memory,
        ...     session_id="session-123",
        ...     context_limit=10
        ... )
    """

    def __init__(
        self, importance_threshold: float = 0.0, recency_weight: float = 0.3, min_recent: int = 3
    ):
        """
        Initialize importance weighting strategy.

        Args:
            importance_threshold: Minimum importance to consider (0.0-1.0)
            recency_weight: Weight for recency bonus (0.0-1.0)
            min_recent: Always include N most recent messages
        """
        self.importance_threshold = importance_threshold
        self.recency_weight = recency_weight
        self.min_recent = min_recent

    async def select(
        self, memory: "Memory", session_id: str, context_limit: int, **kwargs
    ) -> list["Message"]:
        """
        Select messages by importance score.

        Args:
            memory: Memory instance
            session_id: Session identifier
            context_limit: Maximum messages
            **kwargs: May include:
                - custom_scorer: Callable[[Message], float] for custom importance

        Returns:
            Messages sorted by importance (most important first)
        """
        # Get more messages than needed for scoring
        all_messages = await memory.retrieve(session_id, limit=context_limit * 3)

        if not all_messages:
            return []

        # Always include most recent messages
        recent = all_messages[: self.min_recent]

        # Score remaining messages
        scored = []
        for i, msg in enumerate(all_messages[self.min_recent :], start=self.min_recent):
            # Get base importance (default 0.5 if not set)
            importance = self._calculate_importance(msg, kwargs.get("custom_scorer"))

            # Skip if below threshold
            if importance < self.importance_threshold:
                continue

            # Add recency bonus (more recent = higher bonus)
            # Normalize by position in list
            recency_bonus = self.recency_weight * (1.0 - i / len(all_messages))
            final_score = importance + recency_bonus

            scored.append((msg, final_score))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        # Take top messages (minus what we already included)
        remaining_budget = context_limit - len(recent)
        selected = [msg for msg, score in scored[:remaining_budget]]

        # Combine recent + important (keeping recent at the end for context flow)
        return selected + recent

    def _calculate_importance(
        self, message: "Message", custom_scorer: Callable | None = None
    ) -> float:
        """
        Calculate importance score for message.

        Args:
            message: Message to score
            custom_scorer: Optional custom scoring function

        Returns:
            Importance score (0.0-1.0)
        """
        if custom_scorer:
            return custom_scorer(message)

        # Try to get importance from metadata
        if hasattr(message, "metadata") and isinstance(message.metadata, dict):
            return message.metadata.get("importance", 0.5)

        # Default importance
        return 0.5
