# Memory Systems for Autonomous Agents

## Problem Statement

With agents now capable of 30-hour autonomous operation (Claude Sonnet 4.5, November 2025), context management has become critical. Current Message list approach has limitations:

1. **Context Window Limits:** Even 200K context (Claude 4) fills up in long sessions
2. **Cost:** Passing full history every turn is expensive with large contexts
3. **Relevance:** Not all history equally important; need intelligent retrieval
4. **Persistence:** No way to persist memory across restarts
5. **Multi-Session:** Can't share knowledge across conversations

**Current Workaround:** Users manually manage message lists, implement their own summarization.

**2025 Reality:** Production agents need structured memory beyond raw message history.

## Proposed Solution

Implement minimal, composable memory interface with multiple implementations.

### Memory Interface

```python
from abc import ABC, abstractmethod
from typing import Optional

class Memory(ABC):
    """
    Minimal interface for agent memory systems.

    Design principles:
    - Minimal: Only essential methods
    - Flexible: Support multiple storage backends
    - Composable: Combine with strategies
    - Async-first: Production-ready
    """

    @abstractmethod
    async def store(
        self,
        session_id: str,
        message: Message,
        metadata: Optional[dict] = None
    ) -> None:
        """Store message in memory with optional metadata (importance, tags, etc.)."""
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
            query: Optional semantic query for retrieval
            limit: Maximum messages to return
            **kwargs: Backend-specific options (time_range, importance_threshold, etc.)
        """
        pass

    @abstractmethod
    async def summarize(
        self,
        session_id: str,
        **kwargs
    ) -> Message:
        """Create summary of conversation history."""
        pass

    @abstractmethod
    async def clear(self, session_id: str) -> None:
        """Clear memory for session."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """Return memory capabilities (semantic_search, summarization, importance_weighting, etc.)."""
        pass
```

### Core Implementations

#### 1. InMemoryMemory (Baseline)

```python
class InMemoryMemory(Memory):
    """Simple in-memory storage with LRU eviction."""

    def __init__(self, max_size: int = 1000):
        self.storage: dict[str, list[tuple[Message, dict]]] = {}
        self.max_size = max_size
        self.capabilities = ["basic_retrieval"]
```

**Use case:** Testing, simple applications, no persistence needed.

#### 2. RedisMemory (Production)

```python
class RedisMemory(Memory):
    """Redis-backed memory with TTL and pub/sub."""

    def __init__(self, redis_url: str, ttl: int = 86400):
        self.redis = Redis.from_url(redis_url)
        self.ttl = ttl
        self.capabilities = ["basic_retrieval", "persistence", "ttl"]
```

**Use case:** Production deployments, multi-instance agents, automatic expiry.

#### 3. VectorMemory (Semantic)

```python
class VectorMemory(Memory):
    """Vector database for semantic retrieval."""

    def __init__(self, embeddings_model: str, vector_store: VectorStore):
        self.embeddings = Embeddings(embeddings_model)
        self.store = vector_store
        self.capabilities = ["semantic_search", "similarity_retrieval"]

    async def retrieve(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> list[Message]:
        """Semantic retrieval via vector similarity."""
        if query:
            query_embedding = await self.embeddings.embed(query)
            return await self.store.similarity_search(
                session_id, query_embedding, limit
            )
        return await self.store.get_recent(session_id, limit)
```

**Use case:** RAG, semantic memory, large knowledge bases.

#### 4. EndlessMemory (Infinite Context Integration)

```python
class EndlessMemory(Memory):
    """
    Integration with endless project for effectively infinite context.

    NOTE: Does NOT copy code from endless. Integration via client interface only.
    """

    def __init__(self, endless_client):
        """
        Args:
            endless_client: Client for endless project (user provides)
        """
        self.client = endless_client
        self.capabilities = ["infinite_context", "compression", "semantic_search"]

    async def retrieve(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> list[Message]:
        """Retrieve from endless compressed context."""
        # Delegate to endless client
        compressed = await self.client.retrieve_context(session_id, query)
        return self._decompress_to_messages(compressed, limit)
```

**Use case:** Very long conversations, knowledge accumulation, context compression.

**Integration:** Users import endless separately, pass client to EndlessMemory.

### Memory Strategies

```python
class MemoryStrategy(ABC):
    """Strategy for intelligent memory management."""

    @abstractmethod
    async def select(
        self,
        memory: Memory,
        session_id: str,
        context_limit: int
    ) -> list[Message]:
        """Select which messages to include in context."""
        pass

class SlidingWindowStrategy(MemoryStrategy):
    """Keep most recent N messages."""

    async def select(self, memory, session_id, context_limit):
        return await memory.retrieve(session_id, limit=context_limit)

class ImportanceWeightingStrategy(MemoryStrategy):
    """Prioritize messages by importance score."""

    async def select(self, memory, session_id, context_limit):
        all_messages = await memory.retrieve(session_id, limit=1000)
        scored = [(msg, self._calculate_importance(msg)) for msg in all_messages]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [msg for msg, score in scored[:context_limit]]

class SummarizationStrategy(MemoryStrategy):
    """Summarize old messages, keep recent ones verbatim."""

    async def select(self, memory, session_id, context_limit):
        recent = await memory.retrieve(session_id, limit=10)
        summary = await memory.summarize(session_id)
        return [summary] + recent
```

