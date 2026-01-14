# Quick Reference: Python → Rust Migration

**For**: Python developers migrating Agenkit code to Rust
**Time**: 15 minute read
**Full Details**: See [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) and [Rust Language Profile](LANGUAGE_PROFILE_RUST.md)

---

## Key Differences at a Glance

| Aspect | Python | Rust |
|--------|--------|------|
| **Typing** | Dynamic, optional hints | Static, compile-time enforced |
| **Errors** | Exceptions (`try/except`) | `Result<T, E>` type |
| **Concurrency** | `async/await` + `asyncio` | `async/await` + `tokio` |
| **Memory** | GC + refcounting | Ownership system (no GC) |
| **Performance** | Interpreted (~10μs/op) | Compiled (~500ns/op) |
| **Deployment** | Interpreter + packages | Single binary or WASM |
| **Safety** | Runtime errors | Compile-time safety |

---

## Message Creation

### Python
```python
from agenkit import Message
from datetime import datetime

msg = Message(
    role="user",
    content="Hello!",
    metadata={"key": "value"},
    timestamp=datetime.now()
)
```

### Rust
```rust
use agenkit::{Message, Role};
use std::collections::HashMap;
use chrono::Utc;

let mut metadata = HashMap::new();
metadata.insert("key".to_string(), json!("value"));

let msg = Message {
    role: Role::User,
    content: "Hello!".to_string(),
    metadata,
    timestamp: Some(Utc::now()),
};

// Or use builder pattern
let msg = Message::builder()
    .role(Role::User)
    .content("Hello!")
    .metadata("key", "value")
    .build();
```

**Changes**:
- Import path: `agenkit` → `agenkit`
- Constructor → Struct literal or builder
- String literals: `"user"` → `Role::User` enum
- Type: `dict` → `HashMap<String, Value>`
- Strings: `"text"` → `"text".to_string()` (owned)
- `datetime.now()` → `Utc::now()`

---

## Agent Implementation

### Python
```python
from agenkit import Agent, Message

class MyAgent(Agent):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Processed: {message.content}"
        )
```

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, Role, AgentError};

struct MyAgent {
    name: String,
}

impl MyAgent {
    fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text".to_string(), "analysis".to_string()]
    }

    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        Ok(Message {
            role: Role::Assistant,
            content: format!("Processed: {}", msg.content),
            ..Default::default()
        })
    }
}
```

**Changes**:
- `class` → `struct` with `impl` blocks
- `__init__` → `new` associated function
- `@property` → methods in `impl Agent`
- Duck typing → Explicit `#[async_trait] impl Agent`
- `return value` → `return Ok(value)` (explicit success)
- No exceptions → `Result<Message, AgentError>`
- `self` parameter → `&self` (immutable borrow)

---

## Error Handling

### Python
```python
try:
    result = await agent.process(message)
    # Use result
except InvalidMessageError as e:
    print(f"Validation error: {e}")
except AgentError as e:
    print(f"Agent error: {e}")
    raise RuntimeError(f"Failed: {e}") from e
```

### Rust
```rust
match agent.process(message).await {
    Ok(result) => {
        // Use result
        println!("Success: {}", result.content);
    }
    Err(AgentError::InvalidMessage(msg)) => {
        eprintln!("Validation error: {}", msg);
    }
    Err(e) => {
        eprintln!("Agent error: {}", e);
        return Err(e);  // Propagate error
    }
}

// Or use ? operator for concise propagation
let result = agent.process(message).await?;  // Returns early if Err
```

**Changes**:
- `try/except` → `match` on `Result<T, E>`
- Exception types → Enum variants (`AgentError::InvalidMessage`)
- `raise` → `return Err(...)`
- `raise ... from e` → `?` operator (automatic propagation)
- Implicit unwinding → Explicit error handling

### Custom Error Types

**Python**:
```python
class AgentError(Exception):
    pass

class TimeoutError(AgentError):
    pass
```

