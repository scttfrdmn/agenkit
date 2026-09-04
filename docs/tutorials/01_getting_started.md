# Tutorial 1: Your First Agent in 5 Minutes

This tutorial shows you how to build a minimal working agent in all six languages
supported by agenkit. By the end you will have an agent that accepts a text message,
processes it, and returns a response — the same conceptual program written in Python,
Go, TypeScript, Rust, C++, and Zig.

---

## What you are building

A `SummaryAgent` that takes a sentence and echoes it back with a word count. It is
deliberately simple so you can focus on the shape of the API before adding real LLM
calls or middleware.

---

## Prerequisites

| Language   | Tool required                     |
|------------|-----------------------------------|
| Python     | Python 3.11+ and `uv`             |
| Go         | Go 1.25.14+                       |
| TypeScript | Node 22+ and `npm`                |
| Rust       | Rust 1.75+ (`rustup`)             |
| C++        | CMake 3.20+ and a C++17 compiler  |
| Zig        | Zig 0.13+                         |

---

## Python

**Install:**

```bash
uv add agenkit
```

**`summary_agent.py`:**

```python
import asyncio
from agenkit import Agent, Message


class SummaryAgent(Agent):
    """Returns the input text with a word count prepended."""

    @property
    def name(self) -> str:
        return "summary_agent"

    async def process(self, message: Message) -> Message:
        text = str(message.content)
        word_count = len(text.split())
        response = f"[{word_count} words] {text}"
        return Message(role="agent", content=response)


async def main() -> None:
    agent = SummaryAgent()

    msg = Message(role="user", content="The quick brown fox jumps over the lazy dog")
    response = await agent.process(msg)

    print(f"Input : {msg.content}")
    print(f"Output: {response.content}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Run:**

```bash
uv run python summary_agent.py
```

**Expected output:**

```
Input : The quick brown fox jumps over the lazy dog
Output: [9 words] The quick brown fox jumps over the lazy dog
```

---

## Go

**Install:**

```bash
go get github.com/scttfrdmn/agenkit-go
```

**`summary_agent.go`:**

```go
package main

import (
    "context"
    "fmt"
    "strings"

    "github.com/scttfrdmn/agenkit-go/agenkit"
)

// SummaryAgent returns the input with a word count prepended.
type SummaryAgent struct{}

func (s *SummaryAgent) Name() string { return "summary_agent" }

func (s *SummaryAgent) Capabilities() []string { return []string{"summarize"} }

func (s *SummaryAgent) Process(
    ctx context.Context,
    message *agenkit.Message,
) (*agenkit.Message, error) {
    words := strings.Fields(message.ContentString())
    response := fmt.Sprintf("[%d words] %s", len(words), message.Content)
    return agenkit.NewMessage("agent", response), nil
}

func (s *SummaryAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(s)
}

func main() {
    agent := &SummaryAgent{}
    ctx := context.Background()

    msg := agenkit.NewMessage("user", "The quick brown fox jumps over the lazy dog")
    response, err := agent.Process(ctx, msg)
    if err != nil {
        panic(err)
    }

    fmt.Printf("Input : %s\n", msg.Content)
    fmt.Printf("Output: %s\n", response.Content)
}
```

**Run:**

```bash
go run summary_agent.go
```

---

## TypeScript

**Install:**

```bash
npm install agenkit
```

**`summaryAgent.ts`:**

```typescript
import { LocalAgent, Message } from 'agenkit';

const summaryAgent = new LocalAgent({
    name: 'summary_agent',
    process: async (message: Message): Promise<Message> => {
        const text = String(message.content);
        const wordCount = text.trim().split(/\s+/).length;
        return {
            role: 'assistant',
            content: `[${wordCount} words] ${text}`,
        };
    },
});

async function main(): Promise<void> {
    const msg: Message = {
        role: 'user',
        content: 'The quick brown fox jumps over the lazy dog',
    };

    const response = await summaryAgent.process(msg);

    console.log(`Input : ${msg.content}`);
    console.log(`Output: ${response.content}`);
}

main().catch(console.error);
```

**Run:**

```bash
npx ts-node summaryAgent.ts
```

---

## Rust

**`Cargo.toml`:**

```toml
[dependencies]
agenkit = "0.49"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
```

**`src/main.rs`:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

struct SummaryAgent;

#[async_trait]
impl Agent for SummaryAgent {
    fn name(&self) -> &str {
        "summary_agent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let text = message.content_as_str().unwrap_or("");
        let word_count = text.split_whitespace().count();
        let response = format!("[{} words] {}", word_count, text);
        Ok(Message::with_text("assistant", &response))
    }
}

#[tokio::main]
async fn main() {
    let agent = SummaryAgent;
    let msg = Message::with_text("user", "The quick brown fox jumps over the lazy dog");

    match agent.process(msg.clone()).await {
        Ok(response) => {
            println!("Input : {}", msg.content_as_str().unwrap_or(""));
            println!("Output: {}", response.content_as_str().unwrap_or(""));
        }
        Err(e) => eprintln!("Error: {}", e),
    }
}
```

