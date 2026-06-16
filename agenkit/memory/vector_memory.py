"""
Vector-based implementation of Memory interface.

Provides semantic retrieval using embeddings and vector similarity
for intelligent context management.

Supports pluggable embedding providers and vector stores.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from ..interfaces import Message
from .base import Memory


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass


class VectorStore(ABC):
    """Abstract interface for vector stores."""

    @abstractmethod
    async def add(
        self,
        session_id: str,
        message_id: str,
        embedding: list[float],
        message: Message,
        metadata: dict,
        timestamp: float,
    ) -> None:
        """Add message with embedding to store."""
        pass

    @abstractmethod
    async def search(
        self, session_id: str, query_embedding: list[float], limit: int, **kwargs
    ) -> list[tuple[Message, dict, float]]:
        """
        Search for similar messages.

        Returns:
            List of (message, metadata, score) tuples
        """
        pass

    @abstractmethod
    async def get_recent(self, session_id: str, limit: int, **kwargs) -> list[tuple[Message, dict]]:
        """
        Get recent messages without search.

        Supports same kwargs as search() for filtering:
        - time_range: tuple[datetime, datetime]
        - importance_threshold: float
        - tags: list[str]
        """
        pass

    @abstractmethod
    async def clear(self, session_id: str) -> None:
        """Clear all messages for session."""
        pass


class MemoryVectorStore(VectorStore):
    """
    Simple in-memory vector store using cosine similarity.

    Good for testing and small datasets. For production, use
    specialized vector databases (Pinecone, Weaviate, Qdrant, etc.).
    """

    def __init__(self):
        # session_id -> list of (message_id, embedding, message, metadata, timestamp)
        self._storage: dict[str, list[tuple[str, list[float], Message, dict, float]]] = {}
        self._id_counter = 0

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    async def add(
        self,
        session_id: str,
        message_id: str,
        embedding: list[float],
        message: Message,
        metadata: dict,
        timestamp: float,
    ) -> None:
        """Add message with embedding to store."""
        if session_id not in self._storage:
            self._storage[session_id] = []

        self._storage[session_id].append((message_id, embedding, message, metadata, timestamp))

    async def search(
        self, session_id: str, query_embedding: list[float], limit: int, **kwargs
    ) -> list[tuple[Message, dict, float]]:
        """Search for similar messages using cosine similarity."""
        if session_id not in self._storage:
            return []

        # Calculate similarity for all messages
        results = []
        for _msg_id, embedding, message, metadata, timestamp in self._storage[session_id]:
            score = self._cosine_similarity(query_embedding, embedding)
            results.append((message, metadata, score, timestamp))

        # Sort by score (descending)
        results.sort(key=lambda x: x[2], reverse=True)

        # Apply filters if provided
        filtered = []
        for message, metadata, score, timestamp in results:
            # Time range filter
            if "time_range" in kwargs:
                start_time, end_time = kwargs["time_range"]
                msg_time = datetime.fromtimestamp(timestamp, tz=UTC)
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

            # Minimum similarity threshold
            min_score = kwargs.get("min_similarity", 0.0)
            if score < min_score:
                continue

            filtered.append((message, metadata, score))

            if len(filtered) >= limit:
                break

        return filtered[:limit]

    async def get_recent(self, session_id: str, limit: int, **kwargs) -> list[tuple[Message, dict]]:
        """Get recent messages without search."""
        if session_id not in self._storage:
            return []

        # Sort by timestamp (most recent first)
        messages = sorted(
            self._storage[session_id],
            key=lambda x: x[4],  # timestamp
            reverse=True,
        )

        # Apply filters
        filtered = []
        for _msg_id, _embedding, message, metadata, timestamp in messages:
            # Time range filter
            if "time_range" in kwargs:
                start_time, end_time = kwargs["time_range"]
                msg_time = datetime.fromtimestamp(timestamp, tz=UTC)
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

            filtered.append((message, metadata))

            if len(filtered) >= limit:
                break

        return filtered[:limit]

    async def clear(self, session_id: str) -> None:
        """Clear all messages for session."""
        if session_id in self._storage:
            del self._storage[session_id]


class VectorMemory(Memory):
    """
    Vector database for semantic retrieval.

    Features:
    - Semantic search via embeddings
    - Relevance-based retrieval
    - Pluggable embedding providers
    - Pluggable vector stores

    Use cases:
    - RAG (Retrieval-Augmented Generation)
    - Semantic memory
    - Large knowledge bases
    - Context-aware agents

    Example:
        >>> # With custom embedding provider
        >>> from openai import AsyncOpenAI
        >>>
        >>> class OpenAIEmbeddings(EmbeddingProvider):
        ...     def __init__(self, client):
        ...         self.client = client
        ...
        ...     async def embed(self, text):
        ...         response = await self.client.embeddings.create(
        ...             input=text,
        ...             model="text-embedding-3-small"
        ...         )
        ...         return response.data[0].embedding
        ...
        ...     def dimension(self):
        ...         return 1536
        >>>
        >>> embeddings = OpenAIEmbeddings(AsyncOpenAI())
        >>> memory = VectorMemory(embeddings)
        >>> await memory.store("session-123", message)
        >>>
        >>> # Semantic search
        >>> messages = await memory.retrieve(
        ...     "session-123",
        ...     query="What did we discuss about pricing?",
        ...     limit=5
        ... )
    """

    def __init__(
        self, embedding_provider: EmbeddingProvider, vector_store: VectorStore | None = None
    ):
        """
        Initialize vector memory.

        Args:
            embedding_provider: Provider for generating embeddings
            vector_store: Vector storage backend (defaults to in-memory)
        """
        self.embeddings = embedding_provider
        self.vector_store = vector_store or MemoryVectorStore()
        self._id_counter = 0

    def _generate_id(self) -> str:
        """Generate unique message ID."""
        self._id_counter += 1
        return f"msg-{self._id_counter}"

    async def store(self, session_id: str, message: Message, metadata: dict | None = None) -> None:
        """Store message with embedding in vector store."""
        # Generate embedding
        embedding = await self.embeddings.embed(message.content)

        # Store
        timestamp = datetime.now(UTC).timestamp()
        message_id = self._generate_id()

        await self.vector_store.add(
            session_id=session_id,
            message_id=message_id,
            embedding=embedding,
            message=message,
            metadata=metadata or {},
            timestamp=timestamp,
        )

    async def retrieve(
        self, session_id: str, query: str | None = None, limit: int = 10, **kwargs
    ) -> list[Message]:
        """
        Retrieve messages with semantic search.

        If query provided, performs semantic search.
        Otherwise, returns most recent messages.

        Supports kwargs:
        - time_range: tuple[datetime, datetime]
        - importance_threshold: float
        - tags: list[str]
        - min_similarity: float (0-1, for semantic search)
        """
        if query:
            # Semantic search
            query_embedding = await self.embeddings.embed(query)
            results = await self.vector_store.search(
                session_id=session_id, query_embedding=query_embedding, limit=limit, **kwargs
            )
            # Return just messages (drop metadata and scores)
            return [msg for msg, _, _ in results]
        else:
            # Recent messages (no search)
            results = await self.vector_store.get_recent(session_id, limit, **kwargs)
            return [msg for msg, _ in results]

    async def retrieve_with_scores(
        self, session_id: str, query: str, limit: int = 10, **kwargs
    ) -> list[tuple[Message, float]]:
        """
        Retrieve messages with similarity scores.

        Returns:
            List of (message, score) tuples
        """
        query_embedding = await self.embeddings.embed(query)
        results = await self.vector_store.search(
            session_id=session_id, query_embedding=query_embedding, limit=limit, **kwargs
        )
        return [(msg, score) for msg, _, score in results]

    async def summarize(self, session_id: str, **kwargs) -> Message:
        """
        Create summary of conversation history.

        For vector memory, we can use semantic search to find
        key messages and summarize those.
        """
        messages = await self.retrieve(session_id, limit=100)

        if not messages:
            return Message(role="system", content="No messages in session.")

        # Simple concatenation summary
        summary_parts = []
        for i, msg in enumerate(messages[:10], 1):  # Last 10 messages
            preview = msg.content[:100]
            if len(msg.content) > 100:
                preview += "..."
            summary_parts.append(f"{i}. [{msg.role}] {preview}")

        summary_content = f"Session summary ({len(messages)} messages):\n" + "\n".join(
            summary_parts
        )

        return Message(role="system", content=summary_content)

    async def clear(self, session_id: str) -> None:
        """Clear memory for session."""
        await self.vector_store.clear(session_id)

    @property
    def capabilities(self) -> list[str]:
        """Return memory capabilities."""
        return [
            "basic_retrieval",
            "semantic_search",
            "similarity_retrieval",
            "time_filtering",
            "importance_filtering",
            "tag_filtering",
        ]


# Deprecated alias — use MemoryVectorStore in new code.
InMemoryVectorStore = MemoryVectorStore  # Deprecated: Use MemoryVectorStore instead.
