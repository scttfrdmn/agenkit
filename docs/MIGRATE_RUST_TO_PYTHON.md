# Quick Reference: Rust → Python Migration

**For**: Rust developers migrating Agenkit code to Python
**Time**: 15 minute read
**Full Details**: See [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) and [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md)

---

## Key Differences at a Glance

| Aspect | Rust | Python |
|--------|------|--------|
| **Typing** | Static, compile-time checked | Dynamic, optional hints |
| **Memory** | Ownership system, no GC | GC + reference counting |
| **Errors** | `Result<T, E>` (values) | Exceptions (`try/except`) |
| **Concurrency** | tokio async/await | asyncio async/await |
| **Performance** | Zero-cost abstractions | Runtime overhead |
| **Compilation** | Compiled to binary | Interpreted (bytecode) |

---

## Message Creation

### Rust
```rust
use agenkit::{Message, Role};
use std::collections::HashMap;

let mut metadata = HashMap::new();
metadata.insert("key".to_string(), json!("value"));

let msg = Message {
    role: Role::User,
    content: "Hello!".to_string(),
    metadata,
    ..Default::default()
};
```

### Python
```python
from agenkit import Message

msg = Message(
    role="user",
    content="Hello!",
    metadata={"key": "value"}
)
```

**Changes**:
- Struct literal → Constructor call
- `to_string()` → String literals (no conversion needed)
- `HashMap` → `dict` (built-in)
- Enum: `Role::User` → `"user"` string
- No `Default::default()` needed

---

## Agent Implementation

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, AgentError};

