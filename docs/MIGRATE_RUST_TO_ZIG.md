# Quick Reference: Rust → Zig Migration

**For**: Rust developers migrating Agenkit code to Zig
**Time**: 15 minute read
**Full Details**: See [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) and [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md)

---

## Key Differences at a Glance

| Aspect | Rust | Zig |
|--------|------|-----|
| **Memory Safety** | Borrow checker (compile-time) | Manual tracking with defer/errdefer |
| **Errors** | `Result<T, E>` | Error unions `!Type` |
| **Concurrency** | async/await (tokio) | std.Thread (OS threads) |
| **Memory** | Ownership system | Explicit allocators |
| **Performance** | Zero-cost abstractions | Zero-cost, explicit control |
| **Deployment** | Single binary | Single binary (no runtime) |

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

### Zig
```zig
const agenkit = @import("agenkit");
const std = @import("std");

pub fn createMessage(allocator: std.mem.Allocator) !agenkit.Message {
    const content = try allocator.dupe(u8, "Hello!");
    errdefer allocator.free(content);

    var msg = agenkit.Message{
        .role = "user",
        .content = content,
        .metadata = null,
        .timestamp = null,
    };

    return msg;
}

// Caller responsible for cleanup
const msg = try createMessage(allocator);
defer allocator.free(msg.content);
```

**Changes**:
- Import: `use agenkit` → `const agenkit = @import("agenkit")`
- Types: `String` → `[]const u8` or `[]u8` (slices)
- Struct init: `..Default::default()` → explicit field initialization
- Memory: Automatic (ownership) → Manual (allocator + defer)
- Cleanup: RAII (automatic Drop) → Explicit `defer`

---

## Agent Implementation

### Rust
```rust
use async_trait::async_trait;
use agenkit::{Agent, Message, AgentError};

struct MyAgent {
    name: String,
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

### Zig
```zig
const std = @import("std");
const agenkit = @import("agenkit");

const MyAgent = struct {
    allocator: std.mem.Allocator,
    name_str: []const u8,

    pub fn init(allocator: std.mem.Allocator, name: []const u8) !MyAgent {
        return MyAgent{
            .allocator = allocator,
            .name_str = name,
        };
    }

    pub fn deinit(self: *MyAgent) void {
        // Cleanup if needed
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
        errdefer self.allocator.free(content);

        return agenkit.Message{
            .role = "assistant",
            .content = content,
        };
    }
};
```

**Changes**:
- Traits → Function pointers (vtable pattern) or direct struct methods
- `#[async_trait]` → Removed (no async/await in current Zig)
- `&self` → `self: *const MyAgent` (explicit pointer types)
- `Result<T, E>` → `!Type` (error union)
- `format!()` → `std.fmt.allocPrint()`
- Automatic cleanup → `deinit()` + `defer`

---

## Error Handling

### Rust
```rust
// Function returns Result
fn process_message(agent: &impl Agent, msg: Message) -> Result<Message, AgentError> {
    let validated = validate_message(&msg)?;
    let response = agent.process(validated)?;
    Ok(response)
}

// Pattern matching
match process_message(&agent, msg) {
    Ok(response) => println!("Success: {}", response.content),
    Err(e) => eprintln!("Error: {}", e),
}
```

### Zig
```zig
// Function returns error union
fn processMessage(agent: *Agent, msg: Message) !Message {
    const validated = try validateMessage(msg);
    const response = try agent.process(validated);
    return response;
}

// Catch and handle
const result = processMessage(&agent, msg) catch |err| {
    switch (err) {
        error.InvalidMessage => {
            std.debug.print("Invalid message\n", .{});
            return error.InvalidMessage;
        },
        else => return err,
    }
};

// Or use if
if (processMessage(&agent, msg)) |success| {
    std.debug.print("Success: {s}\n", .{success.content});
} else |err| {
    std.debug.print("Error: {}\n", .{err});
}
```

**Changes**:
- `Result<T, E>` → `!Type` (error union syntax)
- `?` operator → `try` keyword
- `match` → `catch |err|` or `if ... else |err|`
- `Ok(value)` → `return value`
- `Err(e)` → `return error.ErrorName`