**Rust**:
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AgentError {
    #[error("Processing failed: {0}")]
    ProcessingFailed(String),

    #[error("Timeout after {0}s")]
    Timeout(u64),

    #[error("Invalid message: {0}")]
    InvalidMessage(String),
}
```

---

## Concurrency

### Python (asyncio)
```python
import asyncio

# Create task
task = asyncio.create_task(agent.process(message))
result = await task

# Gather multiple coroutines
results = await asyncio.gather(
    agent1.process(message),
    agent2.process(message),
    agent3.process(message),
)

# With timeout
try:
    result = await asyncio.wait_for(
        agent.process(message),
        timeout=5.0
    )
except asyncio.TimeoutError:
    print("Timed out!")
```

### Rust (tokio)
```rust
use tokio;

// Spawn task
let task = tokio::spawn(async move {
    agent.process(message).await
});
let result = task.await.unwrap()?;

// Join multiple futures
let (res1, res2, res3) = tokio::join!(
    agent1.process(message.clone()),
    agent2.process(message.clone()),
    agent3.process(message.clone())
);

// With timeout
use tokio::time::{timeout, Duration};

match timeout(Duration::from_secs(5), agent.process(message)).await {
    Ok(result) => println!("Success: {:?}", result),
    Err(_) => eprintln!("Timed out!"),
}
```

**Changes**:
- `asyncio.create_task()` → `tokio::spawn()`
- `asyncio.gather()` → `tokio::join!()`
- `asyncio.wait_for()` → `tokio::time::timeout()`
- `asyncio.Queue` → `tokio::sync::mpsc::channel()`
- Single-threaded event loop → Multi-threaded work-stealing runtime
- GIL limitations → True parallelism

---

## Memory Management

### Python (GC)
```python
# Automatic memory management
def process_data(messages: list[Message]) -> list[Message]:
    results = []  # Allocated
    for msg in messages:
        buffer = bytearray(1024)  # Allocated
        # ...process...
        results.append(msg)
    return results
    # buffer and temporary objects automatically freed
```

### Rust (Ownership)
```rust
// Ownership: Each value has one owner
fn process_data(messages: Vec<Message>) -> Vec<Message> {
    let mut results = Vec::new();  // Allocated
    for msg in messages {  // msg moves into loop, transferred ownership
        let buffer = vec![0u8; 1024];  // Allocated
        // ...process...
        results.push(msg);  // msg moved into results
        // buffer dropped here (deterministic cleanup)
    }
    results
    // results ownership transferred to caller
}

// Borrowing: Temporary access without ownership transfer
fn process_borrowed(messages: &[Message]) -> Vec<Message> {
    let mut results = Vec::new();
    for msg in messages {  // msg is a reference
        // Use msg without taking ownership
        results.push(msg.clone());  // Explicit clone if needed
    }
    results
}
```

**Key Concepts**:
1. **Ownership**: One owner per value, automatic cleanup when owner drops
2. **Borrowing**: `&T` (immutable) or `&mut T` (mutable) temporary access
3. **Move semantics**: Assignment/passing transfers ownership (no copy)
4. **Explicit cloning**: `.clone()` when you need a deep copy
5. **No GC pauses**: Deterministic, predictable performance

---

## Patterns

### Sequential

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(agents=[agent1, agent2, agent3])
result = await sequential.process(message)
```

**Rust**:
```rust
use agenkit::patterns::Sequential;

let sequential = Sequential::new(vec![
    Box::new(agent1),
    Box::new(agent2),
    Box::new(agent3),
]);

let result = sequential.process(message).await?;
```

### Parallel

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(agents=[agent_a, agent_b, agent_c])
result = await parallel.process(message)
```

**Rust**:
```rust
use agenkit::patterns::Parallel;

let parallel = Parallel::new(vec![
    Box::new(agent_a),
    Box::new(agent_b),
    Box::new(agent_c),
]);

