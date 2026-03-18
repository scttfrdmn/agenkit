# Go Testing Framework for Agenkit

## Overview

The Go implementation has comprehensive test coverage across all packages. This document covers the patterns, utilities, and tools used for testing Agenkit-Go agents and middleware.

**Test Coverage:**
- Core agent interface: table-driven tests
- Patterns (Sequential, Parallel, Reflection, etc.): behavior + concurrency tests
- Middleware: retry, circuit breaker, timeout — all tested with mock agents
- Observability: tracing and metrics verification
- Property tests: invariant testing with `pgregory.net/rapid`

---

## go test Patterns

### Basic Test Structure

All tests use the standard `testing` package. Table-driven tests are the Go idiom.

```go
package patterns_test

import (
    "context"
    "errors"
    "testing"

    "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

func TestSequentialAgent(t *testing.T) {
    tests := []struct {
        name    string
        agents  []agenkit.Agent
        input   string
        want    string
        wantErr bool
    }{
        {
            name: "single agent passes through",
            agents: []agenkit.Agent{
                &mockAgent{response: "hello"},
            },
            input: "test",
            want:  "hello",
        },
        {
            name: "two agents chain correctly",
            agents: []agenkit.Agent{
                &mockAgent{response: "step-1"},
                &mockAgent{response: "step-2"},
            },
            input: "test",
            want:  "step-2", // last agent's response
        },
        {
            name:    "empty agent list returns error",
            agents:  []agenkit.Agent{},
            input:   "test",
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            ctx := context.Background()
            seq := patterns.NewSequentialAgent(tt.agents)

            result, err := seq.Process(ctx, agenkit.NewMessage("user", tt.input))
            if tt.wantErr {
                if err == nil {
                    t.Error("expected error, got nil")
                }
                return
            }
            if err != nil {
                t.Fatalf("unexpected error: %v", err)
            }
            if result.Content != tt.want {
                t.Errorf("expected %q, got %q", tt.want, result.Content)
            }
        })
    }
}
```

### Running Tests

```bash
# Run all tests
go test ./...

# Run with verbose output
go test -v ./...

# Run specific package
go test ./patterns/

# Run specific test
go test -run TestSequentialAgent ./patterns/

# Run with race detector (important for concurrent agents)
go test -race ./...

# Run with coverage
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# Run benchmarks
go test -bench=. ./...
go test -bench=BenchmarkParallelAgent -benchtime=10s ./patterns/
```

---

## testutil Package

The `testutil` package provides mock agents and helper utilities for testing.

### MockAgent

Cycles through predefined responses:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/testutil"

func TestWithMockAgent(t *testing.T) {
    ctx := context.Background()

    mock := testutil.NewMockAgent([]string{
        "response 1",
        "response 2",
        "response 3",
    })

    // First call returns "response 1"
    r1, err := mock.Process(ctx, agenkit.NewMessage("user", "first"))
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if r1.Content != "response 1" {
        t.Errorf("expected %q, got %q", "response 1", r1.Content)
    }

    // Second call returns "response 2"
    r2, _ := mock.Process(ctx, agenkit.NewMessage("user", "second"))
    if r2.Content != "response 2" {
        t.Errorf("expected %q, got %q", "response 2", r2.Content)
    }

    // Fourth call wraps back to "response 1"
    _, _ = mock.Process(ctx, agenkit.NewMessage("user", "third"))
    r4, _ := mock.Process(ctx, agenkit.NewMessage("user", "fourth"))
    if r4.Content != "response 1" {
        t.Errorf("expected wrap-around to %q, got %q", "response 1", r4.Content)
    }

    // Verify call count
    if got := mock.CallCount(); got != 4 {
        t.Errorf("expected 4 calls, got %d", got)
    }

    mock.Reset()
    if got := mock.CallCount(); got != 0 {
        t.Errorf("expected 0 calls after reset, got %d", got)
    }
}
```

### FailingMockAgent

Always returns a specified error:

```go
failing := testutil.NewFailingMockAgent(agenkit.ErrEmptyInput)

