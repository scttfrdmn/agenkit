"""
Redis-backed implementation of Memory interface.

Provides persistent memory storage with TTL and multi-instance support
for production deployments.

Requires: redis>=5.0.0
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as redis
else:
    try:
        import redis.asyncio as redis
    except ImportError:
        redis = None  # type: ignore

from .base import Memory
from ..interfaces import Message


class RedisMemory(Memory):
    """
    Redis-backed memory with TTL and pub/sub.

    Features:
    - Persistent storage (survives restarts)
    - TTL support (automatic expiry)
    - Multi-instance agents (shared memory)
    - Fast access (in-memory Redis)
    - Scalable (Redis cluster support)

    Use cases:
    - Production deployments
    - Multi-instance agents
    - When persistence needed
    - Shared memory across agents

    Example:
        >>> memory = RedisMemory(
        ...     redis_url="redis://localhost:6379",
        ...     ttl=86400  # 24 hours
        ... )
        >>> await memory.store("session-123", message)
        >>> messages = await memory.retrieve("session-123", limit=10)

    Redis Data Structure:
        - Key: "agenkit:memory:{session_id}:messages"
        - Type: Sorted Set (ZSET)
        - Score: Timestamp (for ordering)
        - Value: JSON(message, metadata)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl: int = 86400,  # 24 hours
        key_prefix: str = "agenkit:memory"
    ):
        """
        Initialize Redis memory.

        Args:
            redis_url: Redis connection URL
            ttl: Time-to-live in seconds (0 = no expiry)
            key_prefix: Prefix for Redis keys

        Raises:
            ImportError: If redis package not installed
        """
        if redis is None:
            raise ImportError(
                "redis package required for RedisMemory. "
                "Install with: pip install redis>=5.0.0"
            )

        self.redis_url = redis_url
        self.ttl = ttl
        self.key_prefix = key_prefix
        self._client: Optional["redis.Redis"] = None

    async def _get_client(self) -> "redis.Redis":
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def _session_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self.key_prefix}:{session_id}:messages"

    def _serialize_message(self, message: Message, metadata: dict) -> str:
        """Serialize message and metadata to JSON."""
        data = {
            "role": message.role,
            "content": message.content,
            "metadata": metadata
        }
        return json.dumps(data)

    def _deserialize_message(self, data: str) -> tuple[Message, dict]:
        """Deserialize JSON to message and metadata."""
        parsed = json.loads(data)
        message = Message(
            role=parsed["role"],
            content=parsed["content"]
        )
        metadata = parsed.get("metadata", {})
        return message, metadata

    async def store(
        self,
        session_id: str,
        message: Message,
        metadata: Optional[dict] = None
    ) -> None:
        """Store message in Redis with optional metadata."""
        client = await self._get_client()

        # Serialize
        timestamp = datetime.now(timezone.utc).timestamp()
        value = self._serialize_message(message, metadata or {})

        # Store in sorted set (score = timestamp)
        key = self._session_key(session_id)
        await client.zadd(key, {value: timestamp})

        # Set TTL if configured
        if self.ttl > 0:
            await client.expire(key, self.ttl)

    async def retrieve(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> list[Message]:
        """
        Retrieve messages from Redis.

        Supports kwargs:
        - time_range: tuple[datetime, datetime] for filtering
        - importance_threshold: float
        - tags: list[str]
        """
        client = await self._get_client()
        key = self._session_key(session_id)

        # Get messages (most recent first)
        # ZREVRANGE returns highest scores first
        values = await client.zrevrange(key, 0, -1, withscores=True)

        if not values:
            return []

        # Deserialize and filter
        filtered = []
        for value, timestamp in values:
            message, metadata = self._deserialize_message(value)

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
        client = await self._get_client()
        key = self._session_key(session_id)
        await client.delete(key)

    @property
    def capabilities(self) -> list[str]:
        """Return memory capabilities."""
        return [
            "basic_retrieval",
            "persistence",
            "ttl",
            "time_filtering",
            "importance_filtering",
            "tag_filtering"
        ]

    # Additional utility methods

    async def get_session_count(self, session_id: str) -> int:
        """Get number of messages stored for session."""
        client = await self._get_client()
        key = self._session_key(session_id)
        count = await client.zcard(key)
        return count

    async def get_all_sessions(self) -> list[str]:
        """Get list of all session IDs."""
        client = await self._get_client()
        pattern = f"{self.key_prefix}:*:messages"
        keys = []
        async for key in client.scan_iter(match=pattern):
            # Extract session_id from key
            # Format: "agenkit:memory:{session_id}:messages"
            parts = key.split(":")
            if len(parts) >= 3:
                session_id = parts[-2]  # Second to last part
                keys.append(session_id)
        return keys

    async def get_memory_usage(self) -> dict[str, int]:
        """Get memory usage statistics."""
        client = await self._get_client()
        sessions = await self.get_all_sessions()

        total_messages = 0
        for session_id in sessions:
            count = await self.get_session_count(session_id)
            total_messages += count

        return {
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "ttl": self.ttl
        }

    async def close(self):
        """Close Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
