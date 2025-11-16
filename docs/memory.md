# Memory Systems for Autonomous Agents

> **Status**: Production Ready (v0.6.0+)
> **Python**: ✅ | **Go**: 🚧 (Planned Q1 2026)

## Overview

The Agenkit Memory System provides intelligent context management for autonomous agents, enabling conversations that extend beyond raw message lists and context window limits. With support for multiple storage backends, semantic retrieval, and intelligent memory strategies, agents can maintain coherent long-term interactions.

### Why Memory Systems?

**The Challenge**: Modern LLMs like Claude Sonnet 4.5 support 200K token context windows and 30-hour autonomous operation, but:

1. **Context fills up** in long sessions
2. **Costs scale** with history length
3. **Not all history is relevant** to current queries
4. **No persistence** across restarts
5. **No knowledge sharing** between sessions

**The Solution**: Structured memory systems with intelligent retrieval strategies.

## Quick Start

```python
from agenkit.memory import InMemoryMemory, SlidingWindowStrategy
from agenkit.interfaces import Message

# Create memory
memory = InMemoryMemory(max_size=1000)

# Store messages
await memory.store(
    "session-123",
    Message(role="user", content="What's the weather?"),
    metadata={"importance": 0.5}
)

# Retrieve recent messages
messages = await memory.retrieve("session-123", limit=10)

# Use with strategy for intelligent selection
strategy = SlidingWindowStrategy(window_size=10)
context = await strategy.select(memory, "session-123", context_limit=10)
```

## Memory Interface

All memory implementations follow the `Memory` abstract base class:

```python
from abc import ABC, abstractmethod
from typing import Optional

class Memory(ABC):
    """Minimal interface for agent memory systems."""

    @abstractmethod
    async def store(
        self,
        session_id: str,
        message: Message,
        metadata: Optional[dict] = None
    ) -> None:
        """Store message with optional metadata."""
        pass

    @abstractmethod
    async def retrieve(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> list[Message]:
        """Retrieve messages (semantic or recent)."""
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
        """Return memory capabilities."""
        pass
```

## Memory Implementations

### 1. InMemoryMemory (Testing & Prototyping)

Simple in-memory storage with LRU eviction.

**Features**:
- Fast access (no I/O)
- LRU eviction when max_size reached
- Per-session isolation
- Optional metadata support

**Limitations**:
- No persistence (lost on restart)
- No semantic search
- Memory limited

**Use Cases**:
- Testing
- Simple applications
- Prototypes
- When persistence not needed

**Example**:
```python
from agenkit.memory import InMemoryMemory

memory = InMemoryMemory(max_size=1000)

# Store messages
await memory.store("session-1", Message(role="user", content="Hello"))
await memory.store("session-1", Message(role="assistant", content="Hi!"))

# Retrieve recent
messages = await memory.retrieve("session-1", limit=10)

# Check usage
count = memory.get_session_count("session-1")
usage = memory.get_memory_usage()
```

### 2. RedisMemory (Production Deployments)

Redis-backed memory with TTL and multi-instance support.

**Features**:
- Persistent storage (survives restarts)
- TTL support (automatic expiry)
- Multi-instance agents (shared memory)
- Fast access (in-memory Redis)
- Scalable (Redis cluster support)

**Use Cases**:
- Production deployments
- Multi-instance agents
- When persistence needed
- Shared memory across agents

**Example**:
```python
from agenkit.memory import RedisMemory

memory = RedisMemory(
    redis_url="redis://localhost:6379",
    ttl=86400,  # 24 hours
    key_prefix="agenkit:memory"
)

# Use same interface as InMemoryMemory
await memory.store("session-1", message)
messages = await memory.retrieve("session-1", limit=10)

# Context manager for cleanup
async with RedisMemory(redis_url) as memory:
    await memory.store("session-1", message)
    # Automatically closes connection
```

**Installation**:
```bash
pip install redis>=5.0.0
```

### 3. VectorMemory (Semantic Retrieval)

Vector database for semantic similarity search.

**Features**:
- Semantic retrieval via embeddings
- Similarity-based search
- Hybrid: semantic + recency + importance
- Custom embedding providers
- Multiple vector store backends

**Use Cases**:
- RAG (Retrieval Augmented Generation)
- Semantic memory
- Large knowledge bases
- "What did we discuss about X?"