_, err := failing.Process(ctx, agenkit.NewMessage("user", "test"))
if !errors.Is(err, agenkit.ErrEmptyInput) {
    t.Errorf("expected ErrEmptyInput, got %v", err)
}
```

### mockAgent (inline test double)

For simple tests, define a minimal mock inline:

```go
// mockAgent is a minimal agenkit.Agent test double.
type mockAgent struct {
    name     string
    response string
    err      error
    calls    int
}

func (m *mockAgent) Name() string { return m.name }
func (m *mockAgent) Capabilities() []string { return nil }
func (m *mockAgent) Introspect() *agenkit.IntrospectionResult { return nil }
func (m *mockAgent) Process(_ context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
    m.calls++
    if m.err != nil {
        return nil, m.err
    }
    return agenkit.NewMessage("assistant", m.response), nil
}
```

---

## Table-Driven Tests

Table-driven tests are the idiomatic Go testing pattern. Use them for all non-trivial test cases.

### Pattern: Input/Output Tests

```go
func TestMessageRoles(t *testing.T) {
    tests := []struct {
        name    string
        role    string
        content string
        valid   bool
    }{
        {"user message", "user", "hello", true},
        {"assistant message", "assistant", "hi", true},
        {"system message", "system", "be helpful", true},
        {"tool message", "tool", `{"result": "ok"}`, true},
        {"empty content", "user", "", false},
        {"empty role", "", "hello", false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            msg := &agenkit.Message{Role: tt.role, Content: tt.content}
            err := validateMessage(msg)
            if tt.valid && err != nil {
                t.Errorf("expected valid, got error: %v", err)
            }
            if !tt.valid && err == nil {
                t.Error("expected error, got nil")
            }
        })
    }
}
```

### Pattern: Middleware Behavior Tests

```go
func TestRetryMiddleware(t *testing.T) {
    tests := []struct {
        name        string
        failures    int   // how many times to fail before succeeding
        maxRetries  int
        wantErr     bool
        wantCalls   int
    }{
        {"succeeds on first try", 0, 3, false, 1},
        {"succeeds on second try", 1, 3, false, 2},
        {"succeeds on last try", 3, 3, false, 4},
        {"exhausts retries", 4, 3, true, 4},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            ctx := context.Background()

            // Agent fails `failures` times, then succeeds
            failCount := 0
            mock := &funcAgent{
                process: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
                    failCount++
                    if failCount <= tt.failures {
                        return nil, fmt.Errorf("transient error")
                    }
                    return agenkit.NewMessage("assistant", "ok"), nil
                },
            }

            agent := middleware.NewRetryMiddleware(mock, &middleware.RetryConfig{
                MaxRetries:   tt.maxRetries,
                InitialDelay: 1 * time.Millisecond, // Fast for tests
            })

            _, err := agent.Process(ctx, agenkit.NewMessage("user", "test"))
            if tt.wantErr && err == nil {
                t.Error("expected error, got nil")
            }
            if !tt.wantErr && err != nil {
                t.Errorf("unexpected error: %v", err)
            }
            if failCount != tt.wantCalls {
                t.Errorf("expected %d calls, got %d", tt.wantCalls, failCount)
            }
        })
    }
}
```

---

## Mocking Agents

### Interface-Based Mocking

Because `agenkit.Agent` is a small interface, mocking is straightforward:

```go
// funcAgent adapts a function to the Agent interface.
type funcAgent struct {
    name    string
    process func(context.Context, *agenkit.Message) (*agenkit.Message, error)
}

func (f *funcAgent) Name() string {
    if f.name == "" {
        return "func-agent"
    }
    return f.name
}
func (f *funcAgent) Capabilities() []string { return nil }
func (f *funcAgent) Introspect() *agenkit.IntrospectionResult { return nil }
func (f *funcAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    return f.process(ctx, msg)
}

