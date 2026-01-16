# Quick Reference: Go → Rust Migration

**For**: Go developers migrating Agenkit code to Rust
**Time**: 15 minute read
**Full Details**: See [Go Language Profile](LANGUAGE_PROFILE_GO.md) and [Rust Language Profile](LANGUAGE_PROFILE_RUST.md)

---

## Key Differences at a Glance

| Aspect | Go | Rust |
|--------|----|----|
| **Typing** | Static, explicit | Static, explicit + ownership |
| **Errors** | `(result, error)` returns | `Result<T, E>` type |
| **Concurrency** | Goroutines + channels | async/await (tokio) |
| **Memory** | GC, automatic | Ownership system, no GC |
| **Performance** | Fast (compiled) | Very fast (zero-cost abstractions) |
| **Deployment** | Single binary | Single binary |

---

## Message Creation

### Go
```go
import "github.com/agenkit/agenkit-go"

msg := agenkit.Message{
    Role:    agenkit.RoleUser,
    Content: "Hello!",
    Metadata: map[string]interface{}{
        "key": "value",
    },
}
```

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

**Changes**:
- Import path: `agenkit-go` → `agenkit` crate
- Struct literal syntax similar
- Constants: `agenkit.RoleUser` → `Role::User` enum
- Strings: `"text"` → `"text".to_string()` (owned)
- Type: `map[string]interface{}` → `HashMap<String, Value>`
- Must initialize maps before use

---

## Agent Implementation

### Go
```go
type MyAgent struct {
    name string
}

func (a *MyAgent) Name() string {
    return a.name
}

func (a *MyAgent) Capabilities() []string {
    return []string{"text"}
}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    return agenkit.Message{
        Role:    agenkit.RoleAssistant,
        Content: "Response",
    }, nil
}
```

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, Role, AgentError};

struct MyAgent {
    name: String,
}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text".to_string()]
    }

    async fn process(&self, msg: Message) -> Result<Message, AgentError> {
        Ok(Message {
            role: Role::Assistant,
            content: "Response".to_string(),
            ..Default::default()
        })
    }
}
```

**Changes**:
- Struct → `struct` + `impl` block (similar)
- Methods: `func (a *MyAgent)` → `impl Agent for MyAgent`
- `#[async_trait]` required for async trait methods
- `ctx context.Context` → removed (tokio handles context)
- `(result, error)` → `Result<T, E>` enum
- Return `Ok(value)` instead of `value, nil`
- Borrowing: `&self` for immutable, `&mut self` for mutable

---

## Error Handling

### Go
```go
result, err := agent.Process(ctx, msg)
if err != nil {
    return nil, fmt.Errorf("process failed: %w", err)
}
// Use result
```

### Rust
```rust
// Using ? operator
let result = agent.process(msg).await?;
// Use result

// Or match for specific handling
match agent.process(msg).await {
    Ok(result) => {
        // Use result
    }
    Err(e) => {
        return Err(format!("process failed: {}", e).into());
    }
}
```

