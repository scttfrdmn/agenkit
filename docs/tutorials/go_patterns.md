# Building Production AI Agents in Go

A practical guide to building robust, concurrent AI agents using agenkit-go. Each tutorial
is self-contained and runnable with `go run`.

---

## Introduction: Why Go for AI Agents

Go's design aligns naturally with the requirements of production AI agent systems:

- **Goroutines** are cheap (a few KB of stack) — you can run thousands concurrently without
  an explicit thread pool.
- **Channels** give you typed, safe message passing between agents with back-pressure built in.
- **Context propagation** (`context.Context`) lets you cancel work, set deadlines, and carry
  request-scoped values through an entire call tree.
- **Single static binary** means no runtime to install on your server; `go build` produces
  a self-contained executable.
- **True parallelism** — Go's scheduler uses all CPU cores by default, so parallel fan-out
  actually runs in parallel (unlike Python's GIL).

The trade-offs:
- Explicit error handling (`if err != nil`) — more code, fewer surprises.
- No generics-based magic; type safety is explicit.
- Longer iteration cycle than Python for early prototyping.

For background services handling many concurrent LLM requests, Go is an excellent fit.

### Prerequisites

```bash
go get github.com/scttfrdmn/agenkit/agenkit-go@latest
```

Go 1.22+ is required. All examples compile and run with `go run main.go`.

---

## Tutorial 1: Goroutines and Concurrent Agents

### Goal

Fan out a single user message to three specialist agents simultaneously, then combine
their responses — the classic **fan-out / fan-in** pattern.

### Naive Sequential Approach (slow)

```go
package main

import (
    "context"
    "fmt"
    "log"

    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
)

func main() {
    ctx := context.Background()
    msg := agenkit.Message{Role: agenkit.RoleUser, Content: "What is 2+2?"}

    agents := []agenkit.Agent{factChecker, summarizer, critic}
    results := make([]agenkit.Message, 0, len(agents))

    for _, a := range agents {
        resp, err := a.Process(ctx, msg)
        if err != nil {
            log.Printf("agent failed: %v", err)
            continue
        }
        results = append(results, resp)
    }
    // Total time ≈ latency(factChecker) + latency(summarizer) + latency(critic)
    fmt.Printf("Got %d responses\n", len(results))
}
```

### Fan-Out with errgroup (fast)

```go
package main

import (
    "context"
    "fmt"
    "log"
    "sync"

    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
    "golang.org/x/sync/errgroup"
)

// fanOut sends msg to every agent concurrently and returns all responses.
// The first error from any agent cancels the remaining goroutines.
func fanOut(ctx context.Context, msg agenkit.Message, agents []agenkit.Agent) ([]agenkit.Message, error) {
    var mu sync.Mutex
    results := make([]agenkit.Message, 0, len(agents))

    g, ctx := errgroup.WithContext(ctx)

    for _, a := range agents {
        a := a // capture loop variable
        g.Go(func() error {
            resp, err := a.Process(ctx, msg)
            if err != nil {
                return fmt.Errorf("agent %q: %w", a.Name(), err)
            }
            mu.Lock()
            results = append(results, resp)
            mu.Unlock()
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return results, nil
}

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    msg := agenkit.Message{Role: agenkit.RoleUser, Content: "Explain quantum entanglement."}
    agents := []agenkit.Agent{factChecker, summarizer, critic}

    results, err := fanOut(ctx, msg, agents)
    if err != nil {
        log.Fatalf("fan-out failed: %v", err)
    }

    for i, r := range results {
        fmt.Printf("Response %d: %.80s\n", i+1, r.Content)
    }
    // Total time ≈ max(latency(factChecker), latency(summarizer), latency(critic))
}
```

### Fan-In with a Results Channel

When you want streaming results as they arrive (rather than waiting for all):

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
)

type agentResult struct {
    agentName string
    msg       agenkit.Message
    err       error
}