**Example**:
```python
from agenkit.memory import VectorMemory

# Default: Uses sentence transformers + in-memory storage
memory = VectorMemory()

# Store messages (automatically embedded)
await memory.store("session-1", Message(role="user", content="I love Python"))
await memory.store("session-1", Message(role="user", content="Java is okay"))

# Semantic retrieval
messages = await memory.retrieve(
    "session-1",
    query="What programming languages do I like?",
    limit=5
)
# Returns: Messages about Python (higher similarity)

# Get similarity scores
messages_with_scores = await memory.retrieve(
    "session-1",
    query="programming",
    limit=5,
    return_scores=True
)
```

**Custom Embedding Provider**:
```python
from agenkit.memory import VectorMemory, EmbeddingProvider

class OpenAIEmbeddings(EmbeddingProvider):
    def __init__(self, api_key: str):
        self.client = openai.Client(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

memory = VectorMemory(embedding_provider=OpenAIEmbeddings(api_key))
```

### 4. EndlessMemory (Infinite Context)

Integration with [endless project](https://github.com/jxnl/endless) for effectively infinite context through compression.

**Features**:
- Infinite context through compression
- Semantic retrieval from compressed context
- Automatic context management
- Cross-session knowledge accumulation

**Use Cases**:
- Very long conversations (> 200K tokens)
- Knowledge accumulation over time
- Multi-session knowledge sharing
- 30-hour autonomous agents

**Example**:
```python
from agenkit.memory import EndlessMemory
from endless import EndlessClient  # User installs separately

# User provides endless client
endless_client = EndlessClient(api_key="...")
memory = EndlessMemory(endless_client)

# Same interface
await memory.store("session-1", message)
messages = await memory.retrieve(
    "session-1",
    query="What did we discuss about pricing?",
    limit=10
)
```

**Installation**:
```bash
# User installs endless separately
pip install endless
```

**Note**: This is an integration interface only. Users provide their own endless client. See [endless documentation](https://github.com/jxnl/endless) for setup.

## Memory Strategies

Memory strategies intelligently select which messages to include in context.

### Base Strategy Interface

```python
from abc import ABC, abstractmethod

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
```

### 1. SlidingWindowStrategy

Keep most recent N messages.

**Best for**:
- Short conversations
- Chat applications
- When recency matters most

**Example**:
```python
from agenkit.memory import SlidingWindowStrategy

strategy = SlidingWindowStrategy(window_size=10)
context = await strategy.select(memory, "session-1", context_limit=10)
```

### 2. ImportanceWeightingStrategy

Prioritize messages by importance score.

**Best for**:
- Critical information retention
- Task-oriented conversations
- When some messages more valuable

**Example**:
```python
from agenkit.memory import ImportanceWeightingStrategy

strategy = ImportanceWeightingStrategy(
    importance_threshold=0.5,  # Minimum importance to include
    recency_weight=0.3,       # Boost recent messages
    min_recent=2              # Always include N most recent
)

# Store with importance
await memory.store(
    "session-1",
    Message(role="user", content="Critical bug in production!"),
    metadata={"importance": 0.9, "tags": ["critical", "bug"]}
)

# Retrieves high-importance + recent messages
context = await strategy.select(memory, "session-1", context_limit=10)
```

### 3. SummarizationStrategy

Summarize old messages, keep recent ones verbatim.

**Best for**:
- Long conversations
- Background context + recent detail
- Token optimization

**Example**:
```python
from agenkit.memory import SummarizationStrategy

strategy = SummarizationStrategy(
    recent_count=5,       # Keep 5 most recent verbatim
    summarize_older=True  # Summarize everything else
)

context = await strategy.select(memory, "session-1", context_limit=20)
# Returns: [summary_message] + [5 recent messages]
```

## Agent Integration

### ConversationalAgent with Memory

```python
from agenkit.memory import InMemoryMemory, SlidingWindowStrategy

class ConversationalAgent:
    def __init__(
        self,
        name: str,
        memory: Memory,
        strategy: MemoryStrategy = None,
        context_limit: int = 10
    ):
        self.name = name
        self.memory = memory
        self.strategy = strategy or SlidingWindowStrategy(window_size=10)
        self.context_limit = context_limit

    async def process(self, message: Message, session_id: str) -> Message:
        # Store incoming message
        await self.memory.store(session_id, message)

        # Retrieve context using strategy
        context = await self.strategy.select(
            memory=self.memory,
            session_id=session_id,
            context_limit=self.context_limit
        )

        # Generate response with context
        response = await self._generate_response(context, message)

        # Store response
        await self.memory.store(session_id, response)

        return response
```

### Multi-Session Management

```python
# Shared memory across sessions
memory = RedisMemory(redis_url="redis://localhost:6379")

# Different users, isolated memory
await agent.process(msg, session_id="user-alice")
await agent.process(msg, session_id="user-bob")

# Get all sessions
sessions = await memory.get_all_sessions()
```

## Advanced Features

### Time-Based Filtering

```python
from datetime import datetime, timedelta, timezone

# Retrieve messages from last hour
start = datetime.now(timezone.utc) - timedelta(hours=1)
end = datetime.now(timezone.utc)

messages = await memory.retrieve(
    "session-1",
    time_range=(start, end),
    limit=50
)
```

### Tag-Based Filtering

```python
# Store with tags
await memory.store(
    "session-1",
    message,
    metadata={"tags": ["customer-issue", "billing"]}
)

# Retrieve by tag
messages = await memory.retrieve(
    "session-1",
    tags=["customer-issue"],
    limit=20
)
```

### Importance Filtering

```python
# High-importance messages only
messages = await memory.retrieve(
    "session-1",
    importance_threshold=0.8,
    limit=10
)
```

### Combined Filters

```python
# Complex query: high-importance billing issues from last week
messages = await memory.retrieve(
    "session-1",
    time_range=(week_ago, now),
    importance_threshold=0.7,
    tags=["billing"],
    limit=20
)
```

## Performance Considerations

### Retrieval Latency

| Implementation | Retrieval (10 messages) | Retrieval (100 messages) |
|---------------|------------------------|--------------------------|
| InMemoryMemory | < 1ms | < 5ms |
| RedisMemory | 2-5ms | 10-20ms |
| VectorMemory | 10-50ms | 50-200ms |
| EndlessMemory | 50-100ms | 100-300ms |

*Note: Vector and Endless times include embedding/compression overhead*

### Storage Overhead

| Implementation | Per Message | 1000 Messages |
|---------------|-------------|---------------|
| InMemoryMemory | ~1KB | ~1MB |
| RedisMemory | ~1KB | ~1MB |
| VectorMemory | ~2KB (with embedding) | ~2MB |
| EndlessMemory | ~0.5KB (compressed) | ~500KB |

### Optimization Tips

1. **Use appropriate limits**: Don't retrieve more than needed
2. **Leverage metadata**: Filter before retrieval (tags, importance)
3. **Choose right implementation**:
   - Testing → InMemoryMemory
   - Production → RedisMemory
   - Semantic search → VectorMemory
   - Very long context → EndlessMemory
4. **Strategy selection**:
   - Short conversations → SlidingWindow
   - Important info → ImportanceWeighting
   - Long conversations → Summarization

## Best Practices

### 1. Always Use Sessions

```python
# ✅ Good: Isolated per user
await memory.store("user-123", message)

# ❌ Bad: Mixed conversations
await memory.store("global", message)
```

### 2. Set Appropriate Metadata

```python
# ✅ Good: Rich metadata for filtering
await memory.store(
    "session-1",
    message,
    metadata={
        "importance": 0.8,
        "tags": ["feature-request", "ui"],
        "user_id": "user-123"
    }
)

# ❌ Bad: No metadata
await memory.store("session-1", message)
```

### 3. Use Context Limits

```python
# ✅ Good: Bounded context
context = await strategy.select(memory, session_id, context_limit=20)

# ❌ Bad: Unbounded (expensive, slow)
context = await memory.retrieve(session_id, limit=999999)
```

### 4. Clean Up Old Sessions

```python
# Periodic cleanup
for session_id in await memory.get_all_sessions():
    # Clear inactive sessions
    if is_inactive(session_id):
        await memory.clear(session_id)
```

### 5. Choose Right Strategy

```python
# Short conversations
strategy = SlidingWindowStrategy(window_size=10)

# Important info retention
strategy = ImportanceWeightingStrategy(
    importance_threshold=0.6,
    recency_weight=0.3
)

# Long conversations
strategy = SummarizationStrategy(
    recent_count=5,
    summarize_older=True
)
```

## Migration Guide

### From Raw Message Lists

**Before**:
```python
messages = []  # Manual list management

messages.append(user_message)
messages.append(assistant_message)

# Trim manually
if len(messages) > 20:
    messages = messages[-20:]

response = await llm.complete(messages)
```

**After**:
```python
memory = InMemoryMemory(max_size=1000)
strategy = SlidingWindowStrategy(window_size=10)

await memory.store(session_id, user_message)

context = await strategy.select(memory, session_id, context_limit=20)
response = await llm.complete(context)

await memory.store(session_id, response)
```

### From Custom Memory to Agenkit Memory

**Before**:
```python
class MyMemory:
    def save(self, msg):
        # Custom implementation
        pass

    def load(self):
        # Custom implementation
        pass
```

**After**:
```python
from agenkit.memory import Memory

class MyMemory(Memory):
    async def store(self, session_id, message, metadata=None):
        # Implement using Memory interface
        pass

    async def retrieve(self, session_id, query=None, limit=10, **kwargs):
        # Implement using Memory interface
        pass

    # ... implement other abstract methods
```

## Testing

### Unit Testing with InMemoryMemory

```python
import pytest
from agenkit.memory import InMemoryMemory
from agenkit.interfaces import Message

@pytest.mark.asyncio
async def test_agent_with_memory():
    memory = InMemoryMemory(max_size=100)

    # Test storage
    await memory.store(
        "test-session",
        Message(role="user", content="Test")
    )

    # Test retrieval
    messages = await memory.retrieve("test-session", limit=10)
    assert len(messages) == 1
    assert messages[0].content == "Test"
```

### Integration Testing with RedisMemory

```python
import pytest
from agenkit.memory import RedisMemory

@pytest.mark.asyncio
async def test_redis_persistence():
    memory = RedisMemory(redis_url="redis://localhost:6379")

    await memory.store("session-1", message)

    # Create new instance (simulates restart)
    memory2 = RedisMemory(redis_url="redis://localhost:6379")
    messages = await memory2.retrieve("session-1")

    # Message persists across instances
    assert len(messages) == 1
```

## Troubleshooting

### RedisMemory Connection Issues

```python
# Check Redis connection
import redis.asyncio as redis

client = redis.from_url("redis://localhost:6379")
await client.ping()  # Should return True
```

### VectorMemory Embedding Errors

```python
# Verify embedding provider works
from agenkit.memory import VectorMemory

memory = VectorMemory()

# Test embedding
try:
    await memory.store("test", Message(role="user", content="Test"))
except Exception as e:
    print(f"Embedding error: {e}")
```

### Memory Leaks with InMemoryMemory

```python
# Monitor memory usage
usage = memory.get_memory_usage()
print(f"Sessions: {usage['total_sessions']}")
print(f"Messages: {usage['total_messages']}")

# Set appropriate max_size
memory = InMemoryMemory(max_size=1000)  # LRU eviction
```

## Examples

See `examples/memory/conversational_agent.py` for comprehensive examples:

1. Basic conversation with memory
2. Importance-based memory selection
3. Summarization strategy
4. Multi-session management
5. Strategy comparison

```bash
python examples/memory/conversational_agent.py
```

## API Reference

### Memory Interface

- `store(session_id, message, metadata)` - Store message
- `retrieve(session_id, query, limit, **kwargs)` - Retrieve messages
- `summarize(session_id, **kwargs)` - Create summary
- `clear(session_id)` - Clear session
- `capabilities` - List capabilities

### Strategy Interface

- `select(memory, session_id, context_limit)` - Select context

### Capabilities

- `basic_retrieval` - Supports retrieve()
- `semantic_search` - Supports query parameter
- `persistence` - Survives restarts
- `ttl` - Automatic expiry
- `importance_weighting` - Importance-based retrieval
- `infinite_context` - Compression/large context
- `cross_session_knowledge` - Knowledge sharing

## Related

- [Agent Safety Framework](./safety/AGENT_SAFETY_FRAMEWORK.md) - Security for memory systems
- [LLM Adapters](#) - Integrating memory with LLMs
- [Long-Running Agents](#) - Using memory for 30-hour agents

## Contributing

Found an issue? Have a suggestion? [Open an issue](https://github.com/agenkit/agenkit/issues)

Want to add a new memory implementation? See [CONTRIBUTING.md](../CONTRIBUTING.md)
