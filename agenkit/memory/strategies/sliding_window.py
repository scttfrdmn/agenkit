"""
Sliding window memory strategy.

Keeps the most recent N messages in context.
"""

from typing import TYPE_CHECKING

from .base import MemoryStrategy

if TYPE_CHECKING:
    from ...interfaces import Message
    from ..base import Memory


class SlidingWindowStrategy(MemoryStrategy):
    """
    Keep most recent N messages.

    This is the simplest and most common strategy:
    - Always includes most recent messages
    - Maintains conversation flow
    - Fixed memory usage
    - No complex logic

    Use cases:
    - General chatbots
    - Simple agents
    - When recent context is most important

    Example:
        >>> strategy = SlidingWindowStrategy(window_size=10)
        >>> messages = await strategy.select(
        ...     memory=memory,
        ...     session_id="session-123",
        ...     context_limit=10
        ... )
    """

    def __init__(self, window_size: int = 10):
        """
        Initialize sliding window strategy.

        Args:
            window_size: Number of recent messages to keep (default: 10)
        """
        self.window_size = window_size

    async def select(
        self, memory: "Memory", session_id: str, context_limit: int, **kwargs
    ) -> list["Message"]:
        """
        Select most recent messages.

        Args:
            memory: Memory instance
            session_id: Session identifier
            context_limit: Maximum messages (takes min of context_limit and window_size)
            **kwargs: Ignored

        Returns:
            Most recent messages (up to limit)
        """
        limit = min(context_limit, self.window_size)
        return await memory.retrieve(session_id, limit=limit)
