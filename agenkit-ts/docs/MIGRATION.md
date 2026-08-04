# Migration Guide — To and From Agenkit TypeScript

This guide covers migrating to Agenkit TypeScript from five other languages and runtimes, plus migrating from popular TypeScript AI frameworks.

## Table of Contents

- [Python → TypeScript](#python--typescript)
- [Go → TypeScript](#go--typescript)
- [Rust → TypeScript](#rust--typescript)
- [C++ → TypeScript](#c--typescript)
- [Zig → TypeScript](#zig--typescript)
- [LangChain.js → Agenkit](#langchainjs--agenkit)
- [Vercel AI SDK → Agenkit](#vercel-ai-sdk--agenkit)
- [Mastra → Agenkit](#mastra--agenkit)
- [Quick Comparison Reference](#quick-comparison-reference)

---

## Python → TypeScript

### Why Migrate?

| Aspect | Python | TypeScript |
|--------|--------|------------|
| Deployment | Server-only | Server + browser + edge |
| Type Safety | Runtime (mypy optional) | Compile-time |
| Performance | ~1x | ~2-3x (for CPU-bound work) |
| Ecosystem | pip, conda | npm — 2M+ packages |
| Async | asyncio (coroutines) | Native async/await |
| Tooling | ruff, mypy, pytest | eslint, tsc, vitest |

### Setup Comparison

**Python:**
```python
# pyproject.toml or requirements.txt
# pip install agenkit
from agenkit import Agent, Message, createMessage
```

**TypeScript:**
```bash
npm install @agenkit/core
```

```typescript
import { Agent, Message, createMessage } from '@agenkit/core';
```

### Async Patterns

Python uses `asyncio` with `async def` and `await`. TypeScript uses native `async/await` with `Promise`. The patterns are almost identical in syntax but differ in the runtime model.

**Python (asyncio):**
```python
import asyncio
from agenkit import LocalAgent, create_message

agent = LocalAgent(
    name="greeter",
    process=lambda msg: {"role": "assistant", "content": f"Hello, {msg['content']}!"}
)

async def main() -> None:
    message = create_message("user", "World")
    response = await agent.process(message)
    print(response["content"])  # Hello, World!

asyncio.run(main())
```

**TypeScript:**
```typescript
import { LocalAgent, createMessage } from '@agenkit/core';

const agent = new LocalAgent({
  name: 'greeter',
  process: async (msg) => ({
    role: 'assistant',
    content: `Hello, ${msg.content}!`,
  }),
});

async function main(): Promise<void> {
  const message = createMessage('user', 'World');
  const response = await agent.process(message);
  console.log(response.content); // Hello, World!
}

main().catch(console.error);
```

### Concurrent Processing

**Python (asyncio.gather):**
```python
import asyncio
from agenkit import create_message

messages = [create_message("user", f"Query {i}") for i in range(3)]
responses = await asyncio.gather(*[agent.process(m) for m in messages])
```

**TypeScript (Promise.all):**
```typescript
import { createMessage } from '@agenkit/core';

const messages = [0, 1, 2].map((i) => createMessage('user', `Query ${i}`));
const responses = await Promise.all(messages.map((m) => agent.process(m)));
```

### Class Definitions

**Python:**
```python
from agenkit import Agent, Message
from typing import Any

class SummarizerAgent(Agent):
    def __init__(self, model: str) -> None:
        self.model = model

    @property
    def name(self) -> str:
        return "summarizer"

    async def process(self, message: Message) -> Message:
        text = message["content"]
        summary = await self._summarize(str(text))
        return {"role": "assistant", "content": summary}

    async def _summarize(self, text: str) -> str:
        # LLM call...
        return f"Summary: {text[:50]}..."
```

**TypeScript:**
```typescript
import { Agent, Message } from '@agenkit/core';

class SummarizerAgent implements Agent {
  readonly name = 'summarizer';

  constructor(private readonly model: string) {}

  async process(message: Message): Promise<Message> {
    const text = message.content as string;
    const summary = await this.summarize(text);
    return { role: 'assistant', content: summary };
  }

  private async summarize(text: string): Promise<string> {
    // LLM call...
    return `Summary: ${text.slice(0, 50)}...`;
  }
}
```

### Error Handling

**Python:**
```python
from agenkit import AgentError

try:
    response = await agent.process(message)
except AgentError as e:
    print(f"Agent failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

**TypeScript:**
```typescript
try {
  const response = await agent.process(message);
} catch (error) {
  if (error instanceof AgentError) {
    console.error(`Agent failed: ${error.message}`);
  } else if (error instanceof Error) {
    console.error(`Unexpected error: ${error.message}`);
  }
}
```

### Testing

**Python (pytest):**
```python
import pytest
from agenkit import LocalAgent, create_message

@pytest.mark.asyncio
async def test_greeter():
    agent = LocalAgent(name="greeter", process=lambda m: {
        "role": "assistant",
        "content": f"Hello, {m['content']}!"
    })
    msg = create_message("user", "World")
    response = await agent.process(msg)
    assert response["content"] == "Hello, World!"
```

**TypeScript (Vitest):**
```typescript
import { describe, it, expect } from 'vitest';
import { LocalAgent, createMessage } from '@agenkit/core';

describe('GreetingAgent', () => {
  it('greets with user name', async () => {
    const agent = new LocalAgent({
      name: 'greeter',
      process: async (msg) => ({
        role: 'assistant',
        content: `Hello, ${msg.content}!`,
      }),
    });

    const response = await agent.process(createMessage('user', 'World'));
    expect(response.content).toBe('Hello, World!');
  });
});
```

### Key Differences Summary

| Concept | Python | TypeScript |
|---------|--------|------------|
| Type annotations | Optional (mypy) | Compiled (always on) |
| `async`/`await` | Works in coroutines | Works anywhere |
| Concurrency | `asyncio.gather` | `Promise.all` |
| Null safety | `Optional[T]` | `T \| undefined` |
| Data classes | `@dataclass` | `interface` |
| Module imports | `from x import y` | `import { y } from 'x'` |
| Package manager | pip / uv | npm / yarn / pnpm |
| Test framework | pytest | Vitest |
| Linter | ruff | eslint |
| Type checker | mypy | tsc |

---

## Go → TypeScript

### Why Migrate?

| Aspect | Go | TypeScript |
|--------|-----|------------|
| Target runtime | Server, CLI | Server + browser + edge |
| Concurrency | Goroutines + channels | `Promise.all`, Web Workers |
| Type system | Static, structural | Static, structural |
| Generics | Yes (Go 1.18+) | Yes (full generics) |
| Null safety | No nil checks at compile time | `T \| undefined` enforced |
| Ecosystem | Go modules | npm |
| Build | `go build` | `tsc` / `esbuild` / `vite` |

### Setup Comparison

**Go:**
```bash
go get github.com/scttfrdmn/agenkit-go@v0.75.0
```

```go
import "github.com/scttfrdmn/agenkit-go"
```

**TypeScript:**
```bash
npm install @agenkit/core
```

```typescript
import { Agent, Message, createMessage } from '@agenkit/core';
```

### Interface Definitions

Go and TypeScript both use structural typing. A key difference: Go interfaces are implicit (satisfied automatically), while TypeScript uses explicit `implements`.

**Go:**
```go
type Agent interface {
    Name() string
    Process(ctx context.Context, msg Message) (Message, error)
}

type GreetingAgent struct {
    name string
}

func (a *GreetingAgent) Name() string { return a.name }

func (a *GreetingAgent) Process(ctx context.Context, msg Message) (Message, error) {
    return Message{
        Role:    "assistant",
        Content: fmt.Sprintf("Hello, %s!", msg.Content),
    }, nil
}
```

**TypeScript:**
```typescript
import { Agent, Message, createMessage } from '@agenkit/core';

class GreetingAgent implements Agent {
  constructor(readonly name: string) {}

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Hello, ${message.content}!`,
    };
  }
}
```

### Concurrency: Goroutines vs Promise.all

**Go (goroutines + channels):**
```go
var wg sync.WaitGroup
results := make([]Message, len(agents))

for i, agent := range agents {
    wg.Add(1)
    go func(idx int, a Agent) {
        defer wg.Done()
        result, err := a.Process(ctx, message)
        if err == nil {
            results[idx] = result
        }
    }(i, agent)
}
wg.Wait()
```

**TypeScript (Promise.all):**
```typescript
const results = await Promise.all(
  agents.map((agent) => agent.process(message))
);
```

### Error Handling: Multiple Returns vs try/catch

**Go:**
```go
result, err := agent.Process(ctx, message)
if err != nil {
    return fmt.Errorf("agent failed: %w", err)
}
```

**TypeScript:**
```typescript
try {
  const result = await agent.process(message);
  return result;
} catch (error) {
  throw new Error(`agent failed: ${error instanceof Error ? error.message : String(error)}`);
}
```

### Context Cancellation

**Go (context.Context):**
```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

result, err := agent.Process(ctx, message)
```

**TypeScript (AbortController):**
```typescript
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), 5000);

try {
  const result = await agent.process(message);
  return result;
} finally {
  clearTimeout(timer);
}
```

### Middleware Composition

**Go (decorator pattern):**
```go
var agent Agent = NewBaseAgent()
agent = NewRetryDecorator(agent, RetryConfig{MaxRetries: 3})
agent = NewTimeoutDecorator(agent, 5*time.Second)
```

**TypeScript:**
```typescript
import { RetryMiddleware, TimeoutMiddleware } from '@agenkit/core/middleware';

let agent: Agent = new BaseAgent();
agent = new RetryMiddleware(agent, { maxRetries: 3, initialDelayMs: 1000 });
agent = new TimeoutMiddleware(agent, { timeoutMs: 5000 });
```

### Key Differences Summary

| Concept | Go | TypeScript |
|---------|-----|------------|
| Concurrency | Goroutines + channels | `Promise.all` + Web Workers |
| Error handling | Multiple returns `(T, error)` | `try/catch` |
| Context/cancellation | `context.Context` | `AbortController` |
| Interfaces | Implicit (structural) | Explicit `implements` |
| Generics | `[T any]` | `<T>` |
| Null | `nil` | `undefined` / `null` |
| Package management | Go modules | npm |
| Build | `go build` | `tsc` |
| Test | `testing.T` + `go test` | Vitest |

---

## Rust → TypeScript

### Why Migrate?

| Aspect | Rust | TypeScript |
|--------|------|------------|
| Memory management | Manual (borrow checker) | Garbage collected |
| Target runtime | Native, WASM | Server + browser + WASM |
| Async runtime | Tokio, async-std | Node.js / browser built-in |
| Learning curve | Very steep | Moderate |
| Build system | Cargo | npm |
| Compile speed | Slow | Fast |
| Runtime speed | Fastest | Fast (JIT) |

### Setup Comparison

**Rust:**
```toml
# Cargo.toml
[dependencies]
agenkit-rs = "0.75.0"
tokio = { version = "1", features = ["full"] }
```

```rust
use agenkit_rs::{Agent, Message, create_message};
```

**TypeScript:**
```bash
npm install @agenkit/core
```

```typescript
import { Agent, Message, createMessage } from '@agenkit/core';
```

### Trait vs Interface

**Rust (trait):**
```rust
use agenkit_rs::{Agent, Message, AgentError};
use async_trait::async_trait;

struct GreetingAgent {
    name: String,
}

#[async_trait]
impl Agent for GreetingAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message {
            role: "assistant".to_string(),
            content: format!("Hello, {}!", message.content),
            metadata: None,
            timestamp: None,
        })
    }
}
```

**TypeScript:**
```typescript
import { Agent, Message } from '@agenkit/core';

class GreetingAgent implements Agent {
  constructor(readonly name: string) {}

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Hello, ${message.content}!`,
    };
  }
}
```

### Result vs try/catch

Rust uses `Result<T, E>` for recoverable errors. TypeScript uses exceptions.

**Rust:**
```rust
match agent.process(message).await {
    Ok(response) => println!("Response: {}", response.content),
    Err(AgentError::InvalidInput) => eprintln!("Bad input"),
    Err(e) => eprintln!("Error: {:?}", e),
}
```

**TypeScript:**
```typescript
try {
  const response = await agent.process(message);
  console.log(`Response: ${response.content}`);
} catch (error) {
  if (error instanceof InvalidInputError) {
    console.error('Bad input');
  } else {
    console.error(`Error: ${error}`);
  }
}
```

### Option vs Undefined

**Rust:**
```rust
// Option<T> — explicit null handling
let session_id: Option<&str> = message.metadata
    .as_ref()
    .and_then(|m| m.get("session_id"))
    .and_then(|v| v.as_str());

if let Some(id) = session_id {
    println!("Session: {}", id);
}
```

**TypeScript:**
```typescript
// T | undefined — TypeScript strict mode enforces checks
const sessionId = message.metadata?.session_id as string | undefined;

if (sessionId !== undefined) {
  console.log(`Session: ${sessionId}`);
}
```

### Async: Tokio vs Node.js

**Rust (Tokio):**
```rust
#[tokio::main]
async fn main() {
    let agent = GreetingAgent { name: "greeter".to_string() };
    let message = create_message("user", "World");
    let response = agent.process(message).await.unwrap();
    println!("{}", response.content);
}
```

**TypeScript:**
```typescript
async function main(): Promise<void> {
  const agent = new GreetingAgent('greeter');
  const response = await agent.process(createMessage('user', 'World'));
  console.log(response.content);
}

main().catch(console.error);
```

### Key Differences Summary

| Concept | Rust | TypeScript |
|---------|------|------------|
| Memory | Borrow checker | GC |
| Errors | `Result<T, E>` | `try/catch` |
| Null | `Option<T>` | `T \| undefined` |
| Async runtime | Tokio / async-std | Node.js built-in |
| Traits | `impl Trait for Type` | `implements Interface` |
| Generics | `<T: Trait>` | `<T extends Type>` |
| Build | `cargo build` | `tsc` / bundlers |
| Test | `#[test]` / `cargo test` | Vitest |

---

## C++ → TypeScript

### Why Migrate?

| Aspect | C++ | TypeScript |
|--------|-----|------------|
| Memory management | Manual (`new`/`delete`, RAII) | Garbage collected |
| Build system | CMake, Make, Bazel | npm scripts, Webpack |
| Platform | Native binary | Server + browser + edge |
| Headers | `.hpp` + `.cpp` | Single `.ts` file |
| Async | std::async, coroutines | Native async/await |
| ABI | Fragile | N/A (JS bytecode) |

### Setup Comparison

**C++ (CMakeLists.txt):**
```cmake
cmake_minimum_required(VERSION 3.20)
project(my_agent)

find_package(agenkit-cpp REQUIRED)

add_executable(my_agent src/main.cpp)
target_link_libraries(my_agent agenkit::agenkit)
```

**TypeScript:**
```bash
npm install @agenkit/core
npx tsc --init
```

### Class Definitions

**C++:**
```cpp
#include <agenkit/agent.hpp>
#include <agenkit/message.hpp>

class GreetingAgent : public agenkit::Agent {
public:
    explicit GreetingAgent(std::string name) : name_(std::move(name)) {}

    [[nodiscard]] std::string_view name() const override {
        return name_;
    }

    [[nodiscard]] std::future<agenkit::Message> process(
        const agenkit::Message& message
    ) override {
        return std::async(std::launch::async, [&message, this]() {
            return agenkit::Message{
                .role = "assistant",
                .content = "Hello, " + std::get<std::string>(message.content) + "!",
            };
        });
    }

private:
    std::string name_;
};
```

**TypeScript:**
```typescript
import { Agent, Message } from '@agenkit/core';

class GreetingAgent implements Agent {
  constructor(readonly name: string) {}

  async process(message: Message): Promise<Message> {
    return {
      role: 'assistant',
      content: `Hello, ${message.content}!`,
    };
  }
}
```

### Memory Management

C++ requires explicit memory management. TypeScript uses garbage collection.

**C++ (RAII + smart pointers):**
```cpp
// Smart pointer manages lifetime
auto agent = std::make_unique<GreetingAgent>("greeter");
auto message = agenkit::create_message("user", "World");

auto future = agent->process(message);
auto response = future.get();

// agent automatically destroyed when it goes out of scope
```

**TypeScript:**
```typescript
// GC handles cleanup — no explicit free/delete
const agent = new GreetingAgent('greeter');
const response = await agent.process(createMessage('user', 'World'));
// No cleanup needed
```

### Concurrency: std::async vs Promise.all

**C++:**
```cpp
std::vector<std::future<agenkit::Message>> futures;
for (auto& agent : agents) {
    futures.push_back(agent->process(message));
}

std::vector<agenkit::Message> results;
for (auto& future : futures) {
    results.push_back(future.get());
}
```

**TypeScript:**
```typescript
const results = await Promise.all(
  agents.map((agent) => agent.process(message))
);
```

### Error Handling

**C++ (exceptions):**
```cpp
try {
    auto response = agent->process(message).get();
} catch (const agenkit::InvalidInputError& e) {
    std::cerr << "Bad input: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}
```

**TypeScript:**
```typescript
try {
  const response = await agent.process(message);
} catch (error) {
  if (error instanceof InvalidInputError) {
    console.error(`Bad input: ${error.message}`);
  } else if (error instanceof Error) {
    console.error(`Error: ${error.message}`);
  }
}
```

### Key Differences Summary

| Concept | C++ | TypeScript |
|---------|-----|------------|
| Memory | RAII, smart pointers | GC |
| Async | `std::future`, coroutines | `async/await` |
| Concurrency | Threads, `std::async` | `Promise.all` |
| Null | raw pointers, `std::optional` | `T \| undefined` |
| Generics | Templates | Generics `<T>` |
| Build | CMake → binary | `tsc` → JS |
| Test | GoogleTest, Catch2 | Vitest |
| Headers | `.hpp` + `.cpp` | Single `.ts` file |

---

## Zig → TypeScript

### Why Migrate?

| Aspect | Zig | TypeScript |
|--------|-----|------------|
| Memory management | Explicit allocators | GC |
| Error handling | Error unions `!T` | `try/catch` |
| Async | `async fn` + coroutines | `async/await` (Promises) |
| Target | Native, WASM, embedded | Server + browser + edge |
| Build | build.zig | tsconfig.json + npm |
| Generics | `comptime` | TypeScript generics |
| Null safety | Optional type (`?T`) | `T \| undefined` |

### Setup Comparison

**Zig (build.zig.zon):**
```zig
.{
    .name = "my-agent",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/scttfrdmn/agenkit/releases/...",
            .hash = "1220...",
        },
    },
}
```

**TypeScript:**
```bash
npm install @agenkit/core
```

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "strict": true
  }
}
```

### Interface Definitions: vtable vs implements

Zig uses explicit vtable structs. TypeScript uses interface-based polymorphism.

**Zig:**
```zig
pub const GreetingAgent = struct {
    allocator: std.mem.Allocator,

    pub fn agent(self: *GreetingAgent) agenkit.Agent {
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

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *GreetingAgent = @ptrCast(@alignCast(ptr));
        const text = try message.contentAsText();
        const greeting = try std.fmt.allocPrint(self.allocator, "Hello, {s}!", .{text});
        defer self.allocator.free(greeting);
        const response = try agenkit.Message.withText(self.allocator, .assistant, greeting);
        return agenkit.Result{ .ok = response };
    }
};
```

**TypeScript:**
```typescript
import { Agent, Message } from '@agenkit/core';

class GreetingAgent implements Agent {
  readonly name = 'greeting-agent';

  async process(message: Message): Promise<Message> {
    const text = message.content as string;
    return { role: 'assistant', content: `Hello, ${text}!` };
  }
}
```

### Memory Management: Allocators vs GC

**Zig (explicit allocators + defer):**
```zig
var msg = try agenkit.Message.withText(allocator, .user, "Hello");
defer msg.deinit(); // MUST free explicitly

const result = try agent.process(msg);
var response = try result.unwrap();
defer response.deinit();
```

**TypeScript (garbage collected):**
```typescript
const msg = createMessage('user', 'Hello');
// No cleanup needed — GC handles it

const response = await agent.process(msg);
// response is just a plain object — GC frees it
```

### Error Handling: Error Unions vs try/catch

**Zig:**
```zig
// Error union: either Message or AgentError
const result = agent.process(msg) catch |err| {
    std.debug.print("Failed: {}\n", .{err});
    return err;
};
```

**TypeScript:**
```typescript
try {
  const response = await agent.process(message);
  console.log(response.content);
} catch (error) {
  console.error(`Failed: ${error instanceof Error ? error.message : error}`);
}
```

### Comptime vs TypeScript Generics

**Zig (comptime):**
```zig
pub fn Pipeline(comptime T: type) type {
    return struct {
        agents: []const T,

        pub fn process(self: @This(), msg: Message) !Message {
            var current = msg;
            for (self.agents) |agent| {
                current = try agent.process(current);
            }
            return current;
        }
    };
}
```

**TypeScript (generics):**
```typescript
class Pipeline<T extends Agent> {
  constructor(private readonly agents: T[]) {}

  async process(message: Message): Promise<Message> {
    let current = message;
    for (const agent of this.agents) {
      current = await agent.process(current);
    }
    return current;
  }
}
```

### Optionals: ?T vs T | undefined

**Zig:**
```zig
// Optional type — must check for null
const value: ?[]const u8 = message.getMetadata("session_id");
if (value) |session_id| {
    std.debug.print("Session: {s}\n", .{session_id});
}
```

**TypeScript:**
```typescript
// Strict mode enforces null checks
const sessionId = message.metadata?.session_id as string | undefined;
if (sessionId !== undefined) {
  console.log(`Session: ${sessionId}`);
}
```

### Key Differences Summary

| Concept | Zig | TypeScript |
|---------|-----|------------|
| Memory | Explicit allocators | GC |
| Error handling | `!T` error unions | `try/catch` |
| Null | `?T` optional | `T \| undefined` |
| Generics | `comptime` | `<T extends U>` |
| Interfaces | vtable struct | `implements` |
| Build config | `build.zig` / `build.zig.zon` | `tsconfig.json` |
| Package manager | Zig build system | npm |
| Test | `zig build test` | Vitest |
| Cleanup | `defer obj.deinit()` | Automatic GC |

---

## LangChain.js → Agenkit

### Why Migrate?

- **Simpler API**: 2 required methods vs extensive chain configuration
- **Full control**: No hidden behavior or auto-prompt injection
- **Type safety**: Better TypeScript inference
- **Performance**: Lower overhead, no chain compilation step

### Basic Chain Replacement

**LangChain.js:**
```typescript
import { ChatOpenAI } from '@langchain/openai';
import { HumanMessage } from '@langchain/core/messages';

const model = new ChatOpenAI({ model: 'gpt-4o' });
const response = await model.invoke([new HumanMessage('Hello!')]);
console.log(response.content);
```

**Agenkit:**
```typescript
import { OpenAIAgent, createMessage } from '@agenkit/core';

const agent = new OpenAIAgent({ apiKey: process.env.OPENAI_API_KEY!, model: 'gpt-4o' });
const response = await agent.process(createMessage('user', 'Hello!'));
console.log(response.content);
```

### Tool Usage Replacement

**LangChain.js:**
```typescript
import { DynamicTool } from '@langchain/core/tools';
import { createOpenAIFunctionsAgent, AgentExecutor } from 'langchain/agents';

const tools = [
  new DynamicTool({
    name: 'search',
    description: 'Search the web',
    func: async (query) => `Results for: ${query}`,
  }),
];

const agent = await createOpenAIFunctionsAgent({ llm: model, tools, prompt });
const executor = new AgentExecutor({ agent, tools });
const result = await executor.invoke({ input: 'What is the weather?' });
```

**Agenkit:**
```typescript
import { ReActAgent, LocalAgent, createMessage } from '@agenkit/core';
import type { Tool, ToolResult } from '@agenkit/core';

const searchTool: Tool = {
  name: 'search',
  description: 'Search the web',
  execute: async (params) => ({
    output: `Results for: ${params.query}`,
    success: true,
  }),
};

const agent = new ReActAgent(llmAgent, [searchTool]);
const response = await agent.process(createMessage('user', 'What is the weather?'));
```

---

## Vercel AI SDK → Agenkit

### Why Migrate?

- **Transport agnostic**: HTTP, WebSocket, gRPC — not just HTTP streams
- **Patterns library**: 11 built-in patterns vs manual chain construction
- **Backend-first**: Not tied to Next.js / React

### Streaming Replacement

**Vercel AI SDK:**
```typescript
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

const { textStream } = await streamText({
  model: openai('gpt-4o'),
  prompt: 'What is TypeScript?',
});

for await (const text of textStream) {
  process.stdout.write(text);
}
```

**Agenkit:**
```typescript
import { OpenAIAgent, createMessage } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
});

for await (const chunk of agent.processStream!(createMessage('user', 'What is TypeScript?'))) {
  process.stdout.write(chunk.content as string);
}
```

### Tool Calls Replacement

**Vercel AI SDK:**
```typescript
import { generateText, tool } from 'ai';
import { z } from 'zod';

const { text } = await generateText({
  model: openai('gpt-4o'),
  tools: {
    weather: tool({
      description: 'Get weather',
      parameters: z.object({ city: z.string() }),
      execute: async ({ city }) => `Weather in ${city}: sunny`,
    }),
  },
  prompt: "What's the weather in Paris?",
});
```

**Agenkit:**
```typescript
import { ReActAgent, createMessage } from '@agenkit/core';
import type { Tool } from '@agenkit/core';

const weatherTool: Tool = {
  name: 'weather',
  description: 'Get weather',
  parametersSchema: {
    type: 'object',
    properties: { city: { type: 'string' } },
    required: ['city'],
  },
  execute: async (params) => ({
    output: `Weather in ${params.city}: sunny`,
    success: true,
  }),
};

const agent = new ReActAgent(llmAgent, [weatherTool]);
const response = await agent.process(createMessage('user', "What's the weather in Paris?"));
```

---

## Mastra → Agenkit

### Basic Agent Replacement

**Mastra:**
```typescript
import { Agent } from '@mastra/core/agent';
import { openai } from '@mastra/openai';

const agent = new Agent({
  name: 'assistant',
  instructions: 'You are a helpful assistant.',
  model: openai('gpt-4o'),
});

const response = await agent.generate('Hello!');
```

**Agenkit:**
```typescript
import { OpenAIAgent, createMessage } from '@agenkit/core';

const agent = new OpenAIAgent({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
  systemPrompt: 'You are a helpful assistant.',
});

const response = await agent.process(createMessage('user', 'Hello!'));
```

### Workflow Replacement

**Mastra (workflow):**
```typescript
import { Workflow } from '@mastra/core';

const workflow = new Workflow({ name: 'my-workflow' })
  .step('validate', validateStep)
  .step('process', processStep)
  .commit();
```

**Agenkit:**
```typescript
import { SequentialAgent } from '@agenkit/core';

const workflow = new SequentialAgent(
  [validateAgent, processAgent],
  { name: 'my-workflow' }
);
```

---

## Quick Comparison Reference

### Package Managers

| Language | Install | Dependency File |
|----------|---------|-----------------|
| TypeScript | `npm install @agenkit/core` | `package.json` |
| Python | `pip install agenkit` | `pyproject.toml` |
| Go | `go get github.com/scttfrdmn/agenkit-go` | `go.mod` |
| Rust | `cargo add agenkit-rs` | `Cargo.toml` |
| C++ | CMake `find_package` | `CMakeLists.txt` |
| Zig | `build.zig.zon` | `build.zig.zon` |

### Async Primitives

| Language | Single | Multiple | Cancel |
|----------|--------|----------|--------|
| TypeScript | `await promise` | `Promise.all(promises)` | `AbortController` |
| Python | `await coroutine` | `asyncio.gather(...)` | `asyncio.cancel()` |
| Go | goroutine + channel | `sync.WaitGroup` | `context.Cancel()` |
| Rust | `future.await` | `join!` macro | `CancellationToken` |
| C++ | `future.get()` | Loop over futures | `std::stop_token` |
| Zig | `await frame` | Manual | `frame.cancel()` |

### Error Handling

| Language | Pattern | Example |
|----------|---------|---------|
| TypeScript | `try/catch` | `try { await f() } catch (e) {}` |
| Python | `try/except` | `try: await f() except Exception as e:` |
| Go | Multiple return | `result, err := f(); if err != nil {}` |
| Rust | `Result<T,E>` | `match f().await { Ok(v) => .., Err(e) => }` |
| C++ | `try/catch` | `try { f().get(); } catch (...) {}` |
| Zig | Error union | `const v = try f();` or `f() catch |e| {}` |

### Test Frameworks

| Language | Framework | Run |
|----------|-----------|-----|
| TypeScript | Vitest | `npm test` |
| Python | pytest | `uv run pytest` |
| Go | testing | `go test ./...` |
| Rust | built-in | `cargo test` |
| C++ | GoogleTest | `ctest` |
| Zig | built-in | `zig build test` |
