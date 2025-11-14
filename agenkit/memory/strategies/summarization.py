"""
Summarization memory strategy.

Summarizes old messages and keeps recent ones verbatim.
"""

from typing import TYPE_CHECKING

from .base import MemoryStrategy

if TYPE_CHECKING:
    from ..base import Memory
    from ...interfaces import Message


class SummarizationStrategy(MemoryStrategy):
    """
    Summarize old messages, keep recent ones verbatim.

    Strategy:
    - Keep last N messages verbatim (for immediate context)
    - Summarize older messages (for historical context)
    - Reduces token usage while preserving key information

    Use cases:
    - Long conversations
    - Token budget constraints
    - When history matters but details don't

    Example:
        >>> strategy = SummarizationStrategy(
        ...     recent_count=5,
        ...     summarize_older=True
        ... )
        >>> messages = await strategy.select(
        ...     memory=memory,
        ...     session_id="session-123",
        ...     context_limit=10
        ... )
        # Returns: [summary_message, msg1, msg2, msg3, msg4, msg5]
    """

    def __init__(
        self,
        recent_count: int = 10,
        summarize_older: bool = True
    ):
        """
        Initialize summarization strategy.

        Args:
            recent_count: Number of recent messages to keep verbatim
            summarize_older: Whether to include summary of older messages
        """
        self.recent_count = recent_count
        self.summarize_older = summarize_older

    async def select(
        self,
        memory: "Memory",
        session_id: str,
        context_limit: int,
        **kwargs
    ) -> list["Message"]:
        """
        Select messages with summarization.

        Args:
            memory: Memory instance
            session_id: Session identifier
            context_limit: Maximum messages (including summary)
            **kwargs: Ignored

        Returns:
            [summary_message (if enabled), recent_message_1, ..., recent_message_N]

        Note:
            - Summary counts as 1 message in context_limit
            - Recent messages ordered from oldest to newest
        """
        # Get recent messages
        recent = await memory.retrieve(session_id, limit=self.recent_count)

        if not self.summarize_older or not recent:
            # No summarization, just return recent
            # Reverse to get oldest-to-newest order for context flow
            return list(reversed(recent[:context_limit]))

        # Get summary of older messages
        summary = await memory.summarize(session_id)

        # Check if summary indicates no older messages
        if "No messages" in summary.content:
            # No older messages to summarize
            return list(reversed(recent[:context_limit]))

        # Combine summary + recent (summary first, then chronological recent)
        # Reserve 1 slot for summary
        recent_budget = context_limit - 1
        result = [summary] + list(reversed(recent[:recent_budget]))

        return result
