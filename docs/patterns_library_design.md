# Core Agent Patterns Library - Design Document (v0.12.0)

**Status**: Design Phase
**Issue**: #103
**Target Release**: v0.12.0
**Date**: November 2025

## Executive Summary

This document outlines the design and implementation plan for completing the Core Agent Patterns Library for Agenkit v0.12.0. The goal is to implement the 3 remaining patterns from Issue #103, enhance documentation for all patterns, and create comprehensive examples.

## Current State Analysis

### ✅ Patterns Already Implemented (5/8)

| Pattern | File | Status | Tests | Examples |
|---------|------|--------|-------|----------|
| 1. Sequential/Chain | `orchestration.py` | ✅ Complete | ✅ Yes | ✅ Yes |
| 2. Parallel/Fan-out | `orchestration.py` | ✅ Complete | ✅ Yes | ✅ Yes |
| 3. ReAct | `react.py` | ✅ Complete | ✅ Yes | ✅ Yes |
| 4. Planning/Planner-Executor | `planning.py` | ✅ Complete | ✅ Yes | ✅ Yes |
| 5. Consensus/Voting | `multiagent.py` | ✅ Complete | ✅ Yes | ✅ Yes |

**Additional Patterns Beyond Issue #103:**
- ✅ Router Pattern (`orchestration.py`)
- ✅ Conversational Pattern (`conversational.py`)
- ✅ Autonomous Pattern (`autonomous.py`)
- ✅ Task Pattern (`task.py`)

**Test Coverage**: ~2,075 lines across 5 test files

### ❌ Patterns to Implement (3/8)

| Pattern | Priority | Complexity | Estimated LOC |
|---------|----------|------------|---------------|
| 6. Reflection (Self-Critique) | P1-High | Medium | ~300 |
| 7. Agents-as-Tools (Hierarchical) | P1-High | Low | ~200 |
| 8. Memory Hierarchy | P0-Critical | High | ~500 |

---

## Architecture: Missing Patterns

### Pattern 6: Reflection Pattern (Self-Critique)

**Intent**: Agent reviews and critiques its own output, iteratively refining until quality threshold met.

**Use Cases**:
- Code generation with self-review
- Content creation with quality improvement
- Multi-draft writing
- Error detection and correction

**Architecture**:

```
┌─────────────────────────────────────────────────┐
│ ReflectionAgent                                 │
├─────────────────────────────────────────────────┤
│ 1. Generate initial response                    │
│ 2. Critique response (identify issues)          │
│ 3. Refine based on critique                     │
│ 4. Repeat until:                                │
│    - Quality threshold met                      │
│    - Max iterations reached                     │
│    - No more improvements suggested             │
└─────────────────────────────────────────────────┘
```

**API Design**:

```python
from agenkit.patterns import ReflectionAgent

agent = ReflectionAgent(
    generator=MyGeneratorAgent(),
    critic=MyCriticAgent(),
    max_iterations=5,
    quality_threshold=0.9,
    improvement_threshold=0.1  # Min improvement to continue
)

result = await agent.process(
    Message(role="user", content="Write a function to check if a number is prime")
)

# Result metadata includes reflection history
reflection_history = result.metadata["reflection_history"]
# [
#   {"iteration": 1, "output": "...", "critique": "...", "score": 0.6},
#   {"iteration": 2, "output": "...", "critique": "...", "score": 0.8},
#   {"iteration": 3, "output": "...", "critique": "...", "score": 0.95}
# ]
```

**Implementation Details**:

