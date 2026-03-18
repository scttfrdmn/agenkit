# Agenkit C++ Migration Guide

Migration guides for moving between C++ and other Agenkit implementations.

## Table of Contents

- [Python → C++](#python--c)
- [Go → C++](#go--c)
- [TypeScript → C++](#typescript--c)
- [Rust → C++](#rust--c)
- [Zig → C++](#zig--c)
- [C++ → Python](#c--python)
- [C++ → Go](#c--go)
- [C++ → TypeScript](#c--typescript)
- [C++ → Rust](#c--rust)
- [C++ → Zig](#c--zig)

---

## Python → C++

**Why migrate to C++?**
- 20–100x faster execution (benchmarked)
- Predictable memory — no GC pauses
- Direct hardware and system access
- Native threading with `std::thread` / `std::async`
- Single binary deployment

**When to stay with Python:**
- Rapid prototyping and experimentation
- Heavy ML/data science workloads (NumPy, PyTorch)
- Scripting and automation
- Smaller teams without C++ expertise

---

### Project Setup

**Python (pyproject.toml / requirements):**
```toml
[project]
name = "my-agent"
version = "0.1.0"
dependencies = [
    "agenkit>=0.75.0",
]
```

```bash
uv add agenkit
uv run python main.py
```

**C++ (CMakeLists.txt):**
```cmake
cmake_minimum_required(VERSION 3.16)
project(my_agent CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
FetchContent_Declare(
    agenkit
    GIT_REPOSITORY https://github.com/scttfrdmn/agenkit.git
    SOURCE_SUBDIR  agenkit-cpp
    GIT_TAG        v0.75.0
)
FetchContent_MakeAvailable(agenkit)

add_executable(my_agent src/main.cpp)
target_link_libraries(my_agent PRIVATE agenkit::agenkit)
```

```bash
mkdir build && cd build
cmake ..
cmake --build .
./my_agent
```

---

### Core Concepts

#### Message Creation

**Python:**
```python
from agenkit import Message

msg = Message(role="user", content="Hello!")
msg.metadata["session_id"] = "abc-123"

text = msg.content  # str
```

**C++:**
```cpp
#include <agenkit/core/message.hpp>
using namespace agenkit::core;

auto msg = Message::with_text("user", "Hello!");
msg.set_metadata("session_id", "abc-123");

auto text = msg.content().as_text();  // std::string
```

#### Agent Implementation

**Python:**
```python
from agenkit import Agent, Message, Result

class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo"

    async def process(self, message: Message) -> Result[Message, AgentError]:
        response = Message(role="assistant", content=message.content)
        return Result.ok(response)
```

**C++:**
```cpp
#include <agenkit/core/agent.hpp>
using namespace agenkit::core;

class EchoAgent : public Agent {
public:
    std::string name() const override { return "echo"; }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        auto response = Message::with_text(
            "assistant", message.content().as_text()
        );
        return make_ready_future(
            Result<Message, AgentError>::ok(std::move(response))
        );
    }
};
```

#### Async/Await vs std::future

**Python (async/await):**
```python
# Async is the default; use await at call sites
result = await agent.process(message)
if result.is_ok:
    print(result.value.content)
```

**C++ (std::future):**
```cpp
// process() returns std::future
auto future = agent->process(message);

// Block until ready
auto result = future.get();
if (result.is_ok()) {
    std::cout << result.value().content().as_text() << "\n";
}

// Or use std::async for non-blocking composition
auto composed = std::async(std::launch::async, [&] {
    return agent->process(message).get();
});
```

#### Error Handling

**Python:**
```python
from agenkit import AgentError

try:
    result = await agent.process(message)
    if result.is_ok:
        print(result.value.content)
    else:
        print(f"Error: {result.error.message}")
except Exception as e:
    print(f"Exception: {e}")
```

**C++:**
```cpp
// Errors are values, not exceptions, in normal processing
auto result = agent->process(message).get();
if (result.is_ok()) {
    std::cout << result.value().content().as_text() << "\n";
} else {
    std::cerr << "Error: " << result.error().message() << "\n";
}

// Catch unexpected exceptions from LLM adapters
try {
    auto result = agent->process(message).get();
    // handle result
} catch (const std::exception& e) {
    std::cerr << "Unexpected: " << e.what() << "\n";
}
```

#### Type Annotations vs Templates

**Python (dynamic typing with hints):**
```python
from typing import List

def process_batch(
    agent: Agent,
    messages: List[Message]
) -> List[Result[Message, AgentError]]:
    return [await agent.process(m) for m in messages]
```

**C++ (static templates):**
```cpp
#include <vector>
#include <future>

std::vector<std::future<Result<Message, AgentError>>>
process_batch(
    std::shared_ptr<Agent> agent,
    std::vector<Message> messages
) {
    std::vector<std::future<Result<Message, AgentError>>> futures;
    futures.reserve(messages.size());

    for (auto& msg : messages) {
        futures.push_back(agent->process(std::move(msg)));
    }

    return futures;
}

// Wait for all
for (auto& f : futures) {
    auto result = f.get();
    // handle result
}
```

#### Memory Management

**Python (garbage collected):**
```python
# Memory managed automatically
agent = EchoAgent()
message = Message(role="user", content="Hello")
result = await agent.process(message)
# Everything cleaned up by GC
```

**C++ (RAII — deterministic cleanup):**
```cpp
// Cleanup happens when the object goes out of scope
{
    auto agent = std::make_unique<EchoAgent>();
    auto message = Message::with_text("user", "Hello");
    auto result = agent->process(std::move(message)).get();
    // agent destroyed here, memory freed immediately
}
// message is moved-from, result is also destroyed
```

---

### Middleware Mapping

| Python | C++ |
|--------|-----|
| `RetryDecorator(agent, max_retries=3)` | `RetryDecorator(agent, 3, 100)` |
| `TimeoutDecorator(agent, timeout=5.0)` | `TimeoutDecorator(agent, 5000)` |
| `CircuitBreakerDecorator(agent, threshold=5)` | `CircuitBreakerDecorator(agent, 5, 30000)` |
| `RateLimiterDecorator(agent, rps=10)` | `RateLimiterDecorator(agent, 10, 1000)` |

**Note:** C++ uses milliseconds for time parameters. Python uses seconds (floats).

---

## Go → C++

**Why migrate to C++?**
- Finer-grained memory control (no GC pauses)
- Lower-level system/hardware access
- SIMD and GPU acceleration
- Integration with existing C/C++ libraries
- Higher peak throughput in compute-bound workloads

**When to stay with Go:**
- Simpler concurrency with goroutines
- Faster compilation and iteration
- Better developer ergonomics for most server workloads
- Smaller team with Go expertise

---

### Project Setup

**Go (go.mod):**
```go
module my-agent

go 1.21

require github.com/scttfrdmn/agenkit/agenkit-go v0.75.0
```

```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
go run main.go
```

**C++ (CMakeLists.txt):** (see Python section above — same structure)

---

### Core Concepts

#### Agent Implementation

**Go:**
```go
package main

import (
    "context"
    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
)

type EchoAgent struct{}

func (a *EchoAgent) Name() string { return "echo" }

func (a *EchoAgent) Process(
    ctx context.Context, msg agenkit.Message,
) (agenkit.Message, error) {
    return agenkit.Message{
        Role:    "assistant",
        Content: msg.Content,
    }, nil
}
```

**C++:**
```cpp
class EchoAgent : public agenkit::core::Agent {
public:
    std::string name() const override { return "echo"; }

    std::future<agenkit::core::Result<agenkit::core::Message,
                                       agenkit::core::AgentError>>
    process(agenkit::core::Message message) override {
        auto response = agenkit::core::Message::with_text(
            "assistant", message.content().as_text()
        );
        return agenkit::core::make_ready_future(
            agenkit::core::Result<agenkit::core::Message,
                                   agenkit::core::AgentError>::ok(
                std::move(response)
            )
        );
    }
};
```

#### Goroutines vs std::async

**Go (goroutines + channels):**
```go
results := make(chan agenkit.Message, len(messages))

for _, msg := range messages {
    go func(m agenkit.Message) {
        resp, err := agent.Process(ctx, m)
        if err == nil {
            results <- resp
        }
    }(msg)
}

// Collect
for i := 0; i < len(messages); i++ {
    r := <-results
    fmt.Println(r.Content)
}
```

**C++ (std::async + std::future):**
```cpp
std::vector<std::future<Result<Message, AgentError>>> futures;

for (auto& msg : messages) {
    futures.push_back(agent->process(std::move(msg)));
}

for (auto& f : futures) {
    auto result = f.get();
    if (result.is_ok()) {
        std::cout << result.value().content().as_text() << "\n";
    }
}
```

#### Error Handling

**Go (multiple return values):**
```go
result, err := agent.Process(ctx, msg)
if err != nil {
    log.Printf("failed: %v", err)
    return
}
fmt.Println(result.Content)
```

**C++ (Result type):**
```cpp
auto result = agent->process(msg).get();
if (result.is_err()) {
    std::cerr << "failed: " << result.error().message() << "\n";
    return;
}
std::cout << result.value().content().as_text() << "\n";
```

#### Memory: GC vs RAII

**Go (garbage collected):**
```go
// Memory managed by GC — no explicit cleanup
agent := NewEchoAgent()
defer agent.Close()  // Optional cleanup for resources
```

**C++ (RAII — deterministic):**
```cpp
// Cleanup is automatic and deterministic
auto agent = std::make_unique<EchoAgent>();
// agent destroyed when it goes out of scope — no defer needed
```

#### Interfaces

**Go:**
```go
type Agent interface {
    Name() string
    Process(ctx context.Context, msg Message) (Message, error)
}
```

**C++:**
```cpp
class Agent {
public:
    virtual std::string name() const = 0;
    virtual std::future<Result<Message, AgentError>>
    process(Message message) = 0;
    virtual ~Agent() = default;
};
```

---

## TypeScript → C++

**Why migrate to C++?**
- Native performance — no JIT warmup, no runtime overhead
- 10–20x faster for compute-intensive workloads
- True native binary — deploy without Node.js runtime
- Lower memory footprint
- Systems programming access (sockets, file I/O without Node abstractions)

**When to stay with TypeScript:**
- Web browser deployment
- Universal code (Node.js + browser)
- Rich npm ecosystem
- Rapid development with hot reload
- Smaller teams preferring JavaScript/TypeScript

---

### Project Setup

**TypeScript (package.json):**
```json
{
  "name": "my-agent",
  "dependencies": {
    "agenkit": "^0.75.0"
  }
}
```

```bash
npm install
npx ts-node src/main.ts
```

**C++ (CMakeLists.txt):** (see Python section above)

---

### Core Concepts

#### Agent Implementation

**TypeScript:**
```typescript
import { Agent, Message, Result } from 'agenkit';

class EchoAgent implements Agent {
    get name(): string { return 'echo'; }

    async process(message: Message): Promise<Result<Message, AgentError>> {
        const response: Message = {
            role: 'assistant',
            content: message.content,
        };
        return Result.ok(response);
    }
}
```

**C++:**
```cpp
class EchoAgent : public agenkit::core::Agent {
public:
    std::string name() const override { return "echo"; }

    std::future<agenkit::core::Result<agenkit::core::Message,
                                       agenkit::core::AgentError>>
    process(agenkit::core::Message message) override {
        using namespace agenkit::core;
        auto resp = Message::with_text("assistant",
                                       message.content().as_text());
        return make_ready_future(
            Result<Message, AgentError>::ok(std::move(resp))
        );
    }
};
```

#### Async/Await vs std::future

**TypeScript:**
```typescript
const result = await agent.process(message);
if (result.isOk()) {
    console.log(result.value.content);
}
```

**C++:**
```cpp
auto result = agent->process(std::move(message)).get();
if (result.is_ok()) {
    std::cout << result.value().content().as_text() << "\n";
}
```

#### npm vs CMake/vcpkg

| Concept | TypeScript | C++ |
|---------|-----------|-----|
| Package registry | npmjs.com | vcpkg, Conan, GitHub |
| Install | `npm install` | `vcpkg install` |
| Build | `npm run build` / `tsc` | `cmake --build .` |
| Run | `node dist/main.js` | `./build/my_agent` |
| Test | `npm test` / `jest` | `ctest` / GoogleTest |
| Lock file | `package-lock.json` | `vcpkg.json` |

#### Type Safety

**TypeScript (structural typing):**
```typescript
interface Agent {
    name: string;
    process(msg: Message): Promise<Result<Message, AgentError>>;
}

// Structural — any object with these properties works
const myAgent: Agent = {
    name: 'custom',
    async process(msg) { return Result.ok(msg); }
};
```

**C++ (nominal typing with virtual dispatch):**
```cpp
class Agent {
public:
    virtual std::string name() const = 0;
    virtual std::future<Result<Message, AgentError>>
    process(Message message) = 0;
    virtual ~Agent() = default;
};

// Nominal — must explicitly inherit from Agent
class CustomAgent : public Agent {
    std::string name() const override { return "custom"; }
    std::future<Result<Message, AgentError>>
    process(Message message) override {
        return make_ready_future(
            Result<Message, AgentError>::ok(std::move(message))
        );
    }
};
```

---

## Rust → C++

**Why migrate to C++?**
- Integration with existing C/C++ codebases
- C ABI compatibility (C++ has well-defined C ABI for `extern "C"`)
- Larger library ecosystem (Boost, Qt, OpenCV, etc.)
- Familiar patterns for teams with C/C++ background
- Some platforms lack full Rust toolchain support

**When to stay with Rust:**
- New projects requiring memory safety guarantees
- Modern async with Tokio ecosystem
- Systems programming with compile-time safety
- Teams comfortable with ownership/borrow checker

---

### Core Concepts

#### Ownership Models

**Rust:**
```rust
// Ownership is enforced at compile time
let message = Message::with_text("user", "Hello");
let result = agent.process(message).await; // message moved here
// message is no longer accessible

// Borrowing
let result = agent.process_ref(&message).await; // borrow
// message still accessible
```

**C++ (RAII + smart pointers — runtime, not compile-time):**
```cpp
auto message = Message::with_text("user", "Hello");
auto result = agent->process(std::move(message)).get(); // message moved
// message is in moved-from state — do not use

// Sharing
auto shared_msg = std::make_shared<Message>(
    Message::with_text("user", "Hello")
);
agent->process(*shared_msg).get();  // copy
// shared_msg still valid
```

#### Result Types

**Rust:**
```rust
match agent.process(message).await {
    Ok(response) => println!("{}", response.content()),
    Err(e) => eprintln!("Error: {}", e),
}

// ? operator for propagation
let response = agent.process(message).await?;
```

**C++:**
```cpp
auto result = agent->process(message).get();

// Explicit check
if (result.is_ok()) {
    std::cout << result.value().content().as_text() << "\n";
} else {
    std::cerr << "Error: " << result.error().message() << "\n";
}

// Early return pattern (like ?)
if (result.is_err()) return result;
auto response = result.value();
```

#### Cargo vs CMake

| Concept | Rust (Cargo) | C++ (CMake + vcpkg) |
|---------|-------------|---------------------|
| Build file | `Cargo.toml` | `CMakeLists.txt` + `vcpkg.json` |
| Dependencies | `cargo add agenkit` | `vcpkg install agenkit` |
| Build | `cargo build` | `cmake --build .` |
| Test | `cargo test` | `ctest` |
| Release | `cargo build --release` | `cmake -DCMAKE_BUILD_TYPE=Release ..` |
| Docs | `cargo doc` | Doxygen |

#### Concurrency

**Rust (async/await with Tokio):**
```rust
use tokio::join;

let (r1, r2) = join!(
    agent_a.process(msg1),
    agent_b.process(msg2)
);
```

**C++ (std::async):**
```cpp
auto f1 = agent_a->process(std::move(msg1));
auto f2 = agent_b->process(std::move(msg2));

auto r1 = f1.get();
auto r2 = f2.get();
```

#### Memory Safety

**Rust:** Enforced by borrow checker at compile time — use-after-free and data races are impossible.

**C++:** Enforced by programmer discipline and tools:
```cpp
// Use smart pointers — avoid raw new/delete
auto agent = std::make_unique<EchoAgent>();  // not: new EchoAgent()

// Use const references for read-only access
void log_message(const Message& msg);  // no copy, no ownership transfer

// Use std::move for transfers
auto result = agent->process(std::move(msg)).get();

// Enable sanitizers during development:
// cmake -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined" ..
```

---

## Zig → C++

**Why migrate to C++?**
- Larger ecosystem (Boost, OpenCV, Qt, hundreds of libraries)
- More mature tooling (CMake, CLion, Visual Studio, many debuggers)
- RAII — resource management is automatic rather than manual
- Larger team of C++ developers available
- Better IDE support and code navigation

**When to stay with Zig:**
- Simpler language (fewer footguns, no header/source split)
- Explicit control over every allocation
- Compile-time computation (`comptime` is more powerful than C++ templates)
- Faster compile times
- Better C interop (no FFI overhead)

---

### Core Concepts

#### Build Systems

**Zig (`build.zig.zon`):**
```zig
.{
    .name = "my-agent",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/scttfrdmn/agenkit/releases/download/v0.75.0/agenkit-zig.tar.gz",
            .hash = "1220...",
        },
    },
}
```

**C++ (CMakeLists.txt + vcpkg.json):**
```cmake
cmake_minimum_required(VERSION 3.16)
project(my_agent CXX)
set(CMAKE_CXX_STANDARD 17)

include(FetchContent)
FetchContent_Declare(agenkit
    GIT_REPOSITORY https://github.com/scttfrdmn/agenkit.git
    SOURCE_SUBDIR  agenkit-cpp
    GIT_TAG        v0.75.0
)
FetchContent_MakeAvailable(agenkit)

add_executable(my_agent src/main.cpp)
target_link_libraries(my_agent PRIVATE agenkit::agenkit)
```

#### Agent Implementation

**Zig (vtable via struct):**
```zig
const MyAgent = struct {
    // VTable-based dispatch
    pub fn agent(self: *MyAgent) Agent {
        return Agent{
            .ptr    = self,
            .vtable = &vtable,
        };
    }

    const vtable = Agent.VTable{
        .name    = name,
        .process = process,
        .deinit  = deinit,
    };

    fn name(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "my-agent";
    }

    fn process(ptr: *anyopaque, msg: Message) AgentError!Result {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        // ...
    }

    fn deinit(ptr: *anyopaque) void {
        const self: *MyAgent = @ptrCast(@alignCast(ptr));
        _ = self;
    }
};
```

**C++ (virtual dispatch):**
```cpp
class MyAgent : public agenkit::core::Agent {
public:
    std::string name() const override { return "my-agent"; }

    std::future<agenkit::core::Result<agenkit::core::Message,
                                       agenkit::core::AgentError>>
    process(agenkit::core::Message message) override {
        using namespace agenkit::core;
        // Process and return
        return make_ready_future(
            Result<Message, AgentError>::ok(std::move(message))
        );
    }
    // Destructor handled by virtual ~Agent() in base class
};
```

#### comptime vs Templates

**Zig (`comptime`):**
```zig
// Compile-time generic container
pub fn Stack(comptime T: type) type {
    return struct {
        items: std.ArrayList(T),

        pub fn push(self: *@This(), item: T) !void {
            try self.items.append(item);
        }
    };
}

var stack = Stack(Message){};
```

**C++ (templates):**
```cpp
template<typename T>
class Stack {
public:
    void push(T item) {
        items_.push_back(std::move(item));
    }
    std::optional<T> pop() {
        if (items_.empty()) return std::nullopt;
        auto item = std::move(items_.back());
        items_.pop_back();
        return item;
    }
private:
    std::vector<T> items_;
};

Stack<Message> stack;
stack.push(Message::with_text("user", "Hello"));
```

#### Memory Management

**Zig (explicit allocator everywhere):**
```zig
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();

var msg = try Message.withText(allocator, .user, "Hello");
defer msg.deinit();
```

**C++ (RAII — no explicit allocator passing):**
```cpp
// Constructors/destructors handle memory automatically
auto msg = Message::with_text("user", "Hello");
// msg destroyed when it goes out of scope — no defer/deinit needed

auto agent = std::make_unique<EchoAgent>();
// agent destroyed when unique_ptr goes out of scope
```

#### Error Handling

**Zig (error union types):**
```zig
const result = agent.process(msg) catch |err| {
    std.debug.print("Error: {}\n", .{err});
    return err;
};
```

**C++:**
```cpp
auto result = agent->process(std::move(msg)).get();
if (result.is_err()) {
    std::cerr << "Error: " << result.error().message() << "\n";
    return result;  // propagate
}
```

---

## C++ → Python

**Why migrate to Python?**
- Faster iteration and prototyping
- Access to ML/data science ecosystem (PyTorch, HuggingFace, etc.)
- Simpler deployment (no compilation step)
- Larger pool of developers

**Key differences:**

```cpp
// C++: explicit types, RAII, std::future
auto agent = std::make_shared<ClaudeAgent>(config);
auto result = agent->process(message).get();
if (result.is_ok()) { /* ... */ }
```

```python
# Python: dynamic typing, async/await, exceptions
agent = ClaudeAgent(config)
result = await agent.process(message)
if result.is_ok:
    # ...
```

**Middleware parameters:** C++ uses milliseconds. Python uses seconds (floats).

---

## C++ → Go

**Why migrate to Go?**
- Simpler concurrency (goroutines > `std::async`)
- Faster compilation
- Simpler memory model (GC)
- Better standard library for network services

**Key differences:**

```cpp
// C++: virtual inheritance, smart pointers
class MyAgent : public Agent { /* ... */ };
auto agent = std::make_unique<MyAgent>();
auto result = agent->process(message).get();
```

```go
// Go: interfaces, values
type MyAgent struct{}
func (a *MyAgent) Process(ctx context.Context, msg Message) (Message, error) { /* ... */ }
agent := &MyAgent{}
result, err := agent.Process(ctx, message)
```

---

## C++ → TypeScript

**Why migrate to TypeScript?**
- Browser deployment
- npm ecosystem
- Faster development cycle
- Universal code for web applications

**Key differences:**

```cpp
// C++: compiled, statically typed
auto future = agent->process(message);
auto result = future.get();  // blocking wait
```

```typescript
// TypeScript: async/await
const result = await agent.process(message);  // non-blocking
```

---

## C++ → Rust

**Why migrate to Rust?**
- Compile-time memory safety (no use-after-free, no data races)
- Modern async ecosystem (Tokio)
- Better error propagation with `?` operator
- Growing systems programming community

**Key differences:**

```cpp
// C++: RAII via smart pointers (runtime)
auto agent = std::make_shared<MyAgent>();
auto result = agent->process(std::move(message)).get();
```

```rust
// Rust: borrow checker (compile-time)
let agent = Arc::new(MyAgent::new());
let result = agent.process(message).await;
```

---

## C++ → Zig

**Why migrate to Zig?**
- Simpler language semantics
- Explicit allocator model (clear ownership)
- Faster compile times
- Better C interop
- comptime more expressive than templates for some use cases

**Key differences:**

```cpp
// C++: RAII, templates
auto agent = std::make_unique<EchoAgent>();
auto result = agent->process(message).get();
```

```zig
// Zig: explicit allocator, defer cleanup
var agent = try EchoAgent.init(allocator);
defer agent.agent().deinit();
const result = try agent.agent().process(msg);
var response = try result.unwrap();
defer response.deinit();
```

---

## Quick Reference: Key Differences

| Concept | C++ | Python | Go | TypeScript | Rust | Zig |
|---------|-----|--------|----|------------|------|-----|
| Memory | RAII / smart pointers | GC | GC | GC | Borrow checker | Explicit allocator |
| Async | `std::future` / `std::async` | `async/await` | goroutines | `async/await` | Tokio | `async/await` |
| Error handling | `Result<T,E>` type | exceptions + Result | multiple returns | `Result` class | `Result` + `?` | error unions |
| Build | CMake | pip/uv | go mod | npm | cargo | build.zig |
| Time units | milliseconds | seconds | milliseconds | milliseconds | milliseconds | nanoseconds |
| Null safety | `std::optional<T>` | `Optional[T]` | pointer nil | `T \| undefined` | `Option<T>` | optional |
| Interface | abstract class | ABC / Protocol | interface | interface | trait | struct vtable |

---

**Version**: v0.75.0
**Last Updated**: March 2026

For help: Open an issue at https://github.com/scttfrdmn/agenkit/issues
