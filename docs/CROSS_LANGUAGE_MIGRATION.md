# Cross-Language Migration Guide

**Migrate your agenkit agents between Python, Go, TypeScript, Rust, C++, and Zig with 100% feature parity.**

---

## Table of Contents

- [Introduction](#introduction)
- [Quick Reference](#quick-reference)
- [Migration Paths](#migration-paths)
  - [Python → Go](#python--go)
  - [Python → TypeScript](#python--typescript)
  - [Python → Rust](#python--rust)
  - [Python → C++](#python--c)
  - [Python → Zig](#python--zig)
  - [TypeScript → Go](#typescript--go)
  - [TypeScript → Rust](#typescript--rust)
  - [Go → Rust](#go--rust)
  - [Any → Any](#any--any-general-patterns)
- [Common Patterns](#common-patterns)
- [Language-Specific Idioms](#language-specific-idioms)
- [Testing Migration](#testing-migration)
- [Performance Considerations](#performance-considerations)

---

## Introduction

Agenkit provides **100% feature parity** across all 6 languages. This means:
- Same patterns work identically
- Same agent interfaces
- Same behavior and semantics
- Cross-language interoperability via protocols

### Why Migrate?

- **Performance**: Go/Rust/C++/Zig are faster (10-100x for compute-heavy tasks)
- **Type Safety**: Rust/Go/TypeScript catch errors at compile time
- **Memory Efficiency**: C++/Rust/Zig have fine-grained memory control
- **Ecosystem**: TypeScript for web, Python for ML, Go for services
- **Team Skills**: Match language to team expertise

### Migration Difficulty

| From → To | Difficulty | Time Estimate | Notes |
|-----------|-----------|---------------|-------|
| Python → Go | Easy | 2-4 hours | Similar async patterns, explicit errors |
| Python → TypeScript | Easy | 2-4 hours | Similar async/await, type annotations |
| Python → Rust | Medium | 4-8 hours | Ownership/borrowing learning curve |
| Python → C++ | Hard | 8-16 hours | Manual memory management |
| Python → Zig | Hard | 8-16 hours | Explicit allocators |
| TypeScript → Go | Easy | 2-4 hours | Similar concepts, different syntax |
| TypeScript → Rust | Medium | 4-8 hours | Ownership/borrowing |
| Go → Rust | Medium | 4-6 hours | Similar patterns, ownership |

---

## Quick Reference

### Core Concepts Mapping

| Concept | Python | Go | TypeScript | Rust | C++ | Zig |
|---------|--------|----|-----------|----|-----|-----|
| **Agent** | `class MyAgent(Agent)` | `type MyAgent struct{}` | `class MyAgent implements Agent` | `struct MyAgent` | `class MyAgent : public Agent` | `pub const MyAgent = struct` |
| **Async** | `async def` | `go func()` or sync | `async` | `async fn` | `std::future` | sync (blocking) |
| **Error Handling** | `raise Exception` | `return err` | `throw Error` | `Result<T, E>` | `throw` or `std::optional` | `error union !T` |
| **Message** | `Message(...)` | `core.Message{}` | `new Message(...)` | `Message {...}` | `Message{...}` | `Message{...}` |
| **Pattern** | Import from `patterns` | Import from `patterns` | Import from `patterns` | Import from `patterns` | Include from `patterns` | Import from `patterns` |

### Example: Basic Agent Across Languages

**Python:**
```python
from agenkit import Agent, Message

class GreetingAgent(Agent):
    @property
    def name(self) -> str:
        return "greeting"

    async def process(self, message: Message) -> Message:
        return Message(role="assistant", content=f"Hello, {message.content}!")
```

**Go:**
```go
package main

import (
    "context"

    "github.com/scttfrdmn/agenkit-go/agenkit"
)

type GreetingAgent struct{}

func (a *GreetingAgent) Name() string {
    return "greeting"
}

func (a *GreetingAgent) Capabilities() []string {
    return []string{"greeting"}
}

func (a *GreetingAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    // Content is `any`, so use ContentString() rather than concatenating directly.
    return agenkit.NewMessage("assistant", "Hello, "+msg.ContentString()+"!"), nil
}

func (a *GreetingAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
```

**TypeScript:**
```typescript
import { Agent, Message } from '@agenkit/core';

export class GreetingAgent implements Agent {
    get name(): string {  // ⚠️ Getter, not method!
        return 'greeting';
    }

    async process(message: Message): Promise<Message> {
        return {
            role: 'assistant',
            content: `Hello, ${message.content}!`,
        };
    }
}
```

**Rust:**
```rust
use agenkit::core::{Agent, Message};
use async_trait::async_trait;

pub struct GreetingAgent;

#[async_trait]
impl Agent for GreetingAgent {
    fn name(&self) -> &str {
        "greeting"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn std::error::Error + Send + Sync>> {
        Ok(Message {
            role: "assistant".to_string(),
            content: format!("Hello, {}!", message.content),
            ..Default::default()
        })
    }
}
```

**C++:**
```cpp
#include <agenkit/agent.hpp>
#include <future>

class GreetingAgent : public agenkit::Agent {
public:
    std::string name() const override {
        return "greeting";
    }

    std::future<agenkit::Message> process(agenkit::Message message) override {
        agenkit::Message response;
        response.role = "assistant";
        response.content = "Hello, " + std::get<std::string>(message.content) + "!";

        std::promise<agenkit::Message> promise;
        promise.set_value(std::move(response));
        return promise.get_future();
    }
};
```

**Zig:**
```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub const GreetingAgent = struct {
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator) GreetingAgent {
        return GreetingAgent{ .allocator = allocator };
    }

    pub fn name(self: *const GreetingAgent) []const u8 {
        _ = self;
        return "greeting";
    }

    pub fn process(self: *GreetingAgent, message: agenkit.Message) !agenkit.Message {
        const response_content = try std.fmt.allocPrint(
            self.allocator,
            "Hello, {s}!",
            .{message.content},
        );

        return agenkit.Message{
            .role = .assistant,
            .content = response_content,
            .metadata = null,
            .allocator = self.allocator,
        };
    }
};
```

---

## Migration Paths

### Python → Go

**Key Differences:**
1. **Async → Context**: Python's `async/await` → Go's `context.Context`
2. **Exceptions → Errors**: Python `raise` → Go `return err`
3. **Duck Typing → Interfaces**: Python implicit → Go explicit
4. **GIL-free**: Go has true parallelism

**Migration Checklist:**
- [ ] Replace `async def` with `func(ctx context.Context)`
- [ ] Change `raise Exception` to `return err`
- [ ] Add explicit error checks (`if err != nil`)
- [ ] Use `context.Context` for cancellation/timeouts
- [ ] Replace list comprehensions with loops
- [ ] Convert decorators to explicit wrappers

**Example Migration:**

**Before (Python):**
```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message

class Validator(Agent):
    @property
    def name(self) -> str:
        return "validator"

    async def process(self, message: Message) -> Message:
        if not message.content:
            raise ValueError("Empty content")
        return Message(role="assistant", content="Valid")

async def main():
    pipeline = SequentialAgent(
        agents=[Validator(), ProcessorAgent(), FormatterAgent()]
    )

    result = await pipeline.process(Message(role="user", content="data"))
    print(result.content)
```

**After (Go):**
```go
package main

import (
    "context"
    "errors"
    "fmt"

    "github.com/scttfrdmn/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit-go/patterns"
)

type Validator struct{}

func (v *Validator) Name() string {
    return "validator"
}

func (v *Validator) Capabilities() []string {
    return []string{"validation"}
}

func (v *Validator) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    if msg.ContentString() == "" {
        return nil, errors.New("empty content")
    }
    return agenkit.NewMessage("assistant", "Valid"), nil
}

func (v *Validator) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(v)
}

func main() {
    // NewSequentialAgent returns (agent, error) — a nil or empty agent list is an error,
    // not a silently empty pipeline.
    pipeline, err := patterns.NewSequentialAgent([]agenkit.Agent{
        &Validator{},
        &ProcessorAgent{},
        &FormatterAgent{},
    })
    if err != nil {
        panic(err)
    }

    result, err := pipeline.Process(context.Background(), agenkit.NewMessage("user", "data"))
    if err != nil {
        panic(err)
    }

    fmt.Println(result.ContentString())
}
```

**Common Pitfalls:**
1. **Forgetting error checks** - Go requires explicit `if err != nil`
2. **Context not passed** - Always pass `context.Context` through
3. **Pointer vs value receivers** - Use `*Agent` for methods that modify state
4. **Interface nil vs struct nil** - Check both `agent != nil` and concrete type

---

### Python → TypeScript

**Key Differences:**
1. **Similar async/await** - Nearly identical patterns
2. **Type annotations** - TypeScript more strict
3. **Property vs getter** - `@property` → `get name()`
4. **Promise-based** - Explicit Promise types

**Migration Checklist:**
- [ ] Replace `@property` with `get property()`
- [ ] Add explicit type annotations
- [ ] Change `None` to `null` or `undefined`
- [ ] Use `Promise<T>` return types
- [ ] Convert `dict` to objects or `Map`
- [ ] Replace `raise` with `throw`

**Example Migration:**

**Before (Python):**
```python
from agenkit.patterns import ParallelAgent
from agenkit import Agent, Message

class Analyst(Agent):
    def __init__(self, specialty: str):
        self._specialty = specialty

    @property
    def name(self) -> str:
        return f"analyst-{self._specialty}"

    async def process(self, message: Message) -> Message:
        analysis = await self.analyze(message.content)
        return Message(
            role="assistant",
            content=analysis,
            metadata={"specialty": self._specialty}
        )

    async def analyze(self, data: str) -> str:
        # Simulate analysis
        await asyncio.sleep(0.5)
        return f"{self._specialty} analysis: {data}"

async def main():
    analysts = ParallelAgent(
        agents=[
            Analyst("technical"),
            Analyst("business"),
            Analyst("risk")
        ],
        aggregation="concat"
    )

    result = await analysts.process(Message(role="user", content="Project X"))
    print(result.content)
```

**After (TypeScript):**
```typescript
import { ParallelAgent } from '@agenkit/patterns';
import { Agent, Message } from '@agenkit/core';

class Analyst implements Agent {
    private specialty: string;

    constructor(specialty: string) {
        this.specialty = specialty;
    }

    get name(): string {  // ⚠️ Getter, not method
        return `analyst-${this.specialty}`;
    }

    async process(message: Message): Promise<Message> {
        const analysis = await this.analyze(message.content as string);
        return {
            role: 'assistant',
            content: analysis,
            metadata: { specialty: this.specialty },
        };
    }

    private async analyze(data: string): Promise<string> {
        // Simulate analysis
        await new Promise(resolve => setTimeout(resolve, 500));
        return `${this.specialty} analysis: ${data}`;
    }
}

async function main() {
    const analysts = new ParallelAgent({
        agents: [
            new Analyst('technical'),
            new Analyst('business'),
            new Analyst('risk'),
        ],
        aggregation: 'concat',
    });

    const result = await analysts.process({
        role: 'user',
        content: 'Project X',
    });

    console.log(result.content);
}

main();
```

**Common Pitfalls:**
1. **Getter vs method** - TypeScript uses `get name()`, not `name()`
2. **Null vs undefined** - TypeScript distinguishes, Python doesn't
3. **Import syntax** - ES6 modules vs Python imports
4. **Array methods** - `.map()`, `.filter()` instead of list comprehensions

---

### Python → Rust

**Key Differences:**
1. **Ownership/Borrowing** - Rust's core concept, no GC
2. **Error handling** - `Result<T, E>` instead of exceptions
3. **Explicit lifetimes** - Memory safety at compile time
4. **No null** - `Option<T>` for nullable values
5. **Trait system** - Similar to interfaces but more powerful

**Migration Checklist:**
- [ ] Understand ownership (move, borrow, clone)
- [ ] Replace exceptions with `Result<T, E>`
- [ ] Use `Option<T>` for nullable values
- [ ] Add `async_trait` for async trait methods
- [ ] Handle `Send + Sync` for thread safety
- [ ] Use `Box<dyn Error>` for error types

**Example Migration:**

**Before (Python):**
```python
from agenkit.patterns import ReflectionAgent
from agenkit import Agent, Message

class Writer(Agent):
    @property
    def name(self) -> str:
        return "writer"

    async def process(self, message: Message) -> Message:
        content = self.generate(message.content)
        return Message(role="assistant", content=content)

    def generate(self, prompt: str) -> str:
        return f"Draft: {prompt}"

class Critic(Agent):
    @property
    def name(self) -> str:
        return "critic"

    async def process(self, message: Message) -> Message:
        score = self.evaluate(message.content)
        return Message(
            role="assistant",
            content=f"Score: {score}",
            metadata={"reflection_score": score}
        )

    def evaluate(self, content: str) -> float:
        return 0.85 if len(content) > 20 else 0.5

async def main():
    refiner = ReflectionAgent(
        agent=Writer(),
        critic=Critic(),
        max_iterations=3,
        improvement_threshold=0.9
    )

    result = await refiner.process(Message(role="user", content="Write essay"))
    print(result.content)
```

**After (Rust):**
```rust
use agenkit::core::{Agent, Message};
use agenkit::patterns::ReflectionAgent;
use async_trait::async_trait;
use std::error::Error;

pub struct Writer;

#[async_trait]
impl Agent for Writer {
    fn name(&self) -> &str {
        "writer"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        let content = self.generate(&message.content);
        Ok(Message {
            role: "assistant".to_string(),
            content,
            ..Default::default()
        })
    }
}

impl Writer {
    fn generate(&self, prompt: &str) -> String {
        format!("Draft: {}", prompt)
    }
}

pub struct Critic;

#[async_trait]
impl Agent for Critic {
    fn name(&self) -> &str {
        "critic"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        let score = self.evaluate(&message.content);
        let mut metadata = std::collections::HashMap::new();
        metadata.insert("reflection_score".to_string(), score.to_string());

        Ok(Message {
            role: "assistant".to_string(),
            content: format!("Score: {}", score),
            metadata: Some(metadata),
            ..Default::default()
        })
    }
}

impl Critic {
    fn evaluate(&self, content: &str) -> f64 {
        if content.len() > 20 { 0.85 } else { 0.5 }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let refiner = ReflectionAgent::new(
        Box::new(Writer),
        Box::new(Critic),
        3,  // max_iterations
        0.9,  // improvement_threshold
    );

    let result = refiner.process(Message {
        role: "user".to_string(),
        content: "Write essay".to_string(),
        ..Default::default()
    }).await?;

    println!("{}", result.content);
    Ok(())
}
```

**Common Pitfalls:**
1. **Ownership confusion** - Use `&` for borrows, `clone()` when needed
2. **Async trait** - Requires `#[async_trait]` macro
3. **Error propagation** - Use `?` operator instead of try/except
4. **String types** - `&str` (borrowed) vs `String` (owned)
5. **Lifetime annotations** - Sometimes needed for references

**Learning Resources:**
- [The Rust Book](https://doc.rust-lang.org/book/) - Chapters 4 (Ownership), 10 (Traits), 17 (Async)
- [Async Rust](https://rust-lang.github.io/async-book/)

---

### Python → C++

**Key Differences:**
1. **Manual memory management** - RAII, smart pointers
2. **Header files** - Declaration vs implementation
3. **Templates** - Generic programming
4. **Move semantics** - `std::move` for efficiency
5. **Explicit resource management** - Constructors/destructors

**Migration Checklist:**
- [ ] Use smart pointers (`unique_ptr`, `shared_ptr`)
- [ ] Separate `.hpp` headers and `.cpp` implementations
- [ ] Use RAII for resource management
- [ ] Replace `async/await` with `std::future` or coroutines (C++20)
- [ ] Handle exceptions or use `std::optional<T>`
- [ ] Use `std::move` for large objects

**Example Migration:**

**Before (Python):**
```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message

class DataProcessor(Agent):
    def __init__(self, buffer_size: int = 1024):
        self.buffer_size = buffer_size
        self.buffer = []

    @property
    def name(self) -> str:
        return "processor"

    async def process(self, message: Message) -> Message:
        self.buffer.append(message.content)
        processed = self.process_buffer()
        return Message(role="assistant", content=processed)

    def process_buffer(self) -> str:
        return f"Processed {len(self.buffer)} items"
```

**After (C++):**

**processor.hpp:**
```cpp
#ifndef AGENKIT_PROCESSOR_HPP
#define AGENKIT_PROCESSOR_HPP

#include <agenkit/agent.hpp>
#include <vector>
#include <string>
#include <future>
#include <memory>

namespace myapp {

class DataProcessor : public agenkit::Agent {
private:
    size_t buffer_size_;
    std::vector<std::string> buffer_;

    std::string process_buffer() const;

public:
    explicit DataProcessor(size_t buffer_size = 1024);
    ~DataProcessor() override = default;

    std::string name() const override;
    std::future<agenkit::Message> process(agenkit::Message message) override;
};

}  // namespace myapp

#endif  // AGENKIT_PROCESSOR_HPP
```

**processor.cpp:**
```cpp
#include "processor.hpp"
#include <sstream>

namespace myapp {

DataProcessor::DataProcessor(size_t buffer_size)
    : buffer_size_(buffer_size) {
    buffer_.reserve(buffer_size_);
}

std::string DataProcessor::name() const {
    return "processor";
}

std::future<agenkit::Message> DataProcessor::process(agenkit::Message message) {
    // Extract content
    auto content = std::get<std::string>(message.content);
    buffer_.push_back(std::move(content));

    // Process buffer
    auto processed = process_buffer();

    // Create response
    agenkit::Message response;
    response.role = "assistant";
    response.content = std::move(processed);

    // Return as future
    std::promise<agenkit::Message> promise;
    promise.set_value(std::move(response));
    return promise.get_future();
}

std::string DataProcessor::process_buffer() const {
    std::ostringstream oss;
    oss << "Processed " << buffer_.size() << " items";
    return oss.str();
}

}  // namespace myapp
```

**Common Pitfalls:**
1. **Memory leaks** - Always use smart pointers
2. **Dangling references** - Be careful with `&` and lifetimes
3. **Move semantics** - Use `std::move` to avoid copies
4. **Header guards** - Always include `#ifndef` guards
5. **Const correctness** - Mark read-only methods `const`

**Best Practices:**
- Use `std::unique_ptr` for single ownership
- Use `std::shared_ptr` for shared ownership
- Use `std::move` for large objects
- Follow RAII (Resource Acquisition Is Initialization)
- Prefer `override` keyword for virtual methods

---

### Python → Zig

**Key Differences:**
1. **Explicit allocators** - No hidden allocations
2. **Comptime** - Compile-time execution
3. **Error unions** - `!T` for fallible functions
4. **No hidden control flow** - Everything explicit
5. **Manual memory management** - But safer than C

**Migration Checklist:**
- [ ] Pass `std.mem.Allocator` explicitly
- [ ] Use error unions (`!T`) for fallible functions
- [ ] Call `deinit()` for cleanup
- [ ] Understand `comptime` for generics
- [ ] Use `defer` for cleanup
- [ ] Handle errors with `try` or `catch`

**Example Migration:**

**Before (Python):**
```python
from agenkit import Agent, Message

class CacheAgent(Agent):
    def __init__(self):
        self.cache = {}

    @property
    def name(self) -> str:
        return "cache"

    async def process(self, message: Message) -> Message:
        key = message.metadata.get("key", "default")

        if key in self.cache:
            return Message(
                role="assistant",
                content=self.cache[key],
                metadata={"cache_hit": True}
            )

        # Simulate processing
        result = f"Processed: {message.content}"
        self.cache[key] = result

        return Message(
            role="assistant",
            content=result,
            metadata={"cache_hit": False}
        )
```

**After (Zig):**
```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub const CacheAgent = struct {
    allocator: std.mem.Allocator,
    cache: std.StringHashMap([]const u8),

    pub fn init(allocator: std.mem.Allocator) !CacheAgent {
        return CacheAgent{
            .allocator = allocator,
            .cache = std.StringHashMap([]const u8).init(allocator),
        };
    }

    pub fn deinit(self: *CacheAgent) void {
        // Free all cached values
        var it = self.cache.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.value_ptr.*);
        }
        self.cache.deinit();
    }

    pub fn name(self: *const CacheAgent) []const u8 {
        _ = self;
        return "cache";
    }

    pub fn process(self: *CacheAgent, message: agenkit.Message) !agenkit.Message {
        const key = if (message.metadata) |meta|
            meta.get("key") orelse "default"
        else
            "default";

        // Check cache
        if (self.cache.get(key)) |cached| {
            return agenkit.Message{
                .role = .assistant,
                .content = cached,
                .metadata = blk: {
                    var meta = std.StringHashMap([]const u8).init(self.allocator);
                    try meta.put("cache_hit", "true");
                    break :blk meta;
                },
                .allocator = self.allocator,
            };
        }

        // Process and cache
        const result = try std.fmt.allocPrint(
            self.allocator,
            "Processed: {s}",
            .{message.content},
        );

        // Store in cache
        try self.cache.put(key, result);

        return agenkit.Message{
            .role = .assistant,
            .content = result,
            .metadata = blk: {
                var meta = std.StringHashMap([]const u8).init(self.allocator);
                try meta.put("cache_hit", "false");
                break :blk meta;
            },
            .allocator = self.allocator,
        };
    }
};
```

**Common Pitfalls:**
1. **Forgetting allocators** - Every allocation needs an allocator
2. **Memory leaks** - Must call `deinit()` or use `defer`
3. **Error unions** - Use `try` or `catch` for error handling
4. **Slice vs array** - `[]const u8` (slice) vs `[10]u8` (array)
5. **Comptime confusion** - Some things run at compile time

**Best Practices:**
- Use `ArenaAllocator` for temporary allocations
- Use `defer` for cleanup
- Pass allocator explicitly everywhere
- Use error unions (`!T`) for fallible operations
- Prefer `const` for immutable data

---

### TypeScript → Go

**Key Differences:**
1. **Promises → Goroutines/Context** - Different concurrency models
2. **Getter → Method** - TypeScript `get name()` → Go `Name()`
3. **Interface satisfaction** - Go implicit, TypeScript explicit
4. **Error handling** - Go `return err`, TypeScript `throw`

**Migration Checklist:**
- [ ] Change `get property()` to `Property()` method
- [ ] Replace `Promise<T>` with `(T, error)` return
- [ ] Add `context.Context` parameter
- [ ] Implement interfaces explicitly
- [ ] Handle errors with `if err != nil`

**Example Migration:**

**Before (TypeScript):**
```typescript
import { RouterAgent } from '@agenkit/patterns';
import { Agent, Message } from '@agenkit/core';

class BillingAgent implements Agent {
    get name(): string {
        return 'billing';
    }

    async process(message: Message): Promise<Message> {
        // Handle billing queries
        return {
            role: 'assistant',
            content: 'Billing: Your account balance is $50',
        };
    }
}

class TechnicalAgent implements Agent {
    get name(): string {
        return 'technical';
    }

    async process(message: Message): Promise<Message> {
        // Handle technical queries
        return {
            role: 'assistant',
            content: 'Technical: Troubleshooting...',
        };
    }
}

async function main() {
    const router = new RouterAgent({
        routes: {
            billing: new BillingAgent(),
            technical: new TechnicalAgent(),
        },
        routingStrategy: 'keyword',
    });

    const result = await router.process({
        role: 'user',
        content: 'I need help with my bill',
    });

    console.log(result.content);
}
```

**After (Go):**
```go
package main

import (
    "context"
    "fmt"
    "strings"

    "github.com/scttfrdmn/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit-go/patterns"
)

type BillingAgent struct{}

func (a *BillingAgent) Name() string {
    return "billing"
}

func (a *BillingAgent) Capabilities() []string {
    return []string{"billing"}
}

func (a *BillingAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    // Handle billing queries
    return agenkit.NewMessage("assistant", "Billing: Your account balance is $50"), nil
}

func (a *BillingAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}

type TechnicalAgent struct{}

func (a *TechnicalAgent) Name() string {
    return "technical"
}

func (a *TechnicalAgent) Capabilities() []string {
    return []string{"technical"}
}

func (a *TechnicalAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    // Handle technical queries
    return agenkit.NewMessage("assistant", "Technical: Troubleshooting..."), nil
}

func (a *TechnicalAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}

// Routing is done by a ClassifierAgent — an agenkit.Agent that also implements
// Classify. The returned key selects an entry in RouterConfig.Agents.
type KeywordClassifier struct{}

func (c *KeywordClassifier) Name() string { return "keyword-classifier" }

func (c *KeywordClassifier) Capabilities() []string { return []string{"classification"} }

func (c *KeywordClassifier) Classify(ctx context.Context, msg *agenkit.Message) (string, error) {
    content := strings.ToLower(msg.ContentString())
    if strings.Contains(content, "bill") || strings.Contains(content, "payment") {
        return "billing", nil
    }
    if strings.Contains(content, "error") || strings.Contains(content, "broken") {
        return "technical", nil
    }
    return "", nil // falls back to DefaultKey
}

func (c *KeywordClassifier) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    category, err := c.Classify(ctx, msg)
    if err != nil {
        return nil, err
    }
    return agenkit.NewMessage("assistant", category), nil
}

func (c *KeywordClassifier) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(c)
}

func main() {
    router, err := patterns.NewRouterAgent(&patterns.RouterConfig{
        Classifier: &KeywordClassifier{},
        Agents: map[string]agenkit.Agent{
            "billing":   &BillingAgent{},
            "technical": &TechnicalAgent{},
        },
        DefaultKey: "technical",
    })
    if err != nil {
        panic(err)
    }

    result, err := router.Process(context.Background(),
        agenkit.NewMessage("user", "I need help with my bill"))
    if err != nil {
        panic(err)
    }

    fmt.Println(result.ContentString())
}
```

---

### TypeScript → Rust

**Key Differences:**
1. **Ownership** - Rust's core concept
2. **Promises → async_trait** - Different async models
3. **Null safety** - `Option<T>` instead of `null | undefined`
4. **Error handling** - `Result<T, E>` instead of `throw`

**Migration Checklist:**
- [ ] Use `Box<dyn Agent>` for dynamic dispatch
- [ ] Add `#[async_trait]` for async traits
- [ ] Replace `null` with `Option<T>`
- [ ] Use `Result<T, E>` for errors
- [ ] Understand ownership (borrow checker)

---

### Go → Rust

**Key Differences:**
1. **Ownership vs GC** - Rust compile-time, Go runtime
2. **Error types** - Go `error`, Rust `Result<T, E>`
3. **Traits vs interfaces** - Similar but more powerful in Rust
4. **Channels** - Different concurrency primitives

**Migration Checklist:**
- [ ] Replace `error` with `Result<T, E>`
- [ ] Use `Option<T>` instead of nil
- [ ] Understand lifetimes for references
- [ ] Use `tokio` for async runtime
- [ ] Replace goroutines with `tokio::spawn`

---

### Any → Any (General Patterns)

**Universal Migration Steps:**

1. **Understand the Agent Interface**
   - All languages have: `name()` and `process(message)`
   - Return types vary by language idioms

2. **Match Language Idioms**
   - Async: Python/TypeScript/Rust (`async/await`), Go (sync/goroutines), C++/Zig (sync)
   - Errors: Python/TypeScript (`throw`), Go (`return err`), Rust (`Result`), Zig (`!T`)
   - Memory: Python/TypeScript/Go (GC), Rust (ownership), C++/Zig (manual)

3. **Use Same Patterns**
   - Sequential, Parallel, Router, Fallback - all work identically
   - Configuration may differ slightly by language

4. **Test Equivalence**
   - Use cross-language test suite (`tests/cross_language/`)
   - Verify same inputs produce same outputs

---

## Common Patterns

### Error Handling Across Languages

**Python:**
```python
async def process(self, message: Message) -> Message:
    if not message.content:
        raise ValueError("Empty content")
    return Message(role="assistant", content="OK")
```

**Go:**
```go
func (a *Agent) Process(ctx context.Context, msg core.Message) (core.Message, error) {
    if msg.Content == "" {
        return core.Message{}, errors.New("empty content")
    }
    return core.Message{Role: "assistant", Content: "OK"}, nil
}
```

**TypeScript:**
```typescript
async process(message: Message): Promise<Message> {
    if (!message.content) {
        throw new Error('Empty content');
    }
    return { role: 'assistant', content: 'OK' };
}
```

**Rust:**
```rust
async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
    if message.content.is_empty() {
        return Err("Empty content".into());
    }
    Ok(Message { role: "assistant".into(), content: "OK".into(), ..Default::default() })
}
```

### Async Patterns

**Python:**
```python
result = await agent.process(message)
```

**Go (Context-based):**
```go
result, err := agent.Process(ctx, message)
if err != nil {
    return err
}
```

**TypeScript:**
```typescript
const result = await agent.process(message);
```

**Rust:**
```rust
let result = agent.process(message).await?;
```

**C++ (Futures):**
```cpp
auto future = agent.process(message);
auto result = future.get();
```

**Zig (Synchronous):**
```zig
const result = try agent.process(message);
```

---

## Language-Specific Idioms

### Python
- **Async/await**: Native support
- **Duck typing**: Implicit interfaces
- **List comprehensions**: `[x for x in items]`
- **Context managers**: `with resource as r:`
- **Decorators**: `@property`, `@staticmethod`

### Go
- **Context**: Pass `context.Context` everywhere
- **Error handling**: `if err != nil { return err }`
- **Goroutines**: `go func() {}`
- **Defer**: Cleanup with `defer func()`
- **Interfaces**: Implicit satisfaction

### TypeScript
- **Getters**: `get name(): string`
- **Promises**: `async/await` with `Promise<T>`
- **Type guards**: `typeof`, `instanceof`
- **Destructuring**: `const { x, y } = obj`
- **Modules**: ES6 `import/export`

### Rust
- **Ownership**: Move, borrow, clone
- **Traits**: `impl Trait for Type`
- **Error handling**: `Result<T, E>` with `?`
- **Option**: `Option<T>` for nullable
- **Async**: `#[async_trait]` macro

### C++
- **RAII**: Resource management
- **Smart pointers**: `unique_ptr`, `shared_ptr`
- **Move semantics**: `std::move`
- **Const correctness**: `const` methods
- **Templates**: Generic programming

### Zig
- **Allocators**: Pass everywhere
- **Error unions**: `!T` for fallible
- **Comptime**: Compile-time execution
- **Defer**: Cleanup
- **Slices**: `[]const u8`

---

## Testing Migration

### Cross-Language Test Suite

Agenkit includes a cross-language test suite to verify equivalence:

```bash
cd tests/cross_language
python run_equivalence_tests.py --languages python go --patterns sequential
```

This ensures your migrated agent behaves identically to the original.

### Unit Testing Patterns

**Python (pytest):**
```python
import pytest
from agenkit import Message

@pytest.mark.asyncio
async def test_agent():
    agent = MyAgent()
    result = await agent.process(Message(role="user", content="test"))
    assert result.content == "expected"
```

**Go (testing):**
```go
func TestAgent(t *testing.T) {
    agent := &MyAgent{}
    result, err := agent.Process(context.Background(), core.Message{
        Role: "user", Content: "test",
    })
    if err != nil {
        t.Fatal(err)
    }
    if result.Content != "expected" {
        t.Errorf("got %v, want expected", result.Content)
    }
}
```

**TypeScript (Vitest):**
```typescript
import { describe, it, expect } from 'vitest';

describe('MyAgent', () => {
    it('should process message', async () => {
        const agent = new MyAgent();
        const result = await agent.process({ role: 'user', content: 'test' });
        expect(result.content).toBe('expected');
    });
});
```

**Rust (cargo test):**
```rust
#[tokio::test]
async fn test_agent() {
    let agent = MyAgent;
    let result = agent.process(Message {
        role: "user".into(),
        content: "test".into(),
        ..Default::default()
    }).await.unwrap();
    assert_eq!(result.content, "expected");
}
```

---

## Performance Considerations

### Performance by Language

Based on actual benchmarks:

| Language | Sequential (3 agents) | Parallel (3 agents) | Memory Efficiency |
|----------|----------------------|---------------------|-------------------|
| **Python** | 1.35 μs | 2.1 μs | Low (GC overhead) |
| **Go** | 0.45 μs | 0.18 μs | High (efficient GC) |
| **TypeScript** | 1.2 μs | 1.8 μs | Medium (V8 JIT) |
| **Rust** | 0.4 μs | 0.18 μs | Highest (zero-cost) |
| **C++** | 0.3 μs | 0.15 μs | Highest (manual) |
| **Zig** | 0.2 μs | 0.3 μs | Highest (manual) |

### When to Choose Each Language

**Python:**
- Rapid prototyping
- ML/AI integrations
- Team expertise
- Acceptable latency (<100ms)

**Go:**
- High throughput services
- Concurrent workloads
- Fast development + good performance
- Cloud services

**TypeScript:**
- Web applications
- Full-stack JS/TS teams
- Browser-side agents
- Node.js services

**Rust:**
- Maximum performance
- Memory safety critical
- Systems programming
- Long-running services

**C++:**
- Legacy system integration
- Maximum control
- Embedded systems
- Highest performance critical

**Zig:**
- Systems programming
- Explicit control needed
- Embedded systems
- Maximum performance with safety

### Migration for Performance

If migrating for performance:
1. **Profile first** - Identify bottlenecks
2. **Migrate hotspots** - Only rewrite slow parts
3. **Use FFI** - Call Go/Rust from Python via FFI
4. **Benchmark** - Measure before/after
5. **Consider cost** - Development time vs performance gain

---

## Conclusion

Agenkit's cross-language feature parity makes migration straightforward:
- **Same patterns** work in all languages
- **Similar APIs** reduce learning curve
- **Test suite** verifies equivalence
- **Performance benchmarks** guide language choice

### Migration Summary

| From | To | Difficulty | Why Migrate |
|------|----|-----------:|-------------|
| Python | Go | ⭐⭐ Easy | Performance, concurrency |
| Python | TypeScript | ⭐⭐ Easy | Web integration, type safety |
| Python | Rust | ⭐⭐⭐ Medium | Maximum performance, safety |
| Python | C++ | ⭐⭐⭐⭐ Hard | Legacy integration, control |
| Python | Zig | ⭐⭐⭐⭐ Hard | Systems programming, explicit control |

### Next Steps

1. **Read Getting Started** guide for target language
2. **Run examples** in target language
3. **Migrate simplest agent** first
4. **Test equivalence** with cross-language suite
5. **Iterate** on remaining agents

### Resources

- **Getting Started Guides**: `docs/getting-started/{LANGUAGE}.md`
- **Examples**: `examples/` (all languages)
- **Cross-Language Tests**: `tests/cross_language/`
- **Performance Benchmarks**: `docs/PATTERN_BENCHMARK_RESULTS.md`

---

**Happy migrating! 🚀**
