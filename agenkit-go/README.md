# Agenkit Go

**Production-grade AI agent framework for Go 1.21+**

The Go implementation of Agenkit provides exceptional performance (18x faster than Python) while maintaining 100% behavioral parity with the reference Python implementation.

[![Go Reference](https://pkg.go.dev/badge/github.com/scttfrdmn/agenkit/agenkit-go.svg)](https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go)
[![Go 1.21+](https://img.shields.io/badge/go-1.21+-00ADD8.svg)](https://golang.org/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![Cross-Language Parity](https://img.shields.io/badge/parity-100%25-success.svg)](../../tests/cross_language/)

## Why Go?

**18x Performance Improvement** over Python with the same developer experience:

- **Concurrency**: Goroutines for true parallel agent execution
- **Performance**: Sub-millisecond agent orchestration
- **Deployment**: Single binary, no runtime dependencies
- **Scale**: Handle 100K+ requests/second per instance

**Perfect for**:
- Production workloads requiring high throughput
- Microservices and distributed systems
- Edge deployments with constrained resources
- Cost optimization (fewer instances needed)

## Installation

```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

## Quick Start

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
	return agenkit.NewMessage("assistant", fmt.Sprintf("Echo: %s", message.Content)), nil
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

	fmt.Println(response.Content) // "Echo: Hello!"
}
```

### Production-Ready Agent with Resilience

```go
import (
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

func main() {
	// Create agent
	agent := &MyAgent{}

	// Add resilience middleware
	agent = middleware.NewRetryMiddleware(agent, &middleware.RetryConfig{
		MaxRetries:    3,
		BackoffFactor: 2.0,
	})

	agent = middleware.NewCircuitBreakerMiddleware(agent, &middleware.CircuitBreakerConfig{
		FailureThreshold: 5,
		RecoveryTimeout:  60.0,
	})

	agent = middleware.NewTimeoutMiddleware(agent, &middleware.TimeoutConfig{
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
pipeline := patterns.NewSequentialAgent([]agenkit.Agent{
	&DataExtractionAgent{},
	&AnalysisAgent{},
	&ReportGenerationAgent{},
})

result, err := pipeline.Process(ctx, message)
```

#### Parallel Execution

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

// Execute multiple agents concurrently using goroutines
parallel := patterns.NewParallelAgent([]agenkit.Agent{
	&SentimentAnalysisAgent{},
	&EntityExtractionAgent{},
	&TopicClassificationAgent{},
}, nil) // Uses default aggregator

result, err := parallel.Process(ctx, message)
```

#### Conversational Agent

```go
import (
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
	"github.com/scttfrdmn/agenkit/agenkit-go/adapter"
)

// Maintains conversation history
agent := patterns.NewConversationalAgent(&patterns.ConversationalConfig{
	LLM:          adapter.NewAnthropicAdapter(apiKey),
	SystemPrompt: "You are a helpful assistant.",
	MaxHistory:   10,
})

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

// ReAct agent with tools
agent := patterns.NewReActAgent(&patterns.ReActConfig{
	LLM:           myLLM,
	Tools:         []agenkit.Tool{&CalculatorTool{}, &WebSearchTool{}},
	MaxIterations: 5,
})

result, err := agent.Process(ctx, message)
```

### Reasoning Techniques

#### Chain-of-Thought (CoT)

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"

// Step-by-step reasoning
cot := reasoning.NewChainOfThought(myLLM, &reasoning.ChainOfThoughtConfig{
	PromptTemplate: "Let's solve this step by step:\n{query}",
	MaxSteps:       5,
	ParseSteps:     true,
})

result, err := cot.Process(ctx, agenkit.NewMessage("user", "What is 15 * 24?"))
steps := result.Metadata["reasoning_steps"].([]string)
fmt.Println(steps)
// ["1. Multiply 15 by 20: 300", "2. Multiply 15 by 4: 60", "3. Add: 360"]
```

#### Tree-of-Thought (ToT)

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"

// Multi-path exploration with backtracking
tot := reasoning.NewTreeOfThought(myAgent, &reasoning.TreeOfThoughtConfig{
	BranchingFactor: 3,
	MaxDepth:        4,
	Strategy:        reasoning.SearchStrategyBestFirst,
	Evaluator:       customEvaluator,
})

result, err := tot.Process(ctx, message)
path := result.Metadata["reasoning_path"].([]string)
score := result.Metadata["best_score"].(float64)
fmt.Printf("Best path: %v (score: %.2f)\n", path, score)
```

#### Self-Consistency

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"

// Generate multiple reasoning paths and vote
sc := reasoning.NewSelfConsistency(myCOTAgent, &reasoning.SelfConsistencyConfig{
	NumSamples:     7,
	VotingStrategy: reasoning.VotingStrategyMajority,
})

result, err := sc.Process(ctx, message)
consistency := result.Metadata["consistency_score"].(float64)
counts := result.Metadata["answer_counts"].(map[string]int)
fmt.Printf("Consistency: %.2f, Answers: %v\n", consistency, counts)
```

### Observability

```go
import (
	"github.com/scttfrdmn/agenkit/agenkit-go/observability"
	"go.opentelemetry.io/otel"
)

// Enable distributed tracing
tracer := otel.Tracer("my-service")
agent = observability.NewTracingMiddleware(agent, tracer)

// Now all agent calls are traced
ctx, span := tracer.Start(ctx, "process_request")
defer span.End()

result, err := agent.Process(ctx, message)
```

### HTTP Server

```go
import (
	"github.com/scttfrdmn/agenkit/agenkit-go/transport/http"
	"net/http"
)

// Expose agent as HTTP endpoint
server := http.NewHTTPAgent(agent, ":8080")

// Start server
if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
	log.Fatal(err)
}
```

### gRPC Server

```go
import (
	"github.com/scttfrdmn/agenkit/agenkit-go/transport/grpc"
	"google.golang.org/grpc"
)

// Expose agent as gRPC service
server := grpc.NewGRPCAgent(agent, ":50051")

// Start server
if err := server.Serve(); err != nil {
	log.Fatal(err)
}
```

## Package Structure

```
agenkit-go/
├── agenkit/                 # Core package
│   ├── interfaces.go        # Agent, Message, Tool interfaces
│   ├── introspection.go     # Introspection utilities
│   └── message.go           # Message types
├── patterns/                # 32 agent patterns
│   ├── sequential.go        # Pipeline execution
│   ├── parallel.go          # Concurrent execution
│   ├── router.go            # Conditional routing
│   ├── conversational.go    # History management
│   ├── react.go             # Reasoning + Acting
│   ├── reflection.go        # Self-critique loop
│   ├── planning.go          # Task decomposition
│   ├── autonomous.go        # Goal-driven agents
│   ├── memory.go            # Memory hierarchy
│   └── ... [23 more patterns]
├── techniques/              # Reasoning techniques
│   └── reasoning/
│       ├── chain_of_thought.go     # CoT prompting
│       ├── tree_of_thought.go      # ToT search
│       ├── self_consistency.go     # Voting strategy
│       ├── graph_of_thought.go     # Graph reasoning
│       └── reasoning_tree.go       # Tree utilities
├── middleware/              # Production middleware
│   ├── retry.go             # Automatic retries
│   ├── circuit_breaker.go   # Circuit breaker pattern
│   ├── timeout.go           # Timeout handling
│   ├── rate_limiter.go      # Rate limiting
│   ├── caching.go           # Response caching
│   ├── batching.go          # Request batching
│   └── metrics.go           # Metrics collection
├── adapter/                 # LLM adapters
│   ├── anthropic.go         # Claude API
│   ├── openai.go            # OpenAI API
│   ├── bedrock.go           # AWS Bedrock
│   └── gemini.go            # Google Gemini
├── transport/               # Communication protocols
│   ├── http/                # HTTP/REST server & client
│   ├── grpc/                # gRPC server & client
│   └── websocket/           # WebSocket support
├── observability/           # Tracing and metrics
│   ├── tracing.go           # OpenTelemetry integration
│   └── metrics.go           # Prometheus metrics
├── evaluation/              # Testing and optimization
│   ├── recorder.go          # Session recording
│   ├── benchmarks.go        # Performance benchmarks
│   └── optimizer.go         # Hyperparameter optimization
└── budget/                  # Token and cost management
    └── limiter.go           # Budget limiting
```

## API Reference

See [GoDoc](https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go) for complete API documentation.

## Examples

Comprehensive examples are available in [examples/](examples/):

```bash
# Run basic examples
go run examples/basic/echo_agent.go
go run examples/basic/sequential_pattern.go

# Run pattern examples
go run examples/patterns/react_example.go
go run examples/patterns/planning_example.go

# Run reasoning examples
go run examples/techniques/reasoning/cot_example.go
go run examples/techniques/reasoning/tot_example.go

# Run production examples
go run examples/production/http_server.go
go run examples/production/grpc_server.go
```

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

```bash
# Run pattern benchmarks
cd benchmarks && go test -bench=BenchmarkPatterns -benchtime=10s

# Results (Apple M1 Pro):
# Sequential:     2000 ns/op   (500K ops/sec)
# Parallel:       5000 ns/op   (200K ops/sec)
# ReAct:         10000 ns/op   (100K ops/sec)
```

See [../docs/PERFORMANCE_COMPARISON.md](../docs/PERFORMANCE_COMPARISON.md) for detailed benchmarks.

## Cross-Language Compatibility

Go agents maintain 100% behavioral parity with Python:

```bash
# Run cross-language equivalence tests
go run tests/cross_language_harness

# Results:
# Chain-of-Thought: 9/9 scenarios passing (100%)
# Tree-of-Thought: 11/11 scenarios passing (100%)
# Self-Consistency: 7/7 scenarios passing (100%)
```

### Calling Python Agents from Go

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/transport/http"

// Call Python agent over HTTP
pythonAgent := http.NewHTTPClient("http://localhost:8000")
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
FROM golang:1.21-alpine AS builder
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

## Migration from Python

Go follows Python's API closely. Most Python code translates directly:

**Python**:
```python
from agenkit.patterns import SequentialAgent

agent = SequentialAgent([agent1, agent2, agent3])
result = await agent.process(message)
```

**Go**:
```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

agent := patterns.NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
result, err := agent.Process(ctx, message)
```

Key differences:
- Go uses explicit error handling (`err`)
- Go requires `context.Context` for cancellation
- Go uses constructors (`New*`) instead of class initialization
- Go uses struct methods instead of class methods

See [../docs/MIGRATION.md](../docs/MIGRATION.md#python-to-go) for complete migration guide.

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

Contributions are welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - See [LICENSE](../LICENSE) for details.

## Links

- **Documentation**: https://agenkit.dev
- **GoDoc**: https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go
- **GitHub**: https://github.com/scttfrdmn/agenkit
- **Python**: [../agenkit/](../agenkit/)
- **TypeScript**: [../agenkit-ts/](../agenkit-ts/)

## Support

- **Issues**: https://github.com/scttfrdmn/agenkit/issues
- **Discussions**: https://github.com/scttfrdmn/agenkit/discussions
- **Email**: support@agenkit.dev