```python
@dataclass
class ReflectionStep:
    """Single iteration of reflection loop."""
    iteration: int
    output: str
    critique: str
    quality_score: float
    improvement: float
    timestamp: datetime

class ReflectionAgent(Agent):
    """
    Agent that iteratively refines output through self-critique.

    The reflection loop:
    1. Generator creates initial output
    2. Critic evaluates output, provides feedback
    3. Generator refines based on feedback
    4. Repeat until quality threshold or max iterations

    Args:
        generator: Agent that produces output
        critic: Agent that critiques output (returns score + feedback)
        max_iterations: Maximum refinement iterations (default: 5)
        quality_threshold: Stop when score exceeds this (default: 0.9)
        improvement_threshold: Min improvement to continue (default: 0.05)
    """

    def __init__(
        self,
        generator: Agent,
        critic: Agent,
        max_iterations: int = 5,
        quality_threshold: float = 0.9,
        improvement_threshold: float = 0.05
    ):
        self.generator = generator
        self.critic = critic
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.improvement_threshold = improvement_threshold
        self.history: list[ReflectionStep] = []

    async def process(self, message: Message) -> Message:
        """Execute reflection loop."""
        self.history = []

        # Initial generation
        output = await self.generator.process(message)
        previous_score = 0.0

        for iteration in range(self.max_iterations):
            # Critique current output
            critique_message = self._build_critique_prompt(
                original_query=message.content,
                current_output=output.content
            )
            critique_response = await self.critic.process(critique_message)

            # Parse critique (score + feedback)
            score, feedback = self._parse_critique(critique_response.content)
            improvement = score - previous_score

            # Record step
            step = ReflectionStep(
                iteration=iteration + 1,
                output=output.content,
                critique=feedback,
                quality_score=score,
                improvement=improvement,
                timestamp=datetime.now(timezone.utc)
            )
            self.history.append(step)

            # Check stopping conditions
            if score >= self.quality_threshold:
                return self._format_result(output, "quality_threshold_met")

            if improvement < self.improvement_threshold:
                return self._format_result(output, "minimal_improvement")

            # Refine based on critique
            refine_message = self._build_refinement_prompt(
                original_query=message.content,
                current_output=output.content,
                critique=feedback
            )
            output = await self.generator.process(refine_message)
            previous_score = score

        # Max iterations reached
        return self._format_result(output, "max_iterations")
```

**Key Features**:
- Pluggable generator and critic agents
- Configurable quality and improvement thresholds
- Detailed reflection history in metadata
- Multiple stopping conditions
- Clear separation of generation and critique

---

### Pattern 7: Agents-as-Tools Pattern (Hierarchical)

**Intent**: Agents can call other agents as tools, enabling hierarchical delegation.

**Use Cases**:
- Supervisor agent delegating to specialists
- Agent calling specialized sub-agents for specific tasks
- Hierarchical multi-agent systems
- Domain-specific agent orchestration

**Architecture**:

```
┌────────────────────────────────────┐
│ Supervisor Agent (with Tools)     │
├────────────────────────────────────┤
│ Tools:                             │
│  - code_specialist (Agent)         │
│  - data_specialist (Agent)         │
│  - research_specialist (Agent)     │
└────────────────────────────────────┘
         │
         ├─────> Code Specialist Agent
         ├─────> Data Specialist Agent
         └─────> Research Specialist Agent
```

**API Design**:

```python
from agenkit.patterns import AgentTool, agent_as_tool

# Wrap agent as a tool
code_specialist = CodeSpecialistAgent()
code_tool = agent_as_tool(
    agent=code_specialist,
    name="code_specialist",
    description="Specialist for code-related tasks. Use for programming questions, code review, debugging."
)

# Create supervisor with agent tools
supervisor = ReActAgent(
    llm_client=llm,
    tool_registry=ToolRegistry()
)
supervisor.tools.register(code_tool)
supervisor.tools.register(data_tool)
supervisor.tools.register(research_tool)

# Supervisor can delegate to specialist agents
result = await supervisor.process(
    Message(role="user", content="Write a Python function to parse JSON")
)
# Supervisor decides to use code_specialist tool
# -> Delegates to code_specialist agent
# -> Returns result to supervisor
# -> Supervisor formulates final answer
```

