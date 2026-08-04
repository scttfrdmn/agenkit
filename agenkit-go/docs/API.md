# Agenkit Go API Reference

Complete API documentation for Agenkit-Go.

## Table of Contents

- [Core Types](#core-types)
  - [Message](#message)
  - [Agent interface](#agent-interface)
  - [Tool interface](#tool-interface)
  - [ToolResult](#toolresult)
  - [IntrospectionResult](#introspectionresult)
- [Message API](#message-api)
- [Agent Interface API](#agent-interface-api)
- [Middleware](#middleware)
  - [RetryMiddleware](#retrymiddleware)
  - [CircuitBreakerMiddleware](#circuitbreakermiddleware)
  - [TimeoutMiddleware](#timeoutmiddleware)
  - [CachingMiddleware](#cachingmiddleware)
  - [RateLimiterMiddleware](#ratelimitermiddleware)
  - [MetricsMiddleware](#metricsmiddleware)
  - [AuditMiddleware](#auditmiddleware)
  - [LoggingMiddleware](#loggingmiddleware)
- [Patterns](#patterns)
  - [SequentialAgent](#sequentialagent)
  - [ParallelAgent](#parallelagent)
  - [ReflectionAgent](#reflectionagent)
  - [ReActAgent](#reactagent)
  - [PlanningAgent](#planningagent)
  - [TaskAgent](#taskagent)
  - [ConversationalAgent](#conversationalagent)
  - [AgentsAsToolsAgent](#agentsastoolsagent)
  - [AutonomousAgent](#autonomousagent)
  - [MultiagentSystem](#multiagentsystem)
  - [MemoryHierarchyAgent](#memoryhierarchyagent)
- [Observability](#observability)
  - [TracingAgent](#tracingagent)
  - [MetricsCollector](#metricscollector)
- [LLM Adapters](#llm-adapters)
- [Error Handling](#error-handling)
- [Cross-Language Compatibility](#cross-language-compatibility)

---

## Core Types

### Message

The fundamental unit of communication in Agenkit.

```go
// Package: github.com/scttfrdmn/agenkit/agenkit-go/agenkit

type Message struct {
    Role     string                 // "user", "assistant", "system", "tool"
    Content  string                 // Text content
    Metadata map[string]interface{} // Optional key-value pairs
}
```

**Fields:**
- `Role`: The message role. One of `"user"`, `"assistant"`, `"system"`, `"tool"`.
- `Content`: The text content of the message.
- `Metadata`: Arbitrary key-value pairs for session IDs, tracing, etc. May be nil.

**Example:**

```go
msg := agenkit.NewMessage("user", "Hello, agent!")
msg.Metadata = map[string]interface{}{
    "session_id": "abc-123",
    "priority":   5,
}
```

---

### Agent interface

The core interface that all agents implement.

```go
type Agent interface {
    // Name returns the agent's identifier.
    Name() string

    // Capabilities returns the list of capabilities this agent supports.
    Capabilities() []string

    // Process handles a message and returns a response or error.
    // The ctx argument enables cancellation and deadline propagation.
    Process(ctx context.Context, message *Message) (*Message, error)

    // Introspect returns runtime metadata about the agent.
    Introspect() *IntrospectionResult
}
```

**Implementing the interface:**

```go
type MyAgent struct {
    name string
}

func (a *MyAgent) Name() string { return a.name }

func (a *MyAgent) Capabilities() []string {
    return []string{"processing", "analysis"}
}

func (a *MyAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    default:
    }

    if msg.Content == "" {
        return nil, fmt.Errorf("empty message content")
    }

    return agenkit.NewMessage("assistant", "processed: "+msg.ContentString()), nil
}

func (a *MyAgent) Introspect() *agenkit.IntrospectionResult {
    return agenkit.DefaultIntrospectionResult(a)
}
```

---

### Tool interface

Tools that agents can invoke during processing.

```go
type Tool interface {
    // Name returns the tool's identifier used in function calls.
    Name() string

    // Description explains what the tool does, used in LLM prompts.
    Description() string

    // Parameters returns a JSON Schema-compatible map of parameter definitions.
    Parameters() map[string]interface{}

    // Execute runs the tool with the provided parameters.
    Execute(ctx context.Context, params map[string]interface{}) (*ToolResult, error)
}
```

**Example implementation:**

```go
type SearchTool struct{}

func (t *SearchTool) Name() string { return "search" }

func (t *SearchTool) Description() string {
    return "Search the web for information"
}

func (t *SearchTool) Parameters() map[string]interface{} {
    return map[string]interface{}{
        "query": map[string]interface{}{
            "type":        "string",
            "description": "The search query",
        },
    }
}

func (t *SearchTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
    query, ok := params["query"].(string)
    if !ok {
        return nil, fmt.Errorf("missing required parameter: query")
    }
    // Perform search...
    return agenkit.NewToolResult(fmt.Sprintf("results for: %s", query)), nil
}
```

---

### ToolResult

Result returned from tool execution.

```go
type ToolResult struct {
    Success bool
    Result  string
    Error   string
}
```

**Constructor:**

```go
func NewToolResult(result string) *ToolResult
func NewToolError(msg string) *ToolResult
```

---

### IntrospectionResult

Runtime metadata about an agent.

```go
type IntrospectionResult struct {
    Name         string
    Capabilities []string
    Version      string
    Metadata     map[string]interface{}
}
```

**Constructor:**

```go
// DefaultIntrospectionResult creates a basic introspection result from an agent.
func DefaultIntrospectionResult(agent Agent) *IntrospectionResult
```

---

## Message API

### NewMessage

```go
func NewMessage(role, content string) *Message
```

Creates a new message with the given role and content. Metadata is initialized to nil.

**Parameters:**
- `role`: Message role (`"user"`, `"assistant"`, `"system"`, `"tool"`)
- `content`: Text content

**Returns:** `*Message`

**Example:**

```go
msg := agenkit.NewMessage("user", "Hello!")
```

---

### NewMessageWithMetadata

```go
func NewMessageWithMetadata(role, content string, metadata map[string]interface{}) *Message
```

Creates a new message with metadata.

**Example:**

```go
msg := agenkit.NewMessageWithMetadata("user", "Hello!", map[string]interface{}{
    "session_id": "abc-123",
})
```

---

### Message.Clone

```go
func (m *Message) Clone() *Message
```

Returns a deep copy of the message, including metadata.

---

## Agent Interface API

### DefaultIntrospectionResult

```go
func DefaultIntrospectionResult(agent Agent) *IntrospectionResult
```

Returns a standard introspection result populated from the agent's `Name()` and `Capabilities()`.

---

## Middleware

All middleware wraps an existing `Agent` and returns a new `Agent`. Middleware is composable and follows the standard `Agent` interface.

### RetryMiddleware

Automatically retries failed operations with exponential backoff.

```go
// Package: github.com/scttfrdmn/agenkit/agenkit-go/middleware

type RetryConfig struct {
    MaxRetries    int           // Maximum number of retry attempts
    BackoffFactor float64       // Multiplier for each successive delay
    InitialDelay  time.Duration // Delay before first retry
    MaxDelay      time.Duration // Maximum delay cap
}

func NewRetryMiddleware(agent agenkit.Agent, config *RetryConfig) agenkit.Agent
```

**Example:**

```go
agent = middleware.NewRetryMiddleware(agent, &middleware.RetryConfig{
    MaxRetries:    3,
    BackoffFactor: 2.0,
    InitialDelay:  100 * time.Millisecond,
    MaxDelay:      10 * time.Second,
})
```

---

### CircuitBreakerMiddleware

Opens the circuit after repeated failures to prevent cascading errors.

```go
type CircuitBreakerConfig struct {
    FailureThreshold int           // Failures before opening
    RecoveryTimeout  time.Duration // Time before attempting recovery
    SuccessThreshold int           // Successes required to close
}

func NewCircuitBreakerMiddleware(agent agenkit.Agent, config *CircuitBreakerConfig) agenkit.Agent
```

**States:**
- **Closed**: Normal operation, requests pass through
- **Open**: All requests fail fast, no calls to wrapped agent
- **Half-Open**: Testing recovery, limited requests pass through

**Example:**

```go
agent = middleware.NewCircuitBreakerMiddleware(agent, &middleware.CircuitBreakerConfig{
    FailureThreshold: 5,
    RecoveryTimeout:  30 * time.Second,
    SuccessThreshold: 2,
})
```

---

### TimeoutMiddleware

Cancels agent calls that exceed a deadline.

```go
type TimeoutConfig struct {
    Timeout time.Duration // Maximum processing time
}

func NewTimeoutMiddleware(agent agenkit.Agent, config *TimeoutConfig) agenkit.Agent
```

**Example:**

```go
agent = middleware.NewTimeoutMiddleware(agent, &middleware.TimeoutConfig{
    Timeout: 5 * time.Second,
})
```

---

### CachingMiddleware

Caches responses to avoid redundant processing.

```go
type CachingConfig struct {
    TTL        time.Duration // Cache entry lifetime
    MaxEntries int           // Maximum cached entries
    KeyFunc    func(*agenkit.Message) string // Cache key derivation
}

func NewCachingMiddleware(agent agenkit.Agent, config *CachingConfig) agenkit.Agent
```

**Example:**

```go
agent = middleware.NewCachingMiddleware(agent, &middleware.CachingConfig{
    TTL:        5 * time.Minute,
    MaxEntries: 1000,
})
```

---

### RateLimiterMiddleware

Limits request throughput to prevent overload.

```go
type RateLimiterConfig struct {
    RequestsPerSecond float64       // Maximum RPS
    BurstSize         int           // Burst allowance
    WaitTimeout       time.Duration // Max wait time before error
}

func NewRateLimiterMiddleware(agent agenkit.Agent, config *RateLimiterConfig) agenkit.Agent
```

**Example:**

```go
agent = middleware.NewRateLimiterMiddleware(agent, &middleware.RateLimiterConfig{
    RequestsPerSecond: 10.0,
    BurstSize:         20,
    WaitTimeout:       1 * time.Second,
})
```

---

### MetricsMiddleware

Collects processing metrics via Prometheus.

```go
type MetricsConfig struct {
    Namespace  string // Prometheus metric namespace
    Subsystem  string // Prometheus metric subsystem
    Registerer prometheus.Registerer
}

func NewMetricsMiddleware(agent agenkit.Agent, config *MetricsConfig) agenkit.Agent
```

---

### AuditMiddleware

Records agent interactions for compliance.

```go
type AuditConfig struct {
    Logger   *slog.Logger
    LogInput bool // Whether to log message content
}

func NewAuditMiddleware(agent agenkit.Agent, config *AuditConfig) agenkit.Agent
```

---

### LoggingMiddleware

Structured logging for all agent calls.

```go
type LoggingConfig struct {
    Logger *slog.Logger
    Level  slog.Level
}

func NewLoggingMiddleware(agent agenkit.Agent, config *LoggingConfig) agenkit.Agent
```

**Example:**

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
agent = middleware.NewLoggingMiddleware(agent, &middleware.LoggingConfig{
    Logger: logger,
    Level:  slog.LevelInfo,
})
```

---

## Patterns

### SequentialAgent

Executes agents in order, passing each output as input to the next.

```go
// Package: github.com/scttfrdmn/agenkit/agenkit-go/patterns

func NewSequentialAgent(agents []agenkit.Agent) agenkit.Agent
```

**Parameters:**
- `agents`: Ordered slice of agents to execute. Output of agent N becomes input to agent N+1.

**Example:**

```go
pipeline := patterns.NewSequentialAgent([]agenkit.Agent{
    &ValidationAgent{},
    &ProcessingAgent{},
    &FormattingAgent{},
})

result, err := pipeline.Process(ctx, inputMessage)
```

**ASCII diagram:**

```
Input → ValidationAgent → ProcessingAgent → FormattingAgent → Output
```

---

### ParallelAgent

Executes multiple agents concurrently using goroutines and aggregates results.

```go
type AggregatorFunc func(responses []*agenkit.Message) (*agenkit.Message, error)

func NewParallelAgent(agents []agenkit.Agent, aggregator AggregatorFunc) agenkit.Agent
```

**Parameters:**
- `agents`: Agents to run concurrently. All receive the same input message.
- `aggregator`: Function to combine results. Pass `nil` for default concatenation.

**Example:**

```go
parallel := patterns.NewParallelAgent([]agenkit.Agent{
    &SentimentAgent{},
    &EntityAgent{},
    &TopicAgent{},
}, nil)

result, err := parallel.Process(ctx, message)
```

**ASCII diagram:**

```
         ┌→ SentimentAgent ─┐
Input ───┼→ EntityAgent    ─┼→ Aggregator → Output
         └→ TopicAgent     ─┘
```

---

### ReflectionAgent

Iteratively improves output through self-critique cycles.

```go
type ReflectionConfig struct {
    BaseAgent      agenkit.Agent
    MaxIterations  int
    CritiquePrompt string
}

func NewReflectionAgent(config *ReflectionConfig) agenkit.Agent
```

**Example:**

```go
reflective := patterns.NewReflectionAgent(&patterns.ReflectionConfig{
    BaseAgent:     myLLMAgent,
    MaxIterations: 3,
    CritiquePrompt: "Review this response and identify improvements:",
})

result, err := reflective.Process(ctx, message)
```

---

### ReActAgent

Reasoning and Acting pattern — the agent reasons before taking actions with tools.

```go
type ReActConfig struct {
    LLM           agenkit.Agent
    Tools         []agenkit.Tool
    MaxIterations int
    SystemPrompt  string
}

func NewReActAgent(config *ReActConfig) agenkit.Agent
```

**Example:**

```go
react := patterns.NewReActAgent(&patterns.ReActConfig{
    LLM:           myLLM,
    Tools:         []agenkit.Tool{&SearchTool{}, &CalculatorTool{}},
    MaxIterations: 5,
})

result, err := react.Process(ctx, message)
```

---

### PlanningAgent

Decomposes complex tasks into steps and executes them.

```go
type PlanningConfig struct {
    Planner  agenkit.Agent // Generates a plan
    Executor agenkit.Agent // Executes individual steps
    MaxSteps int
}

func NewPlanningAgent(config *PlanningConfig) agenkit.Agent
```

**Example:**

```go
planner := patterns.NewPlanningAgent(&patterns.PlanningConfig{
    Planner:  plannerLLM,
    Executor: executorAgent,
    MaxSteps: 10,
})

result, err := planner.Process(ctx, message)
```

---

### TaskAgent

A single-purpose agent optimized for a specific task.

```go
type TaskConfig struct {
    Name        string
    Description string
    Handler     func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error)
}

func NewTaskAgent(config *TaskConfig) agenkit.Agent
```

**Example:**

```go
summarizer := patterns.NewTaskAgent(&patterns.TaskConfig{
    Name:        "summarizer",
    Description: "Summarizes long documents",
    Handler: func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
        summary := summarize(msg.Content)
        return agenkit.NewMessage("assistant", summary), nil
    },
})
```

---

### ConversationalAgent

Maintains multi-turn conversation history.

```go
type ConversationalConfig struct {
    LLM          agenkit.Agent
    SystemPrompt string
    MaxHistory   int    // Maximum messages to keep in context
    SessionID    string // Optional: for tracking sessions
}

func NewConversationalAgent(config *ConversationalConfig) agenkit.Agent
```

**Example:**

```go
conv := patterns.NewConversationalAgent(&patterns.ConversationalConfig{
    LLM:          myLLM,
    SystemPrompt: "You are a helpful assistant.",
    MaxHistory:   20,
})

resp1, _ := conv.Process(ctx, agenkit.NewMessage("user", "What is Go?"))
resp2, _ := conv.Process(ctx, agenkit.NewMessage("user", "What about goroutines?"))
// Agent remembers the context from resp1
```

---

### AgentsAsToolsAgent

An orchestrating agent that can delegate to specialized sub-agents as tools.

```go
type AgentsAsToolsConfig struct {
    Orchestrator agenkit.Agent
    SubAgents    map[string]agenkit.Agent
}

func NewAgentsAsToolsAgent(config *AgentsAsToolsConfig) agenkit.Agent
```

**Example:**

```go
orchestrator := patterns.NewAgentsAsToolsAgent(&patterns.AgentsAsToolsConfig{
    Orchestrator: myLLM,
    SubAgents: map[string]agenkit.Agent{
        "calculator": &CalculatorAgent{},
        "search":     &SearchAgent{},
        "code":       &CodeAgent{},
    },
})

result, err := orchestrator.Process(ctx, message)
```

---

### AutonomousAgent

Self-directed agent that pursues goals without step-by-step instructions.

```go
type AutonomousConfig struct {
    BaseAgent    agenkit.Agent
    Goal         string
    MaxSteps     int
    StopCriteria func(response *agenkit.Message) bool
}

func NewAutonomousAgent(config *AutonomousConfig) agenkit.Agent
```

**Example:**

```go
auto := patterns.NewAutonomousAgent(&patterns.AutonomousConfig{
    BaseAgent: myLLM,
    Goal:      "Research and summarize the latest Go release",
    MaxSteps:  20,
    StopCriteria: func(resp *agenkit.Message) bool {
        return strings.Contains(resp.ContentString(), "DONE")
    },
})

result, err := auto.Process(ctx, agenkit.NewMessage("user", "start"))
```

---

### MultiagentSystem

Coordinates multiple agents that collaborate to complete tasks.

```go
type MultiagentConfig struct {
    Coordinator agenkit.Agent
    Agents      map[string]agenkit.Agent
    MaxRounds   int
}

func NewMultiagentSystem(config *MultiagentConfig) agenkit.Agent
```

**Example:**

```go
system := patterns.NewMultiagentSystem(&patterns.MultiagentConfig{
    Coordinator: coordinatorLLM,
    Agents: map[string]agenkit.Agent{
        "researcher": &ResearchAgent{},
        "writer":     &WritingAgent{},
        "editor":     &EditingAgent{},
    },
    MaxRounds: 5,
})

result, err := system.Process(ctx, message)
```

---

### MemoryHierarchyAgent

Manages working memory, short-term memory, and long-term memory.

```go
type MemoryConfig struct {
    BaseAgent        agenkit.Agent
    WorkingSize      int    // Messages in working context
    ShortTermSize    int    // Recent interaction buffer
    LongTermStore    string // Path or connection string for persistence
}

func NewMemoryHierarchyAgent(config *MemoryConfig) agenkit.Agent
```

**Example:**

```go
memAgent := patterns.NewMemoryHierarchyAgent(&patterns.MemoryConfig{
    BaseAgent:     myLLM,
    WorkingSize:   5,
    ShortTermSize: 50,
    LongTermStore: "./memory.db",
})

result, err := memAgent.Process(ctx, message)
```

**Memory tiers:**

```
Working Memory  ←→ Short-Term Memory  ←→ Long-Term Memory
  (5 msgs)           (50 msgs)             (persistent)
```

---

## Observability

### TracingAgent

Wraps an agent with OpenTelemetry distributed tracing.

```go
// Package: github.com/scttfrdmn/agenkit/agenkit-go/observability

type TracingConfig struct {
    ServiceName string
    Tracer      trace.Tracer
}

func NewTracingMiddleware(agent agenkit.Agent, tracer trace.Tracer) agenkit.Agent
```

**Example:**

```go
import (
    "go.opentelemetry.io/otel"
    "github.com/scttfrdmn/agenkit/agenkit-go/observability"
)

tracer := otel.Tracer("my-service")
traced := observability.NewTracingMiddleware(agent, tracer)

ctx, span := tracer.Start(ctx, "process_request")
defer span.End()

result, err := traced.Process(ctx, message)
```

---

### MetricsCollector

Collects and exports agent performance metrics.

```go
type MetricsCollector struct {
    // unexported fields
}

func NewMetricsCollector(namespace string) *MetricsCollector

// Register registers Prometheus metrics with the default registerer.
func (c *MetricsCollector) Register() error

// Middleware returns an agent middleware that records metrics.
func (c *MetricsCollector) Middleware(agent agenkit.Agent) agenkit.Agent

// Snapshot returns a point-in-time metrics snapshot.
func (c *MetricsCollector) Snapshot() MetricsSnapshot
```

**MetricsSnapshot:**

```go
type MetricsSnapshot struct {
    TotalRequests     int64
    SuccessfulRequests int64
    FailedRequests    int64
    TotalLatencyMs    float64
    P50LatencyMs      float64
    P95LatencyMs      float64
    P99LatencyMs      float64
}
```

**Example:**

```go
collector := observability.NewMetricsCollector("agenkit")
if err := collector.Register(); err != nil {
    log.Fatalf("failed to register metrics: %v", err)
}

agent = collector.Middleware(agent)

// Expose metrics
http.Handle("/metrics", promhttp.Handler())
```

---

## LLM Adapters

LLM adapters implement the `agenkit.Agent` interface.

```go
// Package: github.com/scttfrdmn/agenkit/agenkit-go/adapter

// NewAnthropicAdapter creates a Claude adapter.
func NewAnthropicAdapter(apiKey string, opts ...AdapterOption) (agenkit.Agent, error)

// NewOpenAIAdapter creates an OpenAI adapter.
func NewOpenAIAdapter(apiKey string, opts ...AdapterOption) (agenkit.Agent, error)

// NewOpenAICompatibleAdapter creates an adapter for OpenAI-compatible APIs
// (Ollama, vLLM, llama.cpp, etc.).
func NewOpenAICompatibleAdapter(baseURL string, opts ...AdapterOption) (agenkit.Agent, error)

// NewBedrockAdapter creates an AWS Bedrock adapter.
func NewBedrockAdapter(region string, opts ...AdapterOption) (agenkit.Agent, error)
```

**Options:**

```go
func WithModel(model string) AdapterOption
func WithTemperature(t float64) AdapterOption  // 0.0 - 2.0
func WithMaxTokens(n int) AdapterOption        // > 0
func WithSystemPrompt(prompt string) AdapterOption
func WithTopP(p float64) AdapterOption         // 0.0 - 1.0
```

**Example:**

```go
llm, err := adapter.NewAnthropicAdapter(
    os.Getenv("ANTHROPIC_API_KEY"),
    adapter.WithModel("claude-3-5-sonnet-20241022"),
    adapter.WithTemperature(0.7),
    adapter.WithMaxTokens(4096),
)
if err != nil {
    log.Fatalf("failed to create LLM adapter: %v", err)
}
```

---

## Error Handling

### Sentinel Errors

```go
// Package: github.com/scttfrdmn/agenkit/agenkit-go/agenkit

var (
    // ErrEmptyInput is returned when the message content is empty.
    ErrEmptyInput = errors.New("empty input message")

    // ErrContextCanceled is returned when the context is canceled.
    ErrContextCanceled = errors.New("context canceled")

    // ErrBudgetExceeded is returned when the token budget is exceeded.
    ErrBudgetExceeded = errors.New("token budget exceeded")

    // ErrCircuitOpen is returned when the circuit breaker is open.
    ErrCircuitOpen = errors.New("circuit breaker open")

    // ErrRateLimitExceeded is returned when the rate limit is hit.
    ErrRateLimitExceeded = errors.New("rate limit exceeded")
)
```

**Checking errors:**

```go
response, err := agent.Process(ctx, message)
if err != nil {
    switch {
    case errors.Is(err, agenkit.ErrEmptyInput):
        // handle empty input
    case errors.Is(err, agenkit.ErrCircuitOpen):
        // circuit breaker tripped
    case errors.Is(err, context.DeadlineExceeded):
        // timeout
    default:
        log.Printf("unexpected error: %v", err)
    }
}
```

---

## Cross-Language Compatibility

Agenkit-Go maintains 100% behavioral parity with all other implementations.

### Message Structure (Universal)

```json
{
  "role": "user|assistant|system|tool",
  "content": "text content",
  "metadata": {"key": "value"}
}
```

### Agent Interface (Universal)

All implementations expose the same logical interface:

| Method | Go | Python | TypeScript | Rust | C++ | Zig |
|--------|----|----|--------|------|-----|-----|
| `Name()` | `Name() string` | `name` property | `name: string` | `fn name()` | `name()` | `name()` |
| `Process()` | `Process(ctx, *Message)` | `async process()` | `async process()` | `async fn process()` | `process()` | `process()` |
| `Capabilities()` | `Capabilities() []string` | `capabilities()` | `capabilities()` | `fn capabilities()` | `capabilities()` | `capabilities()` |

### HTTP Interoperability

Go agents can call Python agents (and vice versa) over HTTP:

```go
import "github.com/scttfrdmn/agenkit/agenkit-go/transport/http"

// Call a Python agent from Go
pythonAgent := http.NewHTTPClient("http://localhost:8000")
result, err := pythonAgent.Process(ctx, message)
```

---

## Version Information

**API Version:** 0.75.0
**Go Version:** >= 1.21
**Stability:** Production-ready

### Package Overview

| Package | Purpose |
|---------|---------|
| `agenkit` | Core types: Message, Agent, Tool |
| `middleware` | Retry, circuit breaker, timeout, caching |
| `patterns` | 11 agent patterns |
| `adapter` | LLM adapters: Anthropic, OpenAI, Bedrock |
| `observability` | OpenTelemetry tracing, Prometheus metrics |
| `transport/http` | HTTP server and client |
| `transport/grpc` | gRPC server and client |
| `evaluation` | Testing utilities, benchmarks |
| `budget` | Token and cost tracking |
| `safety` | Content filtering, rate limiting |

---

## See Also

- [Getting Started Guide](GETTING_STARTED.md) - Installation and first agent
- [Patterns Guide](PATTERNS.md) - Deep dive into agent patterns
- [Observability Guide](OBSERVABILITY.md) - Tracing and metrics
- [Migration Guide](MIGRATION.md) - Porting from other languages
- [Testing Framework](TESTING_FRAMEWORK.md) - Testing patterns and utilities
- [GoDoc](https://pkg.go.dev/github.com/scttfrdmn/agenkit/agenkit-go) - Auto-generated API docs