// Usage in test:
agent := &funcAgent{
    process: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
        return agenkit.NewMessage("assistant", "mocked: "+msg.Content), nil
    },
}
```

### Spy Agent (tracks calls)

```go
// spyAgent records all calls for verification.
type spyAgent struct {
    calls    []*agenkit.Message
    response string
    mu       sync.Mutex
}

func (s *spyAgent) Name() string { return "spy" }
func (s *spyAgent) Capabilities() []string { return nil }
func (s *spyAgent) Introspect() *agenkit.IntrospectionResult { return nil }
func (s *spyAgent) Process(_ context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    s.mu.Lock()
    s.calls = append(s.calls, msg)
    s.mu.Unlock()
    return agenkit.NewMessage("assistant", s.response), nil
}

func (s *spyAgent) CallCount() int {
    s.mu.Lock()
    defer s.mu.Unlock()
    return len(s.calls)
}

func (s *spyAgent) LastCall() *agenkit.Message {
    s.mu.Lock()
    defer s.mu.Unlock()
    if len(s.calls) == 0 {
        return nil
    }
    return s.calls[len(s.calls)-1]
}

// Usage:
spy := &spyAgent{response: "ok"}
agent := middleware.NewRetryMiddleware(spy, config)
_, _ = agent.Process(ctx, msg)
if spy.CallCount() != 1 {
    t.Errorf("expected 1 call, got %d", spy.CallCount())
}
```

---

## Property Tests with rapid

Property-based tests verify invariants hold for arbitrary inputs. The `pgregory.net/rapid` library provides Go property testing.

```bash
go get pgregory.net/rapid
```

### Basic Property Test

```go
import "pgregory.net/rapid"

func TestMessageRoleIsPreserved(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        // Generate arbitrary role and content
        role := rapid.SampledFrom([]string{"user", "assistant", "system", "tool"}).Draw(t, "role")
        content := rapid.StringN(1, 1000, -1).Draw(t, "content")

        msg := agenkit.NewMessage(role, content)

        // Invariant: role and content are preserved
        if msg.Role != role {
            t.Fatalf("role not preserved: got %q, want %q", msg.Role, role)
        }
        if msg.Content != content {
            t.Fatalf("content not preserved: got %q, want %q", msg.Content, content)
        }
    })
}
```

### Sequential Agent Invariants

```go
func TestSequentialAgentInvariants(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        ctx := context.Background()

        // Generate 1-5 agents
        n := rapid.IntRange(1, 5).Draw(t, "agent_count")
        responses := make([]string, n)
        agents := make([]agenkit.Agent, n)

        for i := range n {
            r := rapid.StringN(1, 50, -1).Draw(t, fmt.Sprintf("response_%d", i))
            responses[i] = r
            agents[i] = &mockAgent{response: r}
        }

        seq := patterns.NewSequentialAgent(agents)
        result, err := seq.Process(ctx, agenkit.NewMessage("user", "test"))
        if err != nil {
            t.Fatalf("unexpected error: %v", err)
        }

        // Invariant: output is always the last agent's response
        if result.Content != responses[n-1] {
            t.Fatalf("expected last response %q, got %q", responses[n-1], result.Content)
        }

        // Invariant: output role is always "assistant"
        if result.Role != "assistant" {
            t.Fatalf("expected role %q, got %q", "assistant", result.Role)
        }
    })
}
```

### Middleware Invariants

```go
func TestRetryMiddlewareAlwaysAttempts(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        ctx := context.Background()
        maxRetries := rapid.IntRange(0, 5).Draw(t, "max_retries")

        var actualCalls int
        alwaysFail := &funcAgent{
            process: func(_ context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
                actualCalls++
                return nil, fmt.Errorf("always fails")
            },
        }

        agent := middleware.NewRetryMiddleware(alwaysFail, &middleware.RetryConfig{
            MaxRetries:   maxRetries,
            InitialDelay: time.Nanosecond,
        })

        _, _ = agent.Process(ctx, agenkit.NewMessage("user", "test"))

        // Invariant: always makes exactly maxRetries+1 attempts
        expected := maxRetries + 1
        if actualCalls != expected {
            t.Fatalf("expected %d calls, got %d", expected, actualCalls)
        }
    })
}
```

---

## Benchmark Tests

Benchmarks measure performance of agents and patterns.

### Writing Benchmarks

```go
func BenchmarkSequentialAgent(b *testing.B) {
    ctx := context.Background()
    agent := patterns.NewSequentialAgent([]agenkit.Agent{
        &mockAgent{response: "step-1"},
        &mockAgent{response: "step-2"},
        &mockAgent{response: "step-3"},
    })
    msg := agenkit.NewMessage("user", "benchmark input")

    b.ResetTimer()
    for b.Loop() {
        _, err := agent.Process(ctx, msg)
        if err != nil {
            b.Fatalf("unexpected error: %v", err)
        }
    }
}

