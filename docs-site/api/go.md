# Go API Reference

Complete API documentation for Agenkit Go implementation.

## Official Documentation

The Go implementation maintains complete API documentation on pkg.go.dev, automatically generated from Go doc comments.

[📚 View Go API Documentation on pkg.go.dev](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go){ .md-button .md-button--primary }

---

## Quick Navigation

### Core Package

[**agenkit**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/agenkit) - Core interfaces and types
```go
import "github.com/scttfrdmn/agenkit-go/agenkit"
```

Key types:
- `Agent` - Core agent interface
- `Message` - Message type for agent communication
- `Tool` - Tool interface
- `ToolResult` - Tool execution result
- `IntrospectionResult` - Agent introspection data

### Patterns

[**patterns**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/patterns) - Agent patterns and compositions
```go
import "github.com/scttfrdmn/agenkit-go/patterns"
```

Available patterns:
- `SequentialAgent` - Sequential pipeline
- `ParallelAgent` - Concurrent execution
- `ConditionalAgent` - Conditional routing
- `RouterAgent` - Dynamic routing
- `ConversationalAgent` - Multi-turn conversations
- `ReActAgent` - Reasoning + Acting
- `ReflectionAgent` - Self-critique loop
- `OrchestrationAgent` - Complex workflows
- `AgentsAsToolsAgent` - Hierarchical delegation
- `PlanningAgent` - Task decomposition
- `AutonomousAgent` - Goal-driven behavior
- `MultiagentAgent` - Multi-agent coordination
- `MemoryHierarchyAgent` - Memory management
- `ReasoningWithToolsAgent` - Advanced tool usage

### Reasoning Techniques

[**techniques/reasoning**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/techniques/reasoning) - Advanced reasoning
```go
import "github.com/scttfrdmn/agenkit-go/techniques/reasoning"
```

Available techniques:
- `ChainOfThought` - Step-by-step reasoning
- `TreeOfThought` - Multi-path exploration
- `GraphOfThought` - Graph-based reasoning
- `SelfConsistency` - Voting strategy
- `ReasoningTree` - Tree utilities

### Middleware

[**middleware**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/middleware) - Production middleware
```go
import "github.com/scttfrdmn/agenkit-go/middleware"
```

Available middleware:
- `RetryMiddleware` - Automatic retries
- `CircuitBreakerMiddleware` - Circuit breaker pattern
- `TimeoutMiddleware` - Timeout handling
- `RateLimiterMiddleware` - Rate limiting
- `CachingMiddleware` - Response caching
- `BatchingMiddleware` - Request batching
- `MetricsMiddleware` - Metrics collection

### LLM Adapters

[**adapter/llm**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/adapter/llm) - LLM provider adapters
```go
import "github.com/scttfrdmn/agenkit-go/adapter/llm"
```

Available adapters:
- `NewAnthropicLLM(apiKey, model, opts...)` - Claude API
- `NewOpenAILLM(apiKey, model)` - OpenAI API
- `NewBedrockLLM(ctx, cfg)` - AWS Bedrock
- `NewGeminiLLM(apiKey, model)` - Google Gemini
- `NewOllamaLLM(model, baseURL)`, `NewVllmLLM(model, baseURL)`,
  `NewSGLangLLM(model, baseURL)` - local models
- `NewLiteLLMLLM(baseURL, model)`, `NewOpenAICompatibleLLM(baseURL, model, provider, apiKey)`

### Transport

[**adapter/http**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/adapter/http) - HTTP server
```go
import "github.com/scttfrdmn/agenkit-go/adapter/http"
```

[**adapter/grpc**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/adapter/grpc) - gRPC server
```go
import "github.com/scttfrdmn/agenkit-go/adapter/grpc"
```

[**adapter/remote**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/adapter/remote) - client for a
remote agent (satisfies `agenkit.Agent`, so it composes like a local one)
```go
import "github.com/scttfrdmn/agenkit-go/adapter/remote"
```

### Observability

[**observability**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/observability) - Tracing and metrics
```go
import "github.com/scttfrdmn/agenkit-go/observability"
```

Features:
- `TracingMiddleware` - OpenTelemetry tracing
- `MetricsCollector` - Prometheus metrics

### Evaluation

[**evaluation**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/evaluation) - Testing and optimization
```go
import "github.com/scttfrdmn/agenkit-go/evaluation"
```

Features:
- `Recorder` - Session recording
- `BenchmarkRunner` - Performance benchmarks
- `BayesianOptimizer` - Hyperparameter optimization
- `PromptOptimizer` - Prompt optimization

### Memory

[**memory**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/memory) - Memory management
```go
import "github.com/scttfrdmn/agenkit-go/memory"
```

Features:
- `MemoryHierarchy` - Working/episodic/semantic memory
- `WorkingMemory` - Short-term memory
- `EpisodicMemory` - Experience memory
- `SemanticMemory` - Knowledge memory

### Budget