---

## Concurrency

### Rust (async/await + tokio)
```rust
use tokio;

// Async function
async fn fetch_data() -> Result<String, Error> {
    tokio::time::sleep(Duration::from_secs(1)).await;
    Ok("data".to_string())
}

// Spawn task
#[tokio::main]
async fn main() {
    let handle = tokio::spawn(async move {
        let result = agent.process(msg).await;
        println!("{:?}", result);
    });

    handle.await.unwrap();
}

// Join multiple
let (res1, res2, res3) = tokio::join!(
    agent1.process(msg.clone()),
    agent2.process(msg.clone()),
    agent3.process(msg.clone())
);
```

### Zig (OS threads)
```zig
const std = @import("std");

// Worker function (no async)
fn fetchData(allocator: std.mem.Allocator) ![]const u8 {
    std.time.sleep(1 * std.time.ns_per_s);
    return try allocator.dupe(u8, "data");
}

// Spawn thread
pub fn main() !void {
    const handle = try std.Thread.spawn(.{}, workerFunction, .{allocator, agent, msg});
    handle.join();  // Wait for completion
}

fn workerFunction(allocator: std.mem.Allocator, agent: *Agent, msg: Message) void {
    const result = agent.process(msg) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };
    defer allocator.free(result.content);

    std.debug.print("Result: {s}\n", .{result.content});
}

// Multiple threads (manual join)
var handles: [3]std.Thread = undefined;
handles[0] = try std.Thread.spawn(.{}, processAgent, .{agent1, msg});
handles[1] = try std.Thread.spawn(.{}, processAgent, .{agent2, msg});
handles[2] = try std.Thread.spawn(.{}, processAgent, .{agent3, msg});

for (handles) |handle| {
    handle.join();
}
```

**Changes**:
- `async fn` → regular `fn` (no async keyword)
- `.await` → Removed (blocking calls)
- `tokio::spawn()` → `std.Thread.spawn()`
- `handle.await` → `handle.join()`
- `tokio::join!()` → Manual thread join loop
- Tokio runtime → OS threads (no runtime)

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

**Zig**:
```zig
const patterns = @import("agenkit").patterns;

var parallel = try patterns.Parallel.init(allocator, &[_]Agent{
    agent_a,
    agent_b,
    agent_c,
});
defer parallel.deinit();

const result = try parallel.process(msg);
defer allocator.free(result.content);
```

**Changes**:
- `Box::new()` → Direct value or pointer (no box needed)
- `vec![]` → Array literal `&[_]Type{}`
- `.await?` → `try` (no async)
- Automatic cleanup → Explicit `defer deinit()`

---

## Common Gotchas

### 1. Ownership vs Explicit Allocators

**Rust**: Borrow checker tracks ownership automatically
```rust
fn process(msg: Message) -> Message {
    // msg moved into function
    // Automatically dropped at end
    msg
}
```

**Zig**: Must track allocations manually
```zig
fn process(allocator: std.mem.Allocator, msg: Message) !Message {
    // Must know who owns msg.content
    // Must free explicitly or use defer
    defer allocator.free(msg.content);

    const new_content = try allocator.dupe(u8, "new");
    errdefer allocator.free(new_content);

    return Message{
        .role = "assistant",
        .content = new_content,
    };
}
```

**Solution**: Pass allocator everywhere, use defer/errdefer consistently.

### 2. Result<T, E> vs Error Unions

**Rust**: Named error types in Result
```rust
enum AgentError {
    Timeout(u64),
    InvalidMessage(String),
}

fn process() -> Result<Message, AgentError> {
    Err(AgentError::Timeout(30))
}
```

**Zig**: Error sets (compile-time known)
```zig
const AgentError = error{
    Timeout,
    InvalidMessage,
};

fn process() AgentError!Message {
    return error.Timeout;  // No payload
}

// To carry data, return tuple
fn processWithData() !struct { Message, ?u64 } {
    return .{ message, 30 };  // Timeout value
}
```

**Solution**: Use error sets for types, return tuples or structs for error data.

### 3. Async/Await vs Blocking Threads