### Agent Integration

```python
class ConversationalAgent:
    """Agent with memory support."""

    def __init__(
        self,
        llm: LLM,
        memory: Memory,
        strategy: MemoryStrategy = SlidingWindowStrategy()
    ):
        self.llm = llm
        self.memory = memory
        self.strategy = strategy

    async def call(
        self,
        messages: list[Message],
        session_id: str,
        **kwargs
    ) -> Message:
        # Store incoming messages
        for msg in messages:
            await self.memory.store(session_id, msg)

        # Retrieve relevant context
        context = await self.strategy.select(
            self.memory,
            session_id,
            context_limit=kwargs.get("context_limit", 20)
        )

        # Generate response
        response = await self.llm.complete(context + messages, **kwargs)

        # Store response
        await self.memory.store(session_id, response)

        return response
```

## Go Implementation

```go
package memory

type Memory interface {
    Store(ctx context.Context, sessionID string, msg *Message, metadata map[string]interface{}) error
    Retrieve(ctx context.Context, sessionID string, query *string, limit int, opts ...Option) ([]*Message, error)
    Summarize(ctx context.Context, sessionID string, opts ...Option) (*Message, error)
    Clear(ctx context.Context, sessionID string) error
    Capabilities() []string
}

// Implementations
type InMemoryMemory struct { /* ... */ }
type RedisMemory struct { /* ... */ }
type VectorMemory struct { /* ... */ }
```

## Use Cases

1. **Customer Support Agent:** Remember user preferences, past issues
2. **Research Assistant:** Accumulate knowledge across multiple queries
3. **Code Assistant:** Remember project context, coding patterns
4. **Long-Running Tasks:** 30-hour autonomous agents need persistent state

## Implementation Considerations

**Scope:**
- [x] Python implementation (core + 4 implementations)
- [ ] Go implementation (feature parity)
- [ ] Cross-language compatibility
- [ ] Backward compatible (optional, doesn't break existing code)

**Affected Components:**
- [ ] New package: `agenkit/memory/`
- [ ] New package: `agenkit-go/memory/`
- [ ] Examples: `examples/memory/`
- [ ] Documentation: `docs/memory.md`

**Complexity Estimate:**
- [ ] Small (< 1 day)
- [ ] Medium (1-3 days)
- [x] Large (> 3 days) - 4 implementations + strategies + tests

**Dependencies:**
- Redis: `redis>=5.0.0` (Python), `github.com/redis/go-redis/v9` (Go)
- Vector stores: Optional integrations (Pinecone, Weaviate, Qdrant)
- endless: User-provided client (no direct dependency)

## Acceptance Criteria

### Core Interface
- [ ] Memory ABC defined (Python)
- [ ] Memory interface defined (Go)
- [ ] Unit tests for interface contract

### Implementations
- [ ] InMemoryMemory (Python + Go)
- [ ] RedisMemory (Python + Go)
- [ ] VectorMemory (Python + Go)
- [ ] EndlessMemory (Python + Go) - integration interface only
- [ ] Tests for each implementation (20+ tests per implementation)

### Strategies
- [ ] SlidingWindowStrategy (Python + Go)
- [ ] ImportanceWeightingStrategy (Python + Go)
- [ ] SummarizationStrategy (Python + Go)
- [ ] Tests for strategies (10+ tests per strategy)

### Integration
- [ ] ConversationalAgent example with memory
- [ ] Memory switching examples
- [ ] Strategy comparison examples
- [ ] Performance benchmarks (retrieval latency, storage overhead)

### Documentation
- [ ] Memory interface API docs
- [ ] Implementation comparison guide
- [ ] Strategy selection guide
- [ ] Integration with endless project example
- [ ] Best practices (when to use which implementation)

### Testing
- [ ] Unit tests (50+ tests)
- [ ] Integration tests (10+ tests)
- [ ] Performance tests (5+ benchmarks)
- [ ] Cross-language compatibility tests

## Migration Path

**Existing Code:** No breaking changes
```python
# Old code (still works)
agent.call(messages)

# New code (with memory)
agent = ConversationalAgent(llm, memory=RedisMemory(redis_url))
agent.call(messages, session_id="user-123")
```

## Related

- Integration with endless project (infinite context)
- Complements LLM adapters (#58)
- Enables long-running agents (#69)
- Foundation for evaluation (#73)

## Priority

**Critical** - Q4 2025 (Nov-Dec)

Required for 30-hour autonomous agents to maintain context across restarts and sessions.

## Labels

`enhancement`, `memory`, `python`, `go`, `q4-2025`, `critical`