**Implementation Details**:

```python
class AgentTool:
    """
    Wrapper that exposes an agent as a tool.

    Allows agents to call other agents as tools, enabling
    hierarchical delegation and specialization.

    Args:
        agent: The agent to wrap as a tool
        name: Tool name for identification
        description: Description for LLM to understand when to use
        input_key: Key for input parameter (default: "query")
        output_format: How to format agent output (default: "str")
    """

    def __init__(
        self,
        agent: Agent,
        name: str,
        description: str,
        input_key: str = "query",
        output_format: str = "str"
    ):
        self.agent = agent
        self.name = name
        self.description = description
        self.input_key = input_key
        self.output_format = output_format

    async def execute(self, **kwargs) -> Any:
        """Execute the wrapped agent."""
        # Extract input
        query = kwargs.get(self.input_key)
        if query is None:
            raise ValueError(f"Missing required parameter: {self.input_key}")

        # Create message
        message = Message(role="user", content=str(query))

        # Call agent
        response = await self.agent.process(message)

        # Format output
        if self.output_format == "str":
            return response.content
        elif self.output_format == "dict":
            return {
                "content": response.content,
                "metadata": response.metadata
            }
        else:
            return response


def agent_as_tool(
    agent: Agent,
    name: str,
    description: str,
    input_key: str = "query",
    output_format: str = "str"
) -> AgentTool:
    """
    Convenience function to wrap an agent as a tool.

    Example:
        >>> specialist = CodeSpecialistAgent()
        >>> tool = agent_as_tool(
        ...     agent=specialist,
        ...     name="code_specialist",
        ...     description="Expert in Python programming"
        ... )
        >>> registry.register(tool)
    """
    return AgentTool(
        agent=agent,
        name=name,
        description=description,
        input_key=input_key,
        output_format=output_format
    )
```

**Key Features**:
- Simple wrapper pattern
- Works with any agent
- Compatible with existing ReActAgent and tool infrastructure
- Configurable input/output formatting
- Maintains observability (agent traces preserved)

---

### Pattern 8: Memory Hierarchy Pattern

**Intent**: Multi-tier memory system (working, short-term, long-term) for agents.

**Use Cases**:
- Long-running conversational agents
- Agents that need to remember facts across sessions
- Context-aware agents with limited context windows
- Personalization and learning

**Architecture**:

```
┌─────────────────────────────────────────────────┐
│ Memory Hierarchy                                │
├─────────────────────────────────────────────────┤
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ Working Memory (in-context)             │   │
│ │ - Current conversation                  │   │
│ │ - Immediate context                     │   │
│ │ - Fast access                           │   │
│ └─────────────────────────────────────────┘   │
│          │                                      │
│          │ (LRU eviction to short-term)        │
│          ▼                                      │
│ ┌─────────────────────────────────────────┐   │
│ │ Short-Term Memory (recent sessions)     │   │
│ │ - Recent conversations                  │   │
│ │ - Sliding window                        │   │
│ │ - Retrieval by recency                  │   │
│ └─────────────────────────────────────────┘   │
│          │                                      │
│          │ (Consolidation to long-term)        │
│          ▼                                      │
│ ┌─────────────────────────────────────────┐   │
│ │ Long-Term Memory (persistent storage)   │   │
│ │ - Important facts                       │   │
│ │ - User preferences                      │   │
│ │ - Retrieval by relevance (semantic)     │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

**API Design**:

```python
from agenkit.patterns import MemoryHierarchy, WorkingMemory, ShortTermMemory, LongTermMemory

# Create memory hierarchy
memory = MemoryHierarchy(
    working_memory=WorkingMemory(max_messages=10),
    short_term_memory=ShortTermMemory(max_messages=100, ttl_seconds=3600),
    long_term_memory=LongTermMemory(storage_backend=VectorStore())
)

# Create agent with memory
agent = ConversationalAgent(
    llm_client=llm,
    memory=memory
)