struct MyAgent {
    name: String,
    config: Config,
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

### Python
```python
from agenkit import Agent, Message
from typing import List

class MyAgent(Agent):
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> List[str]:
        return ["text", "analysis"]

    async def process(self, message: Message) -> Message:
        return Message(
            role="assistant",
            content=f"Processed: {message.content}"
        )
```

**Changes**:
- Struct → Class with `__init__`
- `#[async_trait]` → Not needed (native async)
- `impl Trait for Type` → `class Type(Trait)`
- Methods: `&self` → `self`
- Getters: `fn name(&self) -> &str` → `@property def name(self) -> str`
- `Result<T, E>` → Direct return (errors become exceptions)
- `vec!["text".to_string()]` → `["text"]` (no conversion needed)

---

## Error Handling

### Rust
```rust
// Function returns Result
fn process_message(agent: &impl Agent, msg: Message) -> Result<Message, AgentError> {
    let validated = validate_message(&msg)?;  // ? operator
    let result = agent.process(validated)?;
    Ok(result)
}

// Pattern matching
match agent.process(msg).await {
    Ok(response) => println!("Success: {}", response.content),
    Err(AgentError::Timeout(secs)) => {
        eprintln!("Timeout after {}s", secs)
    }
    Err(e) => eprintln!("Error: {}", e),
}
```

### Python
```python
# Function raises exceptions
async def process_message(agent: Agent, msg: Message) -> Message:
    validate_message(msg)  # Raises on error
    result = await agent.process(msg)  # Raises on error
    return result

# Exception handling
try:
    response = await agent.process(message)
    print(f"Success: {response.content}")
except TimeoutError as e:
    print(f"Timeout: {e}")
except AgentError as e:
    print(f"Error: {e}")
```

**Changes**:
- `Result<T, E>` → Direct return value
- `?` operator → No equivalent (exceptions propagate automatically)
- `Ok(value)` → `return value`
- `Err(error)` → `raise error`
- Pattern matching → `try/except` with multiple exception types
- Error wrapping: `.context("msg")` → `raise ... from e`

---

## Ownership → Garbage Collection

### Rust (Ownership System)
```rust
// Move semantics - ownership transfer
let msg = Message { /* ... */ };
let msg2 = msg;  // msg is now invalid
// println!("{}", msg.content);  // Compile error!

// Borrowing - temporary access
fn process_msg(msg: &Message) {  // Immutable borrow
    println!("{}", msg.content);
}  // Borrow ends, msg still valid

// Mutable borrow - exclusive write
fn modify_msg(msg: &mut Message) {
    msg.content = "Modified".to_string();
}

// Clone when you need multiple owners
let msg2 = msg.clone();  // Explicit deep copy
```

### Python (Garbage Collection)
```python
# No ownership - everything is a reference
msg = Message(role="user", content="Hello")
msg2 = msg  # Both reference same object
print(msg.content)  # Still valid - no moves!

# All function arguments are references
def process_msg(msg: Message):  # Reference passed
    print(msg.content)  # Original object

# Mutations affect all references
def modify_msg(msg: Message):
    msg.content = "Modified"  # Modifies original!

# Explicit copy when needed
import copy
msg2 = copy.deepcopy(msg)  # Deep copy
```

**Changes**:
- **No ownership tracking**: All variables are references
- **No borrowing syntax**: `&` and `&mut` disappear
- **No compile-time safety**: Runtime errors instead
- **Implicit reference counting**: Automatic memory management
- **Circular references**: Handled by GC (not in Rust)
- **Clone**: Explicit → Implicit (no `clone()` needed)

---

## Concurrency

### Rust (tokio)
```rust
use tokio;

// Spawn task
tokio::spawn(async move {
    match agent.process(msg).await {
        Ok(result) => println!("Success: {}", result.content),
        Err(e) => eprintln!("Error: {}", e),
    }
});

// Join multiple tasks
let (res1, res2, res3) = tokio::join!(
    agent1.process(msg.clone()),
    agent2.process(msg.clone()),
    agent3.process(msg.clone())
);

// Select first to complete
tokio::select! {
    res = agent1.process(msg.clone()) => println!("Agent 1: {:?}", res),
    res = agent2.process(msg.clone()) => println!("Agent 2: {:?}", res),
}

// Channels for communication
use tokio::sync::mpsc;
let (tx, mut rx) = mpsc::channel(32);

tx.send(message).await.unwrap();
while let Some(msg) = rx.recv().await {
    println!("Received: {}", msg.content);
}
```

### Python (asyncio)
```python
import asyncio

# Create task
async def process_task():
    try:
        result = await agent.process(message)
        print(f"Success: {result.content}")
    except Exception as e:
        print(f"Error: {e}")

task = asyncio.create_task(process_task())

# Gather multiple coroutines
results = await asyncio.gather(
    agent1.process(message),
    agent2.process(message),
    agent3.process(message),
)

# No select equivalent - use wait with FIRST_COMPLETED
done, pending = await asyncio.wait(
    [agent1.process(message), agent2.process(message)],
    return_when=asyncio.FIRST_COMPLETED
)
first_result = done.pop().result()

# Queue for communication
queue = asyncio.Queue()

await queue.put(message)
while not queue.empty():
    msg = await queue.get()
    print(f"Received: {msg.content}")
```

**Changes**:
- `tokio::spawn` → `asyncio.create_task`
- `tokio::join!` → `asyncio.gather`
- `tokio::select!` → `asyncio.wait(..., FIRST_COMPLETED)`
- `mpsc::channel` → `asyncio.Queue`
- `tx.send()` → `queue.put()`
- `rx.recv()` → `queue.get()`
- `move` keyword → Not needed (no ownership)
- `clone()` → Not needed (references)

---

## Patterns

### Sequential

**Rust**:
```rust
use agenkit::patterns::Sequential;

let sequential = Sequential::new(vec![
    Box::new(agent1),
    Box::new(agent2),
    Box::new(agent3),
]);

let result = sequential.process(msg).await?;
```

**Python**:
```python
from agenkit.patterns import SequentialAgent

sequential = SequentialAgent(agents=[agent1, agent2, agent3])
result = await sequential.process(message)
```

### Parallel

**Rust**:
```rust
use agenkit::patterns::Parallel;

let parallel = Parallel::new(vec![
    Box::new(agent_a),
    Box::new(agent_b),
    Box::new(agent_c),
]);

let result = parallel.process(msg).await?;
```

**Python**:
```python
from agenkit.patterns import ParallelAgent

parallel = ParallelAgent(agents=[agent_a, agent_b, agent_c])
result = await parallel.process(message)
```

### Router

**Rust**:
```rust
use agenkit::patterns::Router;

let router = Router::new(
    |msg: &Message| {
        if msg.content.contains("urgent") {
            "fast"
        } else {
            "thorough"
        }
    },
    vec![
        ("fast", Box::new(fast_agent)),
        ("thorough", Box::new(thorough_agent)),
    ],
);

let result = router.process(msg).await?;
```

**Python**:
```python
from agenkit.patterns import RouterAgent

def router_fn(msg: Message) -> str:
    if "urgent" in msg.content:
        return "fast"
    return "thorough"

router = RouterAgent(
    router=router_fn,
    agents={
        "fast": fast_agent,
        "thorough": thorough_agent,
    },
)

result = await router.process(message)
```

**Changes**:
- `Box::new()` → Not needed (no ownership boxing)
- `vec![]` → `[]` list
- Closure syntax: `|x| expr` → `lambda x: expr` or `def fn(x): return expr`
- Tuples in vec → Dict
- `?` operator → No equivalent (exceptions)

---

## Common Gotchas

### 1. Borrowing → References

**Rust**: Explicit borrowing with lifetime tracking
```rust
fn process_msg(msg: &Message) -> &str {  // Borrow with lifetime
    &msg.content  // Compiler tracks lifetime
}

let msg = Message { /* ... */ };
let content = process_msg(&msg);  // Explicit borrow
println!("{}", content);  // msg still valid
```

**Python**: Everything is a reference
```python
def process_msg(msg: Message) -> str:  # Reference passed implicitly
    return msg.content  # Returns new reference

msg = Message(role="user", content="Hello")
content = process_msg(msg)  # No explicit borrow syntax
print(content)  # msg still valid
```

**Migration Notes**:
- Remove all `&` and `&mut` from function signatures
- Remove lifetime annotations (`'a`, `'static`)
- Be aware: Python mutations affect all references (no `&mut` protection)
- Use `copy.deepcopy()` if you need Rust-like `clone()` behavior

### 2. Result Type → Exceptions

**Rust**: Errors as values, explicit handling
```rust
fn risky_operation() -> Result<String, Error> {
    if check_fails() {
        return Err(Error::Invalid("reason".to_string()));
    }
    Ok("success".to_string())
}

// Must handle Result
match risky_operation() {
    Ok(value) => println!("Got: {}", value),
    Err(e) => eprintln!("Error: {}", e),
}

// Or propagate with ?
let value = risky_operation()?;
```

**Python**: Errors as exceptions, implicit propagation
```python
def risky_operation() -> str:
    if check_fails():
        raise ValueError("reason")
    return "success"

# Can ignore exceptions (propagate up call stack)
value = risky_operation()  # May raise

# Or handle explicitly
try:
    value = risky_operation()
    print(f"Got: {value}")
except ValueError as e:
    print(f"Error: {e}")
```

**Migration Notes**:
- Change return type: `Result<T, E>` → `T`
- Remove `Ok()` wrapping
- Change error returns: `Err(e)` → `raise e`
- Remove `?` operator (exceptions propagate automatically)
- Consider: Python's implicit propagation can hide errors

### 3. Move Semantics → Reference Semantics

**Rust**: Ownership transfer invalidates original
```rust
let msg = Message { /* ... */ };
let msg2 = msg;  // Move - msg invalid now
// process(&msg);  // Compile error!

// Must clone for multiple uses
let msg3 = msg2.clone();
process(&msg2);
process(&msg3);
```

**Python**: Assignment creates new reference
```python
msg = Message(role="user", content="Hello")
msg2 = msg  # New reference - msg still valid!
process(msg)   # Works fine
process(msg2)  # Also works

# Both msg and msg2 reference the same object
msg2.content = "Modified"
print(msg.content)  # "Modified" - same object!
```

**Migration Notes**:
- Remove `clone()` calls (usually unnecessary)
- Be aware: Multiple references to same object in Python
- Use `copy.deepcopy()` if you need independent copies
- Consider: Python's mutability can cause surprising behavior

### 4. Compile-Time Safety → Runtime Safety

**Rust**: Many errors caught at compile time
```rust
let msg: Message = get_message();
// msg.invalid_field;  // Compile error - field doesn't exist
// msg.content.push(42);  // Compile error - type mismatch

let value: u32 = 42;
// let text: String = value;  // Compile error - no implicit conversion
```

**Python**: Errors caught at runtime
```python
msg = get_message()
# msg.invalid_field  # Runtime AttributeError
# msg.content + 42   # Runtime TypeError

value = 42
# text = value  # No error - dynamic typing
# text.upper()  # Runtime AttributeError
```

**Migration Notes**:
- Add comprehensive tests (what compiler checked is now your responsibility)
- Use type hints + mypy for static checking
- Consider runtime validation for critical paths
- Defensive programming: check types/values at boundaries

### 5. Zero-Cost Abstractions → Runtime Overhead

**Rust**: High-level code compiles to optimal machine code
```rust
// Generic function - monomorphization (zero cost)
fn process<A: Agent>(agent: &A, msg: Message) -> Result<Message, AgentError> {
    agent.process(msg)  // Inlined, specialized per type
}

// Iterator - zero allocation, optimized away
let sum: i32 = vec.iter()
    .filter(|x| **x > 0)
    .map(|x| x * 2)
    .sum();  // Compiles to efficient loop
```

**Python**: High-level code stays high-level
```python
# Duck typing - runtime type checks
def process(agent: Agent, msg: Message) -> Message:
    return agent.process(msg)  # Virtual dispatch at runtime

# List comprehension - creates intermediate lists
items = [x * 2 for x in vec if x > 0]
sum_result = sum(items)  # Memory allocation + iteration
```

**Migration Notes**:
- Expect 20-100x slower performance
- Profile before optimizing (Python's simplicity often worth it)
- Use NumPy/Cython for hot paths
- Consider: Python's strength is rapid development, not speed

---

## Testing

### Rust
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
        let invalid_msg = Message {
            role: Role::User,
            content: "".to_string(),
            ..Default::default()
        };

        let result = agent.process(invalid_msg).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::InvalidMessage(_)));
    }
}
```

### Python
```python
import pytest
from agenkit import Message
from myagent import MyAgent, InvalidMessageError

