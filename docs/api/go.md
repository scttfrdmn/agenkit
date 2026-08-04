# Go API Reference

**Module:** `github.com/scttfrdmn/agenkit-go`
**Go:** 1.23+

---

## Core Types

### `agenkit.Message`

```go
// Package: github.com/scttfrdmn/agenkit-go/agenkit

type Message struct {
    Role     string
    Content  string
    Metadata map[string]any
}
```

### `agenkit.Agent` (interface)

```go
type Agent interface {
    Process(ctx context.Context, msg *Message) (*Message, error)
    Name() string
    Capabilities() []string
    Introspect() *IntrospectionResult
}
```

`IntrospectionResult` carries runtime diagnostics: pattern type, sub-agents, middleware stack, and configuration summary.

### `agenkit.IntrospectionResult`

```go
type IntrospectionResult struct {
    Name         string
    Type         string
    Capabilities []string
    SubAgents    []*IntrospectionResult
    Metadata     map[string]any
}
```

---

## LLM Adapters

**Package:** `github.com/scttfrdmn/agenkit-go/adapter/llm`

### `NewAnthropicClient`

```go
type AnthropicConfig struct {
    Model     string  // default: "claude-sonnet-4-6"
    APIKey    string  // falls back to ANTHROPIC_API_KEY env var
    MaxTokens int     // default: 4096
    Temperature float64 // default: 1.0
}

func NewAnthropicClient(cfg AnthropicConfig) (*AnthropicClient, error)
```

### `NewOpenAIClient`

```go
type OpenAIConfig struct {
    Model       string  // default: "gpt-4o"
    APIKey      string  // falls back to OPENAI_API_KEY env var
    MaxTokens   int     // default: 4096
    Temperature float64 // default: 0.7
}

func NewOpenAIClient(cfg OpenAIConfig) (*OpenAIClient, error)
```

### Additional Adapters

| Constructor | Notes |
|-------------|-------|
| `NewBedrockClient(cfg BedrockConfig)` | AWS Bedrock |
| `NewGeminiClient(cfg GeminiConfig)` | Google Gemini |
| `NewOllamaClient(cfg OllamaConfig)` | Local Ollama |
| `NewLiteLLMClient(cfg LiteLLMConfig)` | LiteLLM proxy |

All adapters implement `agenkit.Agent`.

---

## Patterns

**Package:** `github.com/scttfrdmn/agenkit-go/patterns`

| Constructor | Key Parameters |
|-------------|---------------|
| `NewReflectionAgent(agent, opts...)` | `WithMaxIterations(n int)` |
| `NewReactAgent(agent, tools, opts...)` | `[]Tool` |
| `NewAgentsAsToolsAgent(agent, subAgents, opts...)` | `[]Agent` |
| `NewOrchestrationAgent(orchestrator, workers, opts...)` | `[]Agent` |
| `NewReasoningWithToolsAgent(agent, tools, opts...)` | `WithMaxSteps(n int)` |
| `NewConversationalAgent(agent, opts...)` | `WithMemory(Memory)` |
| `NewTaskAgent(agent, task string, opts...)` | task description string |
| `NewMultiagentAgent(agents, opts...)` | `[]Agent` |
| `NewPlanningAgent(planner, executor, opts...)` | two `Agent` values |
| `NewAutonomousAgent(agent, opts...)` | `WithMaxIterations(n int)` |
| `NewSequentialAgent(agents, opts...)` | `[]Agent` |
| `NewParallelAgent(agents, opts...)` | `WithAggregator(func)` |
| `NewRouterAgent(router, routes, opts...)` | `map[string]Agent` |
| `NewFallbackAgent(primary, fallbacks, opts...)` | `[]Agent` |
| `NewCollaborativeAgent(agents, coordinator, opts...)` | coordinator `Agent` |
| `NewHumanInLoopAgent(agent, approval, opts...)` | `func(context.Context, *Message) (bool, error)` |
| `NewSupervisorAgent(supervisor, workers, opts...)` | `[]Agent` |
| `NewWorkingMemoryAgent(agent, memory, opts...)` | `Memory` |

The `patterns/reasoning` sub-package contains a separate `ReasoningAgent` type used by the `ReasoningWithTools` pattern.

---

## Middleware

**Package:** `github.com/scttfrdmn/agenkit-go/middleware`

All middleware wrap an `Agent` and return an `Agent`.

### `RetryMiddleware`

```go
type RetryConfig struct {
    MaxAttempts int           // default: 3
    BackoffBase time.Duration // default: 1s
    BackoffMax  time.Duration // default: 30s
}

func NewRetryMiddleware(agent Agent, cfg RetryConfig) Agent
```

### `TimeoutMiddleware`

```go
func NewTimeoutMiddleware(agent Agent, timeout time.Duration) Agent
```

### `RateLimiter`

```go
type RateLimiterConfig struct {
    RequestsPerSecond float64
    Burst             int
}

func NewRateLimiter(agent Agent, cfg RateLimiterConfig) Agent
```

### `CircuitBreaker`

```go
type CircuitBreakerConfig struct {
    FailureThreshold int           // default: 5
    RecoveryTimeout  time.Duration // default: 60s
}

func NewCircuitBreaker(agent Agent, cfg CircuitBreakerConfig) Agent
```

### `BatchingMiddleware`

```go
type BatchingConfig struct {
    MaxBatchSize int           // default: 10
    MaxWait      time.Duration // default: 100ms
}

func NewBatchingMiddleware(agent Agent, cfg BatchingConfig) Agent
```