# Agent uses hierarchical memory
result = await agent.process(
    Message(role="user", content="What did I tell you about my preferences earlier?"),
    session_id="user-123"
)
# Agent searches:
# 1. Working memory (current conversation)
# 2. Short-term memory (recent sessions)
# 3. Long-term memory (persistent facts)
```

**Implementation Details**:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol


@dataclass
class MemoryEntry:
    """Single memory entry."""
    id: str
    content: str
    metadata: dict[str, Any]
    timestamp: datetime
    access_count: int = 0
    last_accessed: datetime | None = None
    importance: float = 0.0  # 0.0-1.0


class MemoryStore(ABC):
    """Abstract base for memory storage."""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> list[MemoryEntry]:
        """Retrieve relevant memories."""

    @abstractmethod
    async def delete(self, entry_id: str) -> None:
        """Delete a memory entry."""


class WorkingMemory(MemoryStore):
    """
    In-context working memory (current conversation).

    Characteristics:
    - Fast access (in-memory list)
    - Small capacity (10-20 messages)
    - FIFO eviction
    - No persistence

    Args:
        max_messages: Maximum messages to keep (default: 10)
    """

    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self._messages: list[MemoryEntry] = []

    async def store(self, entry: MemoryEntry) -> None:
        """Store message, evicting oldest if at capacity."""
        self._messages.append(entry)
        if len(self._messages) > self.max_messages:
            # Evict oldest (could promote to short-term here)
            self._messages.pop(0)

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> list[MemoryEntry]:
        """Return all messages (they're all relevant in working memory)."""
        return self._messages[-limit:]

    async def delete(self, entry_id: str) -> None:
        """Remove specific entry."""
        self._messages = [e for e in self._messages if e.id != entry_id]

    def get_all(self) -> list[MemoryEntry]:
        """Get all working memory (for context window)."""
        return self._messages.copy()


class ShortTermMemory(MemoryStore):
    """
    Recent session memory (sliding window).

    Characteristics:
    - Medium capacity (100-1000 messages)
    - TTL-based expiration
    - Retrieval by recency
    - Optional persistence

    Args:
        max_messages: Maximum messages to keep (default: 100)
        ttl_seconds: Time-to-live in seconds (default: 3600 = 1 hour)
    """

    def __init__(
        self,
        max_messages: int = 100,
        ttl_seconds: int = 3600
    ):
        self.max_messages = max_messages
        self.ttl = timedelta(seconds=ttl_seconds)
        self._messages: list[MemoryEntry] = []

    async def store(self, entry: MemoryEntry) -> None:
        """Store with TTL check."""
        # Clean expired entries
        await self._clean_expired()

        self._messages.append(entry)

        # Evict if over capacity (LRU)
        if len(self._messages) > self.max_messages:
            # Sort by access time, remove least recently used
            self._messages.sort(key=lambda e: e.last_accessed or e.timestamp)
            self._messages.pop(0)

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> list[MemoryEntry]:
        """Retrieve by recency (most recent first)."""
        await self._clean_expired()

        # Sort by timestamp, return most recent
        sorted_messages = sorted(
            self._messages,
            key=lambda e: e.timestamp,
            reverse=True
        )

        results = sorted_messages[:limit]

        # Update access time
        for entry in results:
            entry.access_count += 1
            entry.last_accessed = datetime.now(timezone.utc)

        return results

    async def delete(self, entry_id: str) -> None:
        """Remove specific entry."""
        self._messages = [e for e in self._messages if e.id != entry_id]

    async def _clean_expired(self) -> None:
        """Remove entries older than TTL."""
        now = datetime.now(timezone.utc)
        self._messages = [
            e for e in self._messages
            if now - e.timestamp < self.ttl
        ]


class LongTermMemory(MemoryStore):
    """
    Persistent semantic memory (vector store).

    Characteristics:
    - Large capacity (unlimited)
    - Semantic retrieval (embeddings)
    - Persistent storage
    - Importance-based retention

    Args:
        storage_backend: Vector store backend (e.g., ChromaDB, Pinecone)
        embedding_model: Model for creating embeddings
        min_importance: Minimum importance to store (default: 0.5)
    """

    def __init__(
        self,
        storage_backend: Any,  # Vector store interface
        embedding_model: Any | None = None,
        min_importance: float = 0.5
    ):
        self.storage = storage_backend
        self.embedding_model = embedding_model
        self.min_importance = min_importance

    async def store(self, entry: MemoryEntry) -> None:
        """Store if important enough."""
        if entry.importance < self.min_importance:
            return  # Not important enough for long-term storage

        # Create embedding
        if self.embedding_model:
            embedding = await self._create_embedding(entry.content)
        else:
            embedding = None

        # Store in backend
        await self.storage.upsert(
            id=entry.id,
            content=entry.content,
            embedding=embedding,
            metadata=entry.metadata
        )

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> list[MemoryEntry]:
        """Semantic retrieval by relevance."""
        # Create query embedding
        if self.embedding_model:
            query_embedding = await self._create_embedding(query)
        else:
            query_embedding = None

        # Search in vector store
        results = await self.storage.search(
            query_embedding=query_embedding,
            query_text=query,
            limit=limit,
            **kwargs
        )

        # Convert to MemoryEntry objects
        entries = [
            MemoryEntry(
                id=r["id"],
                content=r["content"],
                metadata=r["metadata"],
                timestamp=r["timestamp"],
                importance=r["metadata"].get("importance", 0.5)
            )
            for r in results
        ]

        return entries

    async def delete(self, entry_id: str) -> None:
        """Remove from vector store."""
        await self.storage.delete(entry_id)

    async def _create_embedding(self, text: str) -> list[float]:
        """Create embedding for text."""
        # Placeholder - implement with actual embedding model
        return await self.embedding_model.embed(text)


class MemoryHierarchy:
    """
    Multi-tier memory system for agents.

    Manages working, short-term, and long-term memory with
    automatic promotion and eviction.

    Example:
        >>> memory = MemoryHierarchy(
        ...     working_memory=WorkingMemory(max_messages=10),
        ...     short_term_memory=ShortTermMemory(max_messages=100),
        ...     long_term_memory=LongTermMemory(storage_backend=vector_store)
        ... )
        >>>
        >>> await memory.store(
        ...     content="User prefers Python over JavaScript",
        ...     importance=0.8,  # High importance -> stored in long-term
        ...     session_id="user-123"
        ... )
        >>>
        >>> results = await memory.retrieve(
        ...     query="What programming languages does the user prefer?",
        ...     limit=5
        ... )
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        short_term_memory: ShortTermMemory | None = None,
        long_term_memory: LongTermMemory | None = None
    ):
        self.working = working_memory
        self.short_term = short_term_memory
        self.long_term = long_term_memory

    async def store(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
        **kwargs
    ) -> None:
        """Store across appropriate memory tiers."""
        import uuid

        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc),
            importance=importance
        )

        # Always store in working memory
        await self.working.store(entry)

        # Store in short-term if available
        if self.short_term:
            await self.short_term.store(entry)

        # Store in long-term if important
        if self.long_term and importance >= self.long_term.min_importance:
            await self.long_term.store(entry)

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        search_tiers: list[str] | None = None,
        **kwargs
    ) -> list[MemoryEntry]:
        """
        Retrieve from memory hierarchy.

        Args:
            query: Search query
            limit: Maximum results to return
            search_tiers: Which tiers to search (default: all)
            **kwargs: Additional search parameters

        Returns:
            List of relevant memory entries, ordered by relevance
        """
        if search_tiers is None:
            search_tiers = ["working", "short_term", "long_term"]

        results: list[MemoryEntry] = []

        # Search working memory
        if "working" in search_tiers:
            working_results = await self.working.retrieve(query, limit=limit)
            results.extend(working_results)

        # Search short-term memory
        if "short_term" in search_tiers and self.short_term:
            short_results = await self.short_term.retrieve(query, limit=limit)
            results.extend(short_results)

        # Search long-term memory
        if "long_term" in search_tiers and self.long_term:
            long_results = await self.long_term.retrieve(query, limit=limit)
            results.extend(long_results)

        # Deduplicate and sort by relevance
        unique_results = self._deduplicate(results)
        sorted_results = self._sort_by_relevance(unique_results, query)

        return sorted_results[:limit]

    def _deduplicate(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        """Remove duplicate entries."""
        seen_ids = set()
        unique = []
        for entry in entries:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                unique.append(entry)
        return unique

    def _sort_by_relevance(
        self,
        entries: list[MemoryEntry],
        query: str
    ) -> list[MemoryEntry]:
        """Sort entries by relevance to query."""
        # Simple heuristic: recency + importance
        # Can be enhanced with semantic similarity
        scored = [
            (
                entry,
                entry.importance * 0.5 +  # Importance weight
                (1.0 if query.lower() in entry.content.lower() else 0.0) * 0.3 +  # Keyword match
                (entry.access_count / 100.0) * 0.2  # Access frequency
            )
            for entry in entries
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, score in scored]
```

