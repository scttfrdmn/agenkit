# Streaming Patterns Across Languages

**Version**: 1.0
**Last Updated**: January 30, 2026
**Status**: Stable

## Overview

Agenkit implements streaming in each language using that language's most idiomatic pattern. This document explains **why** each language uses a different approach and provides examples of how to use streaming in each implementation.

## Core Philosophy

**Each language should feel natural to developers who know that language.**

Rather than forcing all languages to use the same streaming abstraction (which would make some implementations awkward or non-idiomatic), we embrace language-specific patterns that align with each ecosystem's conventions and best practices.

---

## Language-Specific Patterns

### Python: Async Iterators

**Pattern**: `AsyncIterator[Message]`
**File**: `agenkit/adapters/llm/base.py`

#### Why This Pattern?

- **Native to Python 3.5+**: Async generators (`async def` + `yield`) are built into the language
- **Natural error handling**: Exceptions propagate naturally through the async iterator
- **Pythonic**: Follows PEP 525 (Asynchronous Generators) conventions
- **Integration**: Works seamlessly with `async for` loops

#### Example

```python
from agenkit import OpenAILLM, Message

async def stream_example():
    llm = OpenAILLM(api_key="...")

    messages = [Message(role="user", content="Tell me a story")]

    # Stream responses using async for
    async for chunk in llm.stream(messages):
        print(chunk.content, end="", flush=True)
```

#### Error Handling

```python
async def stream_with_errors():
    llm = OpenAILLM(api_key="...")
    messages = [Message(role="user", content="Hello")]

    try:
        async for chunk in llm.stream(messages):
            print(chunk.content, end="")
    except Exception as e:
        print(f"Streaming error: {e}")
```

---

### Go: Dual Channels

**Pattern**: `(<-chan *Message, <-chan error)`
**File**: `agenkit-go/agenkit/interfaces.go`

#### Why This Pattern?

- **Native to Go**: Channels are Go's fundamental concurrency primitive
- **Explicit error handling**: Separate error channel follows Go's explicit error philosophy
- **Context support**: Works naturally with `context.Context` for cancellation
- **Composable**: Channels can be easily composed with `select` statements

#### Example

```go
package main

import (
    "context"
    "fmt"
    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
)

func streamExample() {
    client := llm.NewOpenAILLM(llm.OpenAIConfig{APIKey: "..."})

    message := &agenkit.Message{
        Role:    "user",
        Content: "Tell me a story",
    }

    ctx := context.Background()
    messageChan, errChan := client.Stream(ctx, message)

    // Read from both channels
    for {
        select {
        case chunk, ok := <-messageChan:
            if !ok {
                return // Channel closed, streaming complete
            }
            fmt.Print(chunk.Content)

        case err := <-errChan:
            if err != nil {
                fmt.Printf("Streaming error: %v\n", err)
                return
            }
        }
    }
}
```

#### Error Handling

```go
func streamWithTimeout() {
    client := llm.NewOpenAILLM(llm.OpenAIConfig{APIKey: "..."})
    message := &agenkit.Message{Role: "user", Content: "Hello"}

    // Create context with timeout
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    messageChan, errChan := client.Stream(ctx, message)

    for {
        select {
        case chunk, ok := <-messageChan:
            if !ok {
                return
            }
            fmt.Print(chunk.Content)

        case err := <-errChan:
            if err != nil {
                fmt.Printf("Error: %v\n", err)
                return
            }

        case <-ctx.Done():
            fmt.Println("Timeout reached")
            return
        }
    }
}
```

---

### TypeScript: Async Generators

**Pattern**: `AsyncGenerator<Message, void, undefined>`
**File**: `agenkit-ts/src/core/interfaces.ts`

#### Why This Pattern?

- **Native to TypeScript/JavaScript**: Async generators are built into ES2018+
- **Type-safe**: TypeScript provides full type inference for generator values
- **Natural error handling**: Exceptions throw from the generator
- **Modern**: Aligns with modern JavaScript async/await patterns

#### Example

```typescript
import { OpenAILLM, Message } from 'agenkit';

async function streamExample() {
    const llm = new OpenAILLM({ apiKey: '...' });

    const message: Message = {
        role: 'user',
        content: 'Tell me a story'
    };

    // Stream responses using for await
    for await (const chunk of llm.processStream(message)) {
        process.stdout.write(chunk.content);
    }
}
```

#### Error Handling

