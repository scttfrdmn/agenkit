"""
Memory Hierarchy Pattern - Multi-Tier Memory for Agents

The Memory Hierarchy pattern provides a three-tier memory system for agents:
working memory (in-context), short-term memory (recent), and long-term memory (persistent).

This enables agents to handle long-running conversations, remember important facts,
and operate effectively even with context window limitations.

Key Concepts:
- Working Memory: Current conversation context (fast, small, in-memory)
- Short-Term Memory: Recent sessions (medium, TTL-based, recency retrieval)
- Long-Term Memory: Persistent facts (large, semantic retrieval, importance-based)
- Automatic Promotion: Important memories move from short-term to long-term
- Intelligent Retrieval: Search across tiers with relevance ranking

Use Cases:
- Long-running conversational agents
- Personalization and user preferences
- Context-aware agents with limited context windows
- Multi-session continuity
- Learning and adaptation

Example:
    >>> from agenkit.patterns import MemoryHierarchy, WorkingMemory, ShortTermMemory
    >>>
    >>> # Create memory hierarchy
    >>> memory = MemoryHierarchy(
    ...     working_memory=WorkingMemory(max_messages=10),
    ...     short_term_memory=ShortTermMemory(max_messages=100, ttl_seconds=3600),
    ...     long_term_memory=None  # Optional
    ... )
    >>>
    >>> # Store memory
    >>> await memory.store(
    ...     content="User prefers Python over JavaScript",
    ...     importance=0.8,
    ...     metadata={"category": "preferences"}
    ... )
    >>>
    >>> # Retrieve relevant memories
    >>> results = await memory.retrieve(
    ...     query="What programming languages does the user prefer?",
    ...     limit=5
    ... )

References:
- Human Memory Systems (Psychology)
- MemGPT: Virtual Context Management (https://arxiv.org/abs/2310.08560)
- LangChain Memory Systems
- Multi-tiered Cache Architectures
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

__all__ = [
    "MemoryEntry",
    "MemoryStore",
    "WorkingMemory",
    "ShortTermMemory",
    "LongTermMemory",
    "MemoryHierarchy",
]


@dataclass
class MemoryEntry:
    """
    Single memory entry across all tiers.

    Attributes:
        id: Unique identifier
        content: Memory content (text)
        metadata: Additional structured information
        timestamp: When memory was created
        access_count: Number of times accessed
        last_accessed: When last accessed
        importance: Importance score (0.0-1.0)
        session_id: Optional session identifier
    """

    id: str
    content: str
    metadata: dict[str, Any]
    timestamp: datetime
    access_count: int = 0
    last_accessed: datetime | None = None
    importance: float = 0.0
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "importance": self.importance,
            "session_id": self.session_id,
        }


class MemoryStore(ABC):
    """
    Abstract base class for memory storage.

    All memory stores must implement store, retrieve, and delete operations.
    """

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """
        Store a memory entry.

        Args:
            entry: Memory entry to store
        """
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[MemoryEntry]:
        """
        Retrieve relevant memories.

        Args:
            query: Search query
            limit: Maximum number of results
            **kwargs: Additional retrieval parameters

        Returns:
            List of relevant memory entries
        """
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> None:
        """
        Delete a memory entry.

        Args:
            entry_id: ID of entry to delete
        """
        pass


class WorkingMemory(MemoryStore):
    """
    In-context working memory for current conversation.

    Characteristics:
    - Fast: O(1) append, O(n) retrieval
    - Small capacity: 10-20 messages typically
    - FIFO eviction: Oldest messages removed first
    - No persistence: Exists only in memory
    - Use for: Current conversation context

    Performance:
    - Space: O(n) where n = max_messages
    - Store: O(1)
    - Retrieve: O(n)
    - Delete: O(n)

    Args:
        max_messages: Maximum messages to keep (default: 10)

    Example:
        >>> working = WorkingMemory(max_messages=10)
        >>> await working.store(entry)
        >>> messages = working.get_all()  # Get all for context window
    """

    def __init__(self, max_messages: int = 10):
        if max_messages < 1:
            raise ValueError("max_messages must be at least 1")
        self.max_messages = max_messages
        self._messages: list[MemoryEntry] = []

    async def store(self, entry: MemoryEntry) -> None:
        """Store message, evicting oldest if at capacity."""
        self._messages.append(entry)

        # Evict oldest if over capacity
        if len(self._messages) > self.max_messages:
            self._messages.pop(0)

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[MemoryEntry]:
        """Return all messages (they're all relevant in working memory)."""
        # Working memory returns all recent messages
        return self._messages[-limit:]

    async def delete(self, entry_id: str) -> None:
        """Remove specific entry."""
        self._messages = [e for e in self._messages if e.id != entry_id]

    def get_all(self) -> list[MemoryEntry]:
        """
        Get all working memory entries.

        Returns:
            All entries in working memory (for context window)
        """
        return self._messages.copy()

    def clear(self) -> None:
        """Clear all working memory."""
        self._messages = []

    def __len__(self) -> int:
        """Number of entries in working memory."""
        return len(self._messages)


class ShortTermMemory(MemoryStore):
    """
    Recent session memory with TTL-based expiration.

    Characteristics:
    - Medium capacity: 100-1000 messages typically
    - TTL-based: Entries expire after time period
    - Recency retrieval: Most recent first
    - LRU eviction: Least recently used removed first
    - Use for: Recent conversations, sliding window

    Performance:
    - Space: O(n) where n = max_messages
    - Store: O(1) + cleanup
    - Retrieve: O(n log n) due to sorting
    - Delete: O(n)

    Args:
        max_messages: Maximum messages to keep (default: 100)
        ttl_seconds: Time-to-live in seconds (default: 3600 = 1 hour)

    Example:
        >>> short_term = ShortTermMemory(max_messages=100, ttl_seconds=3600)
        >>> await short_term.store(entry)
        >>> recent = await short_term.retrieve("", limit=10)  # Get 10 most recent
    """

    def __init__(
        self,
        max_messages: int = 100,
        ttl_seconds: int = 3600,
    ):
        if max_messages < 1:
            raise ValueError("max_messages must be at least 1")
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")

        self.max_messages = max_messages
        self.ttl = timedelta(seconds=ttl_seconds)
        self._messages: list[MemoryEntry] = []

    async def store(self, entry: MemoryEntry) -> None:
        """Store with TTL check and LRU eviction."""
        # Clean expired entries first
        await self._clean_expired()

        self._messages.append(entry)

        # Evict if over capacity (LRU)
        if len(self._messages) > self.max_messages:
            # Sort by access time (least recently used first)
            self._messages.sort(key=lambda e: e.last_accessed or e.timestamp)
            self._messages.pop(0)

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[MemoryEntry]:
        """Retrieve by recency (most recent first)."""
        await self._clean_expired()

        # Sort by timestamp (most recent first)
        sorted_messages = sorted(
            self._messages,
            key=lambda e: e.timestamp,
            reverse=True,
        )

        results = sorted_messages[:limit]

        # Update access time and count
        now = datetime.now(timezone.utc)
        for entry in results:
            entry.access_count += 1
            entry.last_accessed = now

        return results

    async def delete(self, entry_id: str) -> None:
        """Remove specific entry."""
        self._messages = [e for e in self._messages if e.id != entry_id]

    async def _clean_expired(self) -> None:
        """Remove entries older than TTL."""
        now = datetime.now(timezone.utc)
        self._messages = [e for e in self._messages if now - e.timestamp < self.ttl]

    def __len__(self) -> int:
        """Number of entries in short-term memory."""
        return len(self._messages)


class LongTermMemory(MemoryStore):
    """
    Persistent semantic memory with importance-based retention.

    Characteristics:
    - Large capacity: Unlimited (depends on storage backend)
    - Semantic retrieval: By relevance/similarity (embeddings)
    - Persistent: Survives restarts
    - Importance-based: Only important memories stored
    - Use for: User preferences, facts, learned information

    Performance:
    - Space: O(n) where n = total memories
    - Store: O(1) + embedding computation
    - Retrieve: O(log n) with vector index (e.g., HNSW)
    - Delete: O(log n)

    Args:
        storage_backend: Storage interface (e.g., dict, database, vector store)
        embedding_fn: Optional function to create embeddings
        min_importance: Minimum importance to store (default: 0.5)

    Example:
        >>> long_term = LongTermMemory(
        ...     storage_backend={},  # Simple dict for demo
        ...     min_importance=0.5
        ... )
        >>> await long_term.store(entry)  # Only if importance >= 0.5
        >>> important = await long_term.retrieve("user preferences", limit=5)

    Note:
        For production, use a proper vector store backend (ChromaDB, Pinecone, etc.)
        and provide an embedding function for semantic retrieval.
    """

    def __init__(
        self,
        storage_backend: dict[str, MemoryEntry] | None = None,
        embedding_fn: Any | None = None,
        min_importance: float = 0.5,
    ):
        if not 0.0 <= min_importance <= 1.0:
            raise ValueError("min_importance must be between 0.0 and 1.0")

        self.storage = storage_backend if storage_backend is not None else {}
        self.embedding_fn = embedding_fn
        self.min_importance = min_importance

    async def store(self, entry: MemoryEntry) -> None:
        """Store if important enough."""
        # Check importance threshold
        if entry.importance < self.min_importance:
            return  # Not important enough for long-term storage

        # Store in backend (simplified - real implementation would use vector store)
        self.storage[entry.id] = entry

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[MemoryEntry]:
        """
        Semantic retrieval by relevance.

        In a real implementation, this would:
        1. Create embedding for query
        2. Search vector index for similar embeddings
        3. Return top-k most similar entries

        This simplified version uses keyword matching.
        """
        all_entries = list(self.storage.values())

        # Simple keyword-based relevance (replace with semantic search in production)
        scored_entries = []
        query_lower = query.lower()

        for entry in all_entries:
            score = 0.0

            # Keyword match
            if query_lower in entry.content.lower():
                score += 0.5

            # Importance weight
            score += entry.importance * 0.3

            # Recency weight (more recent = higher score)
            age_days = (datetime.now(timezone.utc) - entry.timestamp).days
            recency_score = max(0.0, 1.0 - age_days / 365.0)  # Decay over a year
            score += recency_score * 0.2

            scored_entries.append((entry, score))

        # Sort by score (descending)
        scored_entries.sort(key=lambda x: x[1], reverse=True)

        # Return top-k
        results = [entry for entry, score in scored_entries[:limit]]

        # Update access time
        now = datetime.now(timezone.utc)
        for entry in results:
            entry.access_count += 1
            entry.last_accessed = now

        return results

    async def delete(self, entry_id: str) -> None:
        """Remove from storage."""
        self.storage.pop(entry_id, None)

    def __len__(self) -> int:
        """Number of entries in long-term memory."""
        return len(self.storage)


class MemoryHierarchy:
    """
    Multi-tier memory system for agents.

    Manages working, short-term, and long-term memory with automatic
    promotion and intelligent retrieval across tiers.

    Architecture:
        Working Memory (current conversation)
            ↓ (eviction)
        Short-Term Memory (recent sessions)
            ↓ (importance-based promotion)
        Long-Term Memory (persistent facts)

    Performance Characteristics:
    - Store: O(1) in working, O(1) in short-term, O(log n) in long-term
    - Retrieve: Searches all tiers in parallel, O(n) total
    - Automatic tier management

    Args:
        working_memory: Working memory instance
        short_term_memory: Optional short-term memory instance
        long_term_memory: Optional long-term memory instance

    Example:
        >>> memory = MemoryHierarchy(
        ...     working_memory=WorkingMemory(max_messages=10),
        ...     short_term_memory=ShortTermMemory(max_messages=100),
        ...     long_term_memory=LongTermMemory(min_importance=0.7)
        ... )
        >>>
        >>> # Store across tiers
        >>> await memory.store(
        ...     content="User is vegetarian",
        ...     importance=0.9,  # High importance -> goes to long-term
        ...     metadata={"category": "dietary_preferences"}
        ... )
        >>>
        >>> # Retrieve from all tiers
        >>> memories = await memory.retrieve(
        ...     query="What are the user's dietary restrictions?",
        ...     limit=5
        ... )
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        short_term_memory: ShortTermMemory | None = None,
        long_term_memory: LongTermMemory | None = None,
    ):
        self.working = working_memory
        self.short_term = short_term_memory
        self.long_term = long_term_memory

    async def store(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Store memory across appropriate tiers.

        Args:
            content: Memory content
            metadata: Optional structured metadata
            importance: Importance score (0.0-1.0)
            session_id: Optional session identifier
            **kwargs: Additional parameters

        Returns:
            ID of stored memory entry

        Raises:
            ValueError: If importance not in valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("importance must be between 0.0 and 1.0")

        # Create entry
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc),
            importance=importance,
            session_id=session_id,
        )

        # Always store in working memory
        await self.working.store(entry)

        # Store in short-term if available
        if self.short_term is not None:
            await self.short_term.store(entry)

        # Store in long-term if important enough
        if self.long_term is not None and importance >= self.long_term.min_importance:
            await self.long_term.store(entry)

        return entry.id

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        search_tiers: list[str] | None = None,
        **kwargs: Any,
    ) -> list[MemoryEntry]:
        """
        Retrieve memories from hierarchy.

        Searches across all enabled tiers and returns deduplicated,
        ranked results.

        Args:
            query: Search query
            limit: Maximum results to return
            search_tiers: Which tiers to search (default: all enabled)
            **kwargs: Additional search parameters

        Returns:
            List of relevant memory entries, ordered by relevance
        """
        if search_tiers is None:
            # Search all available tiers
            search_tiers = []
            search_tiers.append("working")
            if self.short_term is not None:
                search_tiers.append("short_term")
            if self.long_term is not None:
                search_tiers.append("long_term")

        results: list[MemoryEntry] = []

        # Search working memory
        if "working" in search_tiers:
            working_results = await self.working.retrieve(query, limit=limit)
            results.extend(working_results)

        # Search short-term memory
        if "short_term" in search_tiers and self.short_term is not None:
            short_results = await self.short_term.retrieve(query, limit=limit)
            results.extend(short_results)

        # Search long-term memory
        if "long_term" in search_tiers and self.long_term is not None:
            long_results = await self.long_term.retrieve(query, limit=limit)
            results.extend(long_results)

        # Deduplicate and rank
        unique_results = self._deduplicate(results)
        ranked_results = self._rank_by_relevance(unique_results, query)

        return ranked_results[:limit]

    def _deduplicate(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        """
        Remove duplicate entries.

        Args:
            entries: List of memory entries (may contain duplicates)

        Returns:
            List with duplicates removed
        """
        seen_ids: set[str] = set()
        unique: list[MemoryEntry] = []

        for entry in entries:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                unique.append(entry)

        return unique

    def _rank_by_relevance(
        self,
        entries: list[MemoryEntry],
        query: str,
    ) -> list[MemoryEntry]:
        """
        Rank entries by relevance to query.

        Ranking factors:
        - Keyword match: Does query appear in content?
        - Importance: Higher importance = higher rank
        - Recency: More recent = higher rank
        - Access frequency: More accessed = higher rank

        Args:
            entries: Memory entries to rank
            query: Search query

        Returns:
            Entries sorted by relevance score (descending)
        """
        scored: list[tuple[MemoryEntry, float]] = []
        query_lower = query.lower()

        for entry in entries:
            score = 0.0

            # Keyword match (30% weight)
            if query_lower in entry.content.lower():
                score += 0.3

            # Importance (30% weight)
            score += entry.importance * 0.3

            # Recency (20% weight)
            age_seconds = (datetime.now(timezone.utc) - entry.timestamp).total_seconds()
            max_age = 86400  # 1 day in seconds
            recency_score = max(0.0, 1.0 - age_seconds / max_age)
            score += recency_score * 0.2

            # Access frequency (20% weight)
            # Normalize by dividing by a reasonable max (100 accesses)
            access_score = min(1.0, entry.access_count / 100.0)
            score += access_score * 0.2

            scored.append((entry, score))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        return [entry for entry, score in scored]

    async def clear_tier(self, tier: str) -> None:
        """
        Clear a specific memory tier.

        Args:
            tier: Tier to clear ("working", "short_term", or "long_term")

        Raises:
            ValueError: If tier is invalid or not configured
        """
        if tier == "working":
            self.working.clear()
        elif tier == "short_term":
            if not self.short_term:
                raise ValueError("Short-term memory not configured")
            # Clear all entries
            for entry in await self.short_term.retrieve("", limit=9999):
                await self.short_term.delete(entry.id)
        elif tier == "long_term":
            if not self.long_term:
                raise ValueError("Long-term memory not configured")
            # Clear all entries
            for entry in await self.long_term.retrieve("", limit=9999):
                await self.long_term.delete(entry.id)
        else:
            raise ValueError(f"Invalid tier: {tier}. Must be 'working', 'short_term', or 'long_term'")

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about memory usage.

        Returns:
            Dictionary with stats for each tier
        """
        stats = {
            "working": {
                "size": len(self.working),
                "capacity": self.working.max_messages,
            }
        }

        if self.short_term is not None:
            stats["short_term"] = {
                "size": len(self.short_term),
                "capacity": self.short_term.max_messages,
                "ttl_seconds": self.short_term.ttl.total_seconds(),
            }

        if self.long_term is not None:
            stats["long_term"] = {
                "size": len(self.long_term),
                "min_importance": self.long_term.min_importance,
            }

        return stats