**Key Features**:
- Three-tier architecture (working, short-term, long-term)
- Automatic promotion and eviction
- Pluggable storage backends
- Semantic retrieval with embeddings
- Importance-based retention
- TTL and capacity management

---

## Implementation Plan

### Phase 1: Core Pattern Implementation (Week 1)

**Tasks**:
1. Implement `ReflectionAgent` in `agenkit/patterns/reflection.py`
2. Implement `AgentTool` and `agent_as_tool` in `agenkit/patterns/agents_as_tools.py`
3. Implement Memory Hierarchy in `agenkit/patterns/memory.py`
4. Update `agenkit/patterns/__init__.py` to export new patterns

**Deliverables**:
- 3 new pattern files (~1,000 LOC total)
- Updated `__init__.py` with exports
- Docstrings and type annotations

### Phase 2: Testing (Week 2)

**Tasks**:
1. Write unit tests for `ReflectionAgent` (~200 LOC)
2. Write unit tests for `AgentTool` (~150 LOC)
3. Write unit tests for Memory Hierarchy (~400 LOC)
4. Integration tests with real agents (~200 LOC)

**Target Coverage**: 90%+

**Deliverables**:
- `tests/patterns/test_reflection.py`
- `tests/patterns/test_agents_as_tools.py`
- `tests/patterns/test_memory.py`
- Integration test suite

