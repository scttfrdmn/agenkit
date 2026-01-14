# Quick Reference: Rust → Go Migration

**For**: Rust developers migrating Agenkit code to Go
**Time**: 15 minute read
**Full Details**: See [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) and [Go Language Profile](LANGUAGE_PROFILE_GO.md)

---

## Key Differences at a Glance

| Aspect | Rust | Go |
|--------|------|-----|
| **Typing** | Static, explicit lifetimes | Static, simpler |
| **Errors** | `Result<T, E>` | `(result, error)` returns |
| **Concurrency** | async/await (tokio) | Goroutines + channels |
| **Memory** | Ownership (no GC) | Garbage collection |
| **Performance** | Fastest (zero-cost) | Fast (compiled) |
| **Deployment** | Single binary | Single binary |

---

## Message Creation

### Rust
```rust
use agenkit::{Message, Role};
use std::collections::HashMap;

let msg = Message {
    role: Role::User,
    content: "Hello!".to_string(),
    metadata: HashMap::new(),
    ..Default::default()
};
```

### Go
```go
import "github.com/agenkit/agenkit-go"

msg := agenkit.Message{
    Role:    agenkit.RoleUser,
    Content: "Hello!",
    Metadata: map[string]interface{}{},
}
```

**Changes**:
- Import path: `agenkit` → `agenkit-go`
- Type annotation: `Role::User` → `agenkit.RoleUser`
- String: `.to_string()` → direct string (GC'd)
- Metadata: `HashMap::new()` → `map[string]interface{}{}`
- No `Default::default()` needed (zero values)

---

## Agent Implementation

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, AgentError};

struct MyAgent {
    name: String,
    capabilities: Vec<String>,
}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        self.capabilities.clone()
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

### Go
```go
import (
    "context"
    "fmt"
    "github.com/agenkit/agenkit-go"
)

type MyAgent struct {
    name         string
    capabilities []string
}

func (a *MyAgent) Name() string {
    return a.name
}

func (a *MyAgent) Capabilities() []string {
    return a.capabilities
}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    return agenkit.Message{
        Role:    agenkit.RoleAssistant,
        Content: fmt.Sprintf("Processed: %s", msg.Content),
    }, nil
}
```

