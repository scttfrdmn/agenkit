# Getting Started with Agenkit-Go

A beginner-friendly guide to building AI agents with Go.

## Table of Contents

- [Installation](#installation)
- [Your First Agent](#your-first-agent)
- [Understanding Messages](#understanding-messages)
- [Goroutine Safety](#goroutine-safety)
- [Error Handling](#error-handling)
- [Testing Your Agent](#testing-your-agent)
- [Next Steps](#next-steps)

---

## Installation

### Prerequisites

You need Go 1.25.12 or later. Check your version:

```bash
go version
# Should output: go1.21.x or higher
```

If you don't have Go installed, download it from [go.dev](https://go.dev/dl/).

### Option 1: Using go get (Recommended)

1. **Initialize your module:**

```bash
mkdir my-agent-project
cd my-agent-project
go mod init example.com/my-agent
```

2. **Add Agenkit:**

```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

3. **Verify installation:**

```bash
go mod tidy
go build ./...
```

### Option 2: Building from Source

Clone the repository and reference it locally:

```bash
git clone https://github.com/scttfrdmn/agenkit.git
```

In your `go.mod`, add a `replace` directive:

```go
module example.com/my-agent

go 1.21

require github.com/scttfrdmn/agenkit/agenkit-go v0.0.0

replace github.com/scttfrdmn/agenkit/agenkit-go => ../agenkit/agenkit-go
```

### Package Import Path

The core package is imported as:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
```

Additional packages:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/middleware"
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
import "github.com/scttfrdmn/agenkit/agenkit-go/adapter"
import "github.com/scttfrdmn/agenkit/agenkit-go/observability"
```

---

## Your First Agent

Let's build a simple echo agent that responds to messages.

### Step 1: Create the Project

```bash
mkdir my-first-agent
cd my-first-agent
go mod init example.com/my-first-agent
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Step 2: Write the Agent Code

Create `main.go`:

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// EchoAgent implements the agenkit.Agent interface.
type EchoAgent struct{}

func (a *EchoAgent) Name() string {
    return "echo-agent"
}

func (a *EchoAgent) Capabilities() []string {
    return []string{"echo"}
}

func (a *EchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", fmt.Sprintf("Echo: %s", message.Content)), nil
}

func (a *EchoAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}

func main() {
    ctx := context.Background()
    agent := &EchoAgent{}

    message := agenkit.NewMessage("user", "Hello, agent!")
    fmt.Printf("User: %s\n", message.Content)

    response, err := agent.Process(ctx, message)
    if err != nil {
        log.Fatalf("agent processing failed: %v", err)
    }

    fmt.Printf("Agent: %s\n", response.Content)
    // Output: Agent: Echo: Hello, agent!
}
```

### Step 3: Build and Run

```bash
go run main.go
```

**Output:**
```
User: Hello, agent!
Agent: Echo: Hello, agent!
```

Congratulations! You've built your first AI agent with Go.

---

## Understanding Messages

Messages are the core data structure in Agenkit. Every interaction uses messages.

### Message Structure

A message has three components:

1. **Role** - Who sent the message (user, assistant, system, tool)
2. **Content** - The message content (text)
3. **Metadata** - Optional key-value pairs

```go
// Message type from the agenkit package
type Message struct {
    Role     string                 // "user", "assistant", "system", "tool"
    Content  string                 // Text content
    Metadata map[string]interface{} // Optional key-value pairs
}
```

### Creating Messages

#### Simple Text Messages

```go
// Using the constructor (preferred)
msg := agenkit.NewMessage("user", "Hello!")

// Or struct literal
msg := &agenkit.Message{
    Role:    "user",
    Content: "Hello!",
}
```

#### Messages with Metadata

```go
msg := &agenkit.Message{
    Role:    "user",
    Content: "Hello!",
    Metadata: map[string]interface{}{
        "session_id": "abc-123",
        "priority":   5,
        "source":     "web-ui",
    },
}
```

#### System Messages

```go
systemMsg := agenkit.NewMessage("system", "You are a helpful assistant.")
userMsg := agenkit.NewMessage("user", "What is Go?")
```

### Reading Messages

```go
// Access fields directly
fmt.Printf("Role: %s\n", msg.Role)
fmt.Printf("Content: %s\n", msg.Content)

// Read metadata
if sessionID, ok := msg.Metadata["session_id"].(string); ok {
    fmt.Printf("Session: %s\n", sessionID)
}
```

### Message Roles

| Role | Description |
|------|-------------|
| `"user"` | Messages from the human user |
| `"assistant"` | Messages from the AI agent |
| `"system"` | System-level instructions |
| `"tool"` | Tool execution results |

---

## Custom Agents

Build your own agent by implementing the `agenkit.Agent` interface.

### The Agent Interface

```go
type Agent interface {
    Name() string
    Capabilities() []string
    Process(ctx context.Context, message *Message) (*Message, error)
    Introspect() *IntrospectionResult
}
```

### Example: Greeting Agent

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// GreetingAgent greets users by name.
type GreetingAgent struct {
    DefaultGreeting string
}

func (a *GreetingAgent) Name() string {
    return "greeting-agent"
}

func (a *GreetingAgent) Capabilities() []string {
    return []string{"greeting", "personalization"}
}

func (a *GreetingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    if message.Content == "" {
        return nil, fmt.Errorf("empty message content")
    }

    response := fmt.Sprintf("%s You said: %s", a.DefaultGreeting, message.Content)
    return agenkit.NewMessage("assistant", response), nil
}

func (a *GreetingAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}

func main() {
    ctx := context.Background()
    agent := &GreetingAgent{DefaultGreeting: "Hello!"}

    msg := agenkit.NewMessage("user", "Hi there!")
    response, err := agent.Process(ctx, msg)
    if err != nil {
        log.Fatalf("processing failed: %v", err)
    }

    fmt.Println(response.Content)
    // Output: Hello! You said: Hi there!
}
```

### Using context.Context

Always pass `context.Context` as the first parameter. It enables cancellation and deadlines:

```go
import (
    "context"
    "time"
)

// Timeout after 5 seconds
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

response, err := agent.Process(ctx, message)
if err != nil {
    // Could be context.DeadlineExceeded
    log.Printf("processing error: %v", err)
}
```

---

## Goroutine Safety

Go agents are designed to be goroutine-safe. Here is what you need to know.

### Stateless Agents (Thread-Safe by Default)

Agents with no mutable state are inherently safe for concurrent use:

```go
// Safe: no mutable state
type StatelessAgent struct {
    name string // immutable after construction
}

func (a *StatelessAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return agenkit.NewMessage("assistant", "processed: "+msg.ContentString()), nil
}
```

### Stateful Agents (Requires Synchronization)

If your agent stores state between calls, use synchronization:

```go
import "sync"

// Safe: mutex protects mutable state
type CountingAgent struct {
    mu    sync.Mutex
    count int
    name  string
}

func (a *CountingAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    a.mu.Lock()
    a.count++
    count := a.count
    a.mu.Unlock()

    return agenkit.NewMessage("assistant", fmt.Sprintf("request #%d: %s", count, msg.Content)), nil
}
```

### Parallel Pattern

The `ParallelAgent` uses goroutines automatically. Your agents just need to be safe:

```go
import (
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// These agents run concurrently - each must be goroutine-safe
parallel := patterns.NewParallelAgent([]agenkit.Agent{
    &SentimentAgent{},
    &ClassificationAgent{},
    &SummaryAgent{},
}, nil)

// All three run in parallel goroutines
result, err := parallel.Process(ctx, message)
```

### Channel-Based Communication

For complex coordination, use channels:

```go
func processAsync(ctx context.Context, agent agenkit.Agent, msg *agenkit.Message) <-chan *agenkit.Message {
    out := make(chan *agenkit.Message, 1)
    go func() {
        defer close(out)
        response, err := agent.Process(ctx, msg)
        if err != nil {
            return
        }
        out <- response
    }()
    return out
}
```

---

## Error Handling

Go uses explicit error returns. Agenkit follows standard Go error patterns.

### Basic Error Handling

```go
response, err := agent.Process(ctx, message)
if err != nil {
    log.Printf("agent processing failed: %v", err)
    return
}
// Use response
fmt.Println(response.Content)
```

### Wrapping Errors

Use `fmt.Errorf` with `%w` to wrap errors for context:

```go
func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    result, err := a.doWork(ctx, msg)
    if err != nil {
        return nil, fmt.Errorf("agent %s failed to process message: %w", a.Name(), err)
    }
    return result, nil
}
```

### Sentinel Error Values

Define exported sentinel errors for callers to check:

```go
import "errors"

var (
    ErrEmptyInput      = errors.New("empty input message")
    ErrContextCanceled = errors.New("context canceled during processing")
    ErrBudgetExceeded  = errors.New("token budget exceeded")
)

func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    if msg.Content == "" {
        return nil, ErrEmptyInput
    }

    // Check context cancellation
    select {
    case <-ctx.Done():
        return nil, fmt.Errorf("%w: %v", ErrContextCanceled, ctx.Err())
    default:
    }

    // Process...
    return response, nil
}

// Caller can check:
_, err := agent.Process(ctx, msg)
if errors.Is(err, ErrEmptyInput) {
    // Handle empty input specifically
}
```

### Error Handling with defer

Always check errors in defer statements:

```go
// WRONG: ignores error
defer file.Close()

// CORRECT: explicitly ignores or handles error
defer func() { _ = file.Close() }()

// CORRECT: log error from defer
defer func() {
    if err := file.Close(); err != nil {
        log.Printf("failed to close file: %v", err)
    }
}()
```

### Switch on Error Types

Use switch for handling multiple error types:

```go
response, err := agent.Process(ctx, message)
if err != nil {
    switch {
    case errors.Is(err, ErrEmptyInput):
        log.Println("provide a non-empty message")
    case errors.Is(err, context.DeadlineExceeded):
        log.Println("request timed out, try again")
    case errors.Is(err, ErrBudgetExceeded):
        log.Println("token budget exceeded for this session")
    default:
        log.Printf("unexpected error: %v", err)
    }
    return
}
```

---

## Production Middleware

Add resilience to your agents with middleware:

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

func main() {
    ctx := context.Background()
    base := &MyAgent{}

    // Layer middleware from innermost to outermost
    agent := agenkit.Agent(base)

    // Retry on transient failures
    agent = middleware.NewRetryMiddleware(agent, &middleware.RetryConfig{
        MaxRetries:    3,
        BackoffFactor: 2.0,
        InitialDelay:  100 * time.Millisecond,
        MaxDelay:      10 * time.Second,
    })

    // Open circuit on repeated failures
    agent = middleware.NewCircuitBreakerMiddleware(agent, &middleware.CircuitBreakerConfig{
        FailureThreshold: 5,
        RecoveryTimeout:  30 * time.Second,
    })

    // Cancel slow calls
    agent = middleware.NewTimeoutMiddleware(agent, &middleware.TimeoutConfig{
        Timeout: 5 * time.Second,
    })

    message := agenkit.NewMessage("user", "Hello production!")
    response, err := agent.Process(ctx, message)
    if err != nil {
        log.Fatalf("processing failed: %v", err)
    }
    fmt.Println(response.Content)
}
```

**Note:** Go uses `time.Duration` for all timeout and delay values (e.g., `100 * time.Millisecond`, `5 * time.Second`). Never use raw integer milliseconds.

---

## Testing Your Agent

### Basic Test Structure

```go
package myagent_test

import (
    "context"
    "testing"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func TestGreetingAgentResponds(t *testing.T) {
    agent := &GreetingAgent{DefaultGreeting: "Hello!"}
    ctx := context.Background()

    msg := agenkit.NewMessage("user", "Hi there!")
    response, err := agent.Process(ctx, msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if response.Role != "assistant" {
        t.Errorf("expected role %q, got %q", "assistant", response.Role)
    }
    if response.Content == "" {
        t.Error("expected non-empty response content")
    }
}
```

### Table-Driven Tests (Idiomatic Go)

```go
func TestGreetingAgentTableDriven(t *testing.T) {
    tests := []struct {
        name        string
        input       string
        wantErr     bool
        wantContain string
    }{
        {
            name:        "normal message",
            input:       "Hello",
            wantContain: "Hello",
        },
        {
            name:    "empty message",
            input:   "",
            wantErr: true,
        },
        {
            name:        "long message",
            input:       "This is a longer test message",
            wantContain: "longer test message",
        },
    }

    agent := &GreetingAgent{DefaultGreeting: "Hi!"}
    ctx := context.Background()

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            msg := agenkit.NewMessage("user", tt.input)
            response, err := agent.Process(ctx, msg)

            if tt.wantErr {
                if err == nil {
                    t.Error("expected error, got nil")
                }
                return
            }
            if err != nil {
                t.Fatalf("unexpected error: %v", err)
            }
            if tt.wantContain != "" && !strings.Contains(response.ContentString(), tt.wantContain) {
                t.Errorf("response %q does not contain %q", response.Content, tt.wantContain)
            }
        })
    }
}
```

### Running Tests

```bash
# Run all tests
go test ./...

# Run tests with verbose output
go test -v ./...

# Run specific package tests
go test ./patterns/

# Run tests matching a pattern
go test -run TestGreeting ./...

# Run with race detector (important for goroutine-safe agents)
go test -race ./...

# Run with coverage
go test -cover ./...
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

### Test Best Practices

1. **Use table-driven tests** - DRY, easy to add cases
2. **Run with -race** - Catch concurrency bugs early
3. **Test error paths** - Don't just test happy paths
4. **Use descriptive names** - `TestAgentHandlesEmptyInput` not `TestCase1`
5. **Test with context cancellation** - Ensure agents respect context

### Example: Testing Context Cancellation

```go
func TestAgentRespectsContextCancellation(t *testing.T) {
    agent := &SlowAgent{delay: 100 * time.Millisecond}
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
    defer cancel()

    _, err := agent.Process(ctx, agenkit.NewMessage("user", "test"))
    if err == nil {
        t.Error("expected error from canceled context, got nil")
    }
    if !errors.Is(err, context.DeadlineExceeded) {
        t.Errorf("expected DeadlineExceeded, got: %v", err)
    }
}
```

---

## Next Steps

Now that you understand the basics, explore more advanced topics:

### 1. Learn Agent Patterns

Agenkit provides 11 core patterns:

- **Sequential** - Process messages through a pipeline
- **Parallel** - Concurrent processing with goroutines
- **Reflection** - Self-improvement through critique loops
- **ReAct** - Reasoning and acting with tools
- **Planning** - Complex task decomposition
- **Task** - Single-purpose specialized agents
- **Conversational** - Stateful multi-turn dialogue
- **AgentsAsTools** - Delegate to specialized sub-agents
- **Autonomous** - Goal-directed autonomous behavior
- **Multiagent** - Coordinate multiple agents
- **MemoryHierarchy** - Working/short-term/long-term memory

See [PATTERNS.md](PATTERNS.md) for a detailed guide.

### 2. Explore Examples

The `examples/` directory contains working examples:

```bash
# Basic examples
go run examples/basic/echo_agent.go
go run examples/basic/sequential_pattern.go

# Pattern examples
go run examples/patterns/react_example.go
go run examples/patterns/planning_example.go

# Production examples
go run examples/production/http_server.go
go run examples/production/grpc_server.go
```

### 3. Read the API Documentation

See [API.md](API.md) for complete API reference.

### 4. Port from Other Languages

If you're coming from Python, TypeScript, Rust, C++, or Zig, see [MIGRATION.md](MIGRATION.md).

### 5. Observability

Add tracing and metrics to your agents. See [OBSERVABILITY.md](OBSERVABILITY.md).

### 6. Build Real Agents

Try building:
- **Chat bot** - Use the Conversational pattern
- **Task executor** - Use the Task pattern
- **Research assistant** - Combine Parallel + Sequential patterns
- **Autonomous agent** - Use Autonomous pattern for goal-driven behavior
- **HTTP service** - Wrap your agent with the HTTP transport

### 7. Join the Community

- [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues) - Report bugs, request features
- [Discussions](https://github.com/scttfrdmn/agenkit/discussions) - Ask questions
- [Contributing](../../.github/CONTRIBUTING.md) - Contribute code

---

## Quick Reference

### Project Setup

```bash
# Create module
mkdir my-agent && cd my-agent
go mod init example.com/my-agent

# Add agenkit
go get github.com/scttfrdmn/agenkit/agenkit-go

# Run
go run main.go
```

### Core Imports

```go
import (
    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/middleware"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
    "github.com/scttfrdmn/agenkit/agenkit-go/adapter"
)
```

### Common Patterns

```go
// Message creation
msg := agenkit.NewMessage("user", "Hello!")

// Agent processing
response, err := agent.Process(ctx, msg)
if err != nil {
    log.Printf("error: %v", err)
    return
}

// Check role
if response.Role == "assistant" {
    fmt.Println(response.Content)
}

// Metadata access
if sessionID, ok := msg.Metadata["session_id"].(string); ok {
    fmt.Println(sessionID)
}

// Defer cleanup
f, err := os.Open("file.txt")
if err != nil {
    return err
}
defer func() { _ = f.Close() }()
```

### Testing

```go
func TestMyAgent(t *testing.T) {
    ctx := context.Background()
    agent := &MyAgent{}

    msg := agenkit.NewMessage("user", "test")
    response, err := agent.Process(ctx, msg)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    // Assertions...
}
```

Run with: `go test ./...`

---

## Troubleshooting

### "undefined: agenkit.NewMessage"

**Cause:** Wrong import path or package not downloaded.

**Fix:** Run `go mod tidy` and verify the import path is `github.com/scttfrdmn/agenkit/agenkit-go/agenkit`.

### "context canceled" errors

**Cause:** The context passed to `Process` was canceled or timed out.

**Fix:** Check that you are not sharing a canceled context across calls. Create fresh contexts per request when needed.

### "data race detected"

**Cause:** Shared state in your agent accessed by multiple goroutines without synchronization.

**Fix:** Add `sync.Mutex` to protect mutable fields. Run `go test -race ./...` regularly to catch these early.

### "golangci-lint: Printf format"

**Cause:** Passing `time.Duration` directly to `%.1fs` format specifier.

**Fix:** Use `.Seconds()`: `log.Printf("timeout=%.1fs", config.Timeout.Seconds())`

---

## Getting Help

- **Documentation:** [API.md](API.md), [PATTERNS.md](PATTERNS.md)
- **Examples:** Check the `examples/` directory
- **Issues:** [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- **Discussions:** [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- **GoDoc:** https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go

Welcome to the Agenkit community. Happy building!
