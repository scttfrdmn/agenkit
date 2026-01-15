# Getting Started with Agenkit - Go

**Complete guide to building high-performance AI agents with Agenkit in Go**

## Table of Contents

1. [Installation](#installation)
2. [Your First Agent](#your-first-agent)
3. [Core Concepts](#core-concepts)
4. [Using Patterns](#using-patterns)
5. [Adding Middleware](#adding-middleware)
6. [Working with LLMs](#working-with-llms)
7. [Testing Your Agents](#testing-your-agents)
8. [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- Go 1.21 or higher
- go mod for dependency management

### Install Package

```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Initialize Your Project

```bash
mkdir my-agent
cd my-agent
go mod init my-agent
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Verify Installation

```go
package main

import (
    "fmt"
    "github.com/scttfrdmn/agenkit/agenkit-go"
)

func main() {
    fmt.Println("Agenkit version:", agenkit.Version)
}
```

```bash
go run main.go
# Output: Agenkit version: 0.46.0
```

---

## Your First Agent

Let's create a simple agent that processes messages:

### Step 1: Create Your Agent

Create a file `agent.go`:

```go
package main

import (
    "context"
    "fmt"
    "github.com/scttfrdmn/agenkit/agenkit-go/core"
)

// GreetingAgent responds with a friendly greeting
type GreetingAgent struct{}

// Name returns the agent's unique identifier
func (a *GreetingAgent) Name() string {
    return "greeting-agent"
}

// Process handles incoming messages
func (a *GreetingAgent) Process(ctx context.Context, message core.Message) (core.Message, error) {
    userMessage := message.Content

    return core.Message{
        Role:    "assistant",
        Content: fmt.Sprintf("Hello! You said: '%s'. How can I help you today?", userMessage),
    }, nil
}
```

### Step 2: Use Your Agent

Create `main.go`:

```go
package main

import (
    "context"
    "fmt"
    "log"
    "github.com/scttfrdmn/agenkit/agenkit-go/core"
)

func main() {
    // Create agent instance
    agent := &GreetingAgent{}

    // Create a user message
    userMsg := core.Message{
        Role:    "user",
        Content: "Hi there!",
    }

    // Process the message
    response, err := agent.Process(context.Background(), userMsg)
    if err != nil {
        log.Fatal(err)
    }

    // Print the response
    fmt.Printf("%s: %s\n", agent.Name(), response.Content)
}
```

### Step 3: Run It

```bash
go run .
# Output: greeting-agent: Hello! You said: 'Hi there!'. How can I help you today?
```

**🎉 Congratulations!** You've created your first Agenkit agent in Go.

---

## Core Concepts

### The Agent Interface

Every agent in Agenkit implements the `Agent` interface:

```go
type Agent interface {
    Name() string
    Process(ctx context.Context, message Message) (Message, error)
}
```

**That's the entire interface.** Everything else is optional.

### Messages

Messages are the unit of communication:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/core"

// Create a message
msg := core.Message{
    Role:    "user",             // Who sent it: "user", "assistant", "system"
    Content: "Hello!",           // The message content (string or any)
    Metadata: map[string]interface{}{  // Optional metadata
        "source": "web",
    },
}

// Access message properties
fmt.Println(msg.Role)      // "user"
fmt.Println(msg.Content)   // "Hello!"
fmt.Println(msg.Metadata)  // map[source:web]
```

### Error Handling

Go agents return errors explicitly:

```go
func (a *MyAgent) Process(ctx context.Context, message core.Message) (core.Message, error) {
    // Check context
    if err := ctx.Err(); err != nil {
        return core.Message{}, err
    }

    // Validate input
    if message.Content == "" {
        return core.Message{}, fmt.Errorf("empty message content")
    }

    // Process message
    result, err := a.processInternal(message)
    if err != nil {
        return core.Message{}, fmt.Errorf("processing failed: %w", err)
    }

    return result, nil
}
```

### Context Usage

Use `context.Context` for cancellation and timeouts:

```go
import (
    "context"
    "time"
)

func main() {
    // Create context with timeout
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    // Process with timeout
    response, err := agent.Process(ctx, message)
    if err == context.DeadlineExceeded {
        log.Println("Agent timed out")
        return
    }
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(response.Content)
}
```

### Tools

Tools let agents take actions:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/core"

type CalculatorTool struct{}

func (t *CalculatorTool) Name() string {
    return "calculator"
}

func (t *CalculatorTool) Description() string {
    return "Performs basic arithmetic operations"
}

func (t *CalculatorTool) Execute(ctx context.Context, params map[string]interface{}) (core.ToolResult, error) {
    operation, _ := params["operation"].(string)
    a, _ := params["a"].(float64)
    b, _ := params["b"].(float64)

    var result float64
    switch operation {
    case "add":
        result = a + b
    case "multiply":
        result = a * b
    default:
        return core.ToolResult{}, fmt.Errorf("unknown operation: %s", operation)
    }

    return core.ToolResult{
        Output: result,
    }, nil
}
```

---

## Using Patterns

Agenkit includes 18 pre-built patterns for common agent architectures.

### Reflection Pattern

Iteratively improve outputs through self-critique:

```go
import (
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"
    "github.com/scttfrdmn/agenkit/agenkit-go/core"
)

// Configure reflection
config := patterns.ReflectionConfig{
    MaxIterations:     3,      // Maximum improvement cycles
    QualityThreshold:  0.8,    // Stop when quality is good enough
    StopOnRepeat:      true,   // Stop if output doesn't change
}

// Create reflection agent
agent, err := patterns.NewReflectionAgent(
    &GeneratorAgent{},  // Generates initial output
    &CriticAgent{},     // Critiques and suggests improvements
    config,
)
if err != nil {
    log.Fatal(err)
}

// Use it
response, err := agent.Process(ctx, core.Message{
    Role:    "user",
    Content: "Write a haiku about coding",
})
if err != nil {
    log.Fatal(err)
}

// Response includes iteration metadata
fmt.Printf("Iterations: %v\n", response.Metadata["iterations"])
fmt.Printf("Quality: %v\n", response.Metadata["final_quality_score"])
```

### Sequential Pattern

Chain multiple agents in sequence:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

// Create a pipeline: research → summarize → format
pipeline := patterns.NewSequentialPattern([]core.Agent{
    &ResearchAgent{},    // Gathers information
    &SummaryAgent{},     // Summarizes findings
    &FormatterAgent{},   // Formats final output
})

// Input flows through each agent in order
response, err := pipeline.Process(ctx, core.Message{
    Role:    "user",
    Content: "Research quantum computing",
})
```

### Parallel Pattern

Run multiple agents concurrently and aggregate results:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

// Configure parallel execution
config := patterns.ParallelConfig{
    Agents: []core.Agent{
        &TechnicalAgent{},   // Technical perspective
        &BusinessAgent{},    // Business perspective
        &UserAgent{},        // User perspective
    },
    Aggregation: patterns.AggregationMerge,  // Combine results
}

// Create parallel pattern
parallel, err := patterns.NewParallelPattern(config)
if err != nil {
    log.Fatal(err)
}

// All agents process simultaneously
response, err := parallel.Process(ctx, core.Message{
    Role:    "user",
    Content: "Analyze this product idea",
})
```

### ReAct Pattern

Reasoning + Acting with tool use:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

// Configure ReAct
config := patterns.ReActConfig{
    MaxSteps: 5,         // Maximum reasoning steps
    Tools: []core.Tool{
        &SearchTool{},      // Web search capability
        &CalculatorTool{},  // Math calculations
    },
}

// Create ReAct agent
agent, err := patterns.NewReActAgent(&ReasoningAgent{}, config)
if err != nil {
    log.Fatal(err)
}

// Agent will alternate between thinking and acting
response, err := agent.Process(ctx, core.Message{
    Role:    "user",
    Content: "What's the population of Tokyo divided by the population of NYC?",
})

// Response includes reasoning trace
fmt.Printf("Steps: %v\n", response.Metadata["steps"])
fmt.Printf("Tool calls: %v\n", response.Metadata["tool_calls"])
```

---

## Adding Middleware

Middleware adds production features without changing your agent code.

### Retry Logic

Automatically retry failed operations:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/middleware"

// Configure retries
config := middleware.RetryConfig{
    MaxAttempts:    3,       // Try up to 3 times
    BackoffFactor:  2.0,     // Exponential backoff
    InitialDelay:   time.Second,    // Start with 1 second
    MaxDelay:       30 * time.Second, // Cap at 30 seconds
}

// Wrap your agent
resilientAgent := middleware.NewRetryMiddleware(myAgent, config)

// Now handles transient failures automatically
response, err := resilientAgent.Process(ctx, message)
```

### Circuit Breaker

Prevent cascading failures:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/middleware"

// Configure circuit breaker
config := middleware.CircuitBreakerConfig{
    FailureThreshold:  5,     // Open after 5 failures
    Timeout:           60 * time.Second,  // Stay open for 60 seconds
    SuccessThreshold:  2,     // Close after 2 successes
}

// Wrap your agent
protectedAgent := middleware.NewCircuitBreakerMiddleware(myAgent, config)

// Fails fast when circuit is open
response, err := protectedAgent.Process(ctx, message)
if err == middleware.ErrCircuitOpen {
    log.Println("Circuit is open - service unavailable")
}
```

### Timeout

Set maximum execution time:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/middleware"

// Configure timeout
config := middleware.TimeoutConfig{
    Timeout:      30 * time.Second,  // 30 second timeout
    GracePeriod:  5 * time.Second,   // 5 second grace for cleanup
}

// Wrap your agent
timedAgent := middleware.NewTimeoutMiddleware(myAgent, config)

// Will cancel after 30 seconds
response, err := timedAgent.Process(ctx, message)
if err == context.DeadlineExceeded {
    log.Println("Agent took too long to respond")
}
```

### Stacking Middleware

Combine multiple middleware layers:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/middleware"

// Stack middleware (innermost to outermost)
agent := myAgent
agent = middleware.NewTimeoutMiddleware(agent, timeoutConfig)
agent = middleware.NewCircuitBreakerMiddleware(agent, circuitConfig)
agent = middleware.NewRetryMiddleware(agent, retryConfig)
agent = middleware.NewRateLimiterMiddleware(agent, rateConfig)

// Now has full production resilience
response, err := agent.Process(ctx, message)
```

---

## Working with LLMs

### OpenAI Integration

```go
import (
    "github.com/scttfrdmn/agenkit/agenkit-go/adapters"
    "os"
)

// Create OpenAI agent
config := adapters.OpenAIConfig{
    Model:  "gpt-4",
    APIKey: os.Getenv("OPENAI_API_KEY"),
}

agent, err := adapters.NewOpenAIAdapter(config)
if err != nil {
    log.Fatal(err)
}

// Use it like any agent
response, err := agent.Process(ctx, core.Message{
    Role:    "user",
    Content: "Explain quantum computing",
})
```

### Anthropic (Claude) Integration

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/adapters"

// Create Claude agent
config := adapters.AnthropicConfig{
    Model:  "claude-3-opus-20240229",
    APIKey: os.Getenv("ANTHROPIC_API_KEY"),
}

agent, err := adapters.NewAnthropicAdapter(config)
if err != nil {
    log.Fatal(err)
}

response, err := agent.Process(ctx, core.Message{
    Role:    "user",
    Content: "Write a function to calculate Fibonacci numbers",
})
```

### Custom LLM Integration

```go
import (
    "net/http"
    "encoding/json"
)

type CustomLLMAgent struct {
    apiURL  string
    apiKey  string
    client  *http.Client
}

func NewCustomLLMAgent(apiURL, apiKey string) *CustomLLMAgent {
    return &CustomLLMAgent{
        apiURL: apiURL,
        apiKey: apiKey,
        client: &http.Client{Timeout: 30 * time.Second},
    }
}

func (a *CustomLLMAgent) Name() string {
    return "custom-llm"
}

func (a *CustomLLMAgent) Process(ctx context.Context, message core.Message) (core.Message, error) {
    // Build request
    reqBody := map[string]interface{}{
        "prompt": message.Content,
    }

    reqData, err := json.Marshal(reqBody)
    if err != nil {
        return core.Message{}, err
    }

    // Call API
    req, err := http.NewRequestWithContext(ctx, "POST", a.apiURL, bytes.NewBuffer(reqData))
    if err != nil {
        return core.Message{}, err
    }

    req.Header.Set("Authorization", "Bearer "+a.apiKey)
    req.Header.Set("Content-Type", "application/json")

    resp, err := a.client.Do(req)
    if err != nil {
        return core.Message{}, err
    }
    defer resp.Body.Close()

    // Parse response
    var result struct {
        Completion string `json:"completion"`
    }
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return core.Message{}, err
    }

    return core.Message{
        Role:    "assistant",
        Content: result.Completion,
    }, nil
}
```

---

## Testing Your Agents

### Unit Testing

```go
package main

import (
    "context"
    "testing"
    "github.com/scttfrdmn/agenkit/agenkit-go/core"
)

func TestGreetingAgent(t *testing.T) {
    agent := &GreetingAgent{}

    // Test basic greeting
    response, err := agent.Process(context.Background(), core.Message{
        Role:    "user",
        Content: "Hello",
    })

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if response.Role != "assistant" {
        t.Errorf("expected role 'assistant', got '%s'", response.Role)
    }

    if !strings.Contains(response.Content.(string), "Hello") {
        t.Errorf("expected response to contain 'Hello'")
    }
}

func TestAgentName(t *testing.T) {
    agent := &GreetingAgent{}
    if agent.Name() != "greeting-agent" {
        t.Errorf("expected name 'greeting-agent', got '%s'", agent.Name())
    }
}
```

### Integration Testing with Mocks

```go
type MockAgent struct {
    response string
}

func (a *MockAgent) Name() string {
    return "mock-agent"
}

func (a *MockAgent) Process(ctx context.Context, message core.Message) (core.Message, error) {
    return core.Message{
        Role:    "assistant",
        Content: a.response,
    }, nil
}

func TestSequentialPattern(t *testing.T) {
    pipeline := patterns.NewSequentialPattern([]core.Agent{
        &MockAgent{response: "Step 1 complete"},
        &MockAgent{response: "Step 2 complete"},
        &MockAgent{response: "Step 3 complete"},
    })

    response, err := pipeline.Process(context.Background(), core.Message{
        Role:    "user",
        Content: "Start pipeline",
    })

    if err != nil {
        t.Fatal(err)
    }

    if !strings.Contains(response.Content.(string), "Step 3 complete") {
        t.Error("expected final step in response")
    }
}
```

### Benchmarking

```go
func BenchmarkAgent(b *testing.B) {
    agent := &GreetingAgent{}
    message := core.Message{
        Role:    "user",
        Content: "Hello",
    }
    ctx := context.Background()

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _, err := agent.Process(ctx, message)
        if err != nil {
            b.Fatal(err)
        }
    }
}
```

Run benchmarks:
```bash
go test -bench=. -benchmem
```

---

## Next Steps

### Learn More

- **[Pattern Guide](../patterns/README.md)** - Detailed guide to all 18 patterns
- **[API Reference](../api/go/README.md)** - Complete API documentation
- **[Best Practices](../best-practices/GO.md)** - Production deployment tips
- **[Examples](../../agenkit-go/examples/)** - Working examples

### Performance Optimization

- **[Goroutine Best Practices](../performance/GO_GOROUTINES.md)** - Efficient concurrency
- **[Memory Management](../performance/GO_MEMORY.md)** - Reduce allocations
- **[Profiling Guide](../performance/GO_PROFILING.md)** - Profile your agents

### Deploy to Production

- **[Docker Deployment](../deployment/DOCKER.md)** - Containerize your agents
- **[Kubernetes Guide](../deployment/KUBERNETES.md)** - Scale with K8s
- **[Monitoring & Observability](../observability/README.md)** - Track agent performance

### Migrate from Other Languages

Coming from Python or TypeScript?

- **[Python → Go Migration](../migration/PYTHON_TO_GO.md)** - Migrate from Python
- **[TypeScript → Go Migration](../migration/TYPESCRIPT_TO_GO.md)** - Migrate from TS

---

## Quick Reference

### Installation
```bash
go get github.com/scttfrdmn/agenkit/agenkit-go
```

### Minimal Agent
```go
type MyAgent struct{}

func (a *MyAgent) Name() string {
    return "my-agent"
}

func (a *MyAgent) Process(ctx context.Context, message core.Message) (core.Message, error) {
    return core.Message{
        Role:    "assistant",
        Content: "Response",
    }, nil
}
```

### Common Imports
```go
import (
    // Core
    "github.com/scttfrdmn/agenkit/agenkit-go/core"

    // Patterns
    "github.com/scttfrdmn/agenkit/agenkit-go/patterns"

    // Middleware
    "github.com/scttfrdmn/agenkit/agenkit-go/middleware"

    // Adapters
    "github.com/scttfrdmn/agenkit/agenkit-go/adapters"
)
```

---

**Ready to build?** Check out the [examples](../../agenkit-go/examples/) for working code you can run right now.

**Performance tip:** Go's goroutines make Agenkit agents 18x faster than Python for CPU-bound workloads!