let result = parallel.process(message).await?;
```

**Changes**:
- `agents=[...]` → `vec![...]`
- Implicit trait objects → Explicit `Box<dyn Agent>`
- `await` → `.await?` (handle errors explicitly)

---

## Common Gotchas

### 1. Ownership and Borrowing (BIGGEST PARADIGM SHIFT!)

**Python**: Everything is a reference, GC handles cleanup
```python
def use_twice(msg: Message):
    process_message(msg)  # msg still valid
    process_message(msg)  # msg still valid
```

**Rust**: Values move unless borrowed
```rust
fn use_twice(msg: Message) {
    process_message(msg);      // msg moved, now invalid
    process_message(msg);      // ERROR: use of moved value
}

// Solution 1: Borrow
fn use_twice_borrow(msg: &Message) {
    process_message(msg);      // Borrow, msg still valid
    process_message(msg);      // OK: msg still valid
}

// Solution 2: Clone
fn use_twice_clone(msg: Message) {
    process_message(msg.clone());  // Clone for first use
    process_message(msg);           // Original for second use
}
```

### 2. String Types

**Python**: One string type (`str`)
**Rust**: Multiple string types

```rust
// &str: String slice (borrowed, immutable)
let s: &str = "Hello";

// String: Owned, growable string
let s: String = "Hello".to_string();
let s: String = String::from("Hello");

// Conversion
let owned: String = "slice".to_string();
let borrowed: &str = &owned;

// In function signatures
fn takes_slice(s: &str) { }      // Accepts both &str and &String
fn takes_owned(s: String) { }    // Takes ownership
```

### 3. Error Propagation

**Python**: Exceptions propagate automatically
```python
async def outer():
    result = await inner()  # Exception propagates automatically
    return result
```

**Rust**: Must explicitly handle or propagate
```rust
async fn outer() -> Result<Message, AgentError> {
    let result = inner().await?;  // ? propagates error
    Ok(result)  // Must wrap success in Ok()
}
```

**Key Point**: Forgetting `?` or `Ok()` is a compile error in Rust.

### 4. Mutable vs Immutable

**Python**: Everything mutable by default
```python
msg = Message(role="user", content="Hello")
msg.content = "Modified"  # OK
```

**Rust**: Immutable by default
```rust
let msg = Message { /* ... */ };
msg.content = "Modified".to_string();  // ERROR: msg is immutable

// Must declare mutable
let mut msg = Message { /* ... */ };
msg.content = "Modified".to_string();  // OK
```

### 5. Async Trait Implementation

**Python**: Async methods just work
```python
class MyAgent(Agent):
    async def process(self, msg: Message) -> Message:
        return result
```

**Rust**: Need `#[async_trait]` macro
```rust
use async_trait::async_trait;

#[async_trait]  // Required for async trait methods
impl Agent for MyAgent {
    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        Ok(result)
    }
}
```

---

## Type System Migration

### Python Type Hints → Rust Types

| Python | Rust | Notes |
|--------|------|-------|
| `str` | `&str` or `String` | `&str` borrowed, `String` owned |
| `int` | `i32`, `i64`, `usize` | Rust has sized integers |
| `float` | `f32`, `f64` | Rust specifies precision |
| `bool` | `bool` | Same |
| `list[T]` | `Vec<T>` | Growable array |
| `dict[K, V]` | `HashMap<K, V>` | Hash map |
| `Optional[T]` | `Option<T>` | Explicit null safety |
| `tuple[T, U]` | `(T, U)` | Tuples similar |
| `Any` | No direct equivalent | Rust requires type |

### None/Null Handling

**Python**:
```python
def maybe_process(msg: Optional[Message]) -> Optional[Message]:
    if msg is None:
        return None
    return process(msg)
```

**Rust**:
```rust
fn maybe_process(msg: Option<Message>) -> Option<Message> {
    match msg {
        None => None,
        Some(m) => Some(process(m)),
    }
}

// Or more idiomatically
fn maybe_process(msg: Option<Message>) -> Option<Message> {
    msg.map(|m| process(m))
}

// Or even simpler with ? operator (in Result context)
fn maybe_process(msg: Option<Message>) -> Option<Message> {
    let m = msg?;  // Returns None if msg is None
    Some(process(m))
}
```

---

## Testing

