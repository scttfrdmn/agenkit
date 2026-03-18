# Agenkit Migration Guide — Rust

Detailed guides for migrating to and from Rust for all supported Agenkit languages.

## Table of Contents

- [Migration Overview](#migration-overview)
- [Python → Rust](#python--rust)
- [Go → Rust](#go--rust)
- [TypeScript → Rust](#typescript--rust)
- [C++ → Rust](#c--rust)
- [Zig → Rust](#zig--rust)
- [Rust → Other Languages](#rust--other-languages)
  - [Rust → Python](#rust--python)
  - [Rust → Go](#rust--go)
  - [Rust → TypeScript](#rust--typescript)

---

## Migration Overview

### Why Migrate to Rust?

| Concern | Rust Advantage |
|---------|---------------|
| Performance | 20-100x faster than Python, 2-5x faster than Go |
| Memory safety | Ownership system prevents use-after-free, data races at compile time |
| Concurrency | Tokio async runtime; fearless concurrent programming |
| WASM support | Compile agents to WebAssembly for browser deployment |
| Type safety | Exhaustive pattern matching; `Option`/`Result` instead of null/exceptions |
| Zero-cost abstractions | Generics and traits have no runtime overhead |

### Agenkit Core Concept Mapping

| Concept | Python | Go | TypeScript | Rust |
|---------|--------|-----|-----------|------|
| Agent interface | `class Agent(ABC)` | `type Agent interface` | `interface Agent` | `trait Agent` |
| Async | `async def` / `asyncio` | `goroutine` / channel | `Promise` / `async` | `async fn` / `tokio` |
| Error handling | Exception | `(result, error)` | `throw` / `try/catch` | `Result<T, E>` |
| Null safety | `Optional` | `*T` / nil check | `T \| undefined` | `Option<T>` |
| Collections | `list`, `dict` | `slice`, `map` | `Array`, `Map` | `Vec<T>`, `HashMap<K,V>` |
| Dependency management | `pip` / `pyproject.toml` | `go.mod` | `npm` / `package.json` | `cargo` / `Cargo.toml` |

---

## Python → Rust

### Key Differences

| Aspect | Python | Rust |
|--------|--------|------|
| Typing | Dynamic (runtime) | Static (compile-time) |
| Memory | Garbage collected | Ownership + borrow checker |
| Async | `asyncio` event loop | Tokio runtime |
| Packages | `pip install` | `cargo add` |
| Entry point | Script or `__main__` | `fn main()` |
| Null | `None` | `Option<T>` |
| Errors | `raise Exception` | `Err(AgentError::...)` |

### Package Management

**Python:**
```bash
pip install agenkit
```

```toml
# pyproject.toml
[tool.poetry.dependencies]
agenkit = "^0.75.0"
```

**Rust:**
```bash
cargo add agenkit
cargo add tokio --features full
cargo add async-trait
```

```toml
# Cargo.toml
[dependencies]
agenkit = "0.75"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
```

### Agent Implementation

**Python:**
```python
from agenkit import Agent, Message, AgentError
from typing import Optional

class GreetingAgent(Agent):
    def __init__(self, greeting: str = "Hello"):
        self.greeting = greeting

    @property
    def name(self) -> str:
        return "greeting-agent"

    async def process(self, message: Message) -> Message:
        user_text = message.content or ""
        response = f"{self.greeting}! You said: {user_text}"
        return Message(role="assistant", content=response)
```

**Rust equivalent:**
```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct GreetingAgent {
    greeting: String,
}

impl GreetingAgent {
    pub fn new(greeting: impl Into<String>) -> Self {
        Self { greeting: greeting.into() }
    }
}

impl Default for GreetingAgent {
    fn default() -> Self {
        Self::new("Hello")
    }
}

#[async_trait]
impl Agent for GreetingAgent {
    fn name(&self) -> &str {
        "greeting-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let user_text = message.content_as_str().unwrap_or("");
        let response = format!("{}! You said: {}", self.greeting, user_text);
        Ok(Message::assistant(&response))
    }
}
```

### Error Handling

**Python:**
```python
from agenkit.exceptions import AgentError, TimeoutError

async def safe_process(agent, message):
    try:
        return await agent.process(message)
    except TimeoutError:
        print("Timed out!")
        return None
    except AgentError as e:
        print(f"Error: {e}")
        raise
```

**Rust equivalent:**
```rust
use agenkit::core::AgentError;

async fn safe_process(
    agent: &impl Agent,
    message: Message,
) -> Option<Message> {
    match agent.process(message).await {
        Ok(msg) => Some(msg),
        Err(AgentError::Timeout) => {
            println!("Timed out!");
            None
        }
        Err(e) => {
            println!("Error: {}", e);
            None
        }
    }
}
```

### Async Patterns

**Python:**
```python
import asyncio

# Sequential
result1 = await agent1.process(message)
result2 = await agent2.process(result1)

# Parallel
results = await asyncio.gather(
    agent1.process(message),
    agent2.process(message),
)
```

**Rust equivalent:**
```rust
// Sequential
let result1 = agent1.process(message.clone()).await?;
let result2 = agent2.process(result1).await?;

// Parallel (fixed count)
let (result_a, result_b) = tokio::join!(
    agent1.process(message.clone()),
    agent2.process(message.clone()),
);
let (a, b) = (result_a?, result_b?);

// Parallel (dynamic)
use futures::future::join_all;
let futures: Vec<_> = agents.iter().map(|a| a.process(message.clone())).collect();
let results = join_all(futures).await;
```

### Type Annotations

**Python:**
```python
from typing import Optional, List, Dict, Any

def process_messages(
    messages: List[Message],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Message]:
    ...
```

**Rust equivalent:**
```rust
use std::collections::HashMap;
use serde_json::Value;

fn process_messages(
    messages: Vec<Message>,
    metadata: Option<HashMap<String, Value>>,
) -> Option<Message> {
    // ...
    todo!()
}
```

### Key Migration Points

1. **Replace `None` with `Option<T>`** — `None` in Rust is the `None` variant of `Option<T>`, not a standalone value.
2. **Replace exceptions with `Result<T, E>`** — No try/catch; use `?` for propagation.
3. **Replace `asyncio.gather` with `tokio::join!` or `join_all`**.
4. **Add explicit types** — Rust requires type annotations for function signatures.
5. **Ownership means no implicit sharing** — Use `Arc<T>` when sharing across tasks.
6. **`self` is always explicit** — Every method takes `&self` or `&mut self`.

---

## Go → Rust

### Key Differences

| Aspect | Go | Rust |
|--------|-----|------|
| Concurrency | Goroutines + channels | Tokio tasks + async/await |
| Memory | Garbage collected | Ownership + borrow checker |
| Error | `(T, error)` returns | `Result<T, E>` |
| Null | `nil` pointer | `Option<T>` |
| Generics | Since 1.18 (limited) | Full generics + const generics |
| Interfaces | Implicit implementation | Explicit `impl Trait for Type` |
| Packages | `go.mod` | `Cargo.toml` |

### Agent Implementation

**Go:**
```go
package main

import (
    "context"
    "fmt"
    agenkit "github.com/agenkit/agenkit-go"
)

type EchoAgent struct {
    name string
}

func (a *EchoAgent) Name() string { return a.name }

func (a *EchoAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    text := msg.ContentAsText()
    return agenkit.NewMessage("assistant", fmt.Sprintf("Echo: %s", text)), nil
}
```

**Rust equivalent:**
```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct EchoAgent {
    name: String,
}

impl EchoAgent {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");
        Ok(Message::assistant(&format!("Echo: {}", text)))
    }
}
```

### Concurrency: Goroutines vs Tokio Tasks

**Go goroutines:**
```go
results := make(chan agenkit.Message, len(agents))

for _, agent := range agents {
    go func(a agenkit.Agent) {
        result, err := a.Process(ctx, message)
        if err == nil {
            results <- result
        }
    }(agent)
}

// Collect results
for i := 0; i < len(agents); i++ {
    fmt.Println(<-results)
}
```

**Rust Tokio equivalent:**
```rust
use futures::future::join_all;

let futures: Vec<_> = agents
    .iter()
    .map(|agent| agent.process(message.clone()))
    .collect();

let results: Vec<Result<Message, AgentError>> = join_all(futures).await;

for result in results {
    match result {
        Ok(msg) => println!("{:?}", msg),
        Err(e) => eprintln!("Error: {}", e),
    }
}
```

### Error Handling: Multiple Returns vs Result

**Go:**
```go
func processMessage(agent Agent, msg Message) (Message, error) {
    result, err := agent.Process(ctx, msg)
    if err != nil {
        return Message{}, fmt.Errorf("processing failed: %w", err)
    }
    return result, nil
}
```

**Rust equivalent:**
```rust
async fn process_message(
    agent: &impl Agent,
    msg: Message,
) -> Result<Message, AgentError> {
    // ? operator propagates error, equivalent to if err != nil { return err }
    let result = agent.process(msg).await
        .map_err(|e| AgentError::ProcessingFailed(format!("processing failed: {}", e)))?;
    Ok(result)
}
```

### Interface vs Trait

**Go interface (implicit):**
```go
type Agent interface {
    Name() string
    Process(ctx context.Context, msg Message) (Message, error)
}

// Any type with these methods satisfies Agent
// No explicit declaration needed
```

**Rust trait (explicit):**
```rust
#[async_trait]
pub trait Agent: Send + Sync {
    fn name(&self) -> &str;
    async fn process(&self, message: Message) -> Result<Message, AgentError>;
}

// Must explicitly implement
#[async_trait]
impl Agent for MyType {
    fn name(&self) -> &str { "my-type" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> { todo!() }
}
```

### Nil vs Option

**Go nil:**
```go
var agent Agent = nil // can be nil
if agent != nil {
    agent.Process(ctx, msg)
}
```

**Rust Option:**
```rust
let agent: Option<Box<dyn Agent>> = None;
if let Some(a) = agent {
    a.process(msg).await?;
}
// Or with map
agent.as_ref().map(|a| a.process(msg)); // returns Option<Future>
```

### Key Migration Points

1. **`context.Context` is not needed** — Tokio handles cancellation via `select!` and `CancellationToken`.
2. **No goroutine leaks** — Tokio tasks are tracked; use `JoinHandle` and `abort()`.
3. **No implicit nil** — Every nullable value must be `Option<T>`.
4. **Explicit trait bounds** — `Box<dyn Agent + Send + Sync>` replaces Go's implicit interface satisfaction.
5. **`defer` → `Drop`** — Use `impl Drop for T` or RAII guards instead of `defer`.
6. **Struct embedding → Composition** — Rust has no struct embedding; use composition with delegation.

---

## TypeScript → Rust

### Key Differences

| Aspect | TypeScript | Rust |
|--------|-----------|------|
| Runtime | Node.js / Deno / Browser | Native binary or WASM |
| Packages | npm / package.json | Cargo / Cargo.toml |
| Async | `Promise` / `async`/`await` | `Future` / Tokio |
| Null | `T \| undefined \| null` | `Option<T>` |
| Errors | `throw` / `try/catch` | `Result<T, E>` |
| Types | Structural (duck typing) | Nominal (named types) |
| Generics | Type parameters | Generics + trait bounds |

### Package Management

**TypeScript:**
```bash
npm install agenkit
```

```json
{
  "dependencies": {
    "agenkit": "^0.75.0"
  }
}
```

**Rust:**
```bash
cargo add agenkit tokio async-trait
```

### Agent Implementation

**TypeScript:**
```typescript
import { Agent, Message, AgentError } from 'agenkit';

class TranslationAgent implements Agent {
    private targetLanguage: string;

    constructor(targetLanguage: string) {
        this.targetLanguage = targetLanguage;
    }

    get name(): string {
        return `translator-${this.targetLanguage}`;
    }

    async process(message: Message): Promise<Message> {
        const text = message.content ?? '';
        const translated = `[${this.targetLanguage}] ${text}`;
        return { role: 'assistant', content: translated, metadata: {} };
    }
}
```

**Rust equivalent:**
```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct TranslationAgent {
    target_language: String,
}

impl TranslationAgent {
    pub fn new(target_language: impl Into<String>) -> Self {
        Self { target_language: target_language.into() }
    }
}

#[async_trait]
impl Agent for TranslationAgent {
    fn name(&self) -> &str {
        // Note: Rust can't return a temporary &str built from format!
        // Use a stored String instead
        "translator"  // Simplification; store formatted name in struct if needed
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");
        let translated = format!("[{}] {}", self.target_language, text);
        Ok(Message::assistant(&translated))
    }
}
```

### Async: Promise vs Future

**TypeScript:**
```typescript
// Promise.all — parallel execution
const [resultA, resultB] = await Promise.all([
    agentA.process(message),
    agentB.process(message),
]);

// Promise.race — first to complete
const first = await Promise.race([
    agentFast.process(message),
    agentSlow.process(message),
]);

// Chaining
const result = await agentA.process(message)
    .then(r => agentB.process(r))
    .catch(e => fallback.process(message));
```

**Rust equivalent:**
```rust
// tokio::join! — parallel execution (both must succeed)
let (result_a, result_b) = tokio::join!(
    agent_a.process(message.clone()),
    agent_b.process(message.clone()),
);

// tokio::select! — first to complete (race)
let first = tokio::select! {
    r = agent_fast.process(message.clone()) => r?,
    r = agent_slow.process(message.clone()) => r?,
};

// Chaining with ?
let intermediate = agent_a.process(message).await?;
let result = agent_b.process(intermediate).await
    .or_else(|_| fallback.process(message.clone()).now_or_never().unwrap_or(
        Err(AgentError::ProcessingFailed("fallback failed".to_string()))
    ))?;
```

### Null Safety

**TypeScript (with strict mode):**
```typescript
function getContent(message: Message): string {
    return message.content ?? 'default';
}

// Optional chaining
const length = message.metadata?.session_id?.length;
```

**Rust equivalent:**
```rust
fn get_content(message: &Message) -> &str {
    message.content_as_str().unwrap_or("default")
}

// Option chaining with and_then
let length = message
    .get_metadata("session_id")
    .and_then(|v| v.as_str())
    .map(|s| s.len());
// length: Option<usize>
```

### Type System Differences

**TypeScript union types:**
```typescript
type Role = 'user' | 'assistant' | 'system' | 'tool';

interface Message {
    role: Role;
    content: string | StructuredContent;
}
```

**Rust enums:**
```rust
pub enum Role {
    User,
    Assistant,
    System,
    Tool,
}

pub enum MessageContent {
    Text(String),
    Structured(serde_json::Value),
}

// Rust requires exhaustive matching
match message.role {
    Role::User => handle_user(),
    Role::Assistant => handle_assistant(),
    Role::System => handle_system(),
    Role::Tool => handle_tool(),
    // Compiler error if any variant is missing!
}
```

### Key Migration Points

1. **No `undefined`** — Use `Option<T>` explicitly; `None` not `undefined`.
2. **No implicit coercion** — Rust never coerces types; use `.to_string()`, `.as_str()`, etc.
3. **`Promise` vs `Future`** — Both are lazy but Futures must be `.await`ed to execute.
4. **Structural vs nominal typing** — TypeScript's duck typing vs Rust's explicit trait implementations.
5. **`Array<T>` vs `Vec<T>`** — Rust Vecs are contiguous heap-allocated arrays.
6. **Node.js modules** — No equivalent; Rust crates are compiled, not interpreted.

---

## C++ → Rust

### Key Differences

| Aspect | C++ | Rust |
|--------|-----|------|
| Memory | Manual `new`/`delete` or smart pointers | Ownership + borrow checker (compile-time) |
| Async | `std::async`, coroutines, or libraries | First-class `async`/`await` + Tokio |
| Build | CMake, Make, Bazel, etc. | Cargo (unified) |
| Packages | vcpkg, Conan, or manual | crates.io + Cargo |
| Undefined behavior | Possible (use-after-free, etc.) | Prevented by borrow checker |
| Exceptions | `throw` / `try`/`catch` | `Result<T, E>` |
| Null | Raw pointer nullptr | `Option<T>` |
| Generics | Templates | Generics + trait bounds |

### Build System

**C++ (CMakeLists.txt):**
```cmake
cmake_minimum_required(VERSION 3.20)
project(my_agent CXX)

find_package(agenkit REQUIRED)
find_package(Threads REQUIRED)

add_executable(my_agent src/main.cpp)
target_link_libraries(my_agent
    agenkit::agenkit
    Threads::Threads
)
```

**Rust (Cargo.toml):**
```toml
[package]
name = "my-agent"
version = "0.1.0"
edition = "2021"

[dependencies]
agenkit = "0.75"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
```

### Agent Implementation

**C++:**
```cpp
#include <agenkit/agent.hpp>
#include <string>
#include <future>

class EchoAgent : public agenkit::Agent {
public:
    explicit EchoAgent(std::string name)
        : name_(std::move(name)) {}

    std::string name() const override {
        return name_;
    }

    std::future<agenkit::Message> process(
        agenkit::Message message
    ) override {
        return std::async(std::launch::async, [msg = std::move(message)]() {
            std::string text = msg.contentAsText().value_or("");
            return agenkit::Message("assistant", "Echo: " + text);
        });
    }

private:
    std::string name_;
};
```

**Rust equivalent:**
```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct EchoAgent {
    name: String,
}

impl EchoAgent {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");
        Ok(Message::assistant(&format!("Echo: {}", text)))
    }
}
```

### Memory Management

**C++ with smart pointers:**
```cpp
#include <memory>
#include <vector>

// Unique ownership
auto agent = std::make_unique<EchoAgent>("echo");

// Shared ownership
auto shared = std::make_shared<EchoAgent>("shared");
auto also_shared = shared;  // Reference count incremented

// Storing in collections
std::vector<std::unique_ptr<agenkit::Agent>> agents;
agents.push_back(std::make_unique<EchoAgent>("echo"));
agents.push_back(std::make_unique<AnalyzerAgent>("analyzer"));
```

**Rust equivalent:**
```rust
use std::sync::Arc;

// Unique ownership (Box<T>)
let agent = Box::new(EchoAgent::new("echo"));

// Shared ownership (Arc<T> — thread-safe Rc)
let shared = Arc::new(EchoAgent::new("shared"));
let also_shared = Arc::clone(&shared);  // Reference count incremented

// Storing in collections (trait objects)
let agents: Vec<Box<dyn Agent>> = vec![
    Box::new(EchoAgent::new("echo")),
    Box::new(AnalyzerAgent::new("analyzer")),
];
```

### Move Semantics

**C++:**
```cpp
// Move semantics
std::string name = "my-agent";
auto agent = EchoAgent(std::move(name));  // name is invalid after this
// name is in "valid but unspecified state"
```

**Rust:**
```rust
// Rust move is enforced by the compiler
let name = String::from("my-agent");
let agent = EchoAgent::new(name);  // name is moved into EchoAgent::new
// println!("{}", name);  // Compile error: use of moved value

// Clone to keep the original
let name = String::from("my-agent");
let agent = EchoAgent::new(name.clone());
println!("{}", name);  // Fine: original still valid
```

### Error Handling

**C++:**
```cpp
try {
    auto result = agent.process(message).get();
    handle_success(result);
} catch (const agenkit::TimeoutError& e) {
    handle_timeout();
} catch (const agenkit::AgentError& e) {
    handle_error(e.what());
}
```

**Rust:**
```rust
match agent.process(message).await {
    Ok(result) => handle_success(result),
    Err(AgentError::Timeout) => handle_timeout(),
    Err(e) => handle_error(&e.to_string()),
}
```

### Key Migration Points

1. **No undefined behavior** — The borrow checker prevents the bugs that make C++ dangerous.
2. **No `std::thread` needed** — Use Tokio tasks (`tokio::spawn`) for async work.
3. **Cargo replaces CMake** — Dependency resolution, building, and testing in one tool.
4. **No header files** — Rust has one source format; no `.h`/`.cpp` split.
5. **Templates → Generics** — Rust generics are checked at definition time, not instantiation.
6. **RAII is the same** — `Drop` in Rust is the same concept as destructors in C++.
7. **Iterators** — Rust's iterator API is equivalent to `std::ranges` but more ergonomic.

---

## Zig → Rust

### Key Differences

| Aspect | Zig | Rust |
|--------|-----|------|
| Build system | `build.zig` | `Cargo.toml` |
| Async | Zig async (compile-time, single-threaded or custom) | Tokio (multi-threaded, mature ecosystem) |
| Allocators | Explicit `Allocator` parameter everywhere | Implicit heap via `Box`/`Vec`; `#[global_allocator]` for custom |
| Comptime | `comptime` for compile-time evaluation | `const fn` and const generics |
| Generics | `comptime` parameters | Explicit type parameters with trait bounds |
| Error handling | `!T` union types | `Result<T, E>` |
| Optionals | `?T` | `Option<T>` |
| Null safety | `null` only in optional types | No null; use `Option<T>` |
| Agent interface | vtable pattern (manual) | `trait Agent` (automatic vtable) |

### Build System

**Zig (build.zig.zon):**
```zig
.{
    .name = "my-agent",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/agenkit/agenkit/releases/download/v0.75.0/agenkit-zig.tar.gz",
            .hash = "1220...",
        },
    },
}
```

**Rust (Cargo.toml):**
```toml
[package]
name = "my-agent"
version = "0.1.0"
edition = "2021"

[dependencies]
agenkit = "0.75"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
```

### Agent Interface

**Zig (vtable pattern):**
```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub const MyAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) !MyAgent {
        return MyAgent{ .allocator = allocator };
    }

    pub fn deinit(self: *MyAgent) void {
        // cleanup
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "my-agent";
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        _ = self;
        const text = try message.contentAsText();
        _ = text;
        return agenkit.Result{ .ok = try agenkit.Message.withText(
            self.allocator, .assistant, "response"
        ) };
    }

    pub fn agent(self: *MyAgent) agenkit.Agent {
        return .{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .process = processImpl,
                .deinit = deinitImpl,
            },
        };
    }
};
```

**Rust equivalent (trait — much simpler):**
```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct MyAgent;

// The trait provides the vtable automatically
#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::assistant("response"))
    }
}
```

### Memory: Allocators vs Ownership

**Zig (explicit allocators everywhere):**
```zig
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var msg = try agenkit.Message.withText(allocator, .user, "Hello");
    defer msg.deinit();

    var agent = try MyAgent.init(allocator);
    defer agent.deinit();

    const result = try agent.process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    std.debug.print("{s}\n", .{try response.contentAsText()});
}
```

**Rust equivalent (automatic deallocation via ownership):**
```rust
#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // No allocator needed — Rust tracks ownership automatically
    let agent = MyAgent;
    let message = Message::with_text("user", "Hello");

    let response = agent.process(message).await?;
    println!("{}", response.content_as_str().unwrap_or(""));

    // All values dropped automatically when they go out of scope
    Ok(())
}
```

### Async: Zig vs Tokio

**Zig async:**
```zig
// Zig async is compile-time; frames are manually managed
pub fn asyncProcess(agent: Agent, message: Message) !Message {
    var frame = async processInternal(agent, message);
    return await frame;
}
```

**Rust/Tokio async:**
```rust
// Tokio provides a full async runtime with thread pool
#[tokio::main]
async fn main() {
    // Spawn tasks on the Tokio runtime
    let handle = tokio::spawn(async {
        let agent = MyAgent;
        let msg = Message::user("Hello");
        agent.process(msg).await
    });

    let result = handle.await.unwrap();  // Wait for the task
}
```

### Error Handling

**Zig:**
```zig
pub const AgentError = error{
    ProcessingFailed,
    Timeout,
    InvalidInput,
    OutOfMemory,
};

fn process(agent: Agent, msg: Message) AgentError!Message {
    const result = agent.process(msg) catch |err| switch (err) {
        AgentError.Timeout => return AgentError.Timeout,
        else => return err,
    };
    return result;
}
```

**Rust:**
```rust
async fn process(
    agent: &impl Agent,
    msg: Message,
) -> Result<Message, AgentError> {
    agent.process(msg).await.map_err(|e| match e {
        AgentError::Timeout => AgentError::Timeout,
        other => other,
    })
}
```

### Comptime vs Const Generics

**Zig comptime:**
```zig
fn makeAgent(comptime T: type) T {
    return T.init();
}
```

**Rust const generics:**
```rust
fn make_agent<T: Agent + Default>() -> T {
    T::default()
}

// For array sizes
fn process_batch<const N: usize>(
    agents: [&dyn Agent; N],
    message: Message,
) -> [Option<Message>; N] {
    // compile-time known array size
    std::array::from_fn(|_| None)
}
```

### Key Migration Points

1. **No explicit `deinit`** — Rust's `Drop` trait handles cleanup automatically.
2. **No allocator parameter** — Rust's standard allocator is global; use `#[global_allocator]` to customize.
3. **Trait = vtable without manual wiring** — `impl Agent for T` generates the vtable automatically.
4. **Tokio is the async story** — Mature, multi-threaded, widely supported.
5. **`comptime` → `const fn` + generics** — Rust's const evaluation at compile time.
6. **`?T` → `Option<T>`** — Same concept, different syntax.
7. **`!T` → `Result<T, E>`** — Zig's error union maps to Rust's Result.

---

## Rust → Other Languages

### Rust → Python

**Why:** Faster prototyping, richer ML ecosystem, easier LLM integration with Python-native tools.

| Rust | Python |
|------|--------|
| `async fn process` | `async def process` |
| `Result<T, E>` | Raise exceptions |
| `Option<T>` | Return `None` |
| `tokio::spawn` | `asyncio.create_task` |
| `Arc<T>` | Reference counting (automatic) |
| `cargo add` | `uv add` / `pip install` |

```rust
// Rust
#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str { "my-agent" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::assistant("response"))
    }
}
```

```python
# Python equivalent
from agenkit import Agent, Message

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "my-agent"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content="response")
```

### Rust → Go

**Why:** Simpler deployment (single binary), no borrow checker, faster iteration cycles.

| Rust | Go |
|------|----|
| `trait Agent` | `interface Agent` |
| `Result<T, E>` | `(T, error)` |
| `Option<T>` | `*T` (nil check) |
| `tokio::spawn` | `go func()` |
| `Arc<T>` | No equivalent (GC handles it) |
| `Cargo.toml` | `go.mod` |

```rust
// Rust
#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str { "my-agent" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::assistant("response"))
    }
}
```

```go
// Go equivalent
type MyAgent struct{}

func (a *MyAgent) Name() string { return "my-agent" }

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    return agenkit.NewMessage("assistant", "response"), nil
}
```

### Rust → TypeScript

**Why:** Web deployment, universal code sharing, easier integration with JavaScript ecosystems.

| Rust | TypeScript |
|------|-----------|
| `trait Agent` | `interface Agent` |
| `Result<T, E>` | `Promise<T>` (throw on error) |
| `Option<T>` | `T \| undefined` |
| `tokio::join!` | `Promise.all` |
| `Vec<T>` | `T[]` |
| `Cargo.toml` | `package.json` |

```rust
// Rust
#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str { "my-agent" }
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::assistant("response"))
    }
}
```

```typescript
// TypeScript equivalent
class MyAgent implements Agent {
    get name(): string { return 'my-agent'; }

    async process(message: Message): Promise<Message> {
        return { role: 'assistant', content: 'response', metadata: {} };
    }
}
```

---

**Version**: v0.75.0
**Last Updated**: March 17, 2026

See also:
- [API.md](API.md) — Complete Rust API reference
- [GETTING_STARTED.md](GETTING_STARTED.md) — First agent tutorial
- [PATTERNS.md](PATTERNS.md) — All 11 patterns with examples