[**budget**](https://pkg.go.dev/github.com/scttfrdmn/agenkit-go/budget) - Cost management
```go
import "github.com/scttfrdmn/agenkit-go/budget"
```

---

## Getting Started with Go

### Installation

```bash
go get github.com/scttfrdmn/agenkit-go
```

### Basic Example

```go
package main

import (
    "context"
    "fmt"

    "github.com/scttfrdmn/agenkit-go/agenkit"
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

---

## Go-Specific Features

### Goroutines

Go agents leverage goroutines for true parallel execution:

```go
import "github.com/scttfrdmn/agenkit-go/patterns"

// Execute 3 agents concurrently
parallel := patterns.NewParallelAgent([]agenkit.Agent{
    agent1,
    agent2,
    agent3,
}, nil)

// All agents run in parallel on separate goroutines
result, err := parallel.Process(ctx, message)
```

### Contexts

Go agents use `context.Context` for cancellation and timeouts:

```go
import "time"

ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

result, err := agent.Process(ctx, message)
```

### Error Handling

Go uses explicit error returns:

```go
result, err := agent.Process(ctx, message)
if err != nil {
    log.Printf("Agent failed: %v", err)
    return err
}
```

### Performance

Go provides exceptional performance:

- **18x faster** than Python
- **Sub-millisecond** orchestration
- **100K+ requests/second** per instance
- **Single binary** deployment

---

## IDE Integration

### GoLand / IntelliJ IDEA

pkg.go.dev documentation is automatically fetched by JetBrains IDEs:

1. Hover over any type/function
2. Press `Ctrl+Q` (Windows/Linux) or `F1` (Mac)
3. View inline documentation

### VS Code

Install the Go extension for inline documentation:

```bash
code --install-extension golang.go
```

Hover over any type/function to see documentation.

### vim-go

Add to your `.vimrc`:

```vim
Plugin 'fatih/vim-go'
```

Use `:GoDoc` to view documentation.

---

## Documentation Standards

All Go packages follow standard Go documentation conventions:

### Package Documentation

Every package has a package-level comment:

```go
// Package agenkit provides the foundation for AI agents.
//
// Minimal, perfect primitives for agent communication.
package agenkit
```

### Type Documentation

Every exported type is documented:

```go
// Agent is the core interface that all agents must implement.
//
// Agents process messages and return responses. They can be composed
// using patterns for complex behaviors.
type Agent interface {
    // Name returns the agent's identifier
    Name() string

    // Capabilities returns the agent's capabilities
    Capabilities() []string

    // Process handles a message and returns a response
    Process(ctx context.Context, message *Message) (*Message, error)

    // Introspect returns agent metadata
    Introspect() *IntrospectionResult
}
```

### Function Documentation

Every exported function is documented:

```go
// NewMessage creates a new message with the given role and content.
//
// Example:
//     msg := agenkit.NewMessage("user", "Hello, world!")
func NewMessage(role, content string) *Message {
    return &Message{
        Role:    role,
        Content: content,
        Metadata: make(map[string]interface{}),
    }
}
```

---

## Examples

Comprehensive examples are available in the [Go examples directory](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-go/examples):

### Basic Examples
- Echo agent
- Sequential pipeline
- Parallel execution

### Pattern Examples
- ReAct with tools
- Planning agent
- Reflection loop
- Conversational agent

### Production Examples
- HTTP server
- gRPC server
- With middleware
- With observability

### Reasoning Examples
- Chain-of-Thought
- Tree-of-Thought
- Self-Consistency

---

## Testing

Run tests for any package:

```bash
cd agenkit-go
go test ./...

# With coverage
go test -cover ./...

# Specific package
go test ./patterns/

# With race detection
go test -race ./...
```

---

## Benchmarks

View performance benchmarks:

```bash
cd agenkit-go/benchmarks
go test -bench=. -benchmem
```

---

## Cross-Language Compatibility

Go agents can communicate with Python, TypeScript, and other language implementations via HTTP/gRPC:

### Call Python Agent from Go

```go
import (
	"time"

	"github.com/scttfrdmn/agenkit-go/adapter/remote"
)

pythonAgent, err := remote.NewRemoteAgent("python-agent", "http://localhost:8000", 30*time.Second)
if err != nil {
	return err
}
result, err := pythonAgent.Process(ctx, message)
```

### Expose Go Agent to Python

```go
import "github.com/scttfrdmn/agenkit-go/adapter/http"

server := http.NewHTTPAgent(agent, ":8080")
if err := server.Start(ctx); err != nil {
	return err
}
defer func() { _ = server.Stop() }()
```

---

## Contributing

Help improve Go implementation:

1. **Report issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Improve docs**: Add doc comments to code
3. **Add examples**: [Submit PR](https://github.com/scttfrdmn/agenkit/pulls)

---

## See Also

- **[Python API Reference](python.md)**: Python implementation
- **[Go Guide](../guides/go.md)**: Comprehensive Go guide
- **[Cross-Language Guide](../guides/cross-language.md)**: Language interop
- **[Go README](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-go/README.md)**: Go-specific features
- **[Migration Guide](../../docs/migrations/langchain-to-agenkit.md)**: Migrate to Agenkit

---

**Last Updated**: December 2025
**Go Version**: 1.21+
**Agenkit Version**: 0.43.1+
