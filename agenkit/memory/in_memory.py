"""
In-memory implementation of Memory interface.

Provides simple in-memory storage with LRU eviction for testing
and simple applications that don't need persistence.
"""

from datetime import datetime, timezone
from typing import Optional

from .base import Memory
from ..interfaces import Message


class InMemoryMemory(Memory):
    """
    Simple in-memory storage with LRU eviction.

    Features:
    - Fast access (no I/O)
    - LRU eviction when max_size reached
    - Per-session storage
    - Optional metadata support

    Limitations:
    - No persistence (data lost on restart)
    - No semantic search
    - Memory limited

    Use cases:
    - Testing
    - Simple applications
    - Prototypes
    - When persistence not needed

    Example:
        >>> memory = InMemoryMemory(max_size=1000)
        >>> await memory.store("session-123", message)
        >>> messages = await memory.retrieve("session-123", limit=10)
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize in-memory storage.

        Args:
            max_size: Maximum number of messages to store per session
                     before LRU eviction
        """
        self.max_size = max_size
        # session_id -> list of (timestamp, message, metadata)
        self._storage: dict[str, list[tuple[float, Message, dict]]] = {}
        # Counter to ensure unique ordering even for same-timestamp messages
        self._counter = 0

    async def store(
        self,
        session_id: str,
        message: Message,
        metadata: Optional[dict] = None
    ) -> None:
        """Store message in memory with optional metadata."""
        if session_id not in self._storage:
            self._storage[session_id] = []

        session_storage = self._storage[session_id]

        # Add message with timestamp (use counter to ensure unique ordering)
        timestamp = datetime.now(timezone.utc).timestamp() + (self._counter * 0.000001)
        self._counter += 1
        session_storage.append((timestamp, message, metadata or {}))

        # LRU eviction if over limit
        if len(session_storage) > self.max_size:
            # Remove oldest (first item in list)
            session_storage.pop(0)

    async def retrieve(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> list[Message]:
        """
        Retrieve messages from memory.

        Supports kwargs:
        - time_range: tuple[datetime, datetime] for filtering
        - importance_threshold: float (requires metadata with "importance")
        - tags: list[str] (requires metadata with "tags")
        """
        if session_id not in self._storage:
            return []

        session_storage = self._storage[session_id]

        # Get all messages (most recent first)
        messages_with_metadata = list(reversed(session_storage))

        # Apply filters
        filtered = []
        for timestamp, message, metadata in messages_with_metadata:
            # Time range filter
            if "time_range" in kwargs:
                start_time, end_time = kwargs["time_range"]
                msg_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                if not (start_time <= msg_time <= end_time):
                    continue

            # Importance threshold filter
            if "importance_threshold" in kwargs:
                threshold = kwargs["importance_threshold"]
                importance = metadata.get("importance", 0.0)
                if importance < threshold:
                    continue

            # Tags filter
            if "tags" in kwargs:
                required_tags = set(kwargs["tags"])
                message_tags = set(metadata.get("tags", []))
                if not required_tags.intersection(message_tags):
                    continue

            filtered.append(message)

            # Stop if we have enough
            if len(filtered) >= limit:
                break

        return filtered[:limit]

    async def summarize(
        self,
        session_id: str,
        **kwargs
    ) -> Message:
        """
        Create summary of conversation history.

        Simple implementation: Returns a message with concatenated content.
        Production use should use LLM-based summarization.
        """
        messages = await self.retrieve(session_id, limit=100)

        if not messages:
            return Message(
                role="system",
                content="No messages in session."
            )

        # Simple concatenation summary
        summary_parts = []
        for i, msg in enumerate(messages[:10], 1):  # Last 10 messages
            preview = msg.content[:100]
            if len(msg.content) > 100:
                preview += "..."
            summary_parts.append(f"{i}. [{msg.role}] {preview}")

        summary_content = f"Session summary ({len(messages)} messages):\n" + "\n".join(summary_parts)

        return Message(
            role="system",
            content=summary_content
        )

    async def clear(self, session_id: str) -> None:
        """Clear memory for session."""
        if session_id in self._storage:
            del self._storage[session_id]

    @property
    def capabilities(self) -> list[str]:
        """Return memory capabilities."""
        return [
            "basic_retrieval",
            "time_filtering",
            "importance_filtering",
            "tag_filtering"
        ]

    # Additional utility methods

    def get_session_count(self, session_id: str) -> int:
        """Get number of messages stored for session."""
        if session_id not in self._storage:
            return 0
        return len(self._storage[session_id])

    def get_all_sessions(self) -> list[str]:
        """Get list of all session IDs."""
        return list(self._storage.keys())

    def get_memory_usage(self) -> dict[str, int]:
        """Get memory usage statistics."""
        return {
            "total_sessions": len(self._storage),
            "total_messages": sum(len(storage) for storage in self._storage.values()),
            "max_size_per_session": self.max_size
        }
