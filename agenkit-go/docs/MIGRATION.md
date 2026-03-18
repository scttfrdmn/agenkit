# Migration Guide: Porting to and from Agenkit-Go

A comprehensive guide for migrating agent code between Go and other Agenkit implementations.

## Table of Contents

- [Overview](#overview)
- [From Python → Go](#from-python--go)
- [From TypeScript → Go](#from-typescript--go)
- [From Rust → Go](#from-rust--go)
- [From C++ → Go](#from-c--go)
- [From Zig → Go](#from-zig--go)
- [From Go → Other Languages](#from-go--other-languages)
- [Common Patterns](#common-patterns)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Performance Considerations](#performance-considerations)

---

## Overview

All Agenkit implementations share the same core concepts:

- **Message** - Unit of communication with role, content, metadata
- **Agent** - Interface with name, capabilities, process methods
- **Patterns** - Reusable agent architectures
- **Middleware** - Cross-cutting concerns (retry, timeout, metrics)

However, each language has idioms and patterns that require translation when moving between them.

### API Compatibility Matrix

| Feature | Python | Go | TypeScript | Rust | C++ | Zig |
|---------|--------|----|----|------|-----|-----|
| Message creation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Agent interface | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| All 11 patterns | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Async/concurrent | async/await | goroutines | async/await | async/await | std::thread | planned |
| JSON serialization | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Garbage collection | ✅ | ✅ | ✅ | ❌ (ownership) | ❌ (manual) | ❌ (manual) |

Legend: ✅ Full support, ❌ Different approach

---

## From Python → Go

### Key Differences

1. **Concurrency model** - Python uses `async/await`; Go uses goroutines and channels
2. **Package management** - `pip`/`uv` → `go get` / `go mod`
3. **Type system** - Python type hints are optional; Go types are mandatory
4. **Error handling** - Python raises exceptions; Go returns errors
5. **Interfaces** - Python uses class inheritance; Go uses implicit interface satisfaction
6. **No GIL** - Go goroutines are truly parallel; Python threads contend on the GIL

### Installation

**Python:**
```bash
uv pip install agenkit
# or
pip install agenkit
```

**Go:**
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Message Creation

**Python:**
```python
from agenkit import Message

msg = Message.with_text("user", "Hello!")
# No explicit cleanup needed — GC handles it
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"

msg := agenkit.NewMessage("user", "Hello!")
// No manual cleanup — Go's GC handles it
// (unlike Zig/C++, you don't need explicit defer cleanup)
```

**Key changes:**
- No `allocator` parameter needed (Go has GC)
- Struct field access is direct: `msg.Content` not `msg.content`
- Metadata is `map[string]interface{}` not a dict

### Creating Agents

**Python:**
```python
from agenkit import Agent, Message
from typing import Optional

class MyAgent(Agent):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def process(self, message: Message) -> Message:
        return Message.with_text("assistant", f"Response: {message.content}")
```

**Go:**
```go
import (
    "context"
    "fmt"
    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

type MyAgent struct {
    name string
}

// Implementing the agenkit.Agent interface implicitly
func (a *MyAgent) Name() string { return a.name }

func (a *MyAgent) Capabilities() []string { return []string{"processing"} }

func (a *MyAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}

// Process is synchronous in Go — use goroutines for concurrency
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", fmt.Sprintf("Response: %s", msg.Content)), nil
}
```

**Key changes:**
- `async def process` → `func Process(ctx context.Context, ...) (*Message, error)`
- `await agent.process(msg)` → `agent.Process(ctx, msg)` (synchronous call)
- Inheritance → interface satisfaction (no `class MyAgent(Agent):`)
- `raise ValueError(...)` → `return nil, fmt.Errorf(...)`

### Async vs. Goroutines

**Python (async):**
```python
import asyncio

async def run_agents():
    # Run concurrently with asyncio
    results = await asyncio.gather(
        agent1.process(msg),
        agent2.process(msg),
        agent3.process(msg),
    )
    return results
```

**Go (goroutines):**
```go
import (
    "sync"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// Option 1: Use ParallelAgent (recommended)
parallel := patterns.NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, nil)
result, err := parallel.Process(ctx, msg)

// Option 2: Manual goroutines with WaitGroup
var wg sync.WaitGroup
results := make([]*agenkit.Message, 3)
errs := make([]error, 3)

for i, ag := range []agenkit.Agent{agent1, agent2, agent3} {
    wg.Add(1)
    go func(idx int, a agenkit.Agent) {
        defer wg.Done()
        results[idx], errs[idx] = a.Process(ctx, msg)
    }(i, ag)
}
wg.Wait()
```

### Error Handling

**Python:**
```python
try:
    response = await agent.process(message)
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

**Go:**
```go
import "errors"

response, err := agent.Process(ctx, message)
if err != nil {
    switch {
    case errors.Is(err, agenkit.ErrEmptyInput):
        log.Println("validation error: empty input")
    default:
        log.Printf("unexpected error: %v", err)
    }
    return
}
```

### Middleware

**Python:**
```python
from agenkit.middleware import RetryMiddleware, TimeoutMiddleware

agent = RetryMiddleware(agent, max_retries=3, initial_delay=0.1)
agent = TimeoutMiddleware(agent, timeout=5.0)
```

**Go:**
```go
import (
    "time"
    "github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

agent = middleware.NewRetryMiddleware(agent, &middleware.RetryConfig{
    MaxRetries:   3,
    InitialDelay: 100 * time.Millisecond, // Use time.Duration, not floats
})
agent = middleware.NewTimeoutMiddleware(agent, &middleware.TimeoutConfig{
    Timeout: 5 * time.Second, // Use time.Duration
})
```

**Key change:** Go uses `time.Duration` constants (`100 * time.Millisecond`, `5 * time.Second`). Never pass raw integers or float seconds.

---

## From TypeScript → Go

### Key Differences

1. **Runtime** - Node.js/Deno → compiled binary
2. **Package management** - `npm`/`yarn` → `go get` / `go mod`
3. **Concurrency** - `Promise`/`async-await` → goroutines/channels
4. **Type system** - Structural typing → structural interfaces (similar concept, different syntax)
5. **Deployment** - Requires Node.js → single static binary

### Installation

**TypeScript:**
```bash
npm install @agenkit/core
# or
yarn add @agenkit/core
```

**Go:**
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Message Creation

**TypeScript:**
```typescript
import { Message } from '@agenkit/core';

const msg = Message.create({ role: 'user', content: 'Hello!' });
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"

msg := agenkit.NewMessage("user", "Hello!")
```

### Creating Agents

**TypeScript:**
```typescript
import { Agent, Message } from '@agenkit/core';

class MyAgent implements Agent {
    name = 'my-agent';

    async process(message: Message): Promise<Message> {
        return Message.create({
            role: 'assistant',
            content: `Response: ${message.content}`,
        });
    }
}
```

**Go:**
```go
type MyAgent struct{}

func (a *MyAgent) Name() string { return "my-agent" }
func (a *MyAgent) Capabilities() []string { return []string{"processing"} }
func (a *MyAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", "Response: "+msg.Content), nil
}
```

### Promises vs. Goroutines

**TypeScript:**
```typescript
// Concurrent execution with Promise.all
const [result1, result2, result3] = await Promise.all([
    agent1.process(msg),
    agent2.process(msg),
    agent3.process(msg),
]);
```

**Go:**
```go
// Option 1: Use ParallelAgent
parallel := patterns.NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, nil)
result, err := parallel.Process(ctx, msg)

// Option 2: Channels for more control
type result struct {
    msg *agenkit.Message
    err error
}

ch := make(chan result, 3)
for _, ag := range []agenkit.Agent{agent1, agent2, agent3} {
    go func(a agenkit.Agent) {
        r, err := a.Process(ctx, msg)
        ch <- result{r, err}
    }(ag)
}

results := make([]*agenkit.Message, 0, 3)
for range 3 {
    r := <-ch
    if r.err != nil {
        log.Printf("agent error: %v", r.err)
        continue
    }
    results = append(results, r.msg)
}
```

### Optional Values

**TypeScript:**
```typescript
// Optional via undefined
function getUserID(message: Message): string | undefined {
    return message.metadata?.['user_id'] as string | undefined;
}
```

**Go:**
```go
// Optional via pointer
func getUserID(msg *agenkit.Message) *string {
    if msg.Metadata == nil {
        return nil
    }
    v, ok := msg.Metadata["user_id"].(string)
    if !ok {
        return nil
    }
    return &v
}

// Usage
userID := getUserID(msg)
if userID == nil {
    // anonymous user
} else {
    fmt.Println(*userID)
}
```

**Key change:** Go uses `*string` (pointer) for "optional string", not `string | undefined`. This was corrected in v0.70.0 — the empty-string sentinel `""` is no longer used.

---

## From Rust → Go

### Key Differences

1. **Memory model** - Ownership/borrowing → garbage collection
2. **Package management** - `Cargo` → `go mod` / `go get`
3. **Error handling** - `Result<T, E>` → `(T, error)`
4. **Concurrency** - `tokio`/`async-std` → goroutines
5. **Traits** - `impl Trait for Struct` → implicit interface satisfaction
6. **Build** - `cargo build` → `go build`

### Installation

**Rust:**
```toml
# Cargo.toml
[dependencies]
agenkit = "0.75"
```

**Go:**
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Message Creation

**Rust:**
```rust
use agenkit::Message;

let msg = Message::new("user", "Hello!");
// Ownership: msg is owned, no GC
```

**Go:**
```go
msg := agenkit.NewMessage("user", "Hello!")
// GC manages memory; no ownership transfer
```

### Creating Agents

**Rust:**
```rust
use agenkit::{Agent, Message, AgentError};
use async_trait::async_trait;

struct MyAgent {
    name: String,
}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::new("assistant", format!("Response: {}", message.content)))
    }
}
```

**Go:**
```go
type MyAgent struct {
    name string
}

func (a *MyAgent) Name() string { return a.name }
func (a *MyAgent) Capabilities() []string { return nil }
func (a *MyAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", "Response: "+msg.Content), nil
}
```

### Result Type Translation

**Rust:**
```rust
match agent.process(message).await {
    Ok(response) => println!("{}", response.content),
    Err(AgentError::EmptyInput) => eprintln!("empty input"),
    Err(e) => eprintln!("error: {}", e),
}
```

**Go:**
```go
response, err := agent.Process(ctx, message)
if err != nil {
    switch {
    case errors.Is(err, agenkit.ErrEmptyInput):
        log.Println("empty input")
    default:
        log.Printf("error: %v", err)
    }
    return
}
fmt.Println(response.Content)
```

### Error Propagation

**Rust:**
```rust
async fn run(agent: &dyn Agent, msg: Message) -> Result<(), AgentError> {
    let response = agent.process(msg).await?; // ? propagates
    println!("{}", response.content);
    Ok(())
}
```

**Go:**
```go
func run(ctx context.Context, agent agenkit.Agent, msg *agenkit.Message) error {
    response, err := agent.Process(ctx, msg)
    if err != nil {
        return fmt.Errorf("run failed: %w", err) // %w wraps for errors.Is
    }
    fmt.Println(response.Content)
    return nil
}
```

**Key changes:**
- `?` operator → `if err != nil { return ..., err }` (more verbose, but explicit)
- `Result<T, E>` → `(T, error)` return tuple
- `cargo test` → `go test ./...`
- No `tokio::spawn` — use `go func(){}()` instead

---

## From C++ → Go

### Key Differences

1. **Memory management** - Manual/RAII → garbage collection
2. **Build system** - CMake/Make → `go build` (built-in)
3. **Concurrency** - `std::thread`/`std::async` → goroutines
4. **Polymorphism** - Virtual functions/vtable → interfaces
5. **Error handling** - Exceptions → error return values
6. **Headers** - `.h`/`.hpp` files → none (Go has no headers)

### Installation

**C++:**
```cmake
# CMakeLists.txt
find_package(agenkit REQUIRED)
target_link_libraries(my_agent agenkit::agenkit)
```

**Go:**
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Message Creation

**C++:**
```cpp
#include <agenkit/message.hpp>
using namespace agenkit;

auto msg = Message::create(Role::User, "Hello!");
// RAII: automatic cleanup when msg goes out of scope
```

**Go:**
```go
msg := agenkit.NewMessage("user", "Hello!")
// GC handles cleanup — no RAII needed
```

### Creating Agents

**C++:**
```cpp
#include <agenkit/agent.hpp>
using namespace agenkit;

class MyAgent : public Agent {
public:
    std::string name() const override {
        return "my-agent";
    }

    std::future<Message> process(const Message& message) const override {
        return std::async(std::launch::async, [&message]() {
            return Message::create(Role::Assistant, "Response: " + message.content());
        });
    }
};
```

**Go:**
```go
type MyAgent struct{}

func (a *MyAgent) Name() string { return "my-agent" }
func (a *MyAgent) Capabilities() []string { return nil }
func (a *MyAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", "Response: "+msg.Content), nil
}
```

**Key changes:**
- `class MyAgent : public Agent` → implicit interface satisfaction (no declaration needed)
- `std::future<Message>` → synchronous `(*Message, error)` return
- `override` keyword → none in Go
- `std::async` → `go func(){}()` goroutine

### Memory Management

**C++ (RAII):**
```cpp
{
    auto msg = Message::create(Role::User, "hello");
    auto agent = std::make_unique<MyAgent>();
    auto response = agent->process(msg).get();
    // Automatic cleanup when scope ends (RAII)
}
```

**Go (GC):**
```go
{
    msg := agenkit.NewMessage("user", "hello")
    agent := &MyAgent{}
    response, err := agent.Process(ctx, msg)
    if err != nil {
        return err
    }
    _ = response
    // GC handles cleanup — no explicit release needed
}
```

**However**, for resources like files and connections, Go uses `defer`:

```go
f, err := os.Open("data.txt")
if err != nil {
    return err
}
defer func() { _ = f.Close() }() // Analogous to RAII destructor

// Use f...
```

### Concurrency

**C++:**
```cpp
#include <future>
#include <vector>

std::vector<std::future<Message>> futures;
for (auto& agent : agents) {
    futures.push_back(
        std::async(std::launch::async, [&agent, &msg]() {
            return agent->process(msg).get();
        })
    );
}

std::vector<Message> results;
for (auto& f : futures) {
    results.push_back(f.get());
}
```

**Go:**
```go
// Use ParallelAgent — it handles goroutines internally
parallel := patterns.NewParallelAgent(agents, nil)
result, err := parallel.Process(ctx, msg)
```

**Key changes:**
- `std::async` / `std::thread` → goroutines (`go func(){}()`)
- `std::mutex` / `std::lock_guard` → `sync.Mutex`
- `std::condition_variable` → channels or `sync.Cond`
- `std::atomic<T>` → `sync/atomic` package

---

## From Zig → Go

### Key Differences

1. **Memory model** - Explicit allocators → garbage collection
2. **Build** - `zig build` → `go build`
3. **Concurrency** - Manual/planned → goroutines
4. **Interfaces** - vtable structs → implicit interface satisfaction
5. **Error handling** - Error unions (`!T`) → `(T, error)` return
6. **Generics** - `comptime` → Go generics (`[T any]`)

### Installation

**Zig (build.zig.zon):**
```zig
.{
    .dependencies = .{
        .agenkit = .{ .url = "...", .hash = "..." },
    },
}
```

**Go:**
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Message Creation

**Zig:**
```zig
const agenkit = @import("agenkit");
const allocator = std.heap.GeneralPurposeAllocator(.{}){};

var msg = try agenkit.Message.withText(allocator, .user, "Hello!");
defer msg.deinit(); // REQUIRED: manual cleanup
```

**Go:**
```go
msg := agenkit.NewMessage("user", "Hello!")
// No allocator parameter — Go's GC handles memory
// No defer cleanup needed for messages
```

**Key change:** Go has no allocator parameter and no `deinit()` call. The garbage collector handles memory. You only need `defer` for OS resources (files, connections, etc.).

### Creating Agents

**Zig (vtable pattern):**
```zig
pub const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn agent(self: *MyAgent) agenkit.Agent {
        return agenkit.Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(_: *anyopaque) []const u8 {
        return "my-agent";
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        // ...
    }
};
```

**Go (interface pattern):**
```go
// Go interfaces are implicit — no vtable declaration needed
type MyAgent struct{}

func (a *MyAgent) Name() string { return "my-agent" }
func (a *MyAgent) Capabilities() []string { return nil }
func (a *MyAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", "response"), nil
}

// Usage: just use *MyAgent — it satisfies agenkit.Agent automatically
var _ agenkit.Agent = (*MyAgent)(nil) // Compile-time check (optional)
```

**Key changes:**
- No `.vtable` / `.ptr` / `@ptrCast` — interfaces are implicit
- No `fn agent(self *MyAgent) agenkit.Agent` wrapper needed
- No `deinitImpl` — GC handles cleanup
- `agenkit.AgentError!agenkit.Result` → `(*agenkit.Message, error)`

### Error Handling

**Zig:**
```zig
const result = try agent.process(msg);
if (result.isOk()) {
    var response = try result.unwrap();
    defer response.deinit();
    std.debug.print("{s}\n", .{try response.contentAsText()});
} else {
    const err = result.unwrapErr();
    std.debug.print("Error: {}\n", .{err});
}
```

**Go:**
```go
response, err := agent.Process(ctx, msg)
if err != nil {
    log.Printf("error: %v", err)
    return
}
fmt.Println(response.Content)
```

**Key changes:**
- `Result` union → direct `(*Message, error)` return (no `.unwrap()` needed)
- `try` → `if err != nil { return }`
- `errdefer` → `defer` (but usually not needed for GC-managed objects)

### Comptime vs. Generics

**Zig (comptime):**
```zig
pub fn TypedAgent(comptime T: type) type {
    return struct {
        data: T,
        pub fn process(self: *@This(), msg: agenkit.Message) !agenkit.Result {
            // Work with self.data as type T
        }
    };
}
```

**Go (generics):**
```go
type TypedAgent[T any] struct {
    data T
}

func (a *TypedAgent[T]) Name() string { return "typed-agent" }
func (a *TypedAgent[T]) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    // Work with a.data as type T
    return agenkit.NewMessage("assistant", fmt.Sprintf("%v", a.data)), nil
}

// Usage:
agent := &TypedAgent[int]{data: 42}
```

---

## From Go → Other Languages

### Go → Python

**When to migrate:**
- Prototyping and rapid iteration
- ML/AI integrations (PyTorch, HuggingFace, LangChain)
- Smaller teams preferring dynamic typing
- Less performance-critical workloads

**What to translate:**
- `agenkit.Agent` interface → `class MyAgent(Agent):`
- `(T, error)` returns → exceptions
- Goroutines → `asyncio.gather()` or `asyncio.create_task()`
- `time.Duration` → float seconds

### Go → TypeScript

**When to migrate:**
- Web frontend integration
- Universal deployment (browser + server)
- Teams preferring JavaScript ecosystem
- Serverless functions (Vercel, Cloudflare Workers)

**What to translate:**
- `agenkit.Agent` interface → `class MyAgent implements Agent`
- Goroutines → `Promise.all()` / `async/await`
- `(T, error)` → `Promise<T>` with thrown exceptions
- `go test` → `npm test` / `jest`

### Go → Rust

**When to migrate:**
- Maximum performance requirements
- WASM deployment targets
- Embedded systems
- Zero-cost abstractions without GC pauses

**What to translate:**
- Go interfaces → Rust traits
- `(T, error)` → `Result<T, E>`
- Goroutines → Tokio tasks (`tokio::spawn`)
- `go mod` → `Cargo.toml`

### Go → C++

**When to migrate:**
- C ABI compatibility requirements
- Performance-critical inner loops
- Legacy C/C++ codebase integration
- Platform-specific optimizations

**What to translate:**
- Go interfaces → Abstract base classes (`virtual`)
- GC memory → RAII (`std::unique_ptr`, `std::shared_ptr`)
- `(T, error)` → exceptions or `std::expected<T, E>`
- `go build` → CMake

### Go → Zig

**When to migrate:**
- Embedded/bare-metal targets
- Minimal runtime requirement
- Maximum explicit control over memory
- Cross-compilation needs

**What to translate:**
- Go interfaces → vtable structs
- GC → explicit allocator + `defer deinit()`
- `(T, error)` → `!T` error unions
- Goroutines → planned Zig async

---

## Common Patterns

### Pattern: Pipeline Translation

**Python:**
```python
from agenkit.patterns import Sequential

pipeline = Sequential([agent1, agent2, agent3])
result = await pipeline.process(message)
```

**Go:**
```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

pipeline := patterns.NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
result, err := pipeline.Process(ctx, message)
```

### Pattern: Middleware Stacking

**TypeScript:**
```typescript
import { RetryMiddleware, TimeoutMiddleware } from '@agenkit/middleware';

let agent = new MyAgent();
agent = new RetryMiddleware(agent, { maxRetries: 3 });
agent = new TimeoutMiddleware(agent, { timeoutMs: 5000 });
```

**Go:**
```go
import (
    "time"
    mw "github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

var agent agenkit.Agent = &MyAgent{}
agent = mw.NewRetryMiddleware(agent, &mw.RetryConfig{MaxRetries: 3})
agent = mw.NewTimeoutMiddleware(agent, &mw.TimeoutConfig{Timeout: 5 * time.Second})
```

### Pattern: Tool Implementation

**Python:**
```python
from agenkit import Tool, ToolResult

class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "search"

    async def execute(self, params: dict) -> ToolResult:
        query = params["query"]
        results = await search_web(query)
        return ToolResult(success=True, result=results)
```

**Go:**
```go
type SearchTool struct{}

func (t *SearchTool) Name() string { return "search" }

func (t *SearchTool) Description() string { return "Search the web" }

func (t *SearchTool) Parameters() map[string]interface{} {
    return map[string]interface{}{
        "query": map[string]interface{}{"type": "string"},
    }
}

func (t *SearchTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
    query, ok := params["query"].(string)
    if !ok {
        return nil, fmt.Errorf("missing parameter: query")
    }
    results := searchWeb(ctx, query)
    return agenkit.NewToolResult(results), nil
}
```

---

## Error Handling

### Error Mapping Table

| Python | TypeScript | Rust | C++ | Zig | Go |
|--------|---------|------|-----|-----|-----|
| `raise ValueError(...)` | `throw new Error(...)` | `Err(AgentError::Invalid)` | `throw std::invalid_argument(...)` | `return error.InvalidInput` | `return nil, fmt.Errorf(...)` |
| `except ValueError:` | `catch (e: Error)` | `Err(e) => ...` | `catch (std::exception& e)` | `catch error.InvalidInput` | `if errors.Is(err, ...)` |
| `finally:` | `finally {}` | `defer` (drop) | Destructor | `defer` | `defer` |

### Go Error Idioms (Required by CLAUDE.md)

```go
// CORRECT: Error messages start lowercase
return nil, fmt.Errorf("failed to process message: %w", err)

// WRONG: Capitalized error messages
// return nil, fmt.Errorf("Failed to process message: %w", err)

// CORRECT: Check all errors, even in defer
defer func() { _ = file.Close() }()

// WRONG: Ignore defer errors
// defer file.Close()

// CORRECT: Use switch for multiple error cases
switch {
case errors.Is(err, ErrEmptyInput):
    // ...
case errors.Is(err, context.DeadlineExceeded):
    // ...
default:
    // ...
}

// WRONG: If-else chain for error types
// if errors.Is(err, ErrEmptyInput) { ... } else if ... { ... }
```

---

## Testing

### Test Translation

**Python:**
```python
import pytest
from agenkit import Message

async def test_agent_responds():
    agent = MyAgent()
    msg = Message.with_text("user", "hello")
    response = await agent.process(msg)
    assert response.role == "assistant"
    assert response.content != ""
```

**Go:**
```go
func TestAgentResponds(t *testing.T) {
    ctx := context.Background()
    agent := &MyAgent{}
    msg := agenkit.NewMessage("user", "hello")

    response, err := agent.Process(ctx, msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if response.Role != "assistant" {
        t.Errorf("expected role %q, got %q", "assistant", response.Role)
    }
    if response.Content == "" {
        t.Error("expected non-empty content")
    }
}
```

### Running Tests

| Language | Command |
|----------|---------|
| Python | `uv run pytest tests/` |
| TypeScript | `npm test` |
| Rust | `cargo test` |
| C++ | `cd build && ctest` |
| Zig | `zig build test` |
| Go | `go test ./...` |

---

## Performance Considerations

### Go vs. Other Languages

| Language | Throughput (relative) | Latency | Memory | Cold start |
|----------|----------------------|---------|--------|------------|
| Go | 18x Python | Low | Low | ~10ms |
| Python | 1x | Medium | Medium | ~500ms |
| TypeScript | 3-5x Python | Low | Medium | ~100ms |
| Rust | 20-25x Python | Very Low | Very Low | ~1ms |
| C++ | 20-25x Python | Very Low | Very Low | ~1ms |
| Zig | ~25x Python | Very Low | Very Low | ~1ms |

### When Go Excels

- High-throughput request handling (100K+ RPS per instance)
- Concurrent agent pipelines (goroutines are cheap)
- Microservices with low operational overhead (single binary)
- Teams familiar with Python who need better performance

### When to Consider Alternatives

- **Python**: Prototyping, ML model integration, smaller teams
- **TypeScript**: Browser/frontend deployment, JS ecosystem
- **Rust**: Maximum performance, WASM, zero-GC requirements
- **C++**: Legacy integration, C ABI requirements
- **Zig**: Bare-metal, embedded systems

---

## See Also

- [Getting Started](GETTING_STARTED.md) - Installation and first agent
- [API Reference](API.md) - Complete Go API
- [Patterns Guide](PATTERNS.md) - All 11 agent patterns
- [Observability](OBSERVABILITY.md) - Tracing and metrics
- [Testing Framework](TESTING_FRAMEWORK.md) - Go testing patterns
