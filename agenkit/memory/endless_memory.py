"""
EndlessMemory integration for infinite context compression.

Provides integration with the endless project for effectively infinite context
through compression. Users provide their own endless client.

Note: This is an integration interface only. Does NOT include endless code.
"""

from typing import Protocol

from ..interfaces import Message
from .base import Memory


class EndlessClient(Protocol):
    """
    Protocol for endless project client.

    Users must provide a client implementing this interface.
    See: https://github.com/jxnl/endless (user installs separately)
    """

    async def store_context(
        self, session_id: str, messages: list[dict], metadata: dict | None = None
    ) -> None:
        """Store messages in endless compressed context."""
        ...

    async def retrieve_context(
        self, session_id: str, query: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Retrieve compressed context from endless."""
        ...

    async def summarize_context(self, session_id: str) -> str:
        """Get summary of compressed context."""
        ...

    async def clear_context(self, session_id: str) -> None:
        """Clear context for session."""
        ...


class EndlessMemory(Memory):
    """
    Integration with endless project for infinite context.

    Features:
    - Infinite context through compression
    - Semantic retrieval from compressed context
    - Automatic context management
    - Cross-session knowledge accumulation

    Limitations:
    - Requires endless client (user provides)
    - Compression may lose some details
    - Additional latency for compression/decompression

    Use cases:
    - Very long conversations (> 200K tokens)
    - Knowledge accumulation over time
    - Multi-session knowledge sharing
    - 30-hour autonomous agents

    Example:
        >>> # User installs: pip install endless
        >>> from endless import EndlessClient
        >>>
        >>> endless_client = EndlessClient(api_key="...")
        >>> memory = EndlessMemory(endless_client)
        >>> await memory.store("session-123", message)
        >>> messages = await memory.retrieve("session-123", query="pricing discussion")
    """

    def __init__(self, endless_client: EndlessClient):
        """
        Initialize EndlessMemory with user-provided client.

        Args:
            endless_client: Client implementing EndlessClient protocol
                          (user installs endless separately)

        Example:
            >>> from endless import EndlessClient
            >>> client = EndlessClient(api_key="sk-...")
            >>> memory = EndlessMemory(client)
        """
        self.client = endless_client

    def _message_to_dict(self, message: Message) -> dict:
        """Convert Message to dict for endless storage."""
        return {
            "role": message.role,
            "content": message.content,
        }

    def _dict_to_message(self, data: dict) -> Message:
        """Convert dict from endless to Message."""
        return Message(role=data["role"], content=data["content"])

    async def store(self, session_id: str, message: Message, metadata: dict | None = None) -> None:
        """
        Store message in endless compressed context.

        Args:
            session_id: Session identifier
            message: Message to store
            metadata: Optional metadata (importance, tags, etc.)
        """
        msg_dict = self._message_to_dict(message)
        if metadata:
            msg_dict["metadata"] = metadata

        # Store in endless (compression happens automatically)
        await self.client.store_context(session_id, [msg_dict], metadata=metadata)

    async def retrieve(
        self, session_id: str, query: str | None = None, limit: int = 10, **kwargs
    ) -> list[Message]:
        """
        Retrieve messages from endless compressed context.

        Supports semantic retrieval via query parameter.

        Args:
            session_id: Session identifier
            query: Optional semantic query for retrieval
            limit: Maximum messages to return
            **kwargs: Additional options (passed to endless client)

        Returns:
            List of messages from compressed context
        """
        # Retrieve from endless
        results = await self.client.retrieve_context(session_id, query=query, limit=limit)

        # Convert to Messages
        messages = [self._dict_to_message(data) for data in results]

        return messages

    async def summarize(self, session_id: str, **kwargs) -> Message:
        """
        Get summary of compressed context from endless.

        Args:
            session_id: Session identifier
            **kwargs: Additional options

        Returns:
            Message containing summary
        """
        summary_text = await self.client.summarize_context(session_id)

        return Message(role="system", content=summary_text)

    async def clear(self, session_id: str) -> None:
        """
        Clear endless context for session.

        Args:
            session_id: Session identifier
        """
        await self.client.clear_context(session_id)

    @property
    def capabilities(self) -> list[str]:
        """Return EndlessMemory capabilities."""
        return [
            "infinite_context",
            "compression",
            "semantic_search",
            "cross_session_knowledge",
            "automatic_summarization",
        ]
