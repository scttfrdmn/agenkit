# Getting Started with Agenkit (Go)

**Target audience**: Go developers new to Agenkit
**Time to first agent**: 15-30 minutes
**Prerequisites**: Go 1.25.14+

---

## Installation

```bash
# Add agenkit to your project
go get github.com/yourusername/agenkit-go

# Install optional LLM providers
go get github.com/sashabaranov/go-openai
```

---

## Your First Agent

Let's create a simple greeting agent:

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/yourusername/agenkit-go/agenkit"
)

type GreetingAgent struct{}

func (a *GreetingAgent) Name() string {
    return "greeting-agent"
}

func (a *GreetingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    userContent := message.Content
    greeting := fmt.Sprintf("Hello! You said: %s", userContent)

    return &agenkit.Message{
        Role:    "assistant",
        Content: greeting,
        Metadata: map[string]interface{}{
            "processed_by": a.Name(),
        },
    }, nil
}

func main() {
    ctx := context.Background()
    agent := &GreetingAgent{}

    message := &agenkit.Message{
        Role:    "user",
        Content: "Hi there!",
    }

    response, err := agent.Process(ctx, message)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Agent: %s\n", response.Content)
    // Output: Agent: Hello! You said: Hi there!
}
```

Run it:
```bash
go run main.go
```

---

## Production-Ready Agent with Middleware

Add resilience with retry, circuit breaker, and timeout middleware:

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    "github.com/yourusername/agenkit-go/agenkit"
    "github.com/yourusername/agenkit-go/middleware"
)

type ProductionAgent struct{}

func (a *ProductionAgent) Name() string {
    return "production-agent"
}

func (a *ProductionAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    // Simulate some processing
    time.Sleep(100 * time.Millisecond)

    return &agenkit.Message{
        Role:    "assistant",
        Content: fmt.Sprintf("Processed: %s", message.Content),
        Metadata: map[string]interface{}{
            "agent": a.Name(),
        },
    }, nil
}

func main() {
    ctx := context.Background()
    baseAgent := &ProductionAgent{}

    // Wrap with middleware (v0.50.0 uses time.Duration - idiomatic Go)
    agent := middleware.NewRetryDecorator(
        baseAgent,
        middleware.WithMaxAttempts(3),
        middleware.WithInitialDelay(100*time.Millisecond),
    )

    agent = middleware.NewCircuitBreakerDecorator(
        agent,
        middleware.WithFailureThreshold(5),
        middleware.WithRecoveryTimeout(30*time.Second),
    )

    agent = middleware.NewTimeoutDecorator(
        agent,
        middleware.WithTimeout(5*time.Second),
    )

    message := &agenkit.Message{
        Role:    "user",
        Content: "Hello production!",
    }

    response, err := agent.Process(ctx, message)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(response.Content)
}
```

**Note**: Go uses `time.Duration` (idiomatic) instead of milliseconds.

---

## Using LLM Adapters

### OpenAI Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "github.com/yourusername/agenkit-go/adapter/llm"
    "github.com/yourusername/agenkit-go/agenkit"
)