### `CachingMiddleware`

```go
type CachingConfig struct {
    TTL   time.Duration // 0 = no expiry
    Store CacheStore    // default: in-memory
}

func NewCachingMiddleware(agent Agent, cfg CachingConfig) Agent
```

`RedisCacheStore` is available in the same package for distributed caching.

### `MetricsMiddleware`

```go
func NewMetricsMiddleware(agent Agent, collector MetricsCollector) Agent
```

---

## Memory

**Package:** `github.com/scttfrdmn/agenkit-go/memory`

### `Memory` (interface)

```go
type Memory interface {
    Add(ctx context.Context, msg *agenkit.Message) error
    History(ctx context.Context) ([]*agenkit.Message, error)
    Clear(ctx context.Context) error
}
```

### Implementations

| Type | Constructor | Notes |
|------|-------------|-------|
| `InMemoryStore` | `NewInMemoryStore(maxMessages int)` | Ephemeral |
| `RedisMemory` | `NewRedisMemory(addr, key string)` | Persistent |
| `VectorMemory` | `NewVectorMemory(store VectorStore)` | Semantic search |
| `HierarchicalMemory` | `NewHierarchicalMemory(short, long Memory)` | Promotion strategy |
| `EndlessMemory` | `NewEndlessMemory(base Memory)` | No eviction |

### Memory Strategies

**Package:** `memory/strategies`

`SlidingWindowStrategy`, `ImportanceWeightingStrategy`, `SummarizationStrategy` — passed to `HierarchicalMemory` to control promotion from short-term to long-term.

---

## Checkpointing

**Package:** `github.com/scttfrdmn/agenkit-go/checkpointing`

### `CheckpointManager`

```go
func NewCheckpointManager(storage Storage, agentID string) *CheckpointManager

func (m *CheckpointManager) Save(ctx context.Context, state AgentState) (string, error)
func (m *CheckpointManager) Load(ctx context.Context, checkpointID string) (AgentState, error)
func (m *CheckpointManager) List(ctx context.Context) ([]CheckpointMeta, error)
func (m *CheckpointManager) Delete(ctx context.Context, checkpointID string) error
```

### Storage Backends

```go
// Local filesystem
func NewLocalStorage(dir string) Storage

// Amazon S3
type S3StorageConfig struct {
    Bucket string
    Prefix string
    Region string
}
func NewS3Storage(cfg S3StorageConfig) (Storage, error)

// NFS / shared filesystem
func NewNFSStorage(mountPath string) Storage
```

### `DurableAgent`

```go
func NewDurableAgent(agent Agent, manager *CheckpointManager) Agent
```

Wraps any agent with automatic checkpoint save/restore on each `Process` call.

---

## Budget

**Package:** `github.com/scttfrdmn/agenkit-go/budget`

### `TokenBudget`

```go
type TokenBudget struct {
    MaxInputTokens  int
    MaxOutputTokens int
    MaxTotalTokens  int
}

func NewTokenBudget(cfg TokenBudget) *BudgetLimiter
func (b *BudgetLimiter) Wrap(agent Agent) Agent
func (b *BudgetLimiter) Remaining() TokenBudget
```

### `CostTracker`

```go
func NewCostTracker(pricing PricingTable) *CostTracker

func (c *CostTracker) Record(inputTokens, outputTokens int, model string)
func (c *CostTracker) Total() float64
func (c *CostTracker) Reset()
```

`MemoryStorage` stores tracker state in-process. A deprecated alias `InMemoryStorage` remains for backward compatibility.

---

## Infrastructure

**Package:** `github.com/scttfrdmn/agenkit-go/infrastructure`

### `LoadBalancer`

```go
type LoadBalancerConfig struct {
    Strategy  BalancingStrategy  // RoundRobin, LeastLoaded, WeightedRandom
    Agents    []Agent
}

func NewLoadBalancer(cfg LoadBalancerConfig) Agent
```

### `HealthChecker`

```go
func NewHealthChecker(agent Agent, interval time.Duration) *HealthChecker

func (h *HealthChecker) IsHealthy() bool
func (h *HealthChecker) Start(ctx context.Context)
func (h *HealthChecker) Stop()
```

---

## Reasoning Techniques

**Package:** `github.com/scttfrdmn/agenkit-go/techniques/reasoning`

| Constructor | Key Parameters |
|-------------|---------------|
| `NewChainOfThoughtAgent(agent, opts...)` | `WithSteps(n int)` |
| `NewTreeOfThoughtAgent(agent, opts...)` | `WithBranches(n int)`, `WithDepth(n int)` |
| `NewSelfConsistencyAgent(agent, opts...)` | `WithSamples(n int)` |
| `NewGraphOfThoughtAgent(agent, opts...)` | `WithMaxNodes(n int)` |
| `NewPlanAndSolveAgent(planner, solver Agent)` | — |
| `NewLeastToMostAgent(agent, opts...)` | `WithMaxSubproblems(n int)` |

---

## Errors

```go
var (
    ErrAgentFailed    = errors.New("agent processing failed")
    ErrTimeout        = errors.New("agent timed out")
    ErrCircuitOpen    = errors.New("circuit breaker open")
    ErrBudgetExceeded = errors.New("token budget exceeded")
    ErrCheckpoint     = errors.New("checkpoint operation failed")
)
```