**Changes**:
- Traits → Interfaces (implicit implementation)
- `#[async_trait]` → Not needed (goroutines are built-in)
- `&self` → `(a *MyAgent)` method receiver
- `async fn` → Regular `func` (concurrency via goroutines)
- `Result<T, E>` → `(T, error)` return tuple
- `context.Context` parameter added (cancellation)
- References: `&str` → direct values `string` (GC'd)
- `.clone()` → Not needed (GC handles sharing)

---

## Error Handling

### Rust
```rust
// Result type with ? operator
match agent.process(msg).await {
    Ok(result) => println!("Success: {}", result.content),
    Err(e) => eprintln!("Error: {}", e),
}

// Or use ?
async fn handle(agent: &impl Agent, msg: Message) -> Result<Message, AgentError> {
    let result = agent.process(msg).await?;
    Ok(result)
}
```

### Go
```go
// (result, error) tuple
result, err := agent.Process(ctx, msg)
if err != nil {
    log.Printf("Error: %v", err)
    return nil, fmt.Errorf("process failed: %w", err)
}
// Use result
```

**Changes**:
- `Result<T, E>` → `(T, error)` tuple unpacking
- `match` / `?` operator → `if err != nil` checks
- `.await` → Not needed (goroutines handle concurrency)
- Error wrapping: `?` → `fmt.Errorf("...: %w", err)`
- No enum-based error types (use error strings or custom types)

---

## Concurrency

### Rust (tokio)
```rust
use tokio;

// Spawn async task
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

// Channels
use tokio::sync::mpsc;
let (tx, mut rx) = mpsc::channel(32);
tx.send(message).await.unwrap();
while let Some(msg) = rx.recv().await {
    // Process msg
}
```

### Go (goroutines)
```go
// Launch goroutine
go func() {
    result, err := agent.Process(ctx, msg)
    if err != nil {
        log.Printf("Error: %v", err)
        return
    }
    log.Printf("Success: %s", result.Content)
}()

// Wait for multiple with sync.WaitGroup
var wg sync.WaitGroup
for _, agent := range agents {
    wg.Add(1)
    go func(a agenkit.Agent) {
        defer wg.Done()
        _, _ = a.Process(ctx, msg)
    }(agent)
}
wg.Wait()

// Channels
results := make(chan agenkit.Message, 32)
results <- message
msg := <-results
close(results)
```

**Changes**:
- `tokio::spawn(async move {})` → `go func() {}`
- `.await` → Direct execution (goroutines are implicit)
- `tokio::join!` → `sync.WaitGroup` or channel collection
- `tokio::select!` → `select` statement
- `mpsc::channel` → `make(chan T, capacity)`
- `tx.send().await` → `ch <- value` (synchronous)
- `rx.recv().await` → `<-ch` (blocking)
- `Send + Sync` traits → Not needed (Go runtime handles safety)

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

**Go**:
```go
import "github.com/agenkit/agenkit-go/patterns"

sequential := patterns.NewSequential([]agenkit.Agent{
    agent1,
    agent2,
    agent3,
})

result, err := sequential.Process(ctx, msg)
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

**Go**:
```go
import "github.com/agenkit/agenkit-go/patterns"

parallel := patterns.NewParallel([]agenkit.Agent{
    agent_a,
    agent_b,
    agent_c,
})

result, err := parallel.Process(ctx, msg)
```

**Changes**:
- `Box::new()` → Not needed (interfaces handle polymorphism)
- `.await?` → Synchronous call + error check
- `vec![]` → slice literal `[]T{}`

---

## Common Gotchas

### 1. Ownership vs Garbage Collection

**Rust**: Explicit lifetimes prevent memory bugs at compile time
```rust
// Ownership transfer - msg moved
let msg2 = msg;  // msg is now invalid

// Borrowing - temporary access
fn process_msg(msg: &Message) {
    // msg borrowed here
}
```

**Go**: Garbage collection handles memory automatically
```go
// No ownership - GC tracks references
msg2 := msg  // msg still valid, GC tracks both

// Pass by value (copies) or pointer
func processMsg(msg Message) {
    // msg is a copy
}

func processMsgPtr(msg *Message) {
    // msg is a pointer (shared)
}
```

**Migration tip**: Remove all lifetime annotations and borrow checker thinking. Go's GC means you can share freely.

### 2. Result<T,E> vs (result, error)

**Rust**: Type-safe error handling
```rust
// Must handle Result
let result = match operation() {
    Ok(val) => val,
    Err(e) => return Err(e),
};

// Or use ?
let result = operation()?;
```

**Go**: Convention-based error handling
```go
// Must check error by convention
result, err := operation()
if err != nil {
    return nil, err
}
// Use result
```

**Migration tip**: Replace all `?` operators with `if err != nil` checks. Replace `Result<T,E>` return types with `(T, error)`.

### 3. Zero-Cost Abstractions vs Runtime

**Rust**: Abstractions compile away
```rust
// No runtime cost
let iter = vec.iter()
    .filter(|x| x > &5)
    .map(|x| x * 2)
    .collect();
```

**Go**: Some runtime overhead
```go
// Manual loops often clearer/faster
result := make([]int, 0, len(vec))
for _, x := range vec {
    if x > 5 {
        result = append(result, x*2)
    }
}
```

**Migration tip**: Go values simplicity over zero-cost. Write clear loops instead of iterator chains.

### 4. Trait Bounds vs Interface Satisfaction

**Rust**: Explicit trait bounds
```rust
fn process<T: Agent>(agent: &T) -> Result<Message, AgentError> {
    // T must implement Agent
}
```

**Go**: Implicit interface satisfaction
```go
func process(agent Agent) (Message, error) {
    // Any type implementing Agent works
}
```

**Migration tip**: Remove all trait bounds. If a type has the right methods, it satisfies the interface automatically.

### 5. Option<T> vs nil / Zero Values

**Rust**: Explicit optionality
```rust
let timestamp: Option<DateTime> = Some(Utc::now());
match timestamp {
    Some(t) => println!("Time: {}", t),
    None => println!("No timestamp"),
}
```

**Go**: nil for pointers, zero values otherwise
```go
var timestamp *time.Time  // nil means no value
if timestamp != nil {
    fmt.Printf("Time: %v", *timestamp)
} else {
    fmt.Println("No timestamp")
}

// Or use zero value
var count int  // 0 by default
```

**Migration tip**: Replace `Option<T>` with pointer `*T` (for reference types) or use zero values as "no value" signal.

---

## Testing

### Rust
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_process() {
        let agent = MyAgent::new("test");
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
        let agent = MyAgent::new("test");
        let invalid_msg = Message::default();

        let result = agent.process(invalid_msg).await;

        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AgentError::InvalidMessage(_)));
    }
}
```

### Go
```go
import (
    "context"
    "testing"
)

func TestAgentProcess(t *testing.T) {
    agent := NewMyAgent("test")
    msg := agenkit.Message{
        Role:    agenkit.RoleUser,
        Content: "Test",
    }

    result, err := agent.Process(context.Background(), msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if result.Role != agenkit.RoleAssistant {
        t.Errorf("got role %v, want %v", result.Role, agenkit.RoleAssistant)
    }

    if !strings.Contains(result.Content, "Processed") {
        t.Errorf("content %q does not contain 'Processed'", result.Content)
    }
}

func TestAgentError(t *testing.T) {
    agent := NewMyAgent("test")
    invalid := agenkit.Message{}

    _, err := agent.Process(context.Background(), invalid)
    if err == nil {
        t.Fatal("expected error, got nil")
    }
}
```

**Changes**:
- `#[tokio::test]` → `func TestXxx(t *testing.T)`
- `mod tests` → Individual test functions
- `.await.unwrap()` → Explicit error check with `if err != nil`
- `assert_eq!` → `if got != want { t.Errorf() }`
- `assert!` / `matches!` → Manual error type checks
- No async/await in tests (goroutines handle concurrency)

---

## Performance Considerations

| Operation | Rust | Go | Notes |
|-----------|------|-----|-------|
| Agent creation | ~50ns | ~100ns | Go 2x slower (GC overhead) |
| Message processing | ~500ns | ~1μs | Go 2x slower (GC allocation) |
| Sequential (3 agents) | ~1.5μs | ~3μs | Consistent 2x overhead |
| Parallel (3 agents) | ~500ns | ~1μs | Goroutine spawn ~2x tokio |
| Memory footprint | Minimal | Moderate | GC heap overhead |

**When to migrate to Go**:
- Simpler deployment needs (less focus on absolute performance)
- Faster iteration cycles (no fighting borrow checker)
- Easier onboarding (simpler language, no lifetimes)
- Built-in concurrency patterns (goroutines vs tokio complexity)
- More mature tooling (go fmt, go test, go mod)
- Better reflection/metaprogramming support

**When to keep Rust**:
- Memory-constrained environments (embedded, edge)
- Safety-critical applications (no GC pauses)
- WASM targets (smaller binaries, no runtime)
- Maximum performance requirements
- Zero-cost abstractions needed
- Compile-time guarantees essential

---

## Memory Model Comparison

### Rust Ownership
```rust
// Ownership rules enforced at compile time
let s1 = String::from("hello");
let s2 = s1;  // s1 moved, no longer valid

// Borrowing
fn takes_ref(s: &String) {
    println!("{}", s);
}  // s borrowed, not moved

let s3 = String::from("world");
takes_ref(&s3);  // s3 still valid

// Mutable borrowing (exclusive)
fn takes_mut(s: &mut String) {
    s.push_str(" world");
}
```

### Go Garbage Collection
```go
// No ownership concept - GC tracks everything
s1 := "hello"
s2 := s1  // Both valid, GC tracks references

// Passing by value (copy)
func takesCopy(s string) {
    fmt.Println(s)
}

s3 := "world"
takesCopy(s3)  // s3 copied, both valid

// Passing by pointer (reference)
func takesPtr(s *string) {
    *s = *s + " world"
}
```

**Key Difference**: Rust prevents data races at compile time via ownership. Go prevents data races at runtime via GC and mutex locking.

---

## Async/Await Comparison

### Rust (tokio)
```rust
// Explicit async runtime
#[tokio::main]
async fn main() {
    let task1 = tokio::spawn(async {
        process_one().await
    });

    let task2 = tokio::spawn(async {
        process_two().await
    });

    let (res1, res2) = tokio::join!(task1, task2);
}

// Channels are async
use tokio::sync::mpsc;
let (tx, mut rx) = mpsc::channel(10);
tx.send(msg).await?;  // Async send
let msg = rx.recv().await;  // Async receive
```

### Go (goroutines)
```go
// No explicit runtime - goroutines built-in
func main() {
    var wg sync.WaitGroup

    wg.Add(1)
    go func() {
        defer wg.Done()
        processOne()  // No .await
    }()

    wg.Add(1)
    go func() {
        defer wg.Done()
        processTwo()  // No .await
    }()

    wg.Wait()
}

// Channels are synchronous
ch := make(chan Message, 10)
ch <- msg  // Blocks if full
msg := <-ch  // Blocks if empty
```

**Key Difference**: Rust async is explicit (`.await` at every step). Go concurrency is implicit (goroutines just run).

---

## Migration Checklist

- [ ] Remove all lifetime annotations (`'a`, `'static`)
- [ ] Replace `Result<T, E>` with `(T, error)` returns
- [ ] Replace `?` operator with `if err != nil` checks
- [ ] Remove `#[async_trait]` and `.await` calls
- [ ] Add `context.Context` parameter to all agent methods
- [ ] Replace `Box<dyn Trait>` with interface values
- [ ] Replace `Arc<T>` / `Rc<T>` with regular types (GC handles sharing)
- [ ] Replace `tokio::spawn` with `go func()`
- [ ] Replace `tokio::join!` with `sync.WaitGroup`
- [ ] Replace `.clone()` calls (often not needed with GC)
- [ ] Update imports: `agenkit` → `agenkit-go`
- [ ] Convert tests: `#[tokio::test]` → `func TestXxx(t *testing.T)`
- [ ] Replace `Vec<T>` with `[]T` slices
- [ ] Replace `HashMap<K,V>` with `map[K]V`
- [ ] Replace `Option<T>` with `*T` or zero values

---

## Quick Start

```bash
# Rust project structure
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── main.rs
│   └── agent.rs
└── tests/

# Go equivalent
agenkit-go/
├── go.mod
├── main.go
├── agent.go
└── agent_test.go
```

**Build/Run**:
```bash
# Rust
cargo build --release
./target/release/myagent

# Go
go build -o myagent
./myagent
```

**Dependency Management**:
```bash
# Rust
cargo add agenkit

# Go
go get github.com/agenkit/agenkit-go
```

---

## Full Resources

- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms guide
- [Go Language Profile](LANGUAGE_PROFILE_GO.md) - Complete Go idioms guide
- [Go → Rust Migration](MIGRATE_GO_TO_RUST.md) - Reverse direction guide
- [Agenkit Examples](../examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