// fanOutStream sends results on ch as each agent finishes.
func fanOutStream(ctx context.Context, msg agenkit.Message, agents []agenkit.Agent) <-chan agentResult {
    ch := make(chan agentResult, len(agents))

    for _, a := range agents {
        a := a
        go func() {
            resp, err := a.Process(ctx, msg)
            ch <- agentResult{agentName: a.Name(), msg: resp, err: err}
        }()
    }

    // Close channel after all goroutines finish.
    go func() {
        // We know exactly how many results to expect.
        // A sync.WaitGroup inside the goroutines would close cleanly too.
        time.Sleep(60 * time.Second) // safety net — in practice use WaitGroup
        close(ch)
    }()

    return ch
}

func main() {
    ctx := context.Background()
    msg := agenkit.Message{Role: agenkit.RoleUser, Content: "Summarise AI safety risks."}
    agents := []agenkit.Agent{factChecker, summarizer, critic}

    ch := fanOutStream(ctx, msg, agents)

    received := 0
    for result := range ch {
        if result.err != nil {
            log.Printf("agent %q error: %v", result.agentName, result.err)
        } else {
            fmt.Printf("[%s] %.80s\n", result.agentName, result.msg.Content)
        }
        received++
        if received == len(agents) {
            break // got all results
        }
    }
}
```

### Key Takeaways

- Use `errgroup.WithContext` when you want the **first error to cancel** remaining goroutines.
- Use a buffered result channel when you want **streaming output** as each agent finishes.
- Always capture loop variables (`a := a`) before launching goroutines.
- Pass `context.Context` through every call so timeouts propagate correctly.

---

## Tutorial 2: Middleware Chaining

### Goal

Compose retry, timeout, and metrics collection around any `Agent` without modifying
the agent's own code.

### The Middleware Interface

Agenkit-go middleware wraps an `Agent` and returns a new `Agent`:

```go
// Middleware is a function that wraps an Agent.
type Middleware func(agenkit.Agent) agenkit.Agent
```

### Retry Middleware

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "log"
    "time"

    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
)

// retryAgent wraps an agent and retries transient failures.
type retryAgent struct {
    inner      agenkit.Agent
    maxRetries int
    backoff    time.Duration
}

func (r *retryAgent) Name() string         { return r.inner.Name() }
func (r *retryAgent) Capabilities() []string { return r.inner.Capabilities() }

func (r *retryAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    var lastErr error
    for attempt := 0; attempt <= r.maxRetries; attempt++ {
        if attempt > 0 {
            select {
            case <-ctx.Done():
                return agenkit.Message{}, ctx.Err()
            case <-time.After(r.backoff * time.Duration(attempt)):
            }
        }
        resp, err := r.inner.Process(ctx, msg)
        if err == nil {
            return resp, nil
        }
        if !isTransient(err) {
            return agenkit.Message{}, err // non-retryable error
        }
        lastErr = err
        log.Printf("attempt %d/%d failed: %v", attempt+1, r.maxRetries+1, err)
    }
    return agenkit.Message{}, fmt.Errorf("all %d attempts failed: %w", r.maxRetries+1, lastErr)
}

// isTransient returns true for errors that may succeed on retry.
func isTransient(err error) bool {
    var rateLimit *agenkit.RateLimitError
    var timeout *agenkit.TimeoutError
    return errors.As(err, &rateLimit) || errors.As(err, &timeout)
}

// WithRetry wraps an agent with retry logic.
func WithRetry(inner agenkit.Agent, maxRetries int, backoff time.Duration) agenkit.Agent {
    return &retryAgent{inner: inner, maxRetries: maxRetries, backoff: backoff}
}
```

### Timeout Middleware

```go
// timeoutAgent wraps an agent with a per-call deadline.
type timeoutAgent struct {
    inner   agenkit.Agent
    timeout time.Duration
}

func (t *timeoutAgent) Name() string         { return t.inner.Name() }
func (t *timeoutAgent) Capabilities() []string { return t.inner.Capabilities() }

func (t *timeoutAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    ctx, cancel := context.WithTimeout(ctx, t.timeout)
    defer cancel()
    return t.inner.Process(ctx, msg)
}

// WithTimeout wraps an agent with a per-call timeout.
func WithTimeout(inner agenkit.Agent, timeout time.Duration) agenkit.Agent {
    return &timeoutAgent{inner: inner, timeout: timeout}
}
```