**Rust**: Cooperative multitasking
```rust
// Many tasks on few threads
for _ in 0..10000 {
    tokio::spawn(async { /* work */ });
}
// Tokio runtime handles scheduling
```

**Zig**: OS threads (heavier)
```zig
// Each thread is OS thread
var handles: [100]std.Thread = undefined;  // Reasonable limit
for (handles) |*handle| {
    handle.* = try std.Thread.spawn(.{}, work, .{});
}
for (handles) |handle| {
    handle.join();
}
```

**Solution**: Use thread pools or implement event loop for many concurrent operations.

### 4. String Types

**Rust**: `String` (owned) vs `&str` (borrowed)
```rust
let owned: String = "hello".to_string();
let borrowed: &str = "hello";
```

**Zig**: `[]u8` (mutable) vs `[]const u8` (immutable)
```zig
const owned: []u8 = try allocator.dupe(u8, "hello");
defer allocator.free(owned);

const borrowed: []const u8 = "hello";  // Compile-time constant
```

**Solution**: Use `[]const u8` for strings, track ownership manually.

### 5. RAII vs Defer

**Rust**: Automatic cleanup (Drop trait)
```rust
{
    let file = File::open("data.txt")?;
    // Use file
    // Automatically closed at end of scope
}
```

**Zig**: Explicit defer
```zig
{
    const file = try std.fs.cwd().openFile("data.txt", .{});
    defer file.close();  // MUST remember this

    // Use file
}
```

**Solution**: Always write `defer` immediately after acquiring resource.

---

## Testing

### Rust
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_process() {
        let agent = MyAgent { name: "test".to_string() };
        let msg = Message {
            role: Role::User,
            content: "Test".to_string(),
            ..Default::default()
        };

        let result = agent.process(msg).await.unwrap();

        assert_eq!(result.role, Role::Assistant);
        assert!(result.content.contains("Processed"));
    }
}
```

### Zig
```zig
const std = @import("std");
const testing = std.testing;

test "agent processes message" {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var agent = try MyAgent.init(allocator, "test");
    defer agent.deinit();

    const msg = Message{
        .role = "user",
        .content = "Test",
    };

    const result = try agent.process(msg);
    defer allocator.free(result.content);

    try testing.expectEqualStrings("assistant", result.role);
    try testing.expect(std.mem.indexOf(u8, result.content, "Processed") != null);
}
```

**Changes**:
- `#[cfg(test)] mod tests` → `test "name"` blocks
- `#[tokio::test]` → Regular `test` (no async)
- `assert_eq!` → `try testing.expectEqual()`
- `assert!` → `try testing.expect()`
- `.unwrap()` → `try` (tests fail on error)
- Memory setup → GeneralPurposeAllocator + defer deinit

---

## Performance Considerations

| Operation | Rust | Zig | Notes |
|-----------|------|-----|-------|
| Message creation | ~50ns | ~50ns | Comparable |
| Agent processing | ~500ns | ~500ns | Comparable |
| Sequential (3 agents) | ~1.5μs | ~1.5μs | Both zero-cost |
| Parallel (3 agents) | ~500ns | ~5μs | Zig uses OS threads |
| Async task spawn | ~100ns | ~10μs | Zig thread spawn heavier |

**When to use Zig**:
- Embedded systems (no runtime requirement)
- Simpler concurrency model (blocking is acceptable)
- Maximum control over memory layout
- Interfacing with C libraries (no FFI friction)
- Smaller binary size critical

**When to keep Rust**:
- Need async/await ecosystem (tokio, async-std)
- Many concurrent operations (10,000+ tasks)
- Borrow checker safety guarantees important
- Large async library ecosystem
- WASM compilation target

---

## Memory Management Deep Dive

### Rust Ownership Rules
```rust
// Rule 1: Each value has one owner
let msg = Message::new();  // msg owns the Message

// Rule 2: Can borrow immutably many times
let ref1 = &msg;
let ref2 = &msg;

// Rule 3: OR borrow mutably once (exclusive)
let ref_mut = &mut msg;

// Rule 4: Compiler enforces these at compile time
```

