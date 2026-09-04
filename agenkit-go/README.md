# Agenkit Go

**Production-grade AI agent toolkit for Go 1.25.14+**

The Go implementation of Agenkit maintains 100% behavioral parity with the reference
Python implementation, with true parallelism and single-binary deployment.

[![Go Reference](https://pkg.go.dev/badge/github.com/scttfrdmn/agenkit/agenkit-go.svg)](https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go)
[![Go 1.25+](https://img.shields.io/badge/go-1.25+-00ADD8.svg)](https://golang.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![Cross-Language Parity](https://img.shields.io/badge/parity-100%25-success.svg)](https://github.com/scttfrdmn/agenkit/tree/main/tests/cross_language)

## Why Go?

- **Concurrency**: Goroutines for true parallel agent execution
- **Performance**: Microsecond-scale pattern orchestration
- **Deployment**: Single binary, no runtime dependencies

On the [measured pattern benchmarks](https://github.com/scttfrdmn/agenkit/blob/main/docs/PERFORMANCE_COMPARISON.md)
Go beats Python on 8 of 9 patterns — by 56x on Supervisor, 35x on Parallel and 17x on
ReAct — but is **slower on Reflection** (100 μs vs Python's 16 μs), which is enough to
put Go behind Python on the unweighted average. Pick Go for concurrency and deployment
shape, and check the numbers for your pattern rather than assuming a blanket speedup.

**Perfect for**:
- Production workloads requiring high throughput
- Microservices and distributed systems
- Edge deployments with constrained resources
- Cost optimization (fewer instances needed)

## Installation

```bash
go get github.com/scttfrdmn/agenkit-go
```

## Documentation

Full documentation is available in [agenkit-go/docs/](docs/):

- [Getting Started](docs/GETTING_STARTED.md) — Installation, first agent, goroutine safety, testing
- [API Reference](docs/API.md) — Complete Go API documentation
- [Patterns](docs/PATTERNS.md) — the 18 agent patterns, with Go examples
- [Migration Guide](docs/MIGRATION.md) — Migrating to/from Go for 5 languages
- [Observability](docs/OBSERVABILITY.md) — Tracing, metrics, structured logging
- [Testing Framework](docs/TESTING_FRAMEWORK.md) — go test patterns, rapid property tests

## Quick Start

> Every snippet below is copied from [`examples/readme/main.go`](examples/readme/main.go),
> which is compiled by `go build ./...`. If a snippet here references an API that
> doesn't exist, CI fails.

### Basic Agent

```go
package main

import (
	"context"
	"fmt"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

type EchoAgent struct{}

func (a *EchoAgent) Name() string {
	return "echo-agent"
}

func (a *EchoAgent) Capabilities() []string {
	return []string{"echo", "simple"}
}

func (a *EchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Content is `any` — read it through ContentString().
	return agenkit.NewMessage("assistant", fmt.Sprintf("Echo: %s", message.ContentString())), nil
}

func (a *EchoAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

func main() {
	agent := &EchoAgent{}
	ctx := context.Background()

	message := agenkit.NewMessage("user", "Hello!")
	response, err := agent.Process(ctx, message)
	if err != nil {
		panic(err)
	}

	fmt.Println(response.ContentString()) // "Echo: Hello!"
}
```

### Production-Ready Agent with Resilience

```go
import (
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

func main() {
	// Declare as the interface so the decorators can be composed by reassignment
	var agent agenkit.Agent = &MyAgent{}

	// Add resilience decorators — config is passed by value
	agent = middleware.NewRetryDecorator(agent, middleware.RetryConfig{
		MaxRetries:        3,
		InitialRetryDelay: 100 * time.Millisecond,
		RetryMultiplier:   2.0,
	})

	agent = middleware.NewCircuitBreakerDecorator(agent, middleware.CircuitBreakerConfig{
		FailureThreshold: 5,
		RecoveryTimeout:  60 * time.Second,
	})

	agent = middleware.NewTimeoutDecorator(agent, middleware.TimeoutConfig{
		Timeout: 30 * time.Second,
	})

	// Now it's production-ready
	response, err := agent.Process(ctx, message)
}
```

### Agent Patterns

#### Sequential Pipeline

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

// Data flows: Agent1 → Agent2 → Agent3
pipeline, err := patterns.NewSequentialAgent([]agenkit.Agent{
	&DataExtractionAgent{},
	&AnalysisAgent{},
	&ReportGenerationAgent{},
})
if err != nil {
	return err
}

result, err := pipeline.Process(ctx, message)
```

#### Parallel Execution

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

// Execute multiple agents concurrently using goroutines.
//
// The aggregator is required — passing nil returns an error. Choose one of
// patterns.DefaultAggregators (First, Concatenate, MajorityVote) or write your own.
parallel, err := patterns.NewParallelAgent([]agenkit.Agent{
	&SentimentAnalysisAgent{},
	&EntityExtractionAgent{},
	&TopicClassificationAgent{},
}, patterns.DefaultAggregators.Concatenate)
if err != nil {
	return err
}

result, err := parallel.Process(ctx, message)
```

#### Conversational Agent

```go
import (
	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// Maintains conversation history.
//
// LLMClient accepts anything implementing Complete(ctx, messages, ...opts) —
// every shipped adapter satisfies that structurally, so no wrapper is needed.
agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
	LLMClient:    llm.NewAnthropicLLM(apiKey, "claude-sonnet-4-5"),
	SystemPrompt: "You are a helpful assistant.",
	MaxHistory:   10,
})
if err != nil {
	return err
}

response1, _ := agent.Process(ctx, agenkit.NewMessage("user", "What's the capital of France?"))
response2, _ := agent.Process(ctx, agenkit.NewMessage("user", "What's its population?"))
// Agent remembers context from previous messages
```

#### ReAct (Reasoning + Acting)

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

type CalculatorTool struct{}

func (t *CalculatorTool) Name() string {
	return "calculator"
}

func (t *CalculatorTool) Description() string {
	return "Evaluates mathematical expressions"
}

func (t *CalculatorTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	// Implementation here
	return agenkit.NewToolResult(result), nil
}

// ReAct agent with tools.
//
// The reasoning backend is an Agent (field `Agent`), and the step budget is
// `MaxSteps`.
agent, err := patterns.NewReActAgent(&patterns.ReActConfig{
	Agent:    myReasoningAgent,
	Tools:    []agenkit.Tool{&CalculatorTool{}, &WebSearchTool{}},
	MaxSteps: 5,
})
if err != nil {
	return err
}

result, err := agent.Process(ctx, message)
```

### Reasoning Techniques

#### Chain-of-Thought (CoT)

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"

// Step-by-step reasoning.
//
// The techniques take an Agent plus functional options — there is no config struct.
cot := reasoning.NewChainOfThought(
	myAgent,
	reasoning.WithMaxSteps(5),
)

result, err := cot.Process(ctx, agenkit.NewMessage("user", "What is 15 * 24?"))
if err != nil {
	return err
}

// reasoning_steps is only present when steps were parsed from the response,
// so comma-ok rather than a bare assertion.
if steps, ok := result.Metadata["reasoning_steps"].([]string); ok {
	fmt.Println(steps)
	// ["1. Multiply 15 by 20: 300", "2. Multiply 15 by 4: 60", "3. Add: 360"]
}
```

#### Tree-of-Thought (ToT)

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"

// Multi-path exploration with backtracking
tot := reasoning.NewTreeOfThought(
	myAgent,
	reasoning.WithBranchingFactor(3),
	reasoning.WithMaxDepth(4),
	reasoning.WithStrategy(reasoning.SearchStrategyBestFirst),
	reasoning.WithEvaluator(customEvaluator),
)

result, err := tot.Process(ctx, message)
if err != nil {
	return err
}

if path, ok := result.Metadata["reasoning_path"].([]string); ok {
	score, _ := result.Metadata["best_score"].(float64)
	fmt.Printf("Best path: %v (score: %.2f)\n", path, score)
}
```

#### Self-Consistency

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"

// Generate multiple reasoning paths and vote
sc := reasoning.NewSelfConsistency(
	myCOTAgent,
	reasoning.WithNumSamples(7),
	reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
)

result, err := sc.Process(ctx, message)
if err != nil {
	return err
}

consistency, _ := result.Metadata["consistency_score"].(float64)
counts, _ := result.Metadata["answer_counts"].(map[string]int)
fmt.Printf("Consistency: %.2f, Answers: %v\n", consistency, counts)
```

### Observability

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/observability"

// Enable distributed tracing.
//
// The second argument is the span *name*, not a tracer — the middleware resolves
// the tracer itself. Passing "" derives "agent.<name>.process".
agent = observability.NewTracingMiddleware(agent, "process_request")

// Now all agent calls are traced
result, err := agent.Process(ctx, message)
```

### HTTP Server

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/adapter/http"

// Expose agent as HTTP endpoint
server := http.NewHTTPAgent(agent, ":8080")

// Start server — the lifecycle is Start(ctx)/Stop(). Start returns immediately;
// cancelling ctx gracefully shuts the server down, so its lifetime can be tied
// to the caller's scope. Stop() is idempotent, so deferring it is always safe.
if err := server.Start(ctx); err != nil {
	log.Fatal(err)
}
defer func() { _ = server.Stop() }()
```

### gRPC Server

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/adapter/grpc"

// Expose agent as gRPC service
server, err := grpc.NewGRPCServer(agent, ":50051")
if err != nil {
	log.Fatal(err)
}

// Same lifecycle as the HTTP server above: cancelling ctx shuts the server
// down, and Stop() is the explicit path.
if err := server.Start(ctx); err != nil {
	log.Fatal(err)
}
defer func() { _ = server.Stop() }()
```

## Package Structure

```
agenkit-go/
├── agenkit/                 # Core package
│   ├── interfaces.go        # Agent, Message, Tool interfaces
│   └── introspection.go     # Introspection utilities
├── patterns/                # 18 agent patterns
│   ├── sequential.go        # Pipeline execution
│   ├── parallel.go          # Concurrent execution
│   ├── router.go            # Conditional routing
│   ├── conversational.go    # History management
│   ├── react.go             # Reasoning + Acting
│   ├── reflection.go        # Self-critique loop
│   ├── planning.go          # Task decomposition
│   ├── task.go              # Single-shot task execution
│   ├── autonomous.go        # Goal-driven agents
│   ├── supervisor.go        # Planner + specialists
│   ├── collaborative.go     # Peer collaboration
│   ├── multiagent.go        # Multi-agent orchestration
│   ├── orchestration.go     # Orchestrator pattern
│   ├── memory.go            # Memory-augmented agent
│   ├── agents_as_tools.go   # Agents exposed as tools
│   ├── fallback.go          # Ordered degradation
│   ├── human_in_loop.go     # Approval gates
│   └── reasoning_with_tools.go
├── techniques/              # Reasoning techniques
│   └── reasoning/
│       ├── chain_of_thought.go     # CoT prompting
│       ├── tree_of_thought.go      # ToT search
│       ├── self_consistency.go     # Voting strategy
│       ├── graph_of_thought.go     # Graph reasoning
│       └── reasoning_tree.go       # Tree utilities
├── middleware/              # Production middleware (all *Decorator)
│   ├── retry.go             # Automatic retries
│   ├── circuit_breaker.go   # Circuit breaker pattern
│   ├── timeout.go           # Timeout handling
│   ├── rate_limiter.go      # Rate limiting
│   ├── caching.go           # Response caching
│   ├── batching.go          # Request batching
│   └── metrics.go           # Metrics collection
├── adapter/                 # Adapters — LLM providers and transports
│   ├── llm/                 # Anthropic, OpenAI, Bedrock, Gemini, Ollama,
│   │                        #   vLLM, SGLang, LiteLLM, OpenAI-compatible
│   ├── http/                # HTTP/REST server
│   ├── grpc/                # gRPC server
│   ├── remote/              # Remote agent client (cross-language)
│   ├── transport/           # Transport plumbing
│   ├── codec/               # Wire encoding
│   ├── local/               # In-process adapter
│   ├── registry/            # Adapter registry
│   └── errors/              # Adapter error types
├── protocols/               # MCP, AG-UI, A2A
├── memory/                  # Memory stores
├── safety/                  # Guardrails
├── skills/                  # Agent skills
├── composition/             # Pattern composition
├── checkpointing/           # Durable state
├── observability/           # Tracing and metrics
│   ├── tracing.go           # OpenTelemetry integration
│   └── metrics.go           # Prometheus metrics
├── evaluation/              # Testing and optimization
└── budget/                  # Token and cost management
```

## API Reference

See [GoDoc](https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go) for complete API documentation.

## Examples

Comprehensive examples are available in [examples/](examples/):

Examples are packages, so pass the directory rather than a file:

```bash
# Every snippet in this README, compiled
go run ./examples/readme

# Pattern examples
go run ./examples/patterns/react
go run ./examples/patterns/planning
go run ./examples/patterns/router
go run ./examples/patterns/conversational

# Reasoning examples
go run ./examples/techniques/graph_of_thought
```

Some examples carry a `//go:build ignore` tag, which excludes them from `go build ./...`.
Run those by naming the file directly:

```bash
go run examples/middleware/retry_example.go
go run examples/frameworks/minicrew/main.go
```

Because the build tag opts them out of `go build ./...`, `go vet ./...` and CI, eight of
them do not currently compile — tracked in
[#843](https://github.com/scttfrdmn/agenkit/issues/843).

## Testing

```bash
# Run all tests
go test ./...

# Run with coverage
go test -cover ./...

# Run specific package tests
go test ./patterns/
go test ./techniques/reasoning/

# Run benchmarks
go test -bench=. ./benchmarks/
```

## Performance Benchmarks

Each pattern has its own benchmark — there is no umbrella `BenchmarkPatterns`. Select
the ones you care about by name:

```bash
# One pattern
go test -bench='^BenchmarkSequential$' -run='^$' ./benchmarks/

# Several
go test -bench='^Benchmark(Sequential|Parallel|ReAct|Router|Reflection)$' \
    -run='^$' -benchtime=10s ./benchmarks/

# Everything, including middleware and transport overhead
go test -bench=. -run='^$' ./benchmarks/
```

`-run='^$'` matches no tests, so only the benchmarks execute.

Measured on an Apple M4 Pro (`goarch=arm64`, `-benchtime=1s`), orchestration overhead
with stub agents — no LLM calls:

```
BenchmarkRouter-12         176.9 ns/op
BenchmarkSequential-12     683.4 ns/op
BenchmarkReAct-12          688.3 ns/op
BenchmarkParallel-12      2170   ns/op
BenchmarkReflection-12  100503   ns/op
```

Reflection is three orders of magnitude slower than the rest because it runs a
critique-and-revise loop; it is the one pattern where Go loses to Python. Re-measure on
your own hardware before quoting any of these.

See [docs/PERFORMANCE_COMPARISON.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/PERFORMANCE_COMPARISON.md)
for the cross-language comparison.

## Cross-Language Compatibility

Go agents maintain 100% behavioral parity with Python:

`tests/cross_language_harness.go` is a stdin/stdout harness driven by the
cross-language test runner, not a standalone suite — it reads one JSON request per
invocation and writes one JSON response. Run the equivalence tests from the
repository root:

```bash
./scripts/test-parity.sh
```

### Calling Python Agents from Go

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/adapter/remote"

// A remote agent satisfies agenkit.Agent, so it's a drop-in for a local one
pythonAgent, err := remote.NewRemoteAgent("python-agent", "http://localhost:8000", 30*time.Second)
if err != nil {
	log.Fatal(err)
}
defer func() { _ = pythonAgent.Close() }()

result, err := pythonAgent.Process(ctx, message)
```

### Calling Go Agents from Python

```python
from agenkit.transport import HTTPClient

# Call Go agent from Python
go_agent = HTTPClient("http://localhost:8080")
result = await go_agent.process(message)
```

## Deployment

### Docker

```dockerfile
FROM golang:1.25-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o agent ./cmd/agent

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/agent .
CMD ["./agent"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenkit-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenkit-agent
  template:
    metadata:
      labels:
        app: agenkit-agent
    spec:
      containers:
      - name: agent
        image: your-registry/agenkit-agent:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

## Migration Guides

### Migrating to Go

Choose your source language for detailed migration guide:

| From | Guide | Key Benefits |
|------|-------|-------------|
| **Python** | [MIGRATE_PYTHON_TO_GO.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_PYTHON_TO_GO.md) | 5-20x faster, true parallelism, single binary |
| **TypeScript** | [MIGRATE_TYPESCRIPT_TO_GO.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_TYPESCRIPT_TO_GO.md) | Multi-threaded, better concurrency, backend services |
| **Rust** | [MIGRATE_RUST_TO_GO.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_RUST_TO_GO.md) | Simpler deployment, faster iteration, GC simplification |
| **C++** | [MIGRATE_CPP_TO_GO.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_CPP_TO_GO.md) | Simpler memory, better concurrency, faster compilation |
| **Zig** | [MIGRATE_ZIG_TO_GO.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_ZIG_TO_GO.md) | GC simplification, goroutines, better concurrency |

### Migrating from Go

| To | Guide | Primary Use Case |
|----|-------|-----------------|
| **Python** | [MIGRATE_GO_TO_PYTHON.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_GO_TO_PYTHON.md) | Prototyping, ML integration, rapid development |
| **TypeScript** | [MIGRATE_GO_TO_TYPESCRIPT.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_GO_TO_TYPESCRIPT.md) | Web frontend, universal deployment, browser support |
| **Rust** | [MIGRATE_GO_TO_RUST.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_GO_TO_RUST.md) | Memory safety, WASM, zero-cost abstractions |
| **C++** | [MIGRATE_GO_TO_CPP.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_GO_TO_CPP.md) | Performance tuning, legacy integration, C ABI |
| **Zig** | [MIGRATE_GO_TO_ZIG.md](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATE_GO_TO_ZIG.md) | Embedded systems, minimal runtime, explicit control |

**See also:**
- [Language Profile: Go](https://github.com/scttfrdmn/agenkit/blob/main/docs/LANGUAGE_PROFILE_GO.md) - Deep dive into Go idioms and patterns
- [Migration Index](https://github.com/scttfrdmn/agenkit/blob/main/docs/MIGRATION_INDEX.md) - Complete migration documentation hub

## Development

```bash
# Install dependencies
go mod download

# Run linting
golangci-lint run

# Format code
go fmt ./...

# Generate protobuf (if modified)
protoc --go_out=. --go-grpc_out=. proto/*.proto
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](https://github.com/scttfrdmn/agenkit/blob/main/.github/CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - See [LICENSE](https://github.com/scttfrdmn/agenkit/blob/main/LICENSE) for details.

## Links

- **Documentation**: https://agenkit.dev
- **GoDoc**: https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go
- **GitHub**: https://github.com/scttfrdmn/agenkit
- **Python**: [../agenkit/](https://github.com/scttfrdmn/agenkit/tree/main/agenkit)
- **TypeScript**: [../agenkit-ts/](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-ts)

## Support

- **Issues**: https://github.com/scttfrdmn/agenkit/issues
- **Discussions**: https://github.com/scttfrdmn/agenkit/discussions
- **Email**: support@agenkit.dev