### Metrics Middleware

```go
import (
    "go.opentelemetry.io/otel/metric"
)

// metricsAgent records latency and error counts via OpenTelemetry.
type metricsAgent struct {
    inner    agenkit.Agent
    latency  metric.Float64Histogram
    errors   metric.Int64Counter
    calls    metric.Int64Counter
}

func (m *metricsAgent) Name() string         { return m.inner.Name() }
func (m *metricsAgent) Capabilities() []string { return m.inner.Capabilities() }

func (m *metricsAgent) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    start := time.Now()
    if _, err := m.calls.Add(ctx, 1); err != nil {
        log.Printf("metrics counter failed: %v", err)
    }

    resp, err := m.inner.Process(ctx, msg)

    elapsed := time.Since(start).Seconds()
    if recordErr := m.latency.Record(ctx, elapsed); recordErr != nil {
        log.Printf("metrics histogram failed: %v", recordErr)
    }
    if err != nil {
        if _, countErr := m.errors.Add(ctx, 1); countErr != nil {
            log.Printf("metrics error counter failed: %v", countErr)
        }
    }
    return resp, err
}
```

### Composing the Chain

```go
func main() {
    var base agenkit.Agent = &MyLLMAgent{name: "gpt4o"}

    // Layer middleware from innermost to outermost.
    // Order: metrics → timeout → retry → base
    agent := WithMetrics(
        WithRetry(
            WithTimeout(base, 10*time.Second),
            3,              // max retries
            500*time.Millisecond, // base backoff
        ),
        meter, // OpenTelemetry meter
    )

    ctx := context.Background()
    resp, err := agent.Process(ctx, agenkit.Message{
        Role:    agenkit.RoleUser,
        Content: "What is the capital of France?",
    })
    if err != nil {
        log.Fatalf("agent failed after retries: %v", err)
    }
    fmt.Println(resp.Content)
}
```

### Key Takeaways

- Each middleware is an `Agent` that wraps another `Agent` — open/closed principle.
- Composing timeout inside retry means each attempt gets its own deadline.
- All error checks inside middleware use `%w` wrapping so callers can use `errors.As`.

---

## Tutorial 3: Channel-Based Agent Pipelines

### Goal

Build a producer → transform → consumer pipeline where each stage is an independent
goroutine communicating through buffered channels.

### The Pipeline Pattern

```go
package main

import (
    "context"
    "fmt"
    "log"

    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
)

// stage runs an agent on every message from in, sending results to out.
// It closes out when in is exhausted or ctx is cancelled.
func stage(ctx context.Context, agent agenkit.Agent, in <-chan agenkit.Message) <-chan agenkit.Message {
    out := make(chan agenkit.Message, cap(in))
    go func() {
        defer close(out)
        for {
            select {
            case <-ctx.Done():
                return
            case msg, ok := <-in:
                if !ok {
                    return
                }
                resp, err := agent.Process(ctx, msg)
                if err != nil {
                    log.Printf("[%s] error: %v", agent.Name(), err)
                    continue
                }
                select {
                case out <- resp:
                case <-ctx.Done():
                    return
                }
            }
        }
    }()
    return out
}

// source produces messages and sends them on a channel.
func source(ctx context.Context, messages []agenkit.Message) <-chan agenkit.Message {
    ch := make(chan agenkit.Message, len(messages))
    go func() {
        defer close(ch)
        for _, msg := range messages {
            select {
            case <-ctx.Done():
                return
            case ch <- msg:
            }
        }
    }()
    return ch
}

func main() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    inputs := []agenkit.Message{
        {Role: agenkit.RoleUser, Content: "Explain photosynthesis."},
        {Role: agenkit.RoleUser, Content: "What is machine learning?"},
        {Role: agenkit.RoleUser, Content: "Describe the water cycle."},
    }

    // Build pipeline: source → summarizer → critic → sink
    src := source(ctx, inputs)
    summarized := stage(ctx, summarizerAgent, src)
    critiqued := stage(ctx, criticAgent, summarized)

    // Consume results.
    for result := range critiqued {
        fmt.Printf("Final: %.120s\n\n", result.Content)
    }
}
```

