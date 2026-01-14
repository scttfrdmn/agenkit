# Python Language Profile for Agenkit

**Purpose**: This document maps Python language idioms, patterns, and best practices to Agenkit concepts. Use this as a reference when migrating **from** or **to** Python.

**Target Audience**: Developers familiar with Python who are migrating Agenkit code to/from other languages, or developers from other languages learning Python patterns in Agenkit.

---

## Table of Contents

- [Language Philosophy](#language-philosophy)
- [Type System](#type-system)
- [Error Handling](#error-handling)
- [Concurrency Model](#concurrency-model)
- [Memory Management](#memory-management)
- [Agenkit Idioms in Python](#agenkit-idioms-in-python)
- [Common Patterns](#common-patterns)
- [Testing](#testing)
- [Performance Characteristics](#performance-characteristics)

---

## Language Philosophy

### Python's Core Principles

1. **Readability counts**: Clear, expressive syntax
2. **Duck typing**: "If it walks like a duck and quacks like a duck"
3. **Batteries included**: Rich standard library
4. **Explicit is better than implicit**: Clear over clever
5. **There should be one obvious way**: Pythonic patterns

### How This Affects Agenkit

- **Duck typing**: No explicit interfaces, just implement methods
- **async/await**: Native coroutine support with asyncio
- **Decorators**: Function/class modification syntax
- **Dataclasses**: Simple data container syntax
- **Type hints**: Optional static typing for documentation and tooling

---

## Type System

### Dynamic Typing with Optional Type Hints

**Python's Approach**:
```python
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Dataclass for simple data containers
@dataclass
class Message:
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

# Protocol for duck typing (Python 3.8+)
from typing import Protocol

class Agent(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> List[str]: ...

    async def process(self, message: Message) -> Message: ...

# Type hints are optional but recommended
def process_agent(agent: Agent, msg: Message) -> Message:
    return await agent.process(msg)
```

**Key Concepts**:
- **Dynamic typing**: Types checked at runtime, not compile time
- **Type hints**: Optional annotations for tools (mypy, IDEs)
- **Duck typing**: Objects defined by behavior, not inheritance
- **Optional**: `Optional[T]` is `T | None`
- **Any**: Opt-out of type checking

### Duck Typing

```python
# No explicit interface needed
class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def capabilities(self) -> List[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        # Implementation
        pass

# Works anywhere an Agent is expected - no inheritance needed
agent: Agent = MyAgent()  # Type checkers accept this
```

**Migration Notes**:
- Go interfaces → Python protocols (runtime checked)
- Rust traits → Python protocols + abstract base classes
- TypeScript interfaces → Python protocols
- C++ templates → Python generics (duck typed)

---

## Error Handling

### Exceptions

**Python's Pattern**:
```python
class AgentError(Exception):
    """Base exception for agent errors."""
    pass

class InvalidMessageError(AgentError):
    """Message validation failed."""
    pass

class TimeoutError(AgentError):
    """Operation timed out."""
    pass

# Raise exception
def validate_message(msg: Message) -> None:
    if not msg.content:
        raise InvalidMessageError("Message content cannot be empty")

# Catch exception
try:
    result = await agent.process(message)
except InvalidMessageError as e:
    print(f"Validation error: {e}")
except AgentError as e:
    print(f"Agent error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    # Cleanup (always runs)
    await cleanup()
```

**Comparison**:
| Language | Pattern | Control Flow |
|----------|---------|--------------|
| **Python** | Exceptions | Exception unwinding |
| TypeScript | `try/catch` | Exception unwinding (similar) |
| Go | `(result, error)` | Explicit checks |
| Rust | `Result<T, E>` | Explicit checks |
| C++ | Exceptions or codes | Both patterns |
| Zig | Error unions | Explicit checks |

### Context Managers

**Pattern**: Automatic resource cleanup

```python
# Context manager with 'with' statement
with open('file.txt', 'r') as file:
    data = file.read()
# File automatically closed here

# Async context manager
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.text()
# Session and response automatically cleaned up

# Custom context manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def timeout_context(seconds: float):
    task = asyncio.current_task()
    def timeout_handler():
        task.cancel()

    timer = asyncio.get_event_loop().call_later(seconds, timeout_handler)
    try:
        yield
    finally:
        timer.cancel()

# Usage
async with timeout_context(5.0):
    result = await agent.process(message)
```

**Agenkit Convention**:
- Always use context managers for resources
- Prefer async context managers for async resources
- Use `contextlib` for custom managers
- Catch specific exceptions, not bare `except:`

---

## Concurrency Model

### async/await with asyncio

**Definition**: Coroutines for cooperative multitasking

```python
import asyncio

# Async function (coroutine)
async def fetch_data() -> str:
    await asyncio.sleep(1)  # Non-blocking sleep
    return "data"

# Run coroutine
data = await fetch_data()

# Create task
task = asyncio.create_task(fetch_data())
result = await task

# Gather multiple coroutines
results = await asyncio.gather(
    agent1.process(msg),
    agent2.process(msg),
    agent3.process(msg),
)
```

**Characteristics**:
- **Single-threaded**: Event loop, no true parallelism
- **Cooperative**: Tasks yield at `await` points
- **GIL (Global Interpreter Lock)**: Limits CPU-bound parallelism
- **asyncio event loop**: Schedules and runs coroutines

### Threading and Multiprocessing

**For CPU-bound work**:
```python
import concurrent.futures

# Thread pool (good for I/O-bound)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(cpu_task, data) for data in items]
    results = [f.result() for f in futures]

# Process pool (good for CPU-bound, bypasses GIL)
with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(cpu_intensive_function, items))
```

### asyncio Primitives

```python
# Queue for producer-consumer
queue = asyncio.Queue()

await queue.put(message)  # Producer
msg = await queue.get()   # Consumer

# Event for signaling
event = asyncio.Event()

await event.wait()  # Wait for signal
event.set()         # Signal waiters

# Lock for mutual exclusion
lock = asyncio.Lock()

async with lock:
    # Critical section
    shared_resource.modify()
```

### Comparison to Other Languages

| Language | Concurrency Primitive | Parallelism |
|----------|----------------------|-------------|
| **Python** | async/await (asyncio) | Limited (GIL) |
| TypeScript | async/await (Promises) | None (single-threaded) |
| Go | Goroutines | True (multi-core) |
| Rust | async/await (tokio) | True (multi-core) |
| C++ | std::thread | True (multi-core) |
| Zig | std.Thread | True (multi-core) |

---

## Memory Management

### Automatic Garbage Collection + Reference Counting

**Python's Approach**:
- **Reference counting**: Objects freed when refcount reaches 0
- **Cycle detection**: Garbage collector handles circular references
- **No manual management**: All memory handled automatically

```python
# Automatic memory management
def process_message(msg: Message) -> Message:
    buffer = bytearray(1024)  # Allocated
    # ...use buffer...
    return result
    # buffer automatically freed when function returns
```

**Comparison**:
| Language | Memory Model | Developer Action |
|----------|--------------|------------------|
| **Python** | GC + refcounting | None required |
| TypeScript | GC (V8) | None required |
| Go | GC | None required |
| Rust | Ownership | Explicit borrows |
| C++ | Manual + RAII | Use smart pointers |
| Zig | Manual | Pass allocators, defer |

### Weak References

**Pattern**: Allow GC without preventing it

```python
import weakref

# Weak reference doesn't prevent garbage collection
obj = SomeObject()
weak_ref = weakref.ref(obj)

# Check if object still exists
if weak_ref() is not None:
    obj = weak_ref()
    # Use obj
else:
    # Object was garbage collected
    pass

# WeakValueDictionary for caches
cache = weakref.WeakValueDictionary()
cache[key] = expensive_object
# Object can be GC'd when no other references exist
```

---

## Agenkit Idioms in Python

### Message Creation

```python
from agenkit import Message
from datetime import datetime

# Basic message
msg = Message(
    role="user",
    content="Hello!",
)

# With metadata
msg = Message(
    role="assistant",
    content="Response",
    metadata={
        "confidence": 0.95,
        "model": "gpt-4",
    },
)

# With timestamp
msg = Message(
    role="user",
    content="Query",
    timestamp=datetime.now(),
)
```

### Agent Implementation

```python
from agenkit import Agent, Message
from typing import List

class MyAgent(Agent):
    def __init__(self, config: dict):
        self.config = config

    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def capabilities(self) -> List[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        # Process message
        return Message(
            role="assistant",
            content=f"Processed: {message.content}",
        )
```

### Pattern Composition

```python
from agenkit.patterns import SequentialAgent, ParallelAgent, RouterAgent

# Sequential pattern
sequential = SequentialAgent(agents=[agent1, agent2, agent3])

# Parallel pattern
parallel = ParallelAgent(agents=[agent_a, agent_b, agent_c])

# Router pattern
def router_fn(msg: Message) -> str:
    if "urgent" in msg.content:
        return "fast"
    return "thorough"

router = RouterAgent(
    router=router_fn,
    agents={
        "fast": sequential,
        "thorough": parallel,
    },
)
```

---

## Common Patterns

### Error Handling Pattern

```python
async def safe_process(agent: Agent, msg: Message) -> Optional[Message]:
    try:
        return await agent.process(msg)
    except InvalidMessageError as e:
        print(f"Validation error: {e}")
        return None
    except AgentError as e:
        print(f"Agent error: {e}")
        return None
    # Let unexpected exceptions propagate
```

### Retry Pattern

```python
async def process_with_retry(
    agent: Agent,
    msg: Message,
    max_retries: int = 3,
) -> Message:
    for attempt in range(max_retries):
        try:
            return await agent.process(msg)
        except AgentError as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff
            delay = 2 ** attempt
            await asyncio.sleep(delay)

    raise AgentError("Max retries exceeded")
```

### Timeout Pattern

```python
import asyncio

async def process_with_timeout(
    agent: Agent,
    msg: Message,
    timeout: float = 5.0,
) -> Message:
    try:
        return await asyncio.wait_for(
            agent.process(msg),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")
```

---

## Testing

### pytest

**Python Idiom**:
```python
import pytest
from agenkit import Message
from myagent import MyAgent

@pytest.mark.asyncio
async def test_agent_process():
    agent = MyAgent()
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.role == "assistant"
    assert "Processed" in result.content

@pytest.mark.asyncio
async def test_agent_handles_empty_message():
    agent = MyAgent()
    empty_msg = Message(role="user", content="")

    with pytest.raises(InvalidMessageError):
        await agent.process(empty_msg)

# Fixtures for reusable setup
@pytest.fixture
def agent():
    return MyAgent(config={"test": True})

@pytest.fixture
def sample_message():
    return Message(role="user", content="Test message")

def test_with_fixtures(agent, sample_message):
    assert agent.name == "my-agent"
    assert sample_message.content == "Test message"
```

### Mocking

```python
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_with_mock():
    # Mock agent
    mock_agent = AsyncMock(spec=Agent)
    mock_agent.name = "mock-agent"
    mock_agent.process.return_value = Message(
        role="assistant",
        content="Mocked response",
    )

    result = await mock_agent.process(Message(role="user", content="Test"))

    assert result.content == "Mocked response"
    mock_agent.process.assert_called_once()
```

---

## Performance Characteristics

### Strengths

1. **Rapid development**: Quick iteration, expressive syntax
2. **Rich ecosystem**: PyPI has 400K+ packages
3. **ML/Data science**: NumPy, pandas, scikit-learn, TensorFlow, PyTorch
4. **Prototyping**: Fast to write and modify
5. **Excellent tooling**: IPython, Jupyter, debuggers, profilers

### Trade-offs

1. **Slow execution**: Interpreted, 10-100x slower than compiled languages
2. **GIL**: Limits CPU-bound parallelism
3. **Memory usage**: Higher overhead than compiled languages
4. **Type safety**: Dynamic typing catches errors at runtime
5. **Deployment**: Need Python runtime + dependencies

### Agenkit Performance Profile

| Operation | Typical Latency | Throughput |
|-----------|----------------|------------|
| Message creation | ~1μs | 1M ops/sec |
| Agent process (mock) | ~10μs | 100K ops/sec |
| Sequential (3 agents) | ~30μs | 33K ops/sec |
| Parallel (3 agents) | ~20μs | 50K ops/sec |
| asyncio.gather | ~5μs | 200K ops/sec |

**Compared to Other Languages**:
- **TypeScript**: Comparable (both interpreted/JIT)
- **Go**: 10-50x slower
- **Rust**: 20-100x slower
- **C++**: 20-100x slower
- **Zig**: 20-100x slower

**When to use Python**:
- Prototyping and experimentation
- ML/AI integration (best ecosystem)
- Data analysis and scientific computing
- Scripting and automation
- Rapid iteration

**When to migrate from Python**:
- Production deployments (performance critical)
- High concurrency workloads
- Memory-constrained environments
- Real-time systems
- Embedded systems

---

## Migration Quick Links

**From Python**:
- [Python → Go](MIGRATE_PYTHON_TO_GO.md) - For performance, deployment
- [Python → TypeScript](MIGRATE_PYTHON_TO_TYPESCRIPT.md) - For web/Node.js
- [Python → Rust](MIGRATE_PYTHON_TO_RUST.md) - For systems programming, WASM
- [Python → C++](MIGRATE_PYTHON_TO_CPP.md) - For native performance
- [Python → Zig](MIGRATE_PYTHON_TO_ZIG.md) - For embedded, low-level

**To Python**:
- [Go → Python](MIGRATE_GO_TO_PYTHON.md) - For prototyping, ML
- [TypeScript → Python](MIGRATE_TYPESCRIPT_TO_PYTHON.md) - For data science
- [Rust → Python](MIGRATE_RUST_TO_PYTHON.md) - For rapid development
- [C++ → Python](MIGRATE_CPP_TO_PYTHON.md) - For easier maintenance
- [Zig → Python](MIGRATE_ZIG_TO_PYTHON.md) - For high-level APIs

---

## Additional Resources

- [Python Documentation](https://docs.python.org/3/) - Official docs
- [Real Python](https://realpython.com/) - Tutorials and guides
- [Agenkit Python Examples](../examples/) - Working code samples
- [Agenkit Python Tests](../tests/) - Test patterns
- [Main Migration Guide](../docs/MIGRATION.md) - Python → All languages

---

**Document Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
