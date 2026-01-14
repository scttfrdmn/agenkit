# Quick Reference: Zig → Rust Migration

**For**: Zig developers migrating Agenkit code to Rust
**Time**: 15 minute read
**Full Details**: See [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) and [Rust Language Profile](LANGUAGE_PROFILE_RUST.md)

---

## Key Differences at a Glance

| Aspect | Zig | Rust |
|--------|-----|------|
| **Memory** | Manual + explicit allocators | Ownership + borrow checker |
| **Cleanup** | defer/errdefer | RAII + Drop trait |
| **Errors** | Error unions `!Type` | `Result<T, E>` |
| **Concurrency** | std.Thread (OS threads) | async/await (tokio) |
| **Optionals** | `?T` | `Option<T>` |
| **Polymorphism** | comptime generics | Traits + generics |
| **Performance** | Zero-cost, no GC | Zero-cost, no GC |
| **Compilation** | Fast (~2-5s) | Slower (~10-30s) |

**Why Migrate**:
- **Async ecosystem**: Mature tokio runtime vs manual event loops
- **Memory safety**: Compile-time guarantees vs manual tracking
- **Ecosystem**: Larger crate ecosystem (crates.io)
- **Type system**: Borrow checker prevents entire classes of bugs
- **Tooling**: cargo, clippy, rustfmt are mature

---

## Message Creation

### Zig
```zig
const agenkit = @import("agenkit");

var msg = agenkit.Message{
    .role = "user",
    .content = "Hello!",
    .metadata = null,
    .timestamp = null,
};

// With allocator (owned strings)
pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello!");
    errdefer allocator.free(content);

    return agenkit.Message{
        .role = "user",
        .content = content,
    };
}

// Cleanup required
defer allocator.free(msg.content);
```

### Rust
```rust
use agenkit::{Message, Role};

let msg = Message {
    role: Role::User,
    content: "Hello!".to_string(),
    metadata: HashMap::new(),
    timestamp: None,
};

// Or with builder pattern
let msg = Message::builder()
    .role(Role::User)
    .content("Hello!")
    .build();

// No manual cleanup - automatic Drop
```

**Changes**:
- Explicit allocators → Automatic memory management (ownership)
- `errdefer` cleanup → RAII (Drop trait)
- String literals → `.to_string()` for owned strings
- `null` → `None` for optional fields
- Manual `defer` → Automatic cleanup on scope exit

---

## Agent Implementation

### Zig
```zig
const Agent = @import("agenkit").Agent;

const MyAgent = struct {
    allocator: std.mem.Allocator,
    name_str: []const u8,

    pub fn init(allocator: std.mem.Allocator) !MyAgent {
        return MyAgent{
            .allocator = allocator,
            .name_str = "my-agent",
        };
    }

    pub fn deinit(self: *MyAgent) void {
        // Manual cleanup
    }

    pub fn name(self: *const MyAgent) []const u8 {
        return self.name_str;
    }

    pub fn capabilities(self: *const MyAgent) []const []const u8 {
        const caps = &[_][]const u8{ "text", "analysis" };
        return caps;
    }

    pub fn process(self: *MyAgent, msg: agenkit.Message) !agenkit.Message {
        const content = try std.fmt.allocPrint(
            self.allocator,
            "Processed: {s}",
            .{msg.content}
        );

        return agenkit.Message{
            .role = "assistant",
            .content = content,
        };
    }
};
```

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, Role, AgentError};

struct MyAgent {
    name: String,
}