### Parallel Stage (fan-out within a stage)

```go
// parallelStage runs n concurrent copies of agent on messages from in.
func parallelStage(ctx context.Context, agent agenkit.Agent, n int, in <-chan agenkit.Message) <-chan agenkit.Message {
    out := make(chan agenkit.Message, n*2)

    var wg sync.WaitGroup
    for i := 0; i < n; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for {
                select {
                case <-ctx.Done():
                    return
                case msg, ok := <-in:
                    if !ok {
                        return
                    }
                    resp, err := agent.Process(ctx, msg)
                    if err != nil {
                        log.Printf("parallel stage error: %v", err)
                        continue
                    }
                    select {
                    case out <- resp:
                    case <-ctx.Done():
                        return
                    }
                }
            }
        }()
    }

    go func() {
        wg.Wait()
        close(out)
    }()
    return out
}
```

### Back-Pressure with Bounded Channels

```go
// Use small buffer sizes to apply back-pressure.
// The producer will block when the consumer is slow.
const bufferSize = 5

func boundedPipeline(ctx context.Context, agents []agenkit.Agent, inputs []agenkit.Message) {
    ch := make(chan agenkit.Message, bufferSize)

    // Producer
    go func() {
        defer close(ch)
        for _, msg := range inputs {
            select {
            case ch <- msg:
            case <-ctx.Done():
                return
            }
        }
    }()

    // Chain of stages
    for _, agent := range agents {
        ch = stage(ctx, agent, ch) // each stage uses bufferSize internally
    }

    // Consumer
    for result := range ch {
        fmt.Println(result.Content)
    }
}
```

### Key Takeaways

- `defer close(out)` inside every goroutine guarantees downstream stages terminate cleanly.
- Buffered channels decouple producer and consumer speed; small buffers apply back-pressure.
- A `select` on both `ctx.Done()` and the channel ensures every goroutine respects cancellation.
- `parallelStage` reuses a single channel with N goroutines — classic worker pool.

---

## Tutorial 4: Testing with pgregory.net/rapid

### Goal

Use property-based testing to verify agent invariants hold across randomly generated inputs,
not just hand-crafted examples.

### Why Property-Based Tests?

Unit tests check specific cases. Property tests ask: *for any valid input, does this
invariant hold?* They find edge cases you would never think to write manually.

### Setup

```bash
go get pgregory.net/rapid@latest
```

`pgregory.net/rapid` is already in `agenkit-go`'s `go.mod`.

### Defining Agent Properties