@pytest.mark.asyncio
async def test_agent_process():
    agent = MyAgent(name="test-agent")
    msg = Message(role="user", content="Test")

    result = await agent.process(msg)

    assert result.role == "assistant"
    assert "Processed" in result.content

@pytest.mark.asyncio
async def test_agent_error():
    agent = MyAgent(name="test-agent")
    invalid_msg = Message(role="user", content="")

    with pytest.raises(InvalidMessageError):
        await agent.process(invalid_msg)

# Fixtures for reusable setup
@pytest.fixture
def agent():
    return MyAgent(name="test-agent", config={"test": True})

@pytest.fixture
def sample_message():
    return Message(role="user", content="Test")

async def test_with_fixtures(agent, sample_message):
    result = await agent.process(sample_message)
    assert result.content.startswith("Processed")
```

**Changes**:
- `#[cfg(test)] mod tests` → Top-level test files
- `#[tokio::test]` → `@pytest.mark.asyncio`
- `assert_eq!(a, b)` → `assert a == b`
- `assert!(cond)` → `assert cond`
- `.unwrap()` → No equivalent (exceptions propagate)
- `matches!()` → `pytest.raises()`
- `Result::is_err()` → `pytest.raises()` context

---

## Performance Considerations

| Operation | Rust | Python | Ratio |
|-----------|------|--------|-------|
| Message creation | ~50ns | ~1μs | 20x slower |
| Agent process (mock) | ~500ns | ~10μs | 20x slower |
| Sequential (3 agents) | ~1.5μs | ~30μs | 20x slower |
| Parallel (3 agents) | ~500ns | ~20μs | 40x slower |
| Memory overhead | 1x (baseline) | 3-5x | Higher |

