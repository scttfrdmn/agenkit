"""
Base interface for memory strategies.

Strategies determine which messages from memory should be included
in the agent's context window.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...interfaces import Message
    from ..base import Memory


class MemoryStrategy(ABC):
    """
    Strategy for intelligent memory management.

    Memory strategies decide which messages from memory to include
    in the agent's context, optimizing for:
    - Relevance (most important information)
    - Recency (recent conversation flow)
    - Context limits (fit within token budgets)

    Example:
        >>> strategy = SlidingWindowStrategy(window_size=10)
        >>> messages = await strategy.select(
        ...     memory=memory,
        ...     session_id="session-123",
        ...     context_limit=20
        ... )
    """

    @abstractmethod
    async def select(
        self, memory: "Memory", session_id: str, context_limit: int, **kwargs
    ) -> list["Message"]:
        """
        Select which messages to include in context.

        Args:
            memory: Memory instance to retrieve from
            session_id: Session identifier
            context_limit: Maximum number of messages to return
            **kwargs: Strategy-specific options

        Returns:
            List of messages to include in context

        Example:
            >>> messages = await strategy.select(
            ...     memory=memory,
            ...     session_id="session-123",
            ...     context_limit=10
            ... )
        """
        pass