```go
package agent_test

import (
    "context"
    "strings"
    "testing"

    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
    "pgregory.net/rapid"
)

// messageGenerator produces random valid Messages for rapid.
func messageGenerator() *rapid.Generator[agenkit.Message] {
    return rapid.Custom(func(t *rapid.T) agenkit.Message {
        role := rapid.SampledFrom([]agenkit.Role{
            agenkit.RoleUser,
            agenkit.RoleAssistant,
            agenkit.RoleSystem,
        }).Draw(t, "role")
        content := rapid.StringOfN(rapid.RuneFrom(nil, rapid.UnicodeRange('A', 'z')), 1, 500, -1).Draw(t, "content")
        return agenkit.Message{Role: role, Content: content}
    })
}

// Property 1: Process always returns a non-empty response for non-empty input.
func TestEchoAgent_NonEmptyOutput(t *testing.T) {
    agent := &EchoAgent{}
    rapid.Check(t, func(t *rapid.T) {
        msg := messageGenerator().Draw(t, "msg")
        if msg.Content == "" {
            t.Skip() // generator shouldn't produce empty, but guard anyway
        }

        resp, err := agent.Process(context.Background(), msg)

        if err != nil {
            t.Fatalf("unexpected error: %v", err)
        }
        if resp.Content == "" {
            t.Fatalf("got empty response for non-empty input %q", msg.Content)
        }
    })
}

// Property 2: Process always returns role=assistant.
func TestEchoAgent_AlwaysAssistantRole(t *testing.T) {
    agent := &EchoAgent{}
    rapid.Check(t, func(t *rapid.T) {
        msg := messageGenerator().Draw(t, "msg")
        resp, err := agent.Process(context.Background(), msg)
        if err != nil {
            t.Fatalf("unexpected error: %v", err)
        }
        if resp.Role != agenkit.RoleAssistant {
            t.Fatalf("got role %q, want %q", resp.Role, agenkit.RoleAssistant)
        }
    })
}

// Property 3: Sequential(a, b).Process is deterministic — same input, same output.
func TestSequential_Deterministic(t *testing.T) {
    a := &EchoAgent{}
    b := &UpperAgent{}
    seq := patterns.NewSequential([]agenkit.Agent{a, b})

    rapid.Check(t, func(t *rapid.T) {
        msg := messageGenerator().Draw(t, "msg")
        ctx := context.Background()

        resp1, err1 := seq.Process(ctx, msg)
        resp2, err2 := seq.Process(ctx, msg)

        if (err1 == nil) != (err2 == nil) {
            t.Fatalf("non-deterministic error: first=%v second=%v", err1, err2)
        }
        if err1 == nil && resp1.Content != resp2.Content {
            t.Fatalf("non-deterministic output: first=%q second=%q", resp1.Content, resp2.Content)
        }
    })
}

// Property 4: Retry middleware does not change the successful response.
func TestRetryMiddleware_PassthroughOnSuccess(t *testing.T) {
    inner := &EchoAgent{}
    agent := WithRetry(inner, 3, 0)

    rapid.Check(t, func(t *rapid.T) {
        msg := messageGenerator().Draw(t, "msg")

        want, err := inner.Process(context.Background(), msg)
        if err != nil {
            t.Skip() // skip if inner itself fails
        }

        got, err := agent.Process(context.Background(), msg)
        if err != nil {
            t.Fatalf("retry wrapper failed when inner succeeded: %v", err)
        }
        if got.Content != want.Content {
            t.Fatalf("retry changed successful response: got %q, want %q", got.Content, want.Content)
        }
    })
}
```

### Table-Driven Tests for Known Edge Cases

Property tests complement (not replace) table-driven tests:

```go
func TestEchoAgent_EdgeCases(t *testing.T) {
    agent := &EchoAgent{}
    ctx := context.Background()

    tests := []struct {
        name    string
        input   string
        wantErr bool
    }{
        {"empty content", "", true},
        {"only whitespace", "   ", true},
        {"very long input", strings.Repeat("a", 10000), false},
        {"unicode content", "héllo wörld 🌍", false},
        {"null bytes", "\x00\x01\x02", false},
    }

    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            msg := agenkit.Message{Role: agenkit.RoleUser, Content: tc.input}
            _, err := agent.Process(ctx, msg)
            if tc.wantErr && err == nil {
                t.Error("expected error, got nil")
            }
            if !tc.wantErr && err != nil {
                t.Errorf("unexpected error: %v", err)
            }
        })
    }
}
```

### Key Takeaways

- `rapid.Check` runs 100 iterations by default; set `RAPID_CHECKS=1000` for CI.
- Use `t.Skip()` (not `t.Fatal`) when a random input hits a known invalid precondition.
- Properties should be universal truths: role invariants, determinism, idempotency.
- Combine property tests (for coverage) with table tests (for known edge cases).

---

## Tutorial 5: Graceful Shutdown

### Goal

Shut down a long-running agent server cleanly when receiving SIGTERM or SIGINT, allowing
in-flight requests to complete within a deadline.

### Signal Handling

```go
package main

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"

    agenkit "github.com/scttfrdmn/agenkit/agenkit-go"
)

func main() {
    // Root context — cancelled on shutdown signal.
    ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
    defer stop()

    server := NewAgentServer()
    if err := server.Start(ctx); err != nil {
        log.Fatalf("server start: %v", err)
    }

    // Block until signal.
    <-ctx.Done()
    log.Println("shutdown signal received")

    // Give in-flight requests 30 seconds to finish.
    shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    if err := server.Shutdown(shutdownCtx); err != nil {
        log.Printf("graceful shutdown failed: %v", err)
        os.Exit(1)
    }
    log.Println("shutdown complete")
}
```

### Agent Server with In-Flight Tracking

