"""
Memory systems for agent conversation management.

This package provides interfaces and implementations for agent memory,
enabling context management beyond raw message lists.

Classes:
    Memory: Abstract base class for memory systems
    InMemoryMemory: Simple in-memory storage with LRU eviction
    RedisMemory: Redis-backed memory with persistence
    VectorMemory: Vector database for semantic retrieval
    EndlessMemory: Integration with endless project for infinite context

Strategies:
    MemoryStrategy: Base class for memory strategies
    SlidingWindowStrategy: Keep most recent N messages
    ImportanceWeightingStrategy: Prioritize by importance score
    SummarizationStrategy: Summarize old, keep recent verbatim

Example:
    >>> from agenkit.memory import InMemoryMemory, SlidingWindowStrategy
    >>> memory = InMemoryMemory(max_size=1000)
    >>> strategy = SlidingWindowStrategy(window_size=10)
    >>> await memory.store("session-123", message)
    >>> messages = await strategy.select(memory, "session-123", context_limit=10)
"""

from .base import Memory
from .in_memory import InMemoryMemory
from .vector_memory import (
    VectorMemory,
    EmbeddingProvider,
    VectorStore,
    InMemoryVectorStore
)
from .endless_memory import EndlessMemory, EndlessClient

# Import strategies
from .strategies import (
    MemoryStrategy,
    SlidingWindowStrategy,
    ImportanceWeightingStrategy,
    SummarizationStrategy
)

# Optional imports (require extra dependencies)
try:
    from .redis_memory import RedisMemory
    __all__ = [
        "Memory",
        "InMemoryMemory",
        "RedisMemory",
        "VectorMemory",
        "EndlessMemory",
        "EndlessClient",
        "EmbeddingProvider",
        "VectorStore",
        "InMemoryVectorStore",
        "MemoryStrategy",
        "SlidingWindowStrategy",
        "ImportanceWeightingStrategy",
        "SummarizationStrategy",
    ]
except ImportError:
    __all__ = [
        "Memory",
        "InMemoryMemory",
        "VectorMemory",
        "EndlessMemory",
        "EndlessClient",
        "EmbeddingProvider",
        "VectorStore",
        "InMemoryVectorStore",
        "MemoryStrategy",
        "SlidingWindowStrategy",
        "ImportanceWeightingStrategy",
        "SummarizationStrategy",
    ]