```typescript
async function streamWithErrors() {
    const llm = new OpenAILLM({ apiKey: '...' });
    const message: Message = { role: 'user', content: 'Hello' };

    try {
        for await (const chunk of llm.processStream(message)) {
            process.stdout.write(chunk.content);
        }
    } catch (error) {
        console.error('Streaming error:', error);
    }
}
```

---

### Rust: Futures Stream

**Pattern**: `Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>>`
**File**: `agenkit-rust/src/core/agent.rs`

#### Why This Pattern?

- **Ecosystem standard**: `futures::Stream` is the Rust async ecosystem's standard streaming abstraction
- **Zero-cost**: Compiles to efficient machine code with no runtime overhead
- **Type-safe error handling**: `Result` type makes errors explicit in the type system
- **Composable**: Works with all `futures` combinators (`map`, `filter`, etc.)

#### Example

```rust
use agenkit::{OpenAILLM, Message};
use futures::StreamExt;

async fn stream_example() {
    let llm = OpenAILLM::new("...".to_string());

    let message = Message {
        role: "user".to_string(),
        content: "Tell me a story".to_string(),
        ..Default::default()
    };

    // Stream responses
    let mut stream = llm.process_stream(message);

    while let Some(result) = stream.next().await {
        match result {
            Ok(chunk) => print!("{}", chunk.content),
            Err(e) => eprintln!("Error: {}", e),
        }
    }
}
```

#### Error Handling

```rust
use futures::StreamExt;
use tokio::time::{timeout, Duration};

async fn stream_with_timeout() {
    let llm = OpenAILLM::new("...".to_string());
    let message = Message { /* ... */ };

    let stream = llm.process_stream(message);

    // Apply timeout to the stream
    let timeout_stream = timeout(Duration::from_secs(30), async {
        stream
            .collect::<Vec<_>>()
            .await
    });

    match timeout_stream.await {
        Ok(chunks) => {
            for result in chunks {
                match result {
                    Ok(chunk) => println!("{}", chunk.content),
                    Err(e) => eprintln!("Chunk error: {}", e),
                }
            }
        }
        Err(_) => eprintln!("Stream timed out"),
    }
}
```

---

### C++: Callback-Based

**Pattern**: Callbacks (`on_message`, `on_error`, `on_complete`)
**File**: `agenkit-cpp/include/agenkit/core/agent.hpp`

#### Why This Pattern?

- **Universal compatibility**: Works with all C++ standards (C++11+)
- **No async runtime required**: Callbacks don't require a specific async executor
- **Performance**: Zero-cost abstraction with inline callbacks
- **Familiar**: Callback patterns are well-established in C++ (e.g., Boost.Asio)

#### Example

```cpp
#include <agenkit/adapters/llm/openai.hpp>
#include <iostream>

void streamExample() {
    agenkit::OpenAILLM llm("...");

    agenkit::Message message{
        .role = "user",
        .content = "Tell me a story"
    };

    // Define callbacks
    auto onMessage = [](agenkit::Message chunk) {
        std::cout << chunk.content << std::flush;
    };

    auto onError = [](agenkit::AgentError error) {
        std::cerr << "Error: " << error.message << std::endl;
    };

    auto onComplete = []() {
        std::cout << "\nStreaming complete" << std::endl;
    };

    // Start streaming
    auto future = llm.process_stream(message, onMessage, onError, onComplete);

    // Wait for completion
    future.wait();
}
```

#### Error Handling

```cpp
void streamWithErrorHandling() {
    agenkit::OpenAILLM llm("...");
    agenkit::Message message{ /* ... */ };

    bool hadError = false;

    auto onMessage = [](agenkit::Message chunk) {
        std::cout << chunk.content;
    };

    auto onError = [&hadError](agenkit::AgentError error) {
        hadError = true;
        std::cerr << "Streaming error: " << error.message << std::endl;
    };

    auto onComplete = [&hadError]() {
        if (!hadError) {
            std::cout << "\nSuccess!" << std::endl;
        }
    };

    auto future = llm.process_stream(message, onMessage, onError, onComplete);
    future.wait();
}
```

---

### Zig: Callback-Based with Error Unions

**Pattern**: Callbacks with `!void` return (error union)
**File**: `agenkit-zig/src/agent.zig`

#### Why This Pattern?

- **Zig-idiomatic**: Callbacks + error unions follow Zig conventions
- **Explicit errors**: Error unions make error handling explicit
- **No allocations**: Can be implemented without heap allocations
- **Simple**: Straightforward control flow without complex async machinery

#### Example