### Python (pytest)
```python
import pytest
from agenkit import Message

@pytest.mark.asyncio
async def test_agent_process():
    agent = MyAgent("test-agent")
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.role == "assistant"
    assert "Processed" in result.content

@pytest.mark.asyncio
async def test_agent_error():
    agent = MyAgent("test-agent")
    empty_msg = Message(role="user", content="")

    with pytest.raises(InvalidMessageError):
        await agent.process(empty_msg)
```

### Rust (cargo test)
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_process() {
        let agent = MyAgent::new("test-agent");
        let msg = Message {
            role: Role::User,
            content: "Test".to_string(),
            ..Default::default()
        };

        let result = agent.process(msg).await.unwrap();

        assert_eq!(result.role, Role::Assistant);
        assert!(result.content.contains("Processed"));
    }

    #[tokio::test]
    async fn test_agent_error() {
        let agent = MyAgent::new("test-agent");
        let empty_msg = Message {
            role: Role::User,
            content: "".to_string(),
            ..Default::default()
        };

        let result = agent.process(empty_msg).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::InvalidMessage(_)));
    }
}
```

**Changes**:
- `@pytest.mark.asyncio` → `#[tokio::test]`
- `def test_xxx()` → `fn test_xxx()`
- `assert` statements → `assert_eq!`, `assert!` macros
- `pytest.raises` → `matches!` macro with pattern matching
- `with pytest.raises` → `result.is_err()` checks

---

## Performance Comparison

| Operation | Python | Rust | Speedup |
|-----------|--------|------|---------|
| Message creation | ~1μs | ~50ns | **20x** |
| Agent process (mock) | ~10μs | ~500ns | **20x** |
| Sequential (3 agents) | ~30μs | ~1.5μs | **20x** |
| Parallel (3 agents) | ~20μs | ~500ns | **40x** |
| JSON serialization | ~5μs | ~200ns | **25x** |
| String operations | ~100ns | ~10ns | **10x** |
| Async task spawn | ~5μs | ~100ns | **50x** |

**Memory Usage**:
- **Python**: ~50-100MB baseline (interpreter overhead)
- **Rust**: ~2-5MB (compiled binary)
- **Reduction**: **10-50x smaller** memory footprint

**Startup Time**:
- **Python**: ~100-500ms (interpreter init + imports)
- **Rust**: ~1-5ms (compiled binary)
- **Improvement**: **100-500x faster** startup

---

## When to Migrate Python → Rust

### Good Reasons

1. **Performance critical**: 20-100x speed improvement needed
2. **Memory constrained**: Embedded, edge devices, serverless
3. **Predictable latency**: No GC pauses, deterministic performance
4. **Type safety**: Catch bugs at compile time, not runtime
5. **WASM deployment**: Run in browser with near-native speed
6. **Production deployment**: Single binary, no runtime dependencies
7. **Fearless concurrency**: Data race prevention at compile time
8. **Long-running services**: No memory leaks, stable over time

### Bad Reasons

1. **Prototyping**: Python is faster for experimentation
2. **ML/AI integration**: Python ecosystem is unmatched (NumPy, PyTorch)
3. **Small scripts**: Python's simplicity wins for one-offs
4. **Team unfamiliar with Rust**: Learning curve is steep (3-6 months)
5. **Rapid iteration**: Python's dynamic typing speeds up development
6. **Glue code**: Python excels at integrating existing tools

---

## Migration Checklist

- [ ] Replace `class` with `struct` + `impl` blocks
- [ ] Add `#[async_trait]` to async trait implementations
- [ ] Convert exceptions to `Result<T, E>` returns
- [ ] Add `?` operator for error propagation
- [ ] Wrap success returns in `Ok()`
- [ ] Make string literals owned: `"text".to_string()`
- [ ] Add type annotations (required in Rust)
- [ ] Change `list`/`dict` to `Vec`/`HashMap`
- [ ] Convert `None` checks to `Option<T>` pattern matching
- [ ] Update imports: `from agenkit import` → `use agenkit::`
- [ ] Replace `@property` with methods in trait `impl`
- [ ] Add explicit lifetime annotations if needed
- [ ] Handle ownership: use `&` for borrows, `.clone()` for copies
- [ ] Mark mutable variables: `let mut`
- [ ] Update tests: `pytest` → `#[tokio::test]`
- [ ] Update dependencies: `requirements.txt` → `Cargo.toml`
- [ ] Add `#[derive(Debug, Clone)]` to structs as needed