impl MyAgent {
    pub fn new(name: String) -> Self {
        Self { name }
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

// Drop trait automatically cleans up (no manual deinit)
```

**Changes**:
- Struct methods → Trait implementation
- Explicit allocator parameter → Removed (ownership handles it)
- `init`/`deinit` → `new()` + automatic Drop
- `!Type` error unions → `Result<T, E>`
- Sync functions → `async fn` with tokio
- Manual memory tracking → Borrow checker

---

## Error Handling

### Zig
```zig
const AgentError = error{
    InvalidMessage,
    ProcessingFailed,
    Timeout,
};

// Function returns error union
fn processMessage(allocator: std.mem.Allocator, msg: Message) AgentError!Message {
    if (msg.content.len == 0) {
        return error.InvalidMessage;
    }

    // Propagate with try
    const result = try validateMessage(msg);
    return result;
}

// Handle errors
const result = processMessage(allocator, msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// Or with if
if (processMessage(allocator, msg)) |success| {
    // Use success
} else |err| {
    // Handle error
}
```

### Rust
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AgentError {
    #[error("Invalid message: {0}")]
    InvalidMessage(String),

    #[error("Processing failed: {0}")]
    ProcessingFailed(String),

    #[error("Timeout after {0}s")]
    Timeout(u64),
}

// Function returns Result
fn process_message(msg: Message) -> Result<Message, AgentError> {
    if msg.content.is_empty() {
        return Err(AgentError::InvalidMessage("empty content".into()));
    }

    // Propagate with ?
    let result = validate_message(&msg)?;
    Ok(result)
}

// Handle errors
match process_message(msg) {
    Ok(result) => {
        // Use result
    }
    Err(AgentError::InvalidMessage(msg)) => {
        eprintln!("Invalid: {}", msg);
    }
    Err(e) => return Err(e),
}

// Or propagate with ?
let result = process_message(msg)?;
```

**Changes**:
- Error unions `!Type` → `Result<T, E>`
- `try` keyword → `?` operator
- `catch |err|` → `match` or `.unwrap()`
- `return error.Name` → `Err(EnumVariant)`
- `if (x) |success| else |err|` → `match x { Ok(v) => ..., Err(e) => ... }`
- Error sets → Enum with `thiserror` derive

---

## Concurrency

### Zig (Manual OS Threads)
```zig
const std = @import("std");

// Spawn thread
const handle = try std.Thread.spawn(.{}, workerFunction, .{allocator, msg});
handle.join();  // Wait for completion

fn workerFunction(allocator: std.mem.Allocator, msg: Message) void {
    const result = processMessage(allocator, msg) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
    // Use result
}

// Multiple threads (manual)
var threads: [3]std.Thread = undefined;
for (agents) |agent, i| {
    threads[i] = try std.Thread.spawn(.{}, processAgent, .{agent, msg});
}
for (threads) |thread| {
    thread.join();
}

// Mutex for synchronization
var mutex = std.Thread.Mutex{};
fn safeIncrement(counter: *usize) void {
    mutex.lock();
    defer mutex.unlock();
    counter.* += 1;
}
```

### Rust (Async/Await with Tokio)
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
let results = tokio::join!(
    agent1.process(msg.clone()),
    agent2.process(msg.clone()),
    agent3.process(msg.clone())
);

// Or gather dynamic list
use futures::future::join_all;
let futures: Vec<_> = agents.iter()
    .map(|a| a.process(msg.clone()))
    .collect();
let results = join_all(futures).await;

// Arc + Mutex for shared state
use std::sync::Arc;
use tokio::sync::Mutex;

let counter = Arc::new(Mutex::new(0));
let counter_clone = Arc::clone(&counter);

tokio::spawn(async move {
    let mut num = counter_clone.lock().await;
    *num += 1;
});
```

**Changes**:
- `std.Thread.spawn()` → `tokio::spawn()`
- OS threads → Green threads (lightweight tasks)
- Blocking `join()` → `await` (non-blocking)
- Manual thread management → Tokio runtime handles it
- `std.Thread.Mutex` → `tokio::sync::Mutex` (async-aware)
- No built-in channels → `tokio::sync::mpsc` channels
- Explicit function signature → `async fn` returns `Future`

---

## Memory Management

### Zig (Explicit Allocators)
```zig
// Pass allocator everywhere
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();

// Allocate
const buffer = try allocator.alloc(u8, 1024);
defer allocator.free(buffer);  // Manual cleanup

// Arena for bulk free
var arena = std.heap.ArenaAllocator.init(allocator);
defer arena.deinit();  // Frees everything
const temp_allocator = arena.allocator();

// errdefer for error paths
const data = try allocator.alloc(u8, 1024);
errdefer allocator.free(data);  // Only if error

// Manual tracking
const msg = try createMessage(allocator);
defer allocator.free(msg.content);
```

### Rust (Ownership + Borrow Checker)
```rust
// Automatic allocation (heap or stack)
let buffer = vec![0u8; 1024];
// Automatic cleanup when buffer goes out of scope

// Ownership transfer
let msg = Message::new("Hello");
let msg2 = msg;  // msg is moved, msg2 owns it now
// msg is invalid here

// Borrowing (no ownership transfer)
fn print_message(msg: &Message) {  // Immutable borrow
    println!("{}", msg.content);
}

// Mutable borrowing
fn modify_message(msg: &mut Message) {  // Mutable borrow
    msg.content = "Modified".to_string();
}

// RAII - automatic cleanup
{
    let file = File::open("data.txt")?;
    // Use file
}  // file.close() called automatically (Drop trait)

// No manual tracking needed
let msg = Message::new("Hello");
// msg.content freed automatically at end of scope
```

**Changes**:
- Explicit allocators → Ownership system (no allocator parameter)
- `defer`/`errdefer` → RAII (Drop trait)
- Manual `alloc`/`free` → Automatic via ownership
- Arena allocator → Not needed (borrow checker handles lifetimes)
- Developer tracks memory → Compiler enforces safety
- Runtime leak detection → Compile-time prevention

---

## Patterns

### Sequential

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var sequential = try patterns.Sequential.init(allocator, &[_]Agent{
    agent1,
    agent2,
    agent3,
});
defer sequential.deinit();

const result = try sequential.process(msg);
defer allocator.free(result.content);
```

**Rust**:
```rust
use agenkit::patterns::Sequential;

let sequential = Sequential::new(vec![
    Box::new(agent1),
    Box::new(agent2),
    Box::new(agent3),
]);

let result = sequential.process(msg).await?;
// Automatic cleanup
```

### Parallel

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var parallel = try patterns.Parallel.init(allocator, &[_]Agent{
    agent_a,
    agent_b,
    agent_c,
});
defer parallel.deinit();

// Manual thread coordination
const result = try parallel.process(msg);
defer allocator.free(result.content);
```

**Rust**:
```rust
use agenkit::patterns::Parallel;

let parallel = Parallel::new(vec![
    Box::new(agent_a),
    Box::new(agent_b),
    Box::new(agent_c),
]);

// Tokio handles concurrency
let result = parallel.process(msg).await?;
```

---

## Common Gotchas

### 1. Allocator Parameter Everywhere

**Zig**: Explicit allocator in every function
```zig
fn createAgent(allocator: std.mem.Allocator, name: []const u8) !Agent {
    const owned_name = try allocator.dupe(u8, name);
    errdefer allocator.free(owned_name);
    // ...
}
```

**Rust**: No allocator parameter (ownership handles it)
```rust
fn create_agent(name: String) -> Agent {
    Agent { name }  // name ownership transferred
}
```

**Migration**: Remove all allocator parameters and let Rust's ownership system handle memory.

### 2. defer vs Drop

**Zig**: Explicit cleanup with defer
```zig
const file = try std.fs.cwd().openFile("data.txt", .{});
defer file.close();

const buffer = try allocator.alloc(u8, 1024);
defer allocator.free(buffer);
```

**Rust**: Automatic cleanup via Drop trait
```rust
let file = File::open("data.txt")?;
// file.close() called automatically

let buffer = vec![0u8; 1024];
// buffer freed automatically
```

**Migration**: Remove all `defer` statements. Implement `Drop` trait only for custom resource types.

### 3. Error Unions vs Result

**Zig**: Error union with `try` keyword
```zig
const result = try riskyOperation();  // Returns error or value
```

**Rust**: Result type with `?` operator
```rust
let result = risky_operation()?;  // Returns Err or Ok
```

**Migration**: Change `!Type` to `Result<Type, Error>` and `try` to `?`.

### 4. comptime vs Traits

**Zig**: Compile-time code execution
```zig
fn process(comptime T: type, value: T) T {
    // Type-specific code generated at compile time
    return value;
}
```

**Rust**: Traits for polymorphism
```rust
fn process<T: Clone>(value: T) -> T {
    value.clone()
}
```

**Migration**: Replace `comptime` type parameters with trait bounds.

### 5. No Async in Zig

**Zig**: Manual threading
```zig
const handle = try std.Thread.spawn(.{}, worker, .{data});
handle.join();
```

**Rust**: Built-in async/await
```rust
let handle = tokio::spawn(async move {
    worker(data).await
});
handle.await?;
```

**Migration**: Convert blocking operations to `async fn` and use `.await`. Replace thread spawns with `tokio::spawn()`.

---

## Testing

### Zig
```zig
const std = @import("std");
const testing = std.testing;

test "agent processes message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const msg = Message{
        .role = "user",
        .content = "Test",
    };

    const result = try agent.process(msg);
    defer allocator.free(result.content);

    try testing.expectEqualStrings("assistant", result.role);
}

test "handles errors" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const empty_msg = Message{ .role = "user", .content = "" };
    try testing.expectError(error.InvalidMessage, agent.process(empty_msg));
}
```

### Rust
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_process() {
        let agent = MyAgent::new("test-agent".to_string());
        let msg = Message {
            role: Role::User,
            content: "Test".to_string(),
            ..Default::default()
        };

        let result = agent.process(msg).await.unwrap();

        assert_eq!(result.role, Role::Assistant);
    }

    #[tokio::test]
    async fn test_handles_errors() {
        let agent = MyAgent::new("test-agent".to_string());
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
- `test "name"` → `#[tokio::test] async fn test_name()`
- `testing.expectEqual*` → `assert_eq!()`, `assert!()`
- Manual allocator setup → Automatic (no GPA needed)
- `try` for assertions → `assert!()` panics on failure
- `defer` cleanup → Automatic Drop
- `testing.expectError` → `matches!()` macro