```go
type AgentServer struct {
    agent agenkit.Agent
    wg    sync.WaitGroup
    mu    sync.Mutex
    alive bool
}

func NewAgentServer() *AgentServer {
    return &AgentServer{
        agent: buildAgent(),
        alive: true,
    }
}

// Process handles a single agent request, tracking it for graceful shutdown.
func (s *AgentServer) Process(ctx context.Context, msg agenkit.Message) (agenkit.Message, error) {
    s.mu.Lock()
    if !s.alive {
        s.mu.Unlock()
        return agenkit.Message{}, fmt.Errorf("server is shutting down")
    }
    s.wg.Add(1)
    s.mu.Unlock()
    defer s.wg.Done()

    return s.agent.Process(ctx, msg)
}

// Shutdown stops accepting new requests and waits for in-flight ones to finish.
func (s *AgentServer) Shutdown(ctx context.Context) error {
    s.mu.Lock()
    s.alive = false
    s.mu.Unlock()

    done := make(chan struct{})
    go func() {
        s.wg.Wait()
        close(done)
    }()

    select {
    case <-done:
        log.Println("all in-flight requests completed")
        return nil
    case <-ctx.Done():
        return fmt.Errorf("shutdown timed out with requests still in flight: %w", ctx.Err())
    }
}
```

### Worker Pool with Graceful Drain

```go
type WorkerPool struct {
    jobs    chan agenkit.Message
    results chan agenkit.Message
    agent   agenkit.Agent
    wg      sync.WaitGroup
}

func NewWorkerPool(agent agenkit.Agent, workers, queueSize int) *WorkerPool {
    p := &WorkerPool{
        jobs:    make(chan agenkit.Message, queueSize),
        results: make(chan agenkit.Message, queueSize),
        agent:   agent,
    }
    for i := 0; i < workers; i++ {
        p.wg.Add(1)
        go p.worker()
    }
    return p
}

func (p *WorkerPool) worker() {
    defer p.wg.Done()
    for msg := range p.jobs {
        resp, err := p.agent.Process(context.Background(), msg)
        if err != nil {
            log.Printf("worker error: %v", err)
            continue
        }
        p.results <- resp
    }
}

// Submit adds a job to the queue, blocking if full.
func (p *WorkerPool) Submit(msg agenkit.Message) { p.jobs <- msg }

// Drain closes the jobs channel and waits for all workers to finish.
func (p *WorkerPool) Drain() {
    close(p.jobs) // signal workers to finish current jobs and exit
    p.wg.Wait()
    close(p.results)
}

func main() {
    ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
    defer stop()

    pool := NewWorkerPool(buildAgent(), 4, 100)

    // Feed work until shutdown signal.
    go func() {
        for {
            select {
            case <-ctx.Done():
                return
            default:
                pool.Submit(nextJob())
            }
        }
    }()

    // Wait for signal.
    <-ctx.Done()
    log.Println("draining worker pool...")
    pool.Drain()
    log.Println("done")
}
```

### Key Takeaways

- `signal.NotifyContext` is the idiomatic way to hook OS signals into Go's context system.
- Use a `sync.WaitGroup` to track in-flight work; call `wg.Wait()` inside `Shutdown`.
- Close the jobs channel (not a separate "stop" bool) to signal workers cleanly.
- Always pair `context.WithTimeout` with `defer cancel()` to avoid leaking the timer goroutine.

---

## Next Steps

- **Reference**: `agenkit-go/docs/API.md` — complete package documentation
- **Examples**: `examples/go/` — 15+ runnable examples covering all patterns
- **Patterns**: `docs/PATTERNS.md` — canonical pattern catalogue (Go + all languages)
- **Property testing**: `agenkit-go/agent_property_test.go` — 40 property tests to study
- **Benchmarks**: `benchmarks/go/` — performance baselines for common patterns

```bash
# Run all Go tests including property tests
cd agenkit-go && go test ./... -count=1

# Run property tests with more iterations
RAPID_CHECKS=500 go test ./... -run Property

# Benchmark sequential vs parallel fan-out
go test -bench=BenchmarkFanOut -benchtime=10s ./...
```
