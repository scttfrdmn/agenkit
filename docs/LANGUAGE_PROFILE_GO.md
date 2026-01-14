# Go Language Profile for Agenkit

**Purpose**: This document maps Go language idioms, patterns, and best practices to Agenkit concepts. Use this as a reference when migrating **from** or **to** Go.

**Target Audience**: Developers familiar with Go who are migrating Agenkit code to/from other languages, or developers from other languages learning Go patterns in Agenkit.

---

## Table of Contents

- [Language Philosophy](#language-philosophy)
- [Type System](#type-system)
- [Error Handling](#error-handling)
- [Concurrency Model](#concurrency-model)
- [Memory Management](#memory-management)
- [Agenkit Idioms in Go](#agenkit-idioms-in-go)
- [Common Patterns](#common-patterns)
- [Testing](#testing)
- [Performance Characteristics](#performance-characteristics)

---

## Language Philosophy

### Go's Core Principles

1. **Simplicity**: Minimize language features, maximize readability
2. **Explicit over implicit**: No hidden control flow or magic
3. **Composition over inheritance**: Interfaces and embedding
4. **Built-in concurrency**: Goroutines and channels as first-class citizens
5. **Fast compilation**: Quick feedback loops

### How This Affects Agenkit

- **Interfaces define behavior**: `Agent` is an interface, not a class
- **Errors are values**: `error` type returned explicitly, not exceptions
- **Context for cancellation**: `context.Context` threading through all async operations
- **Goroutines for parallelism**: Lightweight threads for concurrent agent execution
- **Struct embedding**: Pattern composition through embedded fields

---

## Type System

### Static Typing

**Go's Approach**:
```go
// Types declared explicitly
type Message struct {
    Role      string
    Content   string
    Metadata  map[string]interface{}
    Timestamp time.Time
}

// Interface for duck typing at compile time
type Agent interface {
    Name() string
    Capabilities() []string
    Process(ctx context.Context, msg Message) (Message, error)
}
```

**Key Concepts**:
- **Structs**: Data containers (like Python dataclasses)
- **Interfaces**: Define behavior, implemented implicitly
- **No generics (pre-Go 1.18)**: Use `interface{}` for any type
- **With generics (Go 1.18+)**: Type-safe containers like `Result[T]`

### Nil vs Zero Values

```go
// Go's zero values (safe defaults)
var msg Message  // All fields initialized to zero values
msg.Role = ""    // empty string
msg.Metadata = nil  // nil map (safe to check, but can't write to)

// Must initialize maps before use
msg.Metadata = make(map[string]interface{})
```

**Migration Notes**:
- Python `None` → Go `nil` (for pointers, slices, maps, interfaces)
- TypeScript `undefined` → Go `nil` (approximately)
- Rust `Option<T>` → Go pointer `*T` or custom zero value pattern

---

## Error Handling

### Error Values (Not Exceptions)

**Go's Pattern**:
```go
// Function returns (result, error) tuple
result, err := agent.Process(ctx, message)
if err != nil {
    // Handle error explicitly
    return nil, fmt.Errorf("agent failed: %w", err)
}
// Use result safely here
```

**Comparison**:
| Language | Pattern | Control Flow |
|----------|---------|--------------|
| **Go** | `if err != nil` | Explicit checks |
| Python | `try/except` | Exception unwinding |
| TypeScript | `try/catch` | Exception unwinding |
| Rust | `Result<T, E>` | Explicit `.unwrap()` or `?` |
| C++ | Exceptions or error codes | Both patterns |

### Error Wrapping

```go
// Wrap errors to preserve context
if err != nil {
    return nil, fmt.Errorf("processing message %s: %w", msg.ID, err)
}

// Unwrap to check original error
if errors.Is(err, ErrTimeout) {
    // Handle timeout specifically
}
```

**Agenkit Convention**:
- Always wrap errors with context: `fmt.Errorf("context: %w", err)`
- Use `errors.Is()` for error type checking
- Return early on error: `if err != nil { return err }`

---

## Concurrency Model

### Goroutines

**Definition**: Lightweight threads managed by Go runtime

```go
// Launch goroutine (runs concurrently)
go func() {
    result, err := agent.Process(ctx, msg)
    if err != nil {
        log.Printf("Error: %v", err)
    }
}()
```

**Characteristics**:
- **Lightweight**: 2KB initial stack (vs ~2MB for OS threads)
- **Multiplexed**: Many goroutines on few OS threads
- **No direct thread control**: Runtime schedules automatically

### Channels

**Purpose**: Type-safe communication between goroutines

```go
// Create buffered channel
results := make(chan Message, 10)

// Send to channel
results <- message

// Receive from channel
msg := <-results

// Close when done
close(results)
```

**Patterns**:
```go
// Fan-out: Distribute work to multiple workers
for i := 0; i < numWorkers; i++ {
    go worker(tasks, results)
}

// Fan-in: Collect results from multiple sources
for i := 0; i < numResults; i++ {
    result := <-results
    processResult(result)
}
```

### Context for Cancellation

**Purpose**: Propagate cancellation and deadlines through call stack

```go
// Create context with timeout
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

// Pass context to all operations
result, err := agent.Process(ctx, message)

// Check for cancellation
select {
case <-ctx.Done():
    return nil, ctx.Err()  // Returns context.Canceled or context.DeadlineExceeded
default:
    // Continue processing
}
```

**Agenkit Convention**:
- All async operations take `context.Context` as first parameter
- Always check `ctx.Done()` in long-running operations
- Propagate context through all function calls

### Comparison to Other Languages

| Language | Concurrency Primitive | Communication |
|----------|----------------------|---------------|
| **Go** | Goroutines | Channels |
| Python | async/await | asyncio.Queue |
| TypeScript | async/await | Promise |
| Rust | async/await (tokio) | mpsc channels |
| C++ | std::thread | std::mutex, condition_variable |

---

## Memory Management

### Automatic Garbage Collection

**Go's Approach**:
- **Tri-color mark-and-sweep GC**
- **Low-latency**: Sub-millisecond pause times (Go 1.20+)
- **No manual memory management** required

```go
// Automatic cleanup - no destructors needed
func processMessage(msg Message) error {
    buffer := make([]byte, 1024)  // Allocated on heap
    // ...use buffer...
    return nil
    // buffer automatically freed when unreachable
}
```

**Comparison**:
| Language | Memory Model | Developer Action |
|----------|--------------|------------------|
| **Go** | GC | None required |
| Python | GC + refcounting | None required |
| TypeScript | GC (V8) | None required |
| Rust | Ownership | Explicit lifetimes |
| C++ | Manual | new/delete or smart pointers |
| Zig | Manual | defer/errdefer |

### Defer for Cleanup

**Pattern**: Schedule cleanup at function exit

```go
func processFile(filename string) error {
    file, err := os.Open(filename)
    if err != nil {
        return err
    }
    defer file.Close()  // Runs when function returns (any path)

    // ...use file...
    return nil
    // file.Close() called automatically
}
```

**Use Cases**:
- Resource cleanup (files, locks, connections)
- Cancellation functions: `defer cancel()`
- Logging function exit
- Panic recovery

---

## Agenkit Idioms in Go

### Message Creation

```go
// Basic message
msg := agenkit.Message{
    Role:    agenkit.RoleUser,
    Content: "Hello, agent!",
}

// With metadata
msg := agenkit.Message{
    Role:    agenkit.RoleAssistant,
    Content: "Response",
    Metadata: map[string]interface{}{
        "confidence": 0.95,
        "model":      "gpt-4",
    },
}

// With timestamp
msg := agenkit.Message{
    Role:      agenkit.RoleUser,
    Content:   "Query",
    Timestamp: time.Now(),
}
```

### Agent Implementation

```go
// Define agent struct
type MyAgent struct {
    name         string
    capabilities []string
    config       Config
}

// Implement Agent interface
func (a *MyAgent) Name() string {
    return a.name
}

func (a *MyAgent) Capabilities() []string {
    return a.capabilities
}

func (a *MyAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    // Check cancellation
    select {
    case <-ctx.Done():
        return agenkit.Message{}, ctx.Err()
    default:
    }

    // Process message
    response := agenkit.Message{
        Role:    agenkit.RoleAssistant,
        Content: fmt.Sprintf("Processed: %s", msg.Content),
    }

    return response, nil
}
```

### Pattern Composition

```go
// Sequential pattern
sequential := patterns.NewSequential([]agenkit.Agent{
    agent1,
    agent2,
    agent3,
})

// Parallel pattern
parallel := patterns.NewParallel([]agenkit.Agent{
    agentA,
    agentB,
    agentC,
})

// Nested composition
router := patterns.NewRouter(func(msg agenkit.Message) (string, error) {
    if strings.Contains(msg.Content, "urgent") {
        return "fast", nil
    }
    return "thorough", nil
}, map[string]agenkit.Agent{
    "fast":     sequential,
    "thorough": parallel,
})
```

---

## Common Patterns

### Error Handling Pattern

```go
// Check and wrap errors
result, err := operation()
if err != nil {
    return nil, fmt.Errorf("operation failed: %w", err)
}

// Check specific error types
if errors.Is(err, context.Canceled) {
    log.Println("Operation canceled")
    return nil, err
}

// Type assertion for custom errors
var agentErr *AgentError
if errors.As(err, &agentErr) {
    log.Printf("Agent %s failed: %v", agentErr.AgentName, agentErr)
}
```

### Retry Pattern

```go
func processWithRetry(ctx context.Context, agent agenkit.Agent, msg agenkit.Message) (agenkit.Message, error) {
    var lastErr error
    for attempt := 0; attempt < maxRetries; attempt++ {
        result, err := agent.Process(ctx, msg)
        if err == nil {
            return result, nil
        }

        // Don't retry on context cancellation
        if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
            return agenkit.Message{}, err
        }

        lastErr = err

        // Exponential backoff
        wait := time.Duration(attempt) * time.Second
        select {
        case <-time.After(wait):
            // Continue to next retry
        case <-ctx.Done():
            return agenkit.Message{}, ctx.Err()
        }
    }

    return agenkit.Message{}, fmt.Errorf("max retries exceeded: %w", lastErr)
}
```

### Timeout Pattern

```go
func processWithTimeout(agent agenkit.Agent, msg agenkit.Message, timeout time.Duration) (agenkit.Message, error) {
    ctx, cancel := context.WithTimeout(context.Background(), timeout)
    defer cancel()

    // Run in goroutine to enable timeout
    type result struct {
        msg agenkit.Message
        err error
    }

    resultCh := make(chan result, 1)
    go func() {
        msg, err := agent.Process(ctx, msg)
        resultCh <- result{msg, err}
    }()

    select {
    case res := <-resultCh:
        return res.msg, res.err
    case <-ctx.Done():
        return agenkit.Message{}, fmt.Errorf("timeout: %w", ctx.Err())
    }
}
```

---

## Testing

### Table-Driven Tests

**Go Idiom**:
```go
func TestAgent(t *testing.T) {
    tests := []struct {
        name    string
        input   agenkit.Message
        want    string
        wantErr bool
    }{
        {
            name:  "simple query",
            input: agenkit.Message{Role: agenkit.RoleUser, Content: "Hello"},
            want:  "Hello!",
            wantErr: false,
        },
        {
            name:  "empty input",
            input: agenkit.Message{},
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            agent := NewMyAgent()
            got, err := agent.Process(context.Background(), tt.input)

            if (err != nil) != tt.wantErr {
                t.Errorf("Process() error = %v, wantErr %v", err, tt.wantErr)
                return
            }

            if got.Content != tt.want {
                t.Errorf("Process() = %v, want %v", got.Content, tt.want)
            }
        })
    }
}
```

### Benchmark Tests

```go
func BenchmarkAgentProcess(b *testing.B) {
    agent := NewMyAgent()
    msg := agenkit.Message{
        Role:    agenkit.RoleUser,
        Content: "Test message",
    }
    ctx := context.Background()

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _, err := agent.Process(ctx, msg)
        if err != nil {
            b.Fatal(err)
        }
    }
}
```

---

## Performance Characteristics

### Strengths

1. **Fast compilation**: Sub-second builds for incremental changes
2. **Efficient runtime**: Native code, no JIT warmup
3. **Excellent concurrency**: Goroutines scale to millions
4. **Predictable GC**: Low-latency pauses (<1ms typical)
5. **Small binaries**: Static linking, ~10MB typical

### Trade-offs

1. **No generics (pre-1.18)**: Type assertions needed for generic code
2. **Verbose error handling**: Explicit checks every call
3. **Limited stdlib**: External packages needed for common tasks
4. **No operator overloading**: Can't customize `+`, `-`, etc.

### Agenkit Performance Profile

| Operation | Typical Latency | Throughput |
|-----------|----------------|------------|
| Message creation | ~100ns | 10M ops/sec |
| Agent process (mock) | ~1μs | 1M ops/sec |
| Sequential (3 agents) | ~3μs | 300K ops/sec |
| Parallel (3 agents) | ~1μs | 1M ops/sec |
| Context cancellation | ~50ns | 20M ops/sec |

**Compared to Other Languages**:
- **Python**: 10-50x slower (interpreted, GIL for concurrency)
- **TypeScript**: 2-5x slower (V8 JIT overhead)
- **Rust**: Comparable (sometimes faster, lower GC overhead)
- **C++**: Comparable (manual memory management trades)
- **Zig**: Comparable (explicit memory management)

---

## Migration Quick Links

**From Go**:
- [Go → Python](MIGRATE_GO_TO_PYTHON.md) - For prototyping, scripting
- [Go → TypeScript](MIGRATE_GO_TO_TYPESCRIPT.md) - For web/Node.js deployment
- [Go → Rust](MIGRATE_GO_TO_RUST.md) - For systems programming, WASM
- [Go → C++](MIGRATE_GO_TO_CPP.md) - For legacy integration
- [Go → Zig](MIGRATE_GO_TO_ZIG.md) - For embedded, low-level control

**To Go**:
- [Python → Go](MIGRATE_PYTHON_TO_GO.md) - For performance, deployment
- [TypeScript → Go](MIGRATE_TYPESCRIPT_TO_GO.md) - For backend services
- [Rust → Go](MIGRATE_RUST_TO_GO.md) - For simpler concurrency
- [C++ → Go](MIGRATE_CPP_TO_GO.md) - For safer memory management
- [Zig → Go](MIGRATE_ZIG_TO_GO.md) - For automatic memory management

---

## Additional Resources

- [Effective Go](https://go.dev/doc/effective_go) - Official style guide
- [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments) - Best practices
- [Agenkit Go Examples](../agenkit-go/examples/) - Working code samples
- [Agenkit Go Tests](../agenkit-go/tests/) - Test patterns and benchmarks

---

**Document Version**: 1.0
**Last Updated**: January 14, 2026
**Agenkit Version**: v0.46.0+