---

## Performance Considerations

| Operation | Zig | Rust | Notes |
|-----------|-----|------|-------|
| Agent creation | ~50ns | ~50ns | Comparable |
| Message processing | ~500ns | ~500ns | Both zero-cost |
| Sequential (3 agents) | ~1.5μs | ~1.5μs | Similar |
| Parallel (3 agents) | ~5μs (OS threads) | ~500ns (tokio) | Rust 10x faster |
| Compilation | ~2-5s | ~10-30s | Zig faster |
| Binary size | Smaller | Larger | Zig strips better |
| Memory usage | Lower (manual) | Slightly higher (LLVM) | Both efficient |

**When to use Rust**:
- Need mature async ecosystem (tokio, async-std)
- Want compile-time memory safety guarantees
- Require larger crate ecosystem (networking, serialization)
- WASM deployment (excellent support)
- Team unfamiliar with manual memory management

**When to keep Zig**:
- Embedded systems (no runtime required)
- Absolute smallest binaries
- Need fastest compilation times
- Want explicit control over every allocation
- Team comfortable with manual memory management
- Using comptime for metaprogramming

---

## Migration Checklist

- [ ] Remove all `allocator: std.mem.Allocator` parameters
- [ ] Replace `!Type` with `Result<Type, Error>`
- [ ] Change `try` to `?` operator
- [ ] Remove all `defer` and `errdefer` (rely on Drop)
- [ ] Convert structs to use ownership (`String` not `[]const u8`)
- [ ] Add `#[async_trait]` to Agent implementations
- [ ] Change sync functions to `async fn`
- [ ] Replace `std.Thread.spawn()` with `tokio::spawn()`
- [ ] Update tests: `test "name"` → `#[tokio::test] async fn`
- [ ] Replace `testing.expect*` with `assert!()` macros
- [ ] Add `#[derive(Debug, Clone)]` to types as needed
- [ ] Implement `Drop` trait only for custom resources (not basic types)
- [ ] Use `Box<dyn Agent>` for trait objects
- [ ] Add `thiserror` for error types, `anyhow` for applications

