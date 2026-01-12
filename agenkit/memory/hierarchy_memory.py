"""
Backward-compatible adapter for MemoryHierarchy.

Implements the session-based Memory interface while using the 3-tier memory
hierarchy internally for improved performance and scalability.
"""

from datetime import datetime, timezone
from typing import Any

from ..interfaces import Message
from ..patterns.memory import (
    LongTermMemory,
    MemoryEntry,
    MemoryHierarchy,
    ShortTermMemory,
    WorkingMemory,
)
from .base import Memory


class HierarchyMemory(Memory):
    """
    Backward-compatible adapter wrapping MemoryHierarchy.

    Implements the session-based Memory interface while using the
    3-tier hierarchy internally for improved performance and scalability.

    Benefits over InMemoryMemory:
    - Automatic importance-based tier routing
    - FIFO/LRU/TTL eviction strategies
    - Better memory management for long sessions
    - Semantic retrieval across tiers
    - Proven architecture (used in Rust/C++/Zig)

    Architecture:
        - Working Memory: Current conversation (FIFO, 10-20 msgs)
        - Short-Term Memory: Recent sessions (LRU+TTL, 100-1000 msgs)
        - Long-Term Memory: Important facts (importance threshold, unlimited)

    Example:
        >>> memory = HierarchyMemory(
        ...     working_capacity=10,
        ...     short_term_capacity=100,
        ...     long_term_min_importance=0.7
        ... )
        >>> await memory.store("session-123", message)
        >>> messages = await memory.retrieve("session-123", limit=10)

    Drop-in replacement for InMemoryMemory:
        >>> # Before
        >>> memory = InMemoryMemory(max_size=1000)
        >>>
        >>> # After (same API, better performance)
        >>> memory = HierarchyMemory(
        ...     working_capacity=20,
        ...     short_term_capacity=1000
        ... )
    """

    def __init__(
        self,
        working_capacity: int = 10,
        short_term_capacity: int = 100,
        short_term_ttl_seconds: int = 3600,
        long_term_min_importance: float = 0.7,
        enable_long_term: bool = True,
    ):
        """
        Initialize HierarchyMemory with tier configurations.

        Args:
            working_capacity: Max messages in working memory (default: 10)
                             Increase for longer context windows
            short_term_capacity: Max messages in short-term memory (default: 100)
                                Increase for longer session history
            short_term_ttl_seconds: Time-to-live for short-term entries (default: 3600 = 1 hour)
                                   Increase to retain history longer
            long_term_min_importance: Minimum importance for long-term storage (default: 0.7)
                                     Lower to store more, higher for only critical info
            enable_long_term: Whether to enable long-term memory (default: True)
                             Disable for testing or simple use cases

        Performance Tuning:
            - Small context (chat): working=10, short_term=100, long_term_min=0.7
            - Large context (docs): working=20, short_term=500, long_term_min=0.6
            - Memory constrained: working=5, short_term=50, enable_long_term=False
        """
        if working_capacity < 1:
            raise ValueError("working_capacity must be at least 1")
        if short_term_capacity < 1:
            raise ValueError("short_term_capacity must be at least 1")
        if short_term_ttl_seconds < 1:
            raise ValueError("short_term_ttl_seconds must be at least 1")
        if not 0.0 <= long_term_min_importance <= 1.0:
            raise ValueError("long_term_min_importance must be between 0.0 and 1.0")

        # Create hierarchy
        working = WorkingMemory(max_messages=working_capacity)
        short_term = ShortTermMemory(
            max_messages=short_term_capacity, ttl_seconds=short_term_ttl_seconds
        )
        long_term = (
            LongTermMemory(min_importance=long_term_min_importance) if enable_long_term else None
        )

        self.hierarchy = MemoryHierarchy(
            working_memory=working, short_term_memory=short_term, long_term_memory=long_term
        )

    async def store(self, session_id: str, message: Message, metadata: dict | None = None) -> None:
        """
        Store message in hierarchy with session association.

        Args:
            session_id: Unique session identifier
            message: Message to store
            metadata: Optional metadata (importance score, tags, etc.)

        Importance Routing:
            - System messages: 0.3 (working + short-term only)
            - User messages: 0.5 (working + short-term, possibly long-term)
            - Assistant messages: 0.4 (working + short-term only)
            - High importance (0.7+): Stored in long-term memory

        To control routing, pass importance in metadata:
            >>> await memory.store(
            ...     "session-123",
            ...     message,
            ...     metadata={"importance": 0.9}  # Force long-term storage
            ... )
        """
        # Merge message metadata with provided metadata
        combined_metadata = {
            "session_id": session_id,
            "role": message.role,
            "message_timestamp": message.timestamp.isoformat(),  # Preserve original timestamp
            **(message.metadata or {}),
            **(metadata or {}),
        }

        # Determine importance (use provided, or default by role)
        importance = combined_metadata.get("importance", self._default_importance(message))

        # Ensure importance is within valid range
        importance = max(0.0, min(1.0, importance))

        # Convert Message content to string for storage
        content = str(message.content)

        # Store in hierarchy
        await self.hierarchy.store(
            content=content,
            metadata=combined_metadata,
            importance=importance,
            session_id=session_id,
        )

    async def retrieve(
        self, session_id: str, query: str | None = None, limit: int = 10, **kwargs: Any
    ) -> list[Message]:
        """
        Retrieve messages from hierarchy filtered by session.

        Args:
            session_id: Session identifier to filter by
            query: Optional semantic query (searches across all tiers)
            limit: Maximum number of messages to return
            **kwargs: Additional filters (importance_threshold, tags, etc.)

        Returns:
            List of messages from this session, ordered by relevance

        Note:
            Unlike InMemoryMemory, this searches semantically across all tiers
            when query is provided. For chronological order, use query="" or None.

        Performance:
            - With query: O(n log n) due to relevance ranking
            - Without query: O(n) where n is messages in session
            - Session filtering happens in Python after tier retrieval
        """
        # Retrieve from hierarchy (get extra to account for filtering)
        # We multiply limit by 3 because:
        # - Multiple sessions may be in hierarchy
        # - Need enough results after session filtering
        # - Better to over-retrieve than under-retrieve
        entries = await self.hierarchy.retrieve(query=query or "", limit=limit * 3)

        # Filter by session and convert to Messages
        messages = []
        for entry in entries:
            if entry.metadata.get("session_id") == session_id:
                # Apply additional filters if provided
                if not self._matches_filters(entry, kwargs):
                    continue

                messages.append(self._entry_to_message(entry))

            if len(messages) >= limit:
                break

        return messages[:limit]

    async def summarize(self, session_id: str, **kwargs: Any) -> Message:
        """
        Create summary of conversation history for session.

        Args:
            session_id: Session to summarize
            **kwargs: Additional parameters (unused in simple implementation)

        Returns:
            Summary message with role="system"

        Note:
            This is a simple implementation using concatenation.
            Production use should use LLM-based summarization.

        Example:
            >>> summary = await memory.summarize("session-123")
            >>> print(summary.content)
            Session summary (45 messages):
            1. [user] Hello, how are you?
            2. [assistant] I'm doing well...
            ...
        """
        # Retrieve all messages for session (up to reasonable limit)
        messages = await self.retrieve(session_id, limit=1000)

        if not messages:
            return Message(role="system", content="No messages in session.")

        # Simple concatenation summary (last 10 messages)
        summary_parts = []
        for i, msg in enumerate(messages[:10], 1):
            preview = str(msg.content)[:100]
            if len(str(msg.content)) > 100:
                preview += "..."
            summary_parts.append(f"{i}. [{msg.role}] {preview}")

        summary_content = f"Session summary ({len(messages)} messages):\n" + "\n".join(
            summary_parts
        )

        return Message(role="system", content=summary_content)

    async def clear(self, session_id: str) -> None:
        """
        Clear all messages for a session from all tiers.

        Args:
            session_id: Session to clear

        Note:
            This removes messages from working, short-term, and long-term memory.
            Deletion is permanent and cannot be undone.

        Performance:
            - O(n) where n is total messages in hierarchy
            - Must scan all tiers to find session entries
            - Consider using get_stats() before clearing to see impact
        """
        # Retrieve all entries for session (across all tiers)
        entries = await self.hierarchy.retrieve(query="", limit=9999)

        # Delete entries matching session from all tiers
        for entry in entries:
            if entry.metadata.get("session_id") == session_id:
                # Delete from working memory
                await self.hierarchy.working.delete(entry.id)

                # Delete from short-term memory if enabled
                if self.hierarchy.short_term is not None:
                    await self.hierarchy.short_term.delete(entry.id)

                # Delete from long-term memory if enabled
                if self.hierarchy.long_term is not None:
                    await self.hierarchy.long_term.delete(entry.id)

    def _default_importance(self, message: Message) -> float:
        """
        Calculate default importance score based on message role.

        Importance determines tier routing:
        - 0.0-0.3: Working + Short-term only (ephemeral)
        - 0.4-0.6: Working + Short-term only (normal)
        - 0.7-1.0: Working + Short-term + Long-term (important)

        Args:
            message: Message to score

        Returns:
            Importance score between 0.0 and 1.0

        Role-based defaults:
            - system: 0.3 (configuration, low importance)
            - user: 0.5 (normal importance, conversational)
            - assistant: 0.4 (responses, moderate importance)
            - tool: 0.3 (tool results, low importance)
        """
        role_importance = {
            "system": 0.3,
            "user": 0.5,
            "assistant": 0.4,
            "tool": 0.3,
            "agent": 0.4,
        }
        return role_importance.get(message.role, 0.5)

    def _entry_to_message(self, entry: MemoryEntry) -> Message:
        """
        Convert MemoryEntry back to Message.

        Args:
            entry: Memory entry from hierarchy

        Returns:
            Message object with role, content, and original timestamp

        Note:
            Filters out internal metadata and reconstructs original message timestamp.
        """
        from datetime import datetime

        # Extract role from metadata (default to assistant if not found)
        role = entry.metadata.get("role", "assistant")

        # Extract original message timestamp if preserved
        timestamp = entry.timestamp  # Default to storage timestamp
        if "message_timestamp" in entry.metadata:
            timestamp = datetime.fromisoformat(entry.metadata["message_timestamp"])

        # Filter out internal metadata keys
        filtered_metadata = {
            k: v
            for k, v in entry.metadata.items()
            if k not in ["session_id", "role", "message_timestamp"]
        }

        return Message(role=role, content=entry.content, metadata=filtered_metadata, timestamp=timestamp)

    def _matches_filters(self, entry: MemoryEntry, filters: dict[str, Any]) -> bool:
        """
        Check if entry matches provided filters.

        Args:
            entry: Memory entry to check
            filters: Filter criteria (importance_threshold, tags, time_range)

        Returns:
            True if entry matches all filters, False otherwise

        Supported filters:
            - importance_threshold: Minimum importance score
            - tags: List of required tags (any match)
            - time_range: Tuple of (start_datetime, end_datetime)
        """
        # Importance threshold filter
        if "importance_threshold" in filters:
            threshold = filters["importance_threshold"]
            if entry.importance < threshold:
                return False

        # Tags filter (any tag matches)
        if "tags" in filters:
            required_tags = set(filters["tags"])
            entry_tags = set(entry.metadata.get("tags", []))
            if not required_tags.intersection(entry_tags):
                return False

        # Time range filter - use original message timestamp, not storage timestamp
        if "time_range" in filters:
            start_time, end_time = filters["time_range"]

            # Get message timestamp from metadata (preserved from original Message)
            if "message_timestamp" in entry.metadata:
                from datetime import datetime
                message_timestamp = datetime.fromisoformat(entry.metadata["message_timestamp"])
                if not (start_time <= message_timestamp <= end_time):
                    return False
            else:
                # Fallback to storage timestamp if message timestamp not preserved
                if not (start_time <= entry.timestamp <= end_time):
                    return False

        return True

    # Additional utility methods for backward compatibility

    @property
    def capabilities(self) -> list[str]:
        """
        Return memory capabilities.

        Capabilities:
            - semantic_search: Search by content relevance
            - importance_filtering: Filter by importance score
            - tag_filtering: Filter by metadata tags
            - time_filtering: Filter by timestamp
            - multi_tier: Three-tier memory architecture
            - auto_eviction: Automatic FIFO/LRU/importance eviction
        """
        return [
            "semantic_search",
            "importance_filtering",
            "tag_filtering",
            "time_filtering",
            "multi_tier",
            "auto_eviction",
        ]

    def get_stats(self) -> dict[str, Any]:
        """
        Get memory usage statistics from hierarchy.

        Returns:
            Dictionary with stats for each tier:
                - working: {size, capacity}
                - short_term: {size, capacity, ttl_seconds}
                - long_term: {size, min_importance}

        Example:
            >>> stats = memory.get_stats()
            >>> print(f"Working: {stats['working']['size']}/{stats['working']['capacity']}")
            >>> print(f"Short-term: {stats['short_term']['size']}/{stats['short_term']['capacity']}")
        """
        return self.hierarchy.get_stats()

    def get_all_sessions(self) -> set[str]:
        """
        Get all session IDs currently in memory.

        Returns:
            Set of session IDs

        Note:
            This requires scanning all tiers, so performance is O(n)
            where n is total entries across all tiers.

        Warning:
            This is not an async method because it's for backward compatibility
            with InMemoryMemory. Use carefully in async code.
        """
        # This is not ideal for async code, but matches InMemoryMemory API
        # In production, consider deprecating this method or making it async
        sessions = set()

        # Scan working memory
        for entry in self.hierarchy.working.get_all():
            if "session_id" in entry.metadata:
                sessions.add(entry.metadata["session_id"])

        return sessions