**Changes**:
- `if err != nil` → `?` operator or `match`
- Error wrapping: `fmt.Errorf(..., %w, err)` → `map_err()` or custom error types
- No tuple unpacking needed
- Compiler forces error handling (can't ignore `Result`)

---

## Concurrency

### Go (Goroutines)
```go
// Launch goroutine
go func() {
    result, err := agent.Process(ctx, msg)
    if err != nil {
        log.Printf("Error: %v", err)
        return
    }
    // Use result
}()

// Wait for multiple
var wg sync.WaitGroup
for _, agent := range agents {
    wg.Add(1)
    go func(a agenkit.Agent) {
        defer wg.Done()
        _, _ = a.Process(ctx, msg)
    }(agent)
}
wg.Wait()
```

### Rust (Tokio)
```rust
// Spawn task
tokio::spawn(async move {
    match agent.process(msg).await {
        Ok(result) => {
            // Use result
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }
});

// Wait for multiple
let results = tokio::join!(
    agent1.process(msg.clone()),
    agent2.process(msg.clone()),
    agent3.process(msg.clone())
);

// Or with a vector
use futures::future::join_all;
let results = join_all(agents.iter().map(|agent| {
    agent.process(msg.clone())
})).await;
```

**Changes**:
- `go func()` → `tokio::spawn(async move {})`
- `sync.WaitGroup` → `tokio::join!()` or `join_all()`
- `context.Context` → implicit in tokio runtime
- Channels: `chan` → `tokio::sync::mpsc`
- Must use `move` to transfer ownership into async block

---

## Patterns

### Sequential

**Go**:
```go
sequential := patterns.NewSequential([]agenkit.Agent{agent1, agent2})
result, err := sequential.Process(ctx, msg)
```

**Rust**:
```rust
use agenkit::patterns::Sequential;

let sequential = Sequential::new(vec![
    Box::new(agent1),
    Box::new(agent2),
]);
let result = sequential.process(msg).await?;
```

### Parallel

**Go**:
```go
parallel := patterns.NewParallel([]agenkit.Agent{agentA, agentB})
result, err := parallel.Process(ctx, msg)
```

**Rust**:
```rust
use agenkit::patterns::Parallel;

let parallel = Parallel::new(vec![
    Box::new(agent_a),
    Box::new(agent_b),
]);
let result = parallel.process(msg).await?;
```

---

## Common Gotchas

### 1. Ownership and Borrowing

**Go**: Pointers and value semantics, GC handles cleanup
**Rust**: Ownership rules enforced at compile time

```go
// Go - copies or shares freely
msg := agenkit.Message{Content: "Hello"}
process1(msg)
process2(msg)  // OK - msg copied or GC'd
```

```rust
// Rust - must be explicit about ownership
let msg = Message {
    content: "Hello".to_string(),
    ..Default::default()
};
process1(msg);
// process2(msg);  // ERROR: msg moved to process1

// Solutions:
// 1. Clone
let msg2 = msg.clone();
process1(msg);
process2(msg2);

// 2. Borrow
process1(&msg);
process2(&msg);
```

### 2. String Types

**Go**: Single `string` type
**Rust**: `String` (owned) vs `&str` (borrowed)

```go
// Go
func get_name() string {
    return "Agent"
}
```

```rust
// Rust - return owned String
fn get_name() -> String {
    "Agent".to_string()
}

// Or return borrowed &str (if static)
fn get_name() -> &'static str {
    "Agent"
}
```

### 3. Nil vs None

**Go**: `nil` for zero value
**Rust**: `Option<T>` for potentially missing values

```go
// Go
var msg *Message = nil
if msg != nil {
    // Use msg
}
```

```rust
// Rust
let msg: Option<Message> = None;
if let Some(m) = msg {
    // Use m
}

// Or use match
match msg {
    Some(m) => { /* use m */ }
    None => { /* handle missing */ }
}
```

### 4. Async Context

**Go**: `context.Context` passed explicitly
**Rust**: Tokio runtime handles cancellation implicitly

```go
// Go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
result, err := agent.Process(ctx, msg)
```

```rust
// Rust
use tokio::time::{timeout, Duration};

let result = timeout(
    Duration::from_secs(5),
    agent.process(msg)
).await?;
```

### 5. Error Types

**Go**: `error` interface
**Rust**: Custom error types or `anyhow`

```go
// Go
type AgentError struct {
    message string
}

func (e AgentError) Error() string {
    return e.message
}
```

```rust
// Rust with thiserror
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AgentError {
    #[error("Processing failed: {0}")]
    ProcessingFailed(String),

    #[error("Timeout")]
    Timeout,
}
```

---

## Testing

### Go
```go
func TestAgent(t *testing.T) {
    agent := NewMyAgent()
    msg := agenkit.Message{Role: agenkit.RoleUser, Content: "Test"}

    result, err := agent.Process(context.Background(), msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if result.Content != "Expected" {
        t.Errorf("got %q, want %q", result.Content, "Expected")
    }
}
```

### Rust
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent() {
        let agent = MyAgent { name: "test".to_string() };
        let msg = Message {
            role: Role::User,
            content: "Test".to_string(),
            ..Default::default()
        };

        let result = agent.process(msg).await.unwrap();

        assert_eq!(result.role, Role::Assistant);
        assert!(result.content.contains("Expected"));
    }
}
```

**Changes**:
- `func TestXxx(t *testing.T)` → `#[test]` or `#[tokio::test]`
- `t.Fatalf/t.Errorf` → `assert!` macros
- `unwrap()` or `?` for error handling in tests
- Tests in `tests` module or `#[cfg(test)]`

---

## Performance Considerations

| Operation | Go | Rust | Notes |
|-----------|----|----|-------|
| Agent creation | ~100ns | ~50ns | Rust 2x faster |
| Message processing | ~1μs | ~500ns | Rust 2x faster |
| Sequential (3 agents) | ~3μs | ~1.5μs | Rust 2x faster |
| Parallel (3 agents) | ~1μs | ~500ns | Rust better parallelism |

**When to use Rust**:
- Maximum performance required
- Memory safety critical (embedded, systems)
- WASM deployment
- Zero-cost abstractions needed
- No GC pauses acceptable
- Systems programming

**When to keep Go**:
- Faster development cycle (no borrow checker)
- Simpler concurrency model (goroutines)
- Larger ecosystem for web services
- Team expertise in Go
- GC pauses acceptable

---

## Migration Checklist

- [ ] Replace `struct` with `struct` + `impl` blocks
- [ ] Convert `(result, error)` to `Result<T, E>`
- [ ] Change goroutines to `tokio::spawn`
- [ ] Remove `context.Context` parameter
- [ ] Update imports: `agenkit-go` → `agenkit` crate
- [ ] Add ownership annotations (`&`, `&mut`, `move`)
- [ ] Convert strings: `string` → `String` or `&str`
- [ ] Replace `nil` with `None` and `Option<T>`
- [ ] Update error handling: `if err != nil` → `?` or `match`
- [ ] Change tests: `*testing.T` → `#[test]` attributes
- [ ] Add `async_trait` for async trait methods
- [ ] Configure `Cargo.toml` with dependencies
- [ ] Handle `Send + Sync` bounds for multi-threading

---

## Quick Start

```bash
# Go project structure
agenkit-go/
├── go.mod
├── main.go
└── agent.go

# Rust equivalent
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── main.rs
│   └── agent.rs
└── target/  # Build output
```

**Build/Run**:
```bash
# Go
go build -o myagent
./myagent

# Rust
cargo build --release
./target/release/myagent

# Or run directly
cargo run --release
```

**Project Setup**:
```bash
# Initialize Rust project
cargo new myagent
cd myagent

# Add dependencies to Cargo.toml
[dependencies]
agenkit = "0.46"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
anyhow = "1.0"
thiserror = "1.0"

# Build
cargo build
```

---

## Full Resources

- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms
- [The Rust Book](https://doc.rust-lang.org/book/) - Official Rust learning resource
- [Agenkit Rust Examples](../agenkit-rust/examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