---

## Type Mapping Reference

| Zig | Rust | Notes |
|-----|------|-------|
| `[]const u8` | `&str` | String slice |
| `[]u8` | `&mut [u8]` | Mutable byte slice |
| `std.ArrayList(T)` | `Vec<T>` | Dynamic array |
| `std.StringHashMap(V)` | `HashMap<String, V>` | Hash map |
| `?T` | `Option<T>` | Optional type |
| `!T` | `Result<T, Error>` | Error union |
| `anyerror` | `anyhow::Error` | Any error type |
| `comptime T: type` | `T: Trait` | Generic constraint |
| `*T` | `&T` | Immutable reference |
| `*mut T` | `&mut T` | Mutable reference |
| `@intCast(T, x)` | `x as T` | Type cast |
| `defer x` | Drop trait | Automatic cleanup |
| `errdefer x` | `?` operator | Error propagation |

---

## Syntax Quick Reference

### Zig → Rust Common Patterns

```zig
// Zig: String formatting
const msg = try std.fmt.allocPrint(allocator, "Value: {d}", .{value});
defer allocator.free(msg);
```
```rust
// Rust: String formatting
let msg = format!("Value: {}", value);
```

```zig
// Zig: Array literal
const items = [_]u32{ 1, 2, 3 };
```
```rust
// Rust: Vec literal
let items = vec![1, 2, 3];
```

```zig
// Zig: Optional handling
if (optional_value) |value| {
    // Use value
} else {
    // Handle none
}
```
```rust
// Rust: Option handling
match optional_value {
    Some(value) => {
        // Use value
    }
    None => {
        // Handle none
    }
}
// Or: if let Some(value) = optional_value { }
```

```zig
// Zig: Loop with index
for (items) |item, i| {
    std.debug.print("{}: {}\n", .{i, item});
}
```
```rust
// Rust: Loop with index
for (i, item) in items.iter().enumerate() {
    println!("{}: {}", i, item);
}
```

---

## Quick Start

```bash
# Zig project structure
agenkit-zig/
├── build.zig
├── src/
│   ├── main.zig
│   └── agent.zig
└── zig-out/

# Rust equivalent
agenkit-rust/
├── Cargo.toml
├── src/
│   ├── main.rs
│   └── agent.rs
└── target/
```

**Build/Run**:
```bash
# Zig
zig build
./zig-out/bin/myagent

# Rust
cargo build --release
./target/release/myagent
```

**Dependencies**:
```zig
// Zig: build.zig
exe.addPackagePath("agenkit", "deps/agenkit/src/agenkit.zig");
```
```toml
# Rust: Cargo.toml
[dependencies]
agenkit = "0.46"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
thiserror = "1.0"
```

---

## Full Resources

- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust patterns guide
- [The Rust Book](https://doc.rust-lang.org/book/) - Learn Rust from scratch
- [Zig Learn](https://ziglearn.org/) - Zig reference
- [Agenkit Examples](../examples/) - Side-by-side code samples

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
