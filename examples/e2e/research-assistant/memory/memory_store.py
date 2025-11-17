"""Memory store implementation for autonomous research assistant.

Provides different types of memory:
- Working Memory: Current task context and intermediate results
- Short-term Memory: Recent conversation history
- Long-term Memory: Important facts and findings to retain
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import json


class MemoryType(Enum):
    """Types of memory in the system."""

    WORKING = "working"  # Current task context
    SHORT_TERM = "short_term"  # Recent history
    LONG_TERM = "long_term"  # Important retained facts


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: str
    content: str
    memory_type: MemoryType
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    importance: float = 0.5  # 0.0 to 1.0, used for memory consolidation
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    def access(self):
        """Record that this memory was accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class MemoryStore:
    """
    Memory management system for autonomous agent.

    Manages three types of memory:
    - Working memory: Current task state (cleared between tasks)
    - Short-term memory: Recent conversation (limited size, FIFO)
    - Long-term memory: Important facts (consolidated from short-term)

    Example:
        ```python
        memory = MemoryStore(short_term_limit=50)

        # Store working memory
        memory.store(
            "task_plan",
            "1. Search for papers\\n2. Summarize findings",
            MemoryType.WORKING,
            {"task_id": "research_001"}
        )

        # Store conversation
        memory.store(
            "user_query",
            "Find papers about neural networks",
            MemoryType.SHORT_TERM
        )

        # Retrieve memories
        task_plan = memory.get("task_plan")
        recent = memory.get_recent(limit=10, memory_type=MemoryType.SHORT_TERM)
        ```
    """

    def __init__(
        self,
        short_term_limit: int = 100,
        long_term_consolidation_threshold: float = 0.7,
    ):
        """
        Initialize memory store.

        Args:
            short_term_limit: Max short-term memories before eviction
            long_term_consolidation_threshold: Importance threshold for long-term storage
        """
        self.memories: Dict[str, MemoryEntry] = {}
        self.short_term_limit = short_term_limit
        self.long_term_consolidation_threshold = long_term_consolidation_threshold
        self._memory_counter = 0

    def store(
        self,
        memory_id: str,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> MemoryEntry:
        """
        Store a memory entry.

        Args:
            memory_id: Unique identifier for this memory
            content: The memory content
            memory_type: Type of memory (working/short-term/long-term)
            metadata: Additional metadata
            importance: Importance score (0.0-1.0)

        Returns:
            The created MemoryEntry
        """
        if memory_id in self.memories:
            # Update existing memory
            entry = self.memories[memory_id]
            entry.content = content
            entry.metadata.update(metadata or {})
            entry.importance = max(entry.importance, importance)
            entry.access()
        else:
            # Create new memory
            entry = MemoryEntry(
                id=memory_id,
                content=content,
                memory_type=memory_type,
                metadata=metadata or {},
                importance=importance,
            )
            self.memories[memory_id] = entry
            self._memory_counter += 1

        # Handle short-term memory limits
        if memory_type == MemoryType.SHORT_TERM:
            self._consolidate_short_term_memory()

        return entry

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory by ID.

        Args:
            memory_id: The memory identifier

        Returns:
            The MemoryEntry or None if not found
        """
        entry = self.memories.get(memory_id)
        if entry:
            entry.access()
        return entry

    def get_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """
        Get all memories of a specific type.

        Args:
            memory_type: The type to filter by

        Returns:
            List of matching memories
        """
        return [m for m in self.memories.values() if m.memory_type == memory_type]

    def get_recent(
        self, limit: int = 10, memory_type: Optional[MemoryType] = None
    ) -> List[MemoryEntry]:
        """
        Get most recent memories.

        Args:
            limit: Maximum number of memories to return
            memory_type: Optional filter by memory type

        Returns:
            List of recent memories, newest first
        """
        memories = list(self.memories.values())

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:limit]

    def search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        min_importance: float = 0.0,
    ) -> List[MemoryEntry]:
        """
        Simple keyword search across memories.

        Args:
            query: Search query (case-insensitive)
            memory_type: Optional filter by type
            min_importance: Minimum importance threshold

        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        results = []

        for memory in self.memories.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            if memory.importance < min_importance:
                continue
            if query_lower in memory.content.lower():
                memory.access()
                results.append(memory)

        # Sort by relevance (access count * importance)
        results.sort(key=lambda m: m.access_count * m.importance, reverse=True)
        return results

    def clear_working_memory(self):
        """Clear all working memory entries."""
        to_remove = [
            mid
            for mid, m in self.memories.items()
            if m.memory_type == MemoryType.WORKING
        ]
        for mid in to_remove:
            del self.memories[mid]

    def clear_all(self):
        """Clear all memories."""
        self.memories.clear()
        self._memory_counter = 0

    def _consolidate_short_term_memory(self):
        """
        Move important short-term memories to long-term and evict old ones.

        This is called automatically when short-term memory exceeds limits.
        """
        short_term = self.get_by_type(MemoryType.SHORT_TERM)

        # If under limit, nothing to do
        if len(short_term) <= self.short_term_limit:
            return

        # Sort by creation time (oldest first)
        short_term.sort(key=lambda m: m.created_at)

        # Process oldest memories
        to_evict_count = len(short_term) - self.short_term_limit
        for memory in short_term[:to_evict_count]:
            # Important memories get promoted to long-term
            if memory.importance >= self.long_term_consolidation_threshold:
                memory.memory_type = MemoryType.LONG_TERM
                memory.metadata["consolidated_from"] = "short_term"
                memory.metadata["consolidated_at"] = datetime.now().isoformat()
            else:
                # Less important memories get evicted
                del self.memories[memory.id]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about memory usage.

        Returns:
            Dict with memory statistics
        """
        by_type = {}
        for mem_type in MemoryType:
            memories = self.get_by_type(mem_type)
            by_type[mem_type.value] = {
                "count": len(memories),
                "total_size": sum(len(m.content) for m in memories),
                "avg_importance": (
                    sum(m.importance for m in memories) / len(memories)
                    if memories
                    else 0.0
                ),
            }

        return {
            "total_memories": len(self.memories),
            "by_type": by_type,
            "total_accesses": sum(m.access_count for m in self.memories.values()),
        }

    def save_checkpoint(self, filepath: str):
        """
        Save memory state to disk.

        Args:
            filepath: Path to save checkpoint file
        """
        checkpoint = {
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "memory_type": m.memory_type.value,
                    "metadata": m.metadata,
                    "created_at": m.created_at.isoformat(),
                    "importance": m.importance,
                    "access_count": m.access_count,
                    "last_accessed": m.last_accessed.isoformat(),
                }
                for m in self.memories.values()
            ],
            "counter": self._memory_counter,
        }

        with open(filepath, "w") as f:
            json.dump(checkpoint, f, indent=2)

    def load_checkpoint(self, filepath: str):
        """
        Load memory state from disk.

        Args:
            filepath: Path to checkpoint file
        """
        with open(filepath, "r") as f:
            checkpoint = json.load(f)

        self.memories.clear()
        for mem_data in checkpoint["memories"]:
            memory = MemoryEntry(
                id=mem_data["id"],
                content=mem_data["content"],
                memory_type=MemoryType(mem_data["memory_type"]),
                metadata=mem_data["metadata"],
                created_at=datetime.fromisoformat(mem_data["created_at"]),
                importance=mem_data["importance"],
                access_count=mem_data["access_count"],
                last_accessed=datetime.fromisoformat(mem_data["last_accessed"]),
            )
            self.memories[memory.id] = memory

        self._memory_counter = checkpoint["counter"]

    def __len__(self) -> int:
        """Return total number of memories."""
        return len(self.memories)

    def __repr__(self) -> str:
        """String representation of memory store."""
        summary = self.get_summary()
        return f"MemoryStore(total={summary['total_memories']}, working={summary['by_type']['working']['count']}, short_term={summary['by_type']['short_term']['count']}, long_term={summary['by_type']['long_term']['count']})"