```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub fn streamExample() !void {
    var llm = agenkit.OpenAILLM.init(allocator, .{ .api_key = "..." });
    defer llm.deinit();

    const message = agenkit.Message{
        .role = "user",
        .content = "Tell me a story",
    };

    // Define callbacks
    const callbacks = agenkit.StreamCallbacks{
        .on_message_fn = onMessage,
        .on_error_fn = onError,
        .on_complete_fn = onComplete,
        .context = &context,
    };

    // Start streaming
    try llm.processStream(message, callbacks);
}

fn onMessage(ctx: *anyopaque, message: agenkit.Message) void {
    const stdout = std.io.getStdOut().writer();
    stdout.print("{s}", .{message.content}) catch {};
}

fn onError(ctx: *anyopaque, err: agenkit.AgentError) void {
    const stderr = std.io.getStdErr().writer();
    stderr.print("Error: {s}\n", .{err.message}) catch {};
}

fn onComplete(ctx: *anyopaque) void {
    const stdout = std.io.getStdOut().writer();
    stdout.print("\nComplete\n", .{}) catch {};
}
```

---

## Comparison Matrix

| Language   | Pattern           | Error Handling      | Requires Runtime? | Cancellable? |
|------------|-------------------|---------------------|-------------------|--------------|
| Python     | AsyncIterator     | Exception           | asyncio           | Yes (task)   |
| Go         | Dual Channels     | Separate channel    | goroutine         | Yes (context)|
| TypeScript | AsyncGenerator    | Exception           | Node/Browser      | Yes (AbortSignal) |
| Rust       | Stream<Result>    | Inline Result       | tokio/async-std   | Yes (drop)   |
| C++        | Callbacks         | Separate callback   | No                | Partial      |
| Zig        | Callbacks         | Error union         | No                | Partial      |

---

## Design Rationale

### Why Not Unify?

You might wonder: "Why not make all languages use the same pattern?"

**Answer**: Forcing a single pattern across all languages would make Agenkit feel foreign and awkward in most languages.

#### Example of Bad Unification

If we forced everyone to use C++-style callbacks:

**Python (awkward):**
```python
def on_message(chunk):
    print(chunk.content)

def on_error(error):
    print(f"Error: {error}")

llm.stream(message, on_message=on_message, on_error=on_error)  # Not Pythonic!
```

**Better Python (idiomatic):**
```python
async for chunk in llm.stream(message):  # Natural Python!
    print(chunk.content)
```

### Benefits of Language-Specific Patterns

1. **Developer Experience**: Developers feel at home in their language
2. **Ecosystem Integration**: Works naturally with existing libraries and tools
3. **Type Safety**: Leverages each language's type system optimally
4. **Performance**: Uses language-native constructs (often zero-cost)
5. **Documentation**: Follows conventions developers already know

---

## Guidelines for Implementers

If you're adding streaming support to a new Agenkit language binding:

1. **Research**: Study how popular libraries in that language handle streaming
2. **Be Idiomatic**: Use the pattern most natural to that language
3. **Document**: Clearly explain your choice and provide examples
4. **Test**: Ensure error cases are handled properly
5. **Consistency**: Match your language's ecosystem conventions

### Examples of Ecosystem Patterns

- **Python**: AsyncIterator (requests, aiohttp, anthropic-sdk)
- **Go**: Channels (net/http, grpc-go)
- **TypeScript**: AsyncGenerator (node-fetch streams, rxjs)
- **Rust**: Stream trait (tokio, async-std, futures)
- **C++**: Callbacks (Boost.Asio, Qt signals)
- **Zig**: Callbacks + error unions (standard library pattern)

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall design principles
- [CONTRIBUTING.md](../.github/CONTRIBUTING.md) - How to contribute
- Language-specific README files for detailed examples

---

## FAQ

### Q: Can I convert between streaming patterns?

**A**: Yes, but you're using the wrong tool if you need to. Agenkit is designed for each language to be used independently. If you need cross-language streaming, consider using a message queue or API layer between languages.

### Q: Which pattern is "best"?

**A**: The one that's most natural for your language! There's no universal "best" - context matters.

### Q: Should I add streaming support to my fork?

**A**: If your language has a standard streaming abstraction, use it. If not, callbacks are a safe fallback.

### Q: How do I handle backpressure?

- **Python**: Slow `async for` consumer naturally creates backpressure
- **Go**: Unbuffered channels or bounded buffer channels
- **TypeScript**: Slow consumer of async generator
- **Rust**: Stream trait respects polling backpressure
- **C++/Zig**: Implement rate limiting in callbacks if needed

---

**Questions or feedback?** Open an issue on GitHub!