func BenchmarkParallelAgent(b *testing.B) {
    ctx := context.Background()
    agents := make([]agenkit.Agent, 4)
    for i := range agents {
        agents[i] = &mockAgent{response: fmt.Sprintf("result-%d", i)}
    }
    parallel := patterns.NewParallelAgent(agents, nil)
    msg := agenkit.NewMessage("user", "benchmark input")

    b.ResetTimer()
    for b.Loop() {
        _, err := parallel.Process(ctx, msg)
        if err != nil {
            b.Fatalf("unexpected error: %v", err)
        }
    }
}
```

### Running Benchmarks

```bash
# Run all benchmarks
go test -bench=. ./...

# Run specific benchmark
go test -bench=BenchmarkSequential ./patterns/

# Run with memory profiling
go test -bench=. -benchmem ./...

# Run longer benchmark for stable results
go test -bench=. -benchtime=10s ./...

# Compare benchmarks with benchstat
go test -bench=. -count=5 ./... > before.txt
# (make changes)
go test -bench=. -count=5 ./... > after.txt
benchstat before.txt after.txt
```

### Expected Performance

```
BenchmarkSequentialAgent-8     2000000     650 ns/op      0 B/op    0 allocs/op
BenchmarkParallelAgent-8        500000    2400 ns/op    320 B/op    4 allocs/op
BenchmarkReflectionAgent-8      100000   12000 ns/op    640 B/op    8 allocs/op
```

---

## Testing Concurrent Agents

Always run concurrent tests with `-race`:

```go
func TestParallelAgentConcurrency(t *testing.T) {
    // This test should be run with -race to detect data races
    ctx := context.Background()

    // Safe: stateless agents
    agents := make([]agenkit.Agent, 10)
    for i := range agents {
        agents[i] = &mockAgent{response: fmt.Sprintf("r%d", i)}
    }

    parallel := patterns.NewParallelAgent(agents, nil)

    // Run many concurrent requests
    var wg sync.WaitGroup
    for range 100 {
        wg.Add(1)
        go func() {
            defer wg.Done()
            msg := agenkit.NewMessage("user", "concurrent test")
            _, err := parallel.Process(ctx, msg)
            if err != nil {
                t.Errorf("concurrent error: %v", err)
            }
        }()
    }
    wg.Wait()
}
```

---

## Test Organization

```
agenkit-go/
├── agenkit/
│   └── message_test.go       # Core type tests
├── patterns/
│   ├── sequential_test.go    # Sequential pattern tests
│   ├── parallel_test.go      # Parallel pattern + race tests
│   ├── reflection_test.go    # Reflection pattern tests
│   └── ...
├── middleware/
│   ├── retry_test.go         # Retry behavior tests
│   ├── circuit_breaker_test.go
│   └── ...
├── testutil/
│   ├── mock_agent.go         # MockAgent, FailingMockAgent
│   └── mock_agent_test.go    # Tests for test utilities
└── benchmarks/
    └── patterns_bench_test.go # Performance benchmarks
```

---

## See Also

- [Getting Started](GETTING_STARTED.md) - Basic test setup
- [API Reference](API.md) - Types and interfaces
- [Patterns Guide](PATTERNS.md) - Patterns being tested
- [Observability](OBSERVABILITY.md) - Testing with mock traces
