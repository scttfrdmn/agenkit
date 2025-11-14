"""
Memory interface for agent memory systems.

This module defines the minimal interface for agent memory systems,
supporting multiple storage backends and retrieval strategies.

Design principles:
- Minimal: Only essential methods
- Flexible: Support multiple storage backends
- Composable: Combine with strategies
- Async-first: Production-ready
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..interfaces import Message


class Memory(ABC):
    """
    Minimal interface for agent memory systems.

    Memory systems store and retrieve agent conversation history,
    enabling context management beyond raw message lists. Different
    implementations support various storage backends and retrieval
    strategies.

    Implementations:
    - InMemoryMemory: Simple in-memory storage with LRU eviction
    - RedisMemory: Redis-backed with TTL and pub/sub
    - VectorMemory: Vector database for semantic retrieval
    - EndlessMemory: Integration with endless project for infinite context

    Example:
        >>> memory = InMemoryMemory(max_size=1000)
        >>> await memory.store("session-123", message)
        >>> messages = await memory.retrieve("session-123", limit=10)
    """

    @abstractmethod
    async def store(
        self,
        session_id: str,
        message: Message,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Store message in memory with optional metadata.

        Args:
            session_id: Unique session identifier
            message: Message to store
            metadata: Optional metadata (importance score, tags, etc.)

        Example:
            >>> await memory.store(
            ...     "session-123",
            ...     Message(role="user", content="Hello"),
            ...     metadata={"importance": 0.8, "tags": ["greeting"]}
            ... )
        """
        pass

    @abstractmethod
    async def retrieve(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> list[Message]:
        """
        Retrieve messages from memory.

        Args:
            session_id: Session identifier
            query: Optional semantic query for retrieval (if supported)
            limit: Maximum messages to return
            **kwargs: Backend-specific options:
                - time_range: tuple[datetime, datetime] for time filtering
                - importance_threshold: float for importance filtering
                - tags: list[str] for tag filtering

        Returns:
            List of messages (most recent first by default)

        Example:
            >>> # Basic retrieval (most recent)
            >>> messages = await memory.retrieve("session-123", limit=10)
            >>>
            >>> # Semantic retrieval (if supported)
            >>> messages = await memory.retrieve(
            ...     "session-123",
            ...     query="What did we discuss about pricing?",
            ...     limit=5
            ... )
            >>>
            >>> # Time-filtered retrieval
            >>> messages = await memory.retrieve(
            ...     "session-123",
            ...     time_range=(start_time, end_time),
            ...     limit=20
            ... )
        """
        pass

    @abstractmethod
    async def summarize(
        self,
        session_id: str,
        **kwargs
    ) -> Message:
        """
        Create summary of conversation history.

        Args:
            session_id: Session identifier
            **kwargs: Backend-specific options:
                - max_length: int for summary length
                - style: str for summary style ("brief", "detailed")

        Returns:
            Message containing summary

        Example:
            >>> summary = await memory.summarize("session-123")
            >>> print(summary.content)
            "Discussed pricing strategy, decided on $50/month tier..."
        """
        pass

    @abstractmethod
    async def clear(self, session_id: str) -> None:
        """
        Clear memory for session.

        Args:
            session_id: Session identifier

        Example:
            >>> await memory.clear("session-123")
        """
        pass

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """
        Return memory capabilities.

        Possible capabilities:
        - "basic_retrieval": Supports simple retrieve()
        - "semantic_search": Supports query-based retrieval
        - "summarization": Supports summarize()
        - "persistence": Data survives restarts
        - "ttl": Supports automatic expiry
        - "importance_weighting": Supports importance-based retrieval
        - "time_travel": Supports point-in-time queries

        Returns:
            List of capability strings

        Example:
            >>> memory.capabilities
            ["basic_retrieval", "persistence", "ttl"]
        """
        pass