### Phase 3: Examples and Documentation (Week 3)

**Tasks**:
1. Create reflection pattern example
2. Create agents-as-tools pattern example
3. Create memory hierarchy pattern example
4. Update pattern guide documentation
5. Create unified patterns API reference
6. Update CHANGELOG.md

**Deliverables**:
- `examples/patterns/06_reflection_agent.py`
- `examples/patterns/07_hierarchical_agents.py`
- `examples/patterns/08_memory_hierarchy.py`
- Updated `docs-site/guides/agent-patterns.md`
- `docs/patterns/PATTERNS_API_REFERENCE.md`

---

## Testing Strategy

### Unit Tests

**Coverage Requirements**: 90%+ for each pattern

**Test Categories**:
1. **Happy Path**: Normal operation
2. **Edge Cases**: Empty inputs, max iterations, thresholds
3. **Error Handling**: Invalid inputs, agent failures
4. **State Management**: Correct state transitions
5. **Metadata**: Correct metadata in responses

**Example Test Structure** (Reflection):

```python
# tests/patterns/test_reflection.py

import pytest
from agenkit.patterns import ReflectionAgent

class MockGenerator:
    async def process(self, message):
        # Returns progressively better output
        pass

class MockCritic:
    async def process(self, message):
        # Returns score + feedback
        pass

@pytest.mark.asyncio
async def test_reflection_basic():
    """Test basic reflection loop."""
    agent = ReflectionAgent(
        generator=MockGenerator(),
        critic=MockCritic(),
        max_iterations=3
    )
    result = await agent.process(Message(...))
    assert result.metadata["reflection_iterations"] <= 3

@pytest.mark.asyncio
async def test_reflection_quality_threshold():
    """Test stopping at quality threshold."""
    # Test that agent stops when quality threshold met
    pass

@pytest.mark.asyncio
async def test_reflection_max_iterations():
    """Test stopping at max iterations."""
    # Test that agent stops at max iterations
    pass

@pytest.mark.asyncio
async def test_reflection_minimal_improvement():
    """Test stopping when improvement too small."""
    # Test improvement threshold
    pass

@pytest.mark.asyncio
async def test_reflection_history():
    """Test reflection history in metadata."""
    # Verify history structure
    pass
```