func main() {
    ctx := context.Background()

    // Initialize LLM (validates parameters at construction)
    openai, err := llm.NewOpenAI(
        llm.WithAPIKey(os.Getenv("OPENAI_API_KEY")),
        llm.WithModel("gpt-4-turbo"),
        llm.WithTemperature(0.7), // Validated: 0-2
        llm.WithMaxTokens(1024),  // Validated: >0
    )
    if err != nil {
        log.Fatal(err)
    }

    // Create conversation
    messages := []*agenkit.Message{
        {Role: "system", Content: "You are a helpful assistant."},
        {Role: "user", Content: "What is Agenkit?"},
    }

    // Get completion
    response, err := openai.Complete(ctx, messages)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(response.Content)

    // Stream response
    messageChan, errorChan := openai.Stream(ctx, messages)
    for {
        select {
        case chunk := <-messageChan:
            if chunk == nil {
                return // Done
            }
            fmt.Print(chunk.Content)
        case err := <-errorChan:
            log.Fatal(err)
        case <-ctx.Done():
            log.Fatal(ctx.Err())
        }
    }
}
```

### Anthropic Example

```go
anthropic, err := llm.NewAnthropic(
    llm.WithAPIKey(os.Getenv("ANTHROPIC_API_KEY")),
    llm.WithModel("claude-3-5-sonnet-20241022"),
    llm.WithTemperature(1.0),
    llm.WithMaxTokens(4096),
)
```

**Parameter Validation** (v0.50.0):
- `temperature`: 0.0 - 2.0 (validated via functional options)
- `max_tokens`: > 0 (validated via functional options)
- `top_p`: 0.0 - 1.0 (validated via functional options)

Invalid values return errors immediately.

---

## Common Patterns

Agenkit provides **18 core patterns** for building AI agents (see the [Agent Patterns Book](../../agent-patterns-book) for comprehensive details). Here are three essential patterns to get started:

### 1. Reflection Pattern

**One-line**: Iterative self-improvement through draft-critique-refine loop

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/yourusername/agenkit-go/patterns"
    "github.com/yourusername/agenkit-go/adapter/llm"
)

func main() {
    ctx := context.Background()

    openaiLLM, _ := llm.NewOpenAI(
        llm.WithModel("gpt-4-turbo"),
    )

    agent := patterns.NewReflectionAgent(
        openaiLLM,
        patterns.WithMaxIterations(3),
        patterns.WithReflectionPrompt("Review and improve this response:"),
    )

    message := &agenkit.Message{
        Role:    "user",
        Content: "Explain context management in Go",
    }

    response, err := agent.Process(ctx, message)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(response.Content)
}
```

### 2. ReAct Pattern

**One-line**: Reasoning + Acting with explicit thought-action-observation loop

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/yourusername/agenkit-go/patterns"
    "github.com/yourusername/agenkit-go/adapter/llm"
    "github.com/yourusername/agenkit-go/agenkit"
)

type SearchTool struct{}

func (t *SearchTool) Name() string {
    return "search"
}

func (t *SearchTool) Description() string {
    return "Search for information"
}

func (t *SearchTool) Parameters() map[string]interface{} {
    return map[string]interface{}{
        "query": map[string]string{
            "type":        "string",
            "description": "Search query",
        },
    }
}

func (t *SearchTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
    query := params["query"].(string)
    // Simulate search
    return &agenkit.ToolResult{
        Success: true,
        Result:  fmt.Sprintf("Search results for: %s", query),
    }, nil
}

func main() {
    ctx := context.Background()

    openaiLLM, _ := llm.NewOpenAI(
        llm.WithModel("gpt-4-turbo"),
    )

    tools := []agenkit.Tool{&SearchTool{}}

    agent := patterns.NewReActAgent(
        openaiLLM,
        tools,
        patterns.WithMaxIterations(5),
    )

    message := &agenkit.Message{
        Role:    "user",
        Content: "What's the weather in Paris?",
    }

    response, err := agent.Process(ctx, message)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(response.Content)
}
```

**Note**: Tool signatures use explicit `params map[string]interface{}` (v0.50.0+).

### 3. Sequential Pattern

**One-line**: Execute agents in order, passing outputs between stages

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/yourusername/agenkit-go/patterns"
)

func main() {
    ctx := context.Background()

    // Create agent pipeline
    agent := patterns.NewSequentialAgent(
        &ResearchAgent{},
        &SummarizerAgent{},
        &EditorAgent{},
    )

    message := &agenkit.Message{
        Role:    "user",
        Content: "Research AI safety",
    }

    finalResponse, err := agent.Process(ctx, message)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(finalResponse.Content)
}
```

**See all 18 patterns**: Refer to the [Agent Patterns Book](../../agent-patterns-book) for complete pattern descriptions, trade-offs, and when to use each pattern.

---

## Observability

### Basic Tracing with OpenTelemetry