**When to migrate Rust → Python**:
- Prototyping and experimentation (much faster development)
- ML/AI integration (Python has best ecosystem: PyTorch, TensorFlow, etc.)
- Data science and analysis (NumPy, pandas, Jupyter)
- Scripting and automation
- Rapid iteration (no compilation step)
- Interfacing with Python-only libraries

**When to keep Rust**:
- Production deployments (performance critical)
- Real-time systems (no GC pauses)
- Embedded systems (no runtime required)
- WebAssembly targets
- Memory-constrained environments
- When you need compile-time safety guarantees

**Best Practice**: Start in Python for speed, migrate hot paths to Rust if needed.

---

## Migration Checklist

- [ ] Remove ownership syntax (`&`, `&mut`, lifetime annotations)
- [ ] Convert `Result<T, E>` returns to direct returns + exceptions
- [ ] Replace `Ok(value)` with `return value`
- [ ] Replace `Err(error)` with `raise error`
- [ ] Remove `?` operator (errors propagate automatically)
- [ ] Change `struct` to `class` with `__init__`
- [ ] Convert `impl Trait for Type` to inheritance
- [ ] Remove `#[async_trait]` (native async support)
- [ ] Update imports: `use` → `from ... import`
- [ ] Replace `Vec<T>` with `List[T]` (type hints)
- [ ] Replace `HashMap` with `dict`
- [ ] Remove `Box::new()` (no heap boxing needed)
- [ ] Update tests: `#[tokio::test]` → `@pytest.mark.asyncio`
- [ ] Convert `assert_eq!` to `assert` statements
- [ ] Add comprehensive tests (replace compile-time checks)

