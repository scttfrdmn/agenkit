"""
Memory systems for agent conversation management.

This package provides interfaces and implementations for agent memory,
enabling context management beyond raw message lists.

Classes:
    Memory: Abstract base class for memory systems
    EphemeralMemory: Simple in-memory storage with LRU eviction
    HierarchyMemory: 3-tier hierarchy adapter (backward compatible)
    RedisMemory: Redis-backed memory with persistence
    VectorMemory: Vector database for semantic retrieval
    EndlessMemory: Integration with endless project for infinite context

Strategies:
    MemoryStrategy: Base class for memory strategies
    SlidingWindowStrategy: Keep most recent N messages
    ImportanceWeightingStrategy: Prioritize by importance score
    SummarizationStrategy: Summarize old, keep recent verbatim

Example:
    >>> from agenkit.memory import EphemeralMemory, SlidingWindowStrategy
    >>> memory = EphemeralMemory(max_size=1000)
    >>> strategy = SlidingWindowStrategy(window_size=10)
    >>> await memory.store("session-123", message)
    >>> messages = await strategy.select(memory, "session-123", context_limit=10)
"""

from .base import Memory
from .endless_memory import EndlessClient, EndlessMemory
from .hierarchy_memory import HierarchyMemory
from .in_memory import EphemeralMemory, InMemoryMemory

# Import strategies
from .strategies import (
    ImportanceWeightingStrategy,
    MemoryStrategy,
    SlidingWindowStrategy,
    SummarizationStrategy,
)
from .vector_memory import (
    EmbeddingProvider,
    InMemoryVectorStore,
    MemoryVectorStore,
    VectorMemory,
    VectorStore,
)

# Optional imports (require extra dependencies)
try:
    from .redis_memory import RedisMemory

    __all__ = [
        "EmbeddingProvider",
        "EndlessClient",
        "EndlessMemory",
        # Current names
        "EphemeralMemory",
        "HierarchyMemory",
        "ImportanceWeightingStrategy",
        "Memory",
        "MemoryStrategy",
        "MemoryVectorStore",
        "RedisMemory",
        "SlidingWindowStrategy",
        "SummarizationStrategy",
        "VectorMemory",
        "VectorStore",
        # Deprecated aliases
        "InMemoryMemory",
        "InMemoryVectorStore",
    ]
except ImportError:
    __all__ = [
        "EmbeddingProvider",
        "EndlessClient",
        "EndlessMemory",
        # Current names
        "EphemeralMemory",
        "HierarchyMemory",
        "ImportanceWeightingStrategy",
        "Memory",
        "MemoryStrategy",
        "MemoryVectorStore",
        "SlidingWindowStrategy",
        "SummarizationStrategy",
        "VectorMemory",
        "VectorStore",
        # Deprecated aliases
        "InMemoryMemory",
        "InMemoryVectorStore",
    ]
