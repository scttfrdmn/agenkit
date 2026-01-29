# Streaming Patterns Across Languages

This document explains why each Agenkit implementation uses different streaming patterns and how they reflect language idioms.

## Design Philosophy

**Each language uses its most idiomatic streaming pattern.** Agenkit is a toolkit, not a framework, so we prioritize:
1. Language idiomaticity over forced consistency
2. Developer familiarity with native patterns
3. Ecosystem compatibility

Users working in a specific language expect that language's standard streaming approach, not a foreign pattern imposed by the library.

## Streaming Patterns by Language

### Python: AsyncIterator

```python
async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[Message]:
    async for chunk in stream.text_stream:
        yield Message(role="agent", content=chunk, metadata={"streaming": True})
```

**Why AsyncIterator?**
- Native Python async generator pattern
- Works seamlessly with `async for` loops
- Natural error propagation via exceptions
- Pythonic: `yield` is the standard way to create iterators

**Example usage:**
```python
async for chunk in agent.stream(messages):
    print(chunk.content, end='', flush=True)
```

### Go: Dual Channels

```go
type StreamingAgent interface {
    Stream(ctx context.Context, message *Message) (<-chan *Message, <-chan error)
}
```

**Why dual channels?**
- Idiomatic Go concurrency pattern
- Separates data flow from error flow
- Leverages Go's CSP (Communicating Sequential Processes) model
- Context-aware cancellation built-in

**Example usage:**
```go
messageChan, errorChan := agent.Stream(ctx, message)
for {
    select {
    case msg := <-messageChan:
        if msg == nil {
            return nil
        }
        fmt.Print(msg.Content)
    case err := <-errorChan:
        return err
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

### TypeScript: AsyncGenerator

```typescript
processStream?(message: Message): AsyncGenerator<Message, void, undefined>;
```

**Why AsyncGenerator?**
- Native TypeScript/ES2018 async iteration
- Works with `for await...of` loops
- Type-safe with generic parameters
- Matches modern JavaScript streaming APIs

**Example usage:**
```typescript
for await (const chunk of agent.processStream(message)) {
    process.stdout.write(chunk.content);
}
```

### Rust: Stream of Result

```rust
fn process_stream(&self, message: Message)
    -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>>
```

**Why Stream<Result>?**
- Idiomatic Rust futures ecosystem pattern
- Inline error handling with `Result` type
- Pin requirement ensures memory safety
- Compatible with `tokio::Stream` ecosystem

**Example usage:**
```rust
let mut stream = agent.process_stream(message);
while let Some(result) = stream.next().await {
    match result {
        Ok(chunk) => print!("{}", chunk.content),
        Err(e) => return Err(e),
    }
}
```

### C++: Callback-based

```cpp
virtual std::future<Result<bool, AgentError>>
process_stream(
    Message message,
    std::function<void(Message)> on_message,
    std::function<void(AgentError)> on_error,
    std::function<void()> on_complete
)
```

**Why callbacks?**
- C++ lacks native async streams
- Compatible with all C++ versions (C++11+)
- Flexible: works with futures, coroutines, or plain callbacks
- Separates concerns: data, errors, completion

**Example usage:**
```cpp
agent.process_stream(
    message,
    [](Message chunk) { std::cout << chunk.content(); },
    [](AgentError err) { std::cerr << err.message() << std::endl; },
    []() { std::cout << "\nComplete\n"; }
);
```

### Zig: Callback-based with Error Unions

```zig
pub const StreamCallbacks = struct {
    on_message_fn: *const fn (ptr: *anyopaque, message: Message) void,
    on_error_fn: *const fn (ptr: *anyopaque, err: AgentError) void,
    on_complete_fn: *const fn (ptr: *anyopaque) void,
};

pub fn processStream(self: Agent, message: Message, callbacks: StreamCallbacks) !void
```

**Why callbacks with error unions?**
- Zig lacks async/await (as of 0.15.2)
- Error unions are idiomatic Zig error handling
- Callbacks provide flexibility for future async when available
- Explicit memory management with Zig's allocator pattern

**Example usage:**
```zig
try agent.processStream(message, .{
    .on_message_fn = handleMessage,
    .on_error_fn = handleError,
    .on_complete_fn = handleComplete,
});
```

## Common Characteristics

Despite different implementations, all streaming patterns share:

1. **Chunked delivery**: Messages arrive incrementally as they're generated
2. **Error handling**: Errors can occur during streaming
3. **Completion signal**: Clear indication when stream ends
4. **Cancellation**: Ability to stop streaming early (via context, break, or return)

## Comparison Matrix

| Language   | Pattern            | Error Handling       | Cancellation       | Idiomatic? |
|------------|-------------------|----------------------|--------------------|------------|
| Python     | AsyncIterator      | Exception propagation | `break` in async for | ✓ Yes      |
| Go         | Dual channels      | Separate error channel | Context cancellation | ✓ Yes      |
| TypeScript | AsyncGenerator     | Exception throwing    | `break` in for await | ✓ Yes      |
| Rust       | Stream<Result>     | Inline Result         | Stream drop          | ✓ Yes      |
| C++        | Callbacks          | on_error callback     | Return false         | ✓ Yes      |
| Zig        | Callbacks          | on_error callback     | Error return         | ✓ Yes      |

## Why Not Force Consistency?

**Forcing a single pattern would make code less idiomatic:**

1. **Python with callbacks?** Violates Python's iterator protocol
2. **Go with iterators?** Ignores Go's channel-based concurrency
3. **TypeScript with dual returns?** Not how modern JS/TS streams work
4. **Rust without Result?** Loses type-safe error handling
5. **C++ with streams?** Requires C++20 coroutines (breaking C++11/14/17 support)
6. **Zig with async?** Not available yet in language

## Cross-Language Migration

When migrating streaming code between languages, focus on **semantic equivalence** rather than syntactic similarity:

```python
# Python: AsyncIterator
async for chunk in agent.stream(messages):
    process(chunk)
```

```go
// Go: Dual channels (semantically equivalent)
messageChan, errorChan := agent.Stream(ctx, message)
for msg := range messageChan {
    process(msg)
}
```

```typescript
// TypeScript: AsyncGenerator (semantically equivalent)
for await (const chunk of agent.processStream(message)) {
    process(chunk);
}
```

The **intent** is the same: process streaming chunks as they arrive. The **mechanism** respects each language's conventions.

## References

- **Python**: [PEP 525 - Asynchronous Generators](https://peps.python.org/pep-0525/)
- **Go**: [Effective Go - Channels](https://go.dev/doc/effective_go#channels)
- **TypeScript**: [Async Iteration](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-2-3.html#async-iteration)
- **Rust**: [futures::Stream](https://rust-lang.github.io/futures-api-docs/0.3.30/futures/stream/trait.Stream.html)
- **C++**: [Callbacks and Futures](https://en.cppreference.com/w/cpp/thread/future)
- **Zig**: [Zig Language Reference](https://ziglang.org/documentation/master/)

## Conclusion

Agenkit's streaming patterns demonstrate **pragmatic polyglotism**: using the best tool for each job rather than forcing one-size-fits-all solutions. This approach maximizes developer productivity and ecosystem compatibility while maintaining consistent semantics across languages.