---

## Quick Start

```bash
# Rust project structure
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   └── agent.rs
└── tests/
    └── integration_test.rs

# Python equivalent
agenkit/
├── pyproject.toml
├── agenkit/
│   ├── __init__.py
│   └── agent.py
└── tests/
    └── test_agent.py
```

**Build/Run**:
```bash
# Rust
cargo build --release
cargo run --release

# Python (with uv for speed)
uv run python main.py

# Or with standard Python
python main.py
```

**Testing**:
```bash
# Rust
cargo test

# Python
uv run pytest tests/
# Or
pytest tests/
```

---

## Type Hint Mapping

| Rust Type | Python Type Hint |
|-----------|-----------------|
| `String` | `str` |
| `&str` | `str` |
| `Vec<T>` | `List[T]` |
| `HashMap<K, V>` | `Dict[K, V]` |
| `Option<T>` | `Optional[T]` or `T \| None` |
| `Result<T, E>` | `T` (exceptions) |
| `Box<T>` | `T` (no boxing) |
| `Arc<T>` | `T` (GC handles sharing) |
| `&T` | `T` (implicit references) |
| `&mut T` | `T` (implicit references) |

---

## Full Resources

- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms guide
- [Python Language Profile](LANGUAGE_PROFILE_PYTHON.md) - Complete Python idioms guide
- [Main Migration Guide](MIGRATION.md) - Python → All languages
- [Agenkit Examples](../examples/) - Side-by-side code samples in all languages
- [The Rust Book](https://doc.rust-lang.org/book/) - Learn Rust
- [Python Documentation](https://docs.python.org/3/) - Python reference

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
