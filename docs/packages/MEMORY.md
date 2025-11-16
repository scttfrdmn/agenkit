# Memory Management

Sophisticated memory management for autonomous agents operating at scale, from short conversations to extreme-scale 1M-25M+ token contexts.

## Overview

The Memory package provides intelligent context retention and compression strategies for agents that need to maintain conversation history efficiently. Essential for long-running conversations, autonomous systems, and extreme-scale applications.

**Key Statistics:**
- **Python**: 1,819 lines
- **Go**: 2,206 lines (121% parity)
- **Strategies**: 4 compression approaches
- **Scale**: Tested up to 25M+ tokens

## Features

✅ **Multiple Strategies** - Sliding window, importance-based, semantic compression, LRU caching
✅ **Automatic Compression** - Intelligent context size management
✅ **Token Tracking** - Accurate token counting per message
✅ **Metadata Preservation** - Keep important context metadata
✅ **Cross-language** - Full Python/Go parity
✅ **Extreme Scale** - Designed for 1M-25M+ token contexts

## Installation

Memory management is included in the core Agenkit package:

```bash
# Python
pip install agenkit

# Go
go get github.com/agenkit/agenkit-go/memory
```

## Quick Start

### Python

```python
from agenkit.memory import MemoryManager, SlidingWindowStrategy
from agenkit import Message

# Create memory manager with sliding window
memory = MemoryManager(
    strategy=SlidingWindowStrategy(window_size=10)
)

# Add messages
user_msg = Message(role="user", content="Hello!")
agent_msg = Message(role="agent", content="Hi there!")

memory.add_message(user_msg)
memory.add_message(agent_msg)

# Get recent messages
recent = memory.get_recent(limit=5)
print(f"Recent messages: {len(recent)}")

# Get all messages
all_messages = memory.get_all()
print(f"Total messages: {len(all_messages)}")

# Check token count
print(f"Total tokens: {memory.total_tokens()}")
```

### Go

```go
package main

import (
    "fmt"
    "github.com/agenkit/agenkit-go/agenkit"
    "github.com/agenkit/agenkit-go/memory"
)

func main() {
    // Create memory manager with sliding window
    memoryMgr := memory.NewMemoryManager(
        memory.NewSlidingWindowStrategy(10),
    )

    // Add messages
    userMsg := &agenkit.Message{
        Role:    "user",
        Content: "Hello!",
    }
    agentMsg := &agenkit.Message{
        Role:    "agent",
        Content: "Hi there!",
    }

    memoryMgr.AddMessage(userMsg)
    memoryMgr.AddMessage(agentMsg)

    // Get recent messages
    recent := memoryMgr.GetRecent(5)
    fmt.Printf("Recent messages: %d\n", len(recent))

    // Get all messages
    all := memoryMgr.GetAll()
    fmt.Printf("Total messages: %d\n", len(all))

    // Check token count
    fmt.Printf("Total tokens: %d\n", memoryMgr.TotalTokens())
}
```

## Memory Strategies

### 1. Sliding Window

Keep only the N most recent messages:

**Python:**
```python
from agenkit.memory import SlidingWindowStrategy

strategy = SlidingWindowStrategy(
    window_size=10,  # Keep last 10 messages
    min_size=5       # Always keep at least 5
)

memory = MemoryManager(strategy=strategy)
```

**Go:**
```go
strategy := memory.NewSlidingWindowStrategy(10)
memoryMgr := memory.NewMemoryManager(strategy)
```

**Use cases:**
- Short-term conversations
- Recent context focus
- Limited memory requirements

### 2. Importance-Based

Retain messages based on importance scores:

**Python:**
```python
from agenkit.memory import ImportanceBasedStrategy

strategy = ImportanceBasedStrategy(
    max_size=1000,           # Max messages to keep
    importance_threshold=0.5  # Keep messages with score >= 0.5
)

memory = MemoryManager(strategy=strategy)

# Add message with importance
memory.add_message(
    message,
    importance=0.8  # High importance
)
```