**Run:**

```bash
cargo run
```

---

## C++

**`CMakeLists.txt` (minimal):**

```cmake
cmake_minimum_required(VERSION 3.20)
project(summary_agent)
find_package(agenkit REQUIRED)
add_executable(summary_agent main.cpp)
target_link_libraries(summary_agent agenkit::agenkit)
```

**`main.cpp`:**

```cpp
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <iostream>
#include <sstream>
#include <future>

using namespace agenkit::core;

class SummaryAgent : public Agent {
public:
    std::string name() const override {
        return "summary_agent";
    }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        const std::string text = message.content_as_str();
        std::istringstream iss(text);
        int word_count = 0;
        std::string word;
        while (iss >> word) { ++word_count; }

        std::string response =
            "[" + std::to_string(word_count) + " words] " + text;

        auto result = Result<Message, AgentError>::ok(
            Message::with_text("assistant", response)
        );
        std::promise<Result<Message, AgentError>> p;
        p.set_value(std::move(result));
        return p.get_future();
    }
};

int main() {
    SummaryAgent agent;
    auto msg = Message::with_text("user",
        "The quick brown fox jumps over the lazy dog");

    auto future = agent.process(msg);
    auto result = future.get();

    if (result.is_ok()) {
        std::cout << "Input : " << msg.content_as_str() << "\n";
        std::cout << "Output: " << result.unwrap().content_as_str() << "\n";
    } else {
        std::cerr << "Error processing message\n";
        return 1;
    }
    return 0;
}
```

**Build and run:**

```bash
cmake -B build && cmake --build build
./build/summary_agent
```

---

## Zig

**`build.zig.zon`:**

```zig
.{
    .name = "summary_agent",
    .version = "0.1.0",
    .dependencies = .{
        .agenkit = .{
            .url = "https://github.com/scttfrdmn/agenkit/archive/v0.49.0.tar.gz",
        },
    },
}
```

**`src/main.zig`:**

```zig
const std = @import("std");
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const Message = agenkit.Message;

// VTable implementation for SummaryAgent
fn summaryProcess(
    ptr: *anyopaque,
    allocator: std.mem.Allocator,
    message: Message,
) Agent.Error!Message {
    _ = ptr;
    const text = message.content.text;
    var word_count: usize = 0;
    var it = std.mem.splitAny(u8, text, " \t\n");
    while (it.next()) |tok| {
        if (tok.len > 0) word_count += 1;
    }

    const response = try std.fmt.allocPrint(
        allocator,
        "[{d} words] {s}",
        .{ word_count, text },
    );
    return Message.initText(allocator, .agent, response);
}

fn summaryName(ptr: *anyopaque) []const u8 {
    _ = ptr;
    return "summary_agent";
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var impl: u8 = 0; // stateless agent — pointer is unused
    const agent = Agent{
        .ptr = &impl,
        .vtable = &.{
            .name = summaryName,
            .process = summaryProcess,
        },
    };

    const msg = try Message.initText(
        allocator,
        .user,
        "The quick brown fox jumps over the lazy dog",
    );
    defer msg.deinit(allocator);

    const response = try agent.vtable.process(agent.ptr, allocator, msg);
    defer response.deinit(allocator);

    std.debug.print("Input : {s}\n", .{msg.content.text});
    std.debug.print("Output: {s}\n", .{response.content.text});
}
```

**Run:**

```bash
zig build run
```

---

## What you just learned

All six implementations share the same conceptual shape:

1. **Define an agent** by subclassing / implementing the `Agent` interface.
2. **Implement two things**: the agent's name and its `process` method.
3. **Create a message** with a `role` (`"user"`) and `content`.
4. **Call `process`** (async in Python/TypeScript/Rust, future-based in C++/Go, error-union in Zig).
5. **Read the response** message from the return value.

The `Message` type is the universal currency. Every agent speaks it.

---

## Next Steps

Continue to **[Tutorial 2: Memory and Conversation Context](./02_memory_and_context.md)**
to learn how to give agents memory so they can hold multi-turn conversations and
remember facts across sessions.