### Zig Manual Tracking
```zig
// Must track ownership manually
var msg = try createMessage(allocator);  // We own this

// Pass pointer (like borrow)
const result = processMessage(&msg);

// Must free when done
defer allocator.free(msg.content);

// Allocator tracks allocations (debug mode)
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
const allocator = gpa.allocator();
// ... use allocator ...
const leaked = gpa.deinit();  // Returns true if leaks detected
```

### Arena Pattern (Common in Zig)
```zig
pub fn processMany(allocator: std.mem.Allocator, messages: []Message) !void {
    // Arena for temporary allocations
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();  // Free everything at once
    const temp_allocator = arena.allocator();

    for (messages) |msg| {
        // All temp allocations use arena
        const processed = try processMessage(temp_allocator, msg);
        // No need to free individually

        // Store results using parent allocator if needed
        const saved = try allocator.dupe(u8, processed.content);
        _ = saved;  // Now owned by caller
    }
    // arena.deinit() frees all temp allocations
}
```

---

## Migration Checklist

- [ ] Replace `Result<T, E>` with error unions `!Type`
- [ ] Convert `async fn` to regular `fn` (remove async/await)
- [ ] Add `std.mem.Allocator` parameter to all allocating functions
- [ ] Replace `?` operator with `try` keyword
- [ ] Add `defer` for cleanup after resource acquisition
- [ ] Use `errdefer` for cleanup on error paths
- [ ] Convert `String` to `[]const u8` or `[]u8`
- [ ] Replace `Vec<T>` with slices `[]T` or `std.ArrayList(T)`
- [ ] Replace `HashMap` with `std.StringHashMap` or `std.AutoHashMap`
- [ ] Convert `tokio::spawn()` to `std.Thread.spawn()`
- [ ] Replace `match` with `catch |err|` or `if ... else |err|`
- [ ] Update tests: `#[test]` → `test "name"`
- [ ] Remove trait implementations, use direct methods or vtables
- [ ] Handle cleanup: RAII → explicit `deinit()` + `defer`
- [ ] Update imports: `use` → `const x = @import()`

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

# Zig equivalent
agenkit-zig/
├── build.zig
├── src/
│   ├── main.zig
│   └── agent.zig
└── tests/
```

**Build/Run**:
```bash
# Rust
cargo build --release
cargo run

# Zig
zig build -Doptimize=ReleaseFast
zig build run
```

**Testing**:
```bash
# Rust
cargo test

# Zig
zig build test
```

---

## Idiom Translation Table

| Rust | Zig | Notes |
|------|-----|-------|
| `String` | `[]const u8` or `[]u8` | Slices instead of owned strings |
| `Vec<T>` | `std.ArrayList(T)` | Dynamic array with allocator |
| `&str` | `[]const u8` | String slice |
| `Option<T>` | `?T` | Optional type (similar) |
| `Result<T, E>` | `!Type` | Error union |
| `impl Trait` | `comptime` or vtable | Different approaches |
| `Box<T>` | Allocator + pointer | Manual allocation |
| `Rc<T>` | Manual refcount | No stdlib helper |
| `Arc<T>` | Manual refcount + Mutex | No stdlib helper |
| `.await` | Removed | Blocking calls |
| `async fn` | `fn` | No async keyword |
| `?` operator | `try` | Error propagation |
| `Ok(v)` | `return v` | Direct return |
| `Err(e)` | `return error.Name` | Error return |
| `match` | `switch` or `if/catch` | Similar but different syntax |

---

## Full Resources

- [Rust Language Profile](LANGUAGE_PROFILE_RUST.md) - Complete Rust idioms guide
- [Zig Language Profile](LANGUAGE_PROFILE_ZIG.md) - Complete Zig idioms guide
- [Agenkit Rust Examples](../agenkit-rust/examples/) - Rust code samples
- [Agenkit Zig Examples](../agenkit-zig/examples/) - Zig code samples
- [Zig Learn](https://ziglearn.org/) - Comprehensive Zig tutorial
- [Zig Language Reference](https://ziglang.org/documentation/master/) - Official docs

---

**Quick Reference Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