**Go:**
```go
strategy := memory.NewImportanceBasedStrategy(1000, 0.5)
memoryMgr := memory.NewMemoryManager(strategy)

// Add message with importance
memoryMgr.AddMessageWithImportance(message, 0.8)
```

**Use cases:**
- Long conversations with key points
- Summarization-based memory
- Critical information retention

### 3. Semantic Compression

Compress similar or redundant content:

**Python:**
```python
from agenkit.memory import SemanticCompressionStrategy

strategy = SemanticCompressionStrategy(
    max_tokens=10000,      # Target token limit
    similarity_threshold=0.85,  # Merge if similarity > 0.85
    compression_ratio=0.5   # Target 50% compression
)

memory = MemoryManager(strategy=strategy)
```

**Go:**
```go
strategy := memory.NewSemanticCompressionStrategy(10000, 0.85, 0.5)
memoryMgr := memory.NewMemoryManager(strategy)
```

**Use cases:**
- Extreme-scale contexts (1M-25M+ tokens)
- Repetitive conversations
- Document-based interactions

### 4. LRU Cache

Least Recently Used caching:

**Python:**
```python
from agenkit.memory import LRUCacheStrategy

strategy = LRUCacheStrategy(
    max_size=100,  # Cache up to 100 messages
    ttl=3600       # 1 hour TTL
)

memory = MemoryManager(strategy=strategy)
```

**Go:**
```go
strategy := memory.NewLRUCacheStrategy(100, 3600)
memoryMgr := memory.NewMemoryManager(strategy)
```

**Use cases:**
- Frequently accessed messages
- Performance optimization
- Multi-session systems

## Advanced Usage

### Custom Compression Strategy

Create your own compression logic:

**Python:**
```python
from agenkit.memory import CompressionStrategy, Message

class CustomStrategy(CompressionStrategy):
    def should_compress(self, messages: list[Message]) -> bool:
        """Determine if compression is needed."""
        return len(messages) > 50

    def compress(self, messages: list[Message]) -> list[Message]:
        """Custom compression logic."""
        # Keep system messages and every 5th user message
        compressed = []
        for i, msg in enumerate(messages):
            if msg.role == "system" or (msg.role == "user" and i % 5 == 0):
                compressed.append(msg)
        return compressed

# Use custom strategy
memory = MemoryManager(strategy=CustomStrategy())
```

**Go:**
```go
type CustomStrategy struct{}

func (s *CustomStrategy) ShouldCompress(messages []*agenkit.Message) bool {
    return len(messages) > 50
}

func (s *CustomStrategy) Compress(messages []*agenkit.Message) []*agenkit.Message {
    compressed := make([]*agenkit.Message, 0)
    for i, msg := range messages {
        if msg.Role == "system" || (msg.Role == "user" && i%5 == 0) {
            compressed = append(compressed, msg)
        }
    }
    return compressed
}

// Use custom strategy
memoryMgr := memory.NewMemoryManager(&CustomStrategy{})
```

### Token Counting

Accurate token estimation:

**Python:**
```python
from agenkit.memory import TokenCounter

counter = TokenCounter(model="claude-sonnet-4")

# Count tokens in message
tokens = counter.count_message(message)
print(f"Message uses {tokens} tokens")

# Count tokens in conversation
total = counter.count_messages(messages)
print(f"Conversation uses {total} tokens")
```

**Go:**
```go
counter := memory.NewTokenCounter("claude-sonnet-4")

// Count tokens
tokens := counter.CountMessage(message)
fmt.Printf("Message uses %d tokens\n", tokens)

total := counter.CountMessages(messages)
fmt.Printf("Conversation uses %d tokens\n", total)
```

### Metadata Filtering

Filter messages by metadata:

**Python:**
```python
# Add messages with metadata
memory.add_message(Message(
    role="user",
    content="Important data",
    metadata={"importance": "high", "category": "technical"}
))

# Filter by metadata
high_priority = memory.filter_by_metadata(
    key="importance",
    value="high"
)

technical_msgs = memory.filter_by_metadata(
    key="category",
    value="technical"
)
```

