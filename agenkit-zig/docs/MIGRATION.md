# Migration Guide: Porting to Agenkit-Zig

A comprehensive guide for porting agent code from Python, Go, Rust, and C++ to Zig.

## Table of Contents

- [Overview](#overview)
- [From Python](#from-python)
- [From Go](#from-go)
- [From Rust](#from-rust)
- [From C++](#from-c)
- [Common Patterns](#common-patterns)
- [Memory Management](#memory-management)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Performance Considerations](#performance-considerations)

---

## Overview

All Agenkit implementations share the same core concepts:

- **Message** - Unit of communication with role, content, metadata
- **Agent** - Interface with name, capabilities, process methods
- **Result** - Success (Message) or Error type
- **Patterns** - Reusable agent architectures

However, each language has idioms and patterns that require translation.

### API Compatibility Matrix

| Feature | Python | Go | Rust | C++ | Zig |
|---------|--------|----|----|------|----|
| Message creation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Agent interface | ✅ | ✅ | ✅ | ✅ | ✅ |
| Patterns | ✅ | ✅ | ✅ | ✅ | ✅ |
| Async/await | ✅ | ✅ | ✅ | ✅ | 🚧 |
| JSON serialization | ✅ | ✅ | ✅ | ✅ | ✅ |
| Memory safety | ⚠️ | ⚠️ | ✅ | ❌ | ✅ |

Legend: ✅ Full support, ⚠️ Partial, ❌ No, 🚧 Planned

---

## From Python

### Key Differences

1. **Explicit memory management** - No garbage collector
2. **Static typing** - Compile-time type checking
3. **No exceptions** - Error unions instead
4. **Explicit allocators** - Pass allocator to functions
5. **Manual cleanup** - Use `defer` for cleanup

### Message Creation

**Python:**
```python
from agenkit import Message

msg = Message.with_text("user", "Hello!")
# Automatic cleanup via garbage collection
```

**Zig:**
```zig
const agenkit = @import("agenkit");

var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit();  // ← Manual cleanup required
```

**Key Changes:**
- Add `allocator` parameter
- Use enum `.user` instead of string
- Must call `deinit()`
- Use `defer` for automatic cleanup

### Creating Agents

**Python:**
```python
from agenkit import Agent

class MyAgent(Agent):
    def __init__(self):
        self.name = "my-agent"

    def process(self, message):
        # Process message
        return Message.with_text("assistant", f"Response: {message.text}")
```

**Zig:**
```zig
pub const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !*MyAgent {
        const self = try allocator.create(MyAgent);
        self.* = .{ .allocator = allocator };
        return self;
    }

    pub fn deinit(self: *MyAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *MyAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "my-agent";
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "custom";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));

        const text = try message.contentAsText();
        const response_text = try std.fmt.allocPrint(
            self.allocator,
            "Response: {s}",
            .{text},
        );
        defer self.allocator.free(response_text);

        const response = try agenkit.Message.withText(
            self.allocator,
            .assistant,
            response_text,
        );
        return agenkit.Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};
```

**Key Changes:**
- Use struct instead of class
- Implement vtable pattern for polymorphism
- Add explicit allocator field
- Add `init`/`deinit` methods
- Cast `*anyopaque` to concrete type in implementations

### Error Handling

**Python:**
```python
try:
    result = agent.process(message)
    print(f"Success: {result.text}")
except AgentError as e:
    print(f"Error: {e}")
```

**Zig:**
```zig
const result = try agent.process(message);
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    const text = try response.contentAsText();
    std.debug.print("Success: {s}\n", .{text});
} else {
    const err = result.unwrapErr();
    std.debug.print("Error: {}\n", .{err});
}
```

**Key Changes:**
- Use `try` for propagation, not `try/except`
- Check `Result` type explicitly with `isOk()`
- Use `unwrap()` to get value
- No exception throwing

### Async/Await

**Python:**
```python
import asyncio
from agenkit import AsyncAgent

class MyAsyncAgent(AsyncAgent):
    async def process(self, message):
        result = await some_async_operation()
        return Message.with_text("assistant", result)

# Usage
result = await agent.process(message)
```

**Zig:**
```zig
// Async support is planned but not yet available
// Current approach: use threads for concurrency

// Option 1: Using std.Thread
const thread = try std.Thread.spawn(.{}, processInThread, .{agent, message});
const result = thread.join();

// Option 2: Use Parallel pattern for concurrent operations
var parallel = try agenkit.patterns.parallel.ParallelAgent.init(allocator);
try parallel.addAgent(agent1.agent());
try parallel.addAgent(agent2.agent());
const results = try parallel.processAll(message);
```

**Key Changes:**
- No async/await yet (planned for future)
- Use threads or Parallel pattern for concurrency
- More explicit concurrency model

### Complete Example

**Python:**
```python
from agenkit import Message, Agent, SequentialAgent

class UppercaseAgent(Agent):
    def process(self, message):
        return Message.with_text("assistant", message.text.upper())

class ExclaimAgent(Agent):
    def process(self, message):
        return Message.with_text("assistant", message.text + "!")

# Build pipeline
pipeline = SequentialAgent()
pipeline.add_agent(UppercaseAgent())
pipeline.add_agent(ExclaimAgent())

# Process
msg = Message.with_text("user", "hello")
result = pipeline.process(msg)
print(result.text)  # "HELLO!"
```

**Zig:**
```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub const UppercaseAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !*UppercaseAgent {
        const self = try allocator.create(UppercaseAgent);
        self.* = .{ .allocator = allocator };
        return self;
    }

    pub fn deinit(self: *UppercaseAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *UppercaseAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "uppercase";
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "text-transform";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *UppercaseAgent = @ptrCast(@alignCast(ptr));

        const text = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        const upper = std.ascii.allocUpperString(self.allocator, text) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(upper);

        const response = agenkit.Message.withText(self.allocator, .assistant, upper) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        return agenkit.Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *UppercaseAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create agents
    var upper = try UppercaseAgent.init(allocator);
    defer upper.agent().deinit();

    var exclaim = try ExclaimAgent.init(allocator);
    defer exclaim.agent().deinit();

    // Build pipeline
    var pipeline = try agenkit.patterns.sequential.SequentialAgent.init(allocator);
    defer pipeline.agent().deinit();

    try pipeline.addAgent(upper.agent());
    try pipeline.addAgent(exclaim.agent());

    // Process
    var msg = try agenkit.Message.withText(allocator, .user, "hello");
    defer msg.deinit();

    const result = try pipeline.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    std.debug.print("{s}\n", .{text});  // "HELLO!"
}
```

---

## From Go

### Key Differences

1. **Explicit memory management** - No garbage collector
2. **Different error handling** - Error unions vs. `error` return
3. **No goroutines** - Threads instead (async planned)
4. **Compile-time safety** - More compile-time checks
5. **Simpler syntax** - No interfaces, use vtables

### Message Creation

**Go:**
```go
import "github.com/scttfrdmn/agenkit-go"

msg := agenkit.NewTextMessage("user", "Hello!")
defer msg.Close()
```

**Zig:**
```zig
var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit();
```

**Key Changes:**
- Add `try` for error handling
- Use enum `.user` instead of string
- Use `deinit()` instead of `Close()`

### Creating Agents

**Go:**
```go
type MyAgent struct {
    name string
}

func (a *MyAgent) Name() string {
    return a.name
}

func (a *MyAgent) Capabilities() []string {
    return []string{"custom"}
}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    text := msg.Text()
    response := agenkit.NewTextMessage("assistant", "Response: "+text)
    return response, nil
}

func (a *MyAgent) Close() error {
    return nil
}
```

**Zig:**
```zig
pub const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !*MyAgent {
        const self = try allocator.create(MyAgent);
        self.* = .{ .allocator = allocator };
        return self;
    }

    pub fn deinit(self: *MyAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *MyAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "my-agent";
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "custom";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));

        const text = try message.contentAsText();
        const response_text = try std.fmt.allocPrint(
            self.allocator,
            "Response: {s}",
            .{text},
        );
        defer self.allocator.free(response_text);

        const response = try agenkit.Message.withText(
            self.allocator,
            .assistant,
            response_text,
        );
        return agenkit.Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};
```

**Key Changes:**
- No interface{}, use vtable pattern
- No Context parameter (not needed yet)
- Return `Result` union, not `(Message, error)`
- Implement vtable functions with `*anyopaque` and casting

### Error Handling

**Go:**
```go
result, err := agent.Process(ctx, msg)
if err != nil {
    log.Printf("Error: %v", err)
    return err
}
log.Printf("Success: %s", result.Text())
```

**Zig:**
```zig
const result = try agent.process(msg);
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    const text = try response.contentAsText();
    std.debug.print("Success: {s}\n", .{text});
} else {
    const err = result.unwrapErr();
    std.debug.print("Error: {}\n", .{err});
}
```

**Key Changes:**
- No `error` return value, use `Result` union
- Use `try` to propagate errors
- Check `isOk()` instead of `err != nil`
- `unwrap()` to get value

### Goroutines

**Go:**
```go
results := make(chan agenkit.Message, 3)

go func() {
    result, _ := agent1.Process(ctx, msg)
    results <- result
}()

go func() {
    result, _ := agent2.Process(ctx, msg)
    results <- result
}()

for i := 0; i < 2; i++ {
    result := <-results
    fmt.Println(result.Text())
}
```

**Zig:**
```zig
// Option 1: Use Parallel pattern
var parallel = try agenkit.patterns.parallel.ParallelAgent.init(allocator);
defer parallel.agent().deinit();

try parallel.addAgent(agent1.agent());
try parallel.addAgent(agent2.agent());

const results = try parallel.processAll(msg);
defer {
    for (results) |*result| {
        if (result.isOk()) {
            var m = try result.unwrap();
            m.deinit();
        }
    }
    allocator.free(results);
}

// Option 2: Use threads (lower-level)
const thread1 = try std.Thread.spawn(.{}, processFunc, .{agent1, msg});
const thread2 = try std.Thread.spawn(.{}, processFunc, .{agent2, msg});

const result1 = thread1.join();
const result2 = thread2.join();
```

**Key Changes:**
- No goroutines, use Parallel pattern or threads
- No channels, use shared memory or results arrays
- More explicit concurrency model

---

## From Rust

### Key Differences

1. **Similar memory safety** - Both have compile-time safety
2. **Different ownership** - Zig uses explicit allocators
3. **No traits** - Use vtables instead
4. **Simpler generics** - Less complex than Rust
5. **No lifetimes** - Manual memory management

### Message Creation

**Rust:**
```rust
use agenkit::{Message, Role};

let msg = Message::with_text(Role::User, "Hello!");
// Drop trait handles cleanup
```

**Zig:**
```zig
var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit();
```

**Key Changes:**
- Add `allocator` parameter
- Use `defer` instead of Drop trait
- Lowercase enum `.user` vs `Role::User`

### Creating Agents

**Rust:**
```rust
use agenkit::{Agent, Message, AgentError, Result};

struct MyAgent;

impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["custom".to_string()]
    }

    fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.text()?;
        let response = Message::with_text(Role::Assistant, format!("Response: {}", text));
        Ok(response)
    }
}
```

**Zig:**
```zig
pub const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !*MyAgent {
        const self = try allocator.create(MyAgent);
        self.* = .{ .allocator = allocator };
        return self;
    }

    pub fn deinit(self: *MyAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *MyAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "my-agent";
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "custom";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));

        const text = try message.contentAsText();
        const response_text = try std.fmt.allocPrint(
            self.allocator,
            "Response: {s}",
            .{text},
        );
        defer self.allocator.free(response_text);

        const response = try agenkit.Message.withText(
            self.allocator,
            .assistant,
            response_text,
        );
        return agenkit.Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};
```

**Key Changes:**
- No trait, use vtable pattern
- Add explicit allocator field
- Manual `init`/`deinit` instead of Drop
- Return `Result` union instead of `Result<T, E>`

### Error Handling

**Rust:**
```rust
let result = agent.process(msg)?;
println!("Success: {}", result.text()?);

// Or explicit handling
match agent.process(msg) {
    Ok(response) => println!("Success: {}", response.text()?),
    Err(e) => println!("Error: {}", e),
}
```

**Zig:**
```zig
const result = try agent.process(msg);
var response = try result.unwrap();
defer response.deinit();
const text = try response.contentAsText();
std.debug.print("Success: {s}\n", .{text});

// Or explicit handling
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    // Handle success
} else {
    const err = result.unwrapErr();
    // Handle error
}
```

**Key Changes:**
- `try` for propagation like `?` in Rust
- No `match`, use `if` with `isOk()`
- Must call `deinit()` manually (no Drop)

### Ownership

**Rust:**
```rust
let msg = Message::with_text(Role::User, "Hello!");
process_message(msg);  // msg moved, can't use again
// msg dropped automatically
```

**Zig:**
```zig
var msg = try Message.withText(allocator, .user, "Hello!");
defer msg.deinit();
// msg can still be used, deinit at end of scope
process_message(msg);  // msg passed by value (copied)
```

**Key Changes:**
- No move semantics, copy by default
- Use pointers for reference passing
- Manual cleanup with `defer`

---

## From C++

### Key Differences

1. **Memory safety** - Compile-time checks vs runtime UB
2. **Simpler semantics** - No move/copy/rule of 5
3. **Explicit allocators** - No `new`/`delete`
4. **No RAII** - Use `defer` instead
5. **Compile-time errors** - More errors caught early

### Message Creation

**C++:**
```cpp
#include <agenkit/message.hpp>

auto msg = agenkit::Message::withText("user", "Hello!");
// Destructor handles cleanup
```

**Zig:**
```zig
var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit();
```

**Key Changes:**
- Add `allocator` parameter
- Use `defer` instead of destructor
- Enum `.user` instead of string

### Creating Agents

**C++:**
```cpp
#include <agenkit/agent.hpp>

class MyAgent : public agenkit::Agent {
public:
    std::string name() const override {
        return "my-agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"custom"};
    }

    agenkit::Result process(const agenkit::Message& message) override {
        auto text = message.text();
        auto response = agenkit::Message::withText("assistant", "Response: " + text);
        return agenkit::Result::ok(response);
    }
};
```

**Zig:**
```zig
pub const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !*MyAgent {
        const self = try allocator.create(MyAgent);
        self.* = .{ .allocator = allocator };
        return self;
    }

    pub fn deinit(self: *MyAgent) void {
        self.allocator.destroy(self);
    }

    pub fn agent(self: *MyAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "my-agent";
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) ![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "custom";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));

        const text = try message.contentAsText();
        const response_text = try std.fmt.allocPrint(
            self.allocator,
            "Response: {s}",
            .{text},
        );
        defer self.allocator.free(response_text);

        const response = try agenkit.Message.withText(
            self.allocator,
            .assistant,
            response_text,
        );
        return agenkit.Result{ .ok = response };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};
```

**Key Changes:**
- No virtual functions, use vtable
- No inheritance, composition instead
- Manual memory management with allocator
- `defer` instead of RAII

### Error Handling

**C++:**
```cpp
try {
    auto result = agent.process(msg);
    std::cout << "Success: " << result.text() << std::endl;
} catch (const agenkit::AgentError& e) {
    std::cerr << "Error: " << e.what() << std::endl;
}
```

**Zig:**
```zig
const result = try agent.process(msg);
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    const text = try response.contentAsText();
    std.debug.print("Success: {s}\n", .{text});
} else {
    const err = result.unwrapErr();
    std.debug.print("Error: {}\n", .{err});
}
```

**Key Changes:**
- No exceptions, use error unions
- `try` propagates errors (like `throw`)
- Check `Result` type explicitly
- No RAII, manual cleanup

### Smart Pointers

**C++:**
```cpp
auto agent = std::make_unique<MyAgent>();
// Automatically deleted
```

**Zig:**
```zig
var agent = try MyAgent.init(allocator);
defer agent.agent().deinit();
// Manual cleanup with defer
```

**Key Changes:**
- No smart pointers, manual management
- Use `defer` for deterministic cleanup
- More explicit but simpler

---

## Common Patterns

### Pattern: Sequential Pipeline

**All Languages:**
- Create Sequential agent
- Add stages in order
- Process message through pipeline

**Python:**
```python
pipeline = SequentialAgent()
pipeline.add_agent(stage1)
pipeline.add_agent(stage2)
result = pipeline.process(msg)
```

**Go:**
```go
pipeline := sequential.New()
pipeline.AddAgent(stage1)
pipeline.AddAgent(stage2)
result, err := pipeline.Process(ctx, msg)
```

**Rust:**
```rust
let mut pipeline = SequentialAgent::new();
pipeline.add_agent(stage1);
pipeline.add_agent(stage2);
let result = pipeline.process(msg)?;
```

**C++:**
```cpp
auto pipeline = agenkit::SequentialAgent();
pipeline.addAgent(stage1);
pipeline.addAgent(stage2);
auto result = pipeline.process(msg);
```

**Zig:**
```zig
var pipeline = try agenkit.patterns.sequential.SequentialAgent.init(allocator);
defer pipeline.agent().deinit();
try pipeline.addAgent(stage1.agent());
try pipeline.addAgent(stage2.agent());
const result = try pipeline.agent().process(msg);
```

### Pattern: Parallel Processing

**Python:**
```python
parallel = ParallelAgent()
parallel.add_agent(agent1)
parallel.add_agent(agent2)
results = await parallel.process_all(msg)
```

**Zig:**
```zig
var parallel = try agenkit.patterns.parallel.ParallelAgent.init(allocator);
defer parallel.agent().deinit();
try parallel.addAgent(agent1.agent());
try parallel.addAgent(agent2.agent());
const results = try parallel.processAll(msg);
defer allocator.free(results);
```

---

## Memory Management

### Allocator Pattern

All Zig code requires explicit allocators:

```zig
// Setup allocator
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();

// Pass to all allocations
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();
```

### Cleanup Pattern

Use `defer` for automatic cleanup:

```zig
var msg = try Message.withText(allocator, .user, "text");
defer msg.deinit();  // Runs when scope exits

// Use errdefer for error-only cleanup
var agent = try MyAgent.init(allocator);
errdefer agent.agent().deinit();  // Only if error occurs
```

### Ownership Transfer

```zig
// Functions that take ownership
try seq.addAgent(agent.agent());  // seq now owns agent

// Functions that borrow
const name = agent.name();  // Borrowed, don't free

// Functions that return owned values
const caps = try agent.capabilities(allocator);
defer allocator.free(caps);  // Caller must free
```

---

## Error Handling

### Error Propagation

```zig
// Use try to propagate errors
const result = try agent.process(msg);

// Equivalent to:
const result = agent.process(msg) catch |err| {
    return err;
};
```

### Error Handling

```zig
// Explicit check
if (result.isOk()) {
    // Handle success
} else {
    // Handle error
}

// Unwrap with custom error
var response = result.unwrap() catch |err| {
    std.debug.print("Failed: {}\n", .{err});
    return err;
};
```

---

## Testing

### Test Structure

**All Languages** - Similar test patterns:

**Python:**
```python
def test_agent():
    agent = MyAgent()
    msg = Message.with_text("user", "test")
    result = agent.process(msg)
    assert result.text == "expected"
```

**Zig:**
```zig
test "agent processes correctly" {
    const allocator = std.testing.allocator;

    var agent = try MyAgent.init(allocator);
    defer agent.agent().deinit();

    var msg = try agenkit.Message.withText(allocator, .user, "test");
    defer msg.deinit();

    const result = try agent.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    try std.testing.expectEqualStrings("expected", text);
}
```

**Key Zig Testing:**
- Use `std.testing.allocator` - detects leaks
- Add `defer` for cleanup
- Use `try std.testing.expect*` for assertions

---

## Performance Considerations

### Zig Advantages

1. **Zero-cost abstractions** - No runtime overhead
2. **Compile-time optimization** - More aggressive than others
3. **Explicit memory control** - Better cache locality
4. **No GC pauses** - Predictable latency

### Performance Tips

1. **Reuse allocators** - Don't create per operation
2. **Batch allocations** - Use ArrayList, not repeated alloc
3. **Profile with tracy** - Built-in profiling support
4. **Use comptime** - Move work to compile time

### Benchmarking

```zig
const start = std.time.nanoTimestamp();

const result = try agent.process(msg);

const end = std.time.nanoTimestamp();
const duration = @as(f64, @floatFromInt(end - start)) / 1_000_000.0;
std.debug.print("Duration: {d:.2}ms\n", .{duration});
```

---

## Migration Checklist

### From Any Language

- [ ] Setup Zig toolchain (0.15.2+)
- [ ] Create `build.zig` and `build.zig.zon`
- [ ] Add agenkit dependency
- [ ] Port data structures to structs
- [ ] Add allocator fields
- [ ] Implement vtable for agents
- [ ] Replace exceptions with error unions
- [ ] Add `defer` for cleanup
- [ ] Port tests with `test` blocks
- [ ] Run `zig build test` to verify
- [ ] Profile and optimize

### Language-Specific

**From Python:**
- [ ] Replace classes with structs
- [ ] Add explicit types
- [ ] Remove async/await (use Parallel)
- [ ] Manual memory management

**From Go:**
- [ ] Remove goroutines (use Parallel)
- [ ] Replace interfaces with vtables
- [ ] Change error handling
- [ ] Manual memory management

**From Rust:**
- [ ] Replace traits with vtables
- [ ] Remove lifetimes
- [ ] Replace Drop with defer
- [ ] Explicit allocators

**From C++:**
- [ ] Replace virtual functions with vtables
- [ ] Remove RAII (use defer)
- [ ] Explicit allocators
- [ ] Simpler error handling

---

## Getting Help

- **Examples:** Check `examples/` directory for complete examples
- **API Docs:** See [API.md](API.md)
- **Patterns:** See [PATTERNS.md](PATTERNS.md)
- **Issues:** [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)

**Welcome to Agenkit-Zig! 🚀**