### Integration Tests

**Goal**: Test patterns with real agents (e.g., OpenAI, Anthropic) or realistic mocks

**Test Scenarios**:
1. Reflection with code generation
2. Hierarchical agents with specialists
3. Memory hierarchy across sessions
4. Composition of multiple patterns

---

## Documentation Strategy

### Pattern Guide Updates

**Location**: `docs-site/guides/agent-patterns.md`

**Additions**:
- Chapter 12: Reflection Pattern (Self-Critique)
- Chapter 13: Agents-as-Tools Pattern (Hierarchical)
- Chapter 14: Memory Hierarchy Pattern
- Updated pattern comparison matrix

### API Reference

**Location**: `docs/patterns/PATTERNS_API_REFERENCE.md`

**Content**:
- Complete API docs for all 8 patterns
- Usage examples for each
- Parameter descriptions
- Return types and metadata structure

### Examples

**Requirements for each example**:
- Real-world use case
- Clear comments explaining WHY
- Complete runnable code
- Output examples
- Performance notes

---

## Success Criteria

### Must-Have (v0.12.0)

- [x] 3 new patterns implemented
- [ ] 90%+ test coverage for new patterns
- [ ] Examples for all 8 patterns
- [ ] Updated pattern guide documentation
- [ ] API reference document
- [ ] Integration tests passing
- [ ] CHANGELOG.md updated

### Nice-to-Have (Future)

- [ ] Performance benchmarks for patterns
- [ ] Cross-language implementation (Go)
- [ ] Pattern composition examples
- [ ] Video tutorials
- [ ] Interactive pattern selector

---

## Open Questions

1. **Memory Hierarchy Storage Backend**: Which vector store to use as default?
   - **Options**: ChromaDB, Pinecone, Weaviate, Custom
   - **Recommendation**: Abstract interface, provide simple in-memory default, document integration with popular stores

2. **Reflection Critique Format**: Structured output or free-form?
   - **Recommendation**: Structured JSON for machine parseability, with fallback to free-form

3. **Agents-as-Tools Protocol**: Should we support streaming responses?
   - **Recommendation**: Not in v0.12.0, add in later release if needed

4. **Memory Importance Scoring**: How to automatically determine importance?
   - **Recommendation**: Allow users to specify, provide optional LLM-based auto-scoring

---

## References

- Issue #103: Core Agent Patterns Library
- `docs-site/guides/agent-patterns.md`: Comprehensive pattern guide
- `docs/patterns/COMPOSITION.md`: Composition patterns
- `agenkit/patterns/`: Existing pattern implementations
- ReAct Paper: https://arxiv.org/abs/2210.03629
- Reflection Pattern (various papers and frameworks)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-24 | System | Initial design document |