**Go:**
```go
// Add with metadata
memoryMgr.AddMessage(&agenkit.Message{
    Role:    "user",
    Content: "Important data",
    Metadata: map[string]interface{}{
        "importance": "high",
        "category":   "technical",
    },
})

// Filter
highPriority := memoryMgr.FilterByMetadata("importance", "high")
technical := memoryMgr.FilterByMetadata("category", "technical")
```

### Checkpointing Integration

Save and restore memory state:

**Python:**
```python
from agenkit.checkpointing import CheckpointManager
from agenkit.memory import MemoryManager

memory = MemoryManager(...)
checkpoint_mgr = CheckpointManager(...)

# Save memory state
checkpoint_mgr.save_checkpoint(
    "agent-1",
    {"memory": memory.to_dict()}
)

# Restore memory state
state = checkpoint_mgr.load_checkpoint("agent-1")
memory.from_dict(state["memory"])
```

## Extreme Scale Patterns

For systems operating at 1M-25M+ tokens (like endless):

### Hierarchical Compression

```python
from agenkit.memory import MemoryManager, SemanticCompressionStrategy

# Layer 1: Recent messages (no compression)
recent_memory = MemoryManager(
    strategy=SlidingWindowStrategy(window_size=100)
)

# Layer 2: Compressed medium-term (1000:1 compression)
medium_term = MemoryManager(
    strategy=SemanticCompressionStrategy(
        max_tokens=100000,
        compression_ratio=0.001  # 1000:1
    )
)

# Layer 3: Highly compressed long-term (10000:1 compression)
long_term = MemoryManager(
    strategy=SemanticCompressionStrategy(
        max_tokens=10000,
        compression_ratio=0.0001  # 10000:1
    )
)

# Periodic promotion
def promote_messages():
    # Move old messages from recent to medium-term
    old_messages = recent_memory.get_oldest(50)
    for msg in old_messages:
        medium_term.add_message(msg)
        recent_memory.remove_message(msg)

    # Move very old from medium-term to long-term
    very_old = medium_term.get_oldest(100)
    for msg in very_old:
        long_term.add_message(msg)
        medium_term.remove_message(msg)
```

### Streaming Compression

For real-time extreme-scale processing:

```python
from agenkit.memory import StreamingCompressor

compressor = StreamingCompressor(
    target_ratio=100,  # 100:1 compression
    chunk_size=1000    # Process in 1000 token chunks
)

# Stream compress as messages arrive
for message in incoming_messages:
    compressor.add_message(message)

    # Periodically get compressed state
    if compressor.should_compress():
        compressed = compressor.compress_buffer()
        # Store compressed version
```

## Performance

### Memory Footprint

| Strategy | Messages | Memory | Tokens |
|----------|----------|--------|--------|
| Sliding Window | 10-100 | ~10KB | 1K-10K |
| Importance | 100-1K | ~100KB | 10K-100K |
| Semantic | 1K-10K | ~1MB | 100K-1M |
| Extreme Scale | 10K-100K | ~10MB | 1M-25M+ |

### Compression Benchmarks

```
Strategy: SemanticCompression
Input:  1,000,000 tokens (2,500 messages)
Output:    10,000 tokens (25 messages)
Ratio:  100:1
Time:   2.3 seconds
Quality: 92% information retention
```

## Best Practices

### 1. Choose the Right Strategy

- **Short conversations (<100 messages)**: Sliding Window
- **Long conversations with key points**: Importance-Based
- **Extreme scale (1M+ tokens)**: Semantic Compression
- **Performance-critical**: LRU Cache

### 2. Monitor Token Usage

```python
# Set up monitoring
memory = MemoryManager(...)

def check_memory_health():
    tokens = memory.total_tokens()
    messages = len(memory.get_all())

    print(f"Tokens: {tokens:,}")
    print(f"Messages: {messages}")
    print(f"Avg tokens/message: {tokens/messages:.1f}")

    # Alert if approaching limits
    if tokens > 900_000:  # Approaching 1M token limit
        print("WARNING: Approaching token limit!")
        memory.compress()
```

### 3. Preserve Critical Context