```go
package main

import (
    "context"

    "github.com/yourusername/agenkit-go/observability"
    "go.opentelemetry.io/otel/exporters/jaeger"
)

func main() {
    // Configure OpenTelemetry
    shutdown, err := observability.Configure(
        observability.WithServiceName("my-agent-service"),
        observability.WithJaegerExporter("http://localhost:14268/api/traces"),
    )
    if err != nil {
        panic(err)
    }
    defer shutdown(context.Background())

    // Your agent automatically gets:
    // - Span creation for each Process() call
    // - W3C Trace Context propagation
    // - LLM call tracing
    // - Error tracking
}
```

### View Traces in Jaeger

```bash
# Start Jaeger (Docker)
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest

# Open UI
open http://localhost:16686
```

---

## Advanced Features

### 1. Memory Hierarchy

```go
import "github.com/yourusername/agenkit-go/memory"

mem := memory.NewHierarchy(
    memory.WithWorkingMemory(10),
    memory.WithLongTermMemory("./memory.db"),
)

agent := NewConversationalAgent(
    memory.WithMemory(mem),
)
```

### 2. Budget Tracking

```go
import "github.com/yourusername/agenkit-go/budget"

tracker := budget.NewTracker(
    budget.WithMaxCostUSD(10.0),
)

agent := NewBudgetAwareAgent(
    llm,
    budget.WithTracker(tracker),
)
```

### 3. Safety Framework

```go
import "github.com/yourusername/agenkit-go/safety"

agent := NewSafeAgent(
    llm,
    safety.WithContentFilter(safety.BlockPII),
    safety.WithRateLimiter(10, 30*time.Second),
)
```

---

## Common Pitfalls

### 1. Not Checking Errors

```go
// WRONG:
defer file.Close()

// CORRECT:
defer func() { _ = file.Close() }()

// WRONG:
w.Write(data)

// CORRECT:
if _, err := w.Write(data); err != nil {
    log.Printf("Failed: %v", err)
}
```

### 2. Nullable Return Patterns (v0.50.0 Fixed)

```go
// OLD (v0.49.0 - BAD):
type UserIDExtractor func(*Message) string // Empty string as sentinel

// NEW (v0.50.0 - GOOD):
type UserIDExtractor func(*Message) *string // Proper nil for "no value"

// Usage:
userID := userIDExtractor(message)
if userID == nil {
    return anonymousID, nil
}
return *userID, nil
```

### 3. Printf Format Strings

```go
// WRONG:
log.Printf("timeout=%.1fs", timeoutConfig.Timeout) // Timeout is time.Duration!

// CORRECT:
log.Printf("timeout=%.1fs", timeoutConfig.Timeout.Seconds())
```

---

## Next Steps

1. **Explore Patterns**: See the [Agent Patterns Book](../../agent-patterns-book) for all 18 patterns
2. **Read Architecture**: `ARCHITECTURE.md` explains design principles
3. **Check Examples**: `examples/go/` has production examples
4. **API Reference**: Coming soon in `docs/api-reference/go/`
5. **Migration Guide**: See `docs/MIGRATION_v0.50.0.md` for breaking changes

---

## Quick Reference

```go
// Core imports
import (
    "github.com/yourusername/agenkit-go/agenkit"
    "github.com/yourusername/agenkit-go/middleware"
    "github.com/yourusername/agenkit-go/adapter/llm"
    "github.com/yourusername/agenkit-go/patterns"
)

// Middleware
middleware.NewRetryDecorator(agent, ...)
middleware.NewTimeoutDecorator(agent, ...)
middleware.NewCircuitBreakerDecorator(agent, ...)
middleware.NewRateLimiterDecorator(agent, ...)

// LLM adapters
llm.NewOpenAI(...)
llm.NewAnthropic(...)
llm.NewOllama(...)

// Patterns
patterns.NewReflectionAgent(llm, ...)
patterns.NewReActAgent(llm, tools, ...)
patterns.NewSequentialAgent(agents...)
patterns.NewParallelAgent(agents...)
```

---

**Version**: v0.50.0
**Last Updated**: January 28, 2026

For help: Open an issue at https://github.com/yourusername/agenkit/issues