---

## Quick Start

```bash
# Python project structure
agenkit/
├── pyproject.toml
├── main.py
└── agent.py

# Rust equivalent
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── main.rs
│   └── agent.rs
```

**Build/Run**:
```bash
# Python
uv run python main.py

# Rust
cargo run --release  # --release for optimizations
```

**Dependencies**:

**Python** (`pyproject.toml`):
```toml
[project]
dependencies = [
    "agenkit>=0.46.0",
]
```

**Rust** (`Cargo.toml`):
```toml
[dependencies]
agenkit = "0.46"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
```

---

## Full Resources

- [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) - Complete Python idioms guide
- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms guide
- [The Rust Book](https://doc.rust-lang.org/book/) - Official Rust learning resource
- [Async Book](https://rust-lang.github.io/async-book/) - Async Rust guide
- [Agenkit Examples](../examples/) - Side-by-side code samples
- [Agenkit Rust Examples](../agenkit-rust/examples/) - Rust-specific examples

---

## Real-World Example: Complete Agent Migration

### Python (Before)
```python
from agenkit import Agent, Message
from typing import List
import asyncio

class TextAnalyzer(Agent):
    def __init__(self, name: str):
        self._name = name
        self._request_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> List[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        self._request_count += 1

        # Simulate processing
        await asyncio.sleep(0.1)

        return Message(
            role="assistant",
            content=f"Analyzed: {message.content}",
            metadata={
                "request_count": self._request_count,
                "word_count": len(message.content.split())
            }
        )

# Usage
async def main():
    agent = TextAnalyzer("analyzer")

    try:
        result = await agent.process(
            Message(role="user", content="Hello world")
        )
        print(f"Result: {result.content}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

### Rust (After)
```rust
use agenkit::{Agent, Message, Role, AgentError};
use async_trait::async_trait;
use std::collections::HashMap;
use tokio::time::{sleep, Duration};

struct TextAnalyzer {
    name: String,
    request_count: std::sync::atomic::AtomicU64,  // Thread-safe counter
}

impl TextAnalyzer {
    fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            request_count: std::sync::atomic::AtomicU64::new(0),
        }
    }
}

#[async_trait]
impl Agent for TextAnalyzer {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text".to_string(), "analysis".to_string()]
    }

    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        // Increment counter (atomic, thread-safe)
        let count = self.request_count.fetch_add(1, std::sync::atomic::Ordering::SeqCst);

        // Simulate processing
        sleep(Duration::from_millis(100)).await;

        // Build metadata
        let mut metadata = HashMap::new();
        metadata.insert("request_count".to_string(), json!(count + 1));
        metadata.insert("word_count".to_string(), json!(msg.content.split_whitespace().count()));

        Ok(Message {
            role: Role::Assistant,
            content: format!("Analyzed: {}", msg.content),
            metadata,
            ..Default::default()
        })
    }
}

// Usage
#[tokio::main]
async fn main() {
    let agent = TextAnalyzer::new("analyzer");

    match agent.process(Message {
        role: Role::User,
        content: "Hello world".to_string(),
        ..Default::default()
    }).await {
        Ok(result) => println!("Result: {}", result.content),
        Err(e) => eprintln!("Error: {}", e),
    }
}
```

**Key Differences Highlighted**:
1. `__init__` → `new()` associated function
2. Mutable counter → `AtomicU64` for thread safety
3. `asyncio.sleep()` → `tokio::time::sleep()`
4. `.split()` → `.split_whitespace()` (more precise)
5. Exception handling → `match` on `Result`
6. `asyncio.run()` → `#[tokio::main]` macro

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