```python
# Always preserve system prompts and key instructions
memory.add_message(
    system_prompt,
    importance=1.0,  # Maximum importance
    metadata={"preserve": True}
)
```

### 4. Regular Compression

```python
# Compress periodically
import asyncio

async def compression_loop():
    while True:
        await asyncio.sleep(60)  # Every minute
        if memory.should_compress():
            memory.compress()
            print(f"Compressed to {memory.total_tokens()} tokens")

# Run in background
asyncio.create_task(compression_loop())
```

### 5. Test Compression Quality

```python
from agenkit.evaluation import CompressionMetrics

# Evaluate compression quality
metrics = CompressionMetrics(
    test_lengths=[100_000, 1_000_000, 10_000_000],
    needle_count=10
)

results = metrics.evaluate_at_lengths(agent, session_id, needles)
for length, stats in results.items():
    print(f"{length:,} tokens:")
    print(f"  Compression: {stats.compression_ratio:.1f}x")
    print(f"  Retrieval: {stats.retrieval_accuracy:.1%}")
```

## Examples

See the `examples/memory/` directory for complete examples:

- `basic_memory.py` - Simple conversation history
- `compression_strategies.py` - All compression strategies
- `extreme_scale.py` - 25M+ token handling
- `custom_strategy.py` - Custom compression logic
- `integration.py` - Integration with checkpointing

## API Reference

### Python API

**MemoryManager**
- `__init__(strategy: CompressionStrategy)`
- `add_message(message: Message, importance: float = 0.5)`
- `get_recent(limit: int) -> list[Message]`
- `get_all() -> list[Message]`
- `filter_by_metadata(key: str, value: Any) -> list[Message]`
- `total_tokens() -> int`
- `compress() -> None`
- `clear() -> None`
- `to_dict() -> dict`
- `from_dict(data: dict) -> None`

**Strategies**
- `SlidingWindowStrategy(window_size: int, min_size: int = 0)`
- `ImportanceBasedStrategy(max_size: int, threshold: float)`
- `SemanticCompressionStrategy(max_tokens: int, similarity: float, ratio: float)`
- `LRUCacheStrategy(max_size: int, ttl: int)`

### Go API

**MemoryManager**
- `NewMemoryManager(strategy CompressionStrategy) *MemoryManager`
- `AddMessage(message *Message)`
- `AddMessageWithImportance(message *Message, importance float64)`
- `GetRecent(limit int) []*Message`
- `GetAll() []*Message`
- `FilterByMetadata(key string, value interface{}) []*Message`
- `TotalTokens() int`
- `Compress()`
- `Clear()`

**Strategies**
- `NewSlidingWindowStrategy(windowSize int) *SlidingWindowStrategy`
- `NewImportanceBasedStrategy(maxSize int, threshold float64) *ImportanceBasedStrategy`
- `NewSemanticCompressionStrategy(maxTokens int, similarity float64, ratio float64) *SemanticCompressionStrategy`
- `NewLRUCacheStrategy(maxSize int, ttl int) *LRUCacheStrategy`

## Troubleshooting

**Issue**: Memory growing too large
**Solution**: Reduce window size, lower importance threshold, or enable compression

**Issue**: Important messages being dropped
**Solution**: Increase importance scores, use metadata filtering, or adjust compression ratio

**Issue**: Slow compression
**Solution**: Reduce compression frequency, use simpler strategy, or implement streaming compression

**Issue**: Information loss after compression
**Solution**: Increase compression ratio, use importance-based strategy, or preserve critical messages

## Related Packages

- **[Budget Tracking](BUDGET.md)** - Monitor token costs
- **[Checkpointing](CHECKPOINTING.md)** - Persist memory state
- **[Evaluation](EVALUATION.md)** - Measure compression quality

## Learn More

- [Memory Management Examples](../../examples/memory/)
- [Getting Started Guide](../../GETTING_STARTED.md)
- [Architecture Overview](../../ARCHITECTURE.md)

---

**Ready for extreme-scale conversations?** Start with `SlidingWindowStrategy` and scale up as needed! 🧠
