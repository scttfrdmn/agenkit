# Rust API Reference

**Crate:** `agenkit`
**Rust:** 1.75+ (async/await, APIT)

---

## Core Types

### `Message`

```rust
// agenkit::core

pub struct Message {
    pub role: String,
    pub content: String,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Message {
    pub fn new(role: impl Into<String>, content: impl Into<String>) -> Self;
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self;
}
```

### `Agent` (trait)

```rust
pub trait Agent: Send + Sync {
    fn name(&self) -> &str;
    fn capabilities(&self) -> Vec<String>;
    fn process(
        &self,
        message: Message,
    ) -> impl Future<Output = Result<Message, AgentError>> + Send;
}
```

`AgentError` is the unified error type for all agent operations.

### `AgentError`

```rust
pub enum AgentError {
    Adapter(String),
    Timeout,
    CircuitOpen,
    BudgetExceeded,
    Checkpoint(String),
    Other(String),
}
```

---

## LLM Adapters

**Module:** `agenkit::adapters`

### Anthropic

```rust
pub struct AnthropicConfig {
    pub model: String,          // default: "claude-sonnet-4-6"
    pub api_key: String,        // or ANTHROPIC_API_KEY env var
    pub max_tokens: u32,        // default: 4096
    pub temperature: f64,       // default: 1.0
}

pub struct AnthropicClient { /* opaque */ }

impl AnthropicClient {
    pub fn new(config: AnthropicConfig) -> Result<Self, AgentError>;
    pub fn from_env() -> Result<Self, AgentError>;  // reads env vars
}
```

### OpenAI

```rust
pub struct OpenAIConfig {
    pub model: String,          // default: "gpt-4o"
    pub api_key: String,        // or OPENAI_API_KEY env var
    pub max_tokens: u32,        // default: 4096
    pub temperature: f64,       // default: 0.7
}

pub struct OpenAIClient { /* opaque */ }

impl OpenAIClient {
    pub fn new(config: OpenAIConfig) -> Result<Self, AgentError>;
    pub fn from_env() -> Result<Self, AgentError>;
}
```

### Additional Adapters

| Struct | Module | Notes |
|--------|--------|-------|
| `BedrockClient` | `agenkit::adapters::bedrock` | AWS Bedrock |
| `GeminiClient` | `agenkit::adapters::gemini` | Google Gemini |
| `OllamaClient` | `agenkit::adapters::ollama` | Local Ollama |

---

## Patterns

**Module:** `agenkit::patterns`

All pattern structs implement `Agent`. Constructors use the builder pattern where configuration is non-trivial.

| Struct | Constructor / Key Fields |
|--------|--------------------------|
| `ReflectionAgent` | `ReflectionAgent::new(agent, max_iterations: u32)` |
| `ReactAgent` | `ReactAgent::new(agent, tools: Vec<Box<dyn Tool>>)` |
| `AgentsAsToolsAgent` | `AgentsAsToolsAgent::new(agent, sub_agents: Vec<Box<dyn Agent>>)` |
| `OrchestrationAgent` | `OrchestrationAgent::new(orchestrator, workers: Vec<Box<dyn Agent>>)` |
| `ReasoningWithToolsAgent` | `ReasoningWithToolsAgent::new(agent, tools, max_steps: u32)` |
| `ConversationalAgent` | `ConversationalAgent::new(agent, memory: Box<dyn Memory>)` |
| `TaskAgent` | `TaskAgent::new(agent, task: String)` |
| `MultiagentAgent` | `MultiagentAgent::new(agents: Vec<Box<dyn Agent>>)` |
| `PlanningAgent` | `PlanningAgent::new(planner, executor)` |
| `AutonomousAgent` | `AutonomousAgent::new(agent, max_iterations: u32)` |
| `SequentialAgent` | `SequentialAgent::new(agents: Vec<Box<dyn Agent>>)` |
| `ParallelAgent` | `ParallelAgent::new(agents: Vec<Box<dyn Agent>>)` |
| `RouterAgent` | `RouterAgent::new(router, routes: HashMap<String, Box<dyn Agent>>)` |
| `FallbackAgent` | `FallbackAgent::new(primary, fallbacks: Vec<Box<dyn Agent>>)` |
| `CollaborativeAgent` | `CollaborativeAgent::new(agents, coordinator)` |
| `HumanInLoopAgent` | `HumanInLoopAgent::new(agent, approval: impl ApprovalCallback)` |
| `SupervisorAgent` | `SupervisorAgent::new(supervisor, workers: Vec<Box<dyn Agent>>)` |
| `WorkingMemoryAgent` | `WorkingMemoryAgent::new(agent, memory: Box<dyn Memory>)` |

---

## Middleware

**Module:** `agenkit::middleware`

All middleware types implement `Agent` and wrap a `Box<dyn Agent>`.

### `RetryMiddleware`

```rust
pub struct RetryConfig {
    pub max_attempts: u32,         // default: 3
    pub backoff_base: Duration,    // default: 1s
    pub backoff_max: Duration,     // default: 30s
}

RetryMiddleware::new(agent: Box<dyn Agent>, config: RetryConfig)
```

### `TimeoutMiddleware`

```rust
TimeoutMiddleware::new(agent: Box<dyn Agent>, timeout: Duration)
```

### `RateLimiter`

```rust
pub struct RateLimiterConfig {
    pub requests_per_second: f64,
    pub burst: u32,
}

RateLimiter::new(agent: Box<dyn Agent>, config: RateLimiterConfig)
```

### `CircuitBreaker`

```rust
pub struct CircuitBreakerConfig {
    pub failure_threshold: u32,    // default: 5
    pub recovery_timeout: Duration // default: 60s
}

CircuitBreaker::new(agent: Box<dyn Agent>, config: CircuitBreakerConfig)
```

### `BatchingMiddleware`

```rust
BatchingMiddleware::new(agent: Box<dyn Agent>, max_batch_size: usize, max_wait: Duration)
```

### `CachingMiddleware`

```rust
CachingMiddleware::new(agent: Box<dyn Agent>, ttl: Option<Duration>)
```

---

## Memory

**Module:** `agenkit::memory`

### `Memory` (trait)

```rust
pub trait Memory: Send + Sync {
    fn add(&self, message: Message) -> impl Future<Output = Result<(), AgentError>> + Send;
    fn history(&self) -> impl Future<Output = Result<Vec<Message>, AgentError>> + Send;
    fn clear(&self) -> impl Future<Output = Result<(), AgentError>> + Send;
}
```

### Implementations

| Struct | Notes |
|--------|-------|
| `ShortTermMemory` | In-process ring buffer |
| `LongTermMemory` | Persistent store |
| `WorkingMemory` | Task-scoped scratch space |
| `HierarchicalMemory` | Composes short-term + long-term |
| `VectorMemory` | Semantic search via embeddings |
| `RedisMemory` | Redis-backed persistence |

---

## Checkpointing

**Module:** `agenkit::checkpointing`

### `CheckpointManager`

```rust
pub struct CheckpointManager { /* opaque */ }

impl CheckpointManager {
    pub fn new(storage: Box<dyn CheckpointStorage>, agent_id: &str) -> Self;
    pub async fn save(&self, state: &AgentState) -> Result<String, AgentError>;
    pub async fn load(&self, id: &str) -> Result<AgentState, AgentError>;
    pub async fn list(&self) -> Result<Vec<CheckpointMeta>, AgentError>;
    pub async fn delete(&self, id: &str) -> Result<(), AgentError>;
}
```

### `DurableAgent`

```rust
pub struct DurableAgent { /* opaque */ }

impl DurableAgent {
    pub fn new(agent: Box<dyn Agent>, manager: CheckpointManager) -> Self;
}
```

### Storage Backends

```rust
// Local filesystem
LocalStorage::new(dir: &Path) -> Box<dyn CheckpointStorage>

// Amazon S3
S3Storage::new(bucket: &str, prefix: &str, region: &str) -> Result<Box<dyn CheckpointStorage>, AgentError>
```

---

## Safety

**Module:** `agenkit::safety`

### `PermissionConfig`

```rust
pub struct PermissionConfig {
    pub allow_network: bool,
    pub allow_filesystem: bool,
    pub allowed_paths: Vec<PathBuf>,
    pub denied_paths: Vec<PathBuf>,
    pub allow_env: bool,
}
```

### `Sandbox`

```rust
pub struct Sandbox { /* opaque */ }

impl Sandbox {
    pub fn builder() -> SandboxBuilder;
    pub fn execute<F, R>(&self, f: F) -> Result<R, SafetyError>
    where
        F: FnOnce() -> R + Send,
        R: Send;
}
```

### `SandboxBuilder`

```rust
pub struct SandboxBuilder { /* opaque */ }

impl SandboxBuilder {
    pub fn allow_path(self, path: impl Into<PathBuf>) -> Self;
    pub fn deny_path(self, path: impl Into<PathBuf>) -> Self;
    pub fn allow_network(self) -> Self;
    pub fn deny_network(self) -> Self;
    pub fn build(self) -> Result<Sandbox, SafetyError>;
}
```

---

## Reasoning Techniques

**Module:** `agenkit::techniques::reasoning`

| Struct | Constructor |
|--------|-------------|
| `ChainOfThoughtAgent` | `ChainOfThoughtAgent::new(agent, steps: u32)` |
| `TreeOfThoughtAgent` | `TreeOfThoughtAgent::new(agent, branches: u32, depth: u32)` |
| `SelfConsistencyAgent` | `SelfConsistencyAgent::new(agent, samples: u32)` |
| `GraphOfThoughtAgent` | `GraphOfThoughtAgent::new(agent, max_nodes: usize)` |
| `PlanAndSolveAgent` | `PlanAndSolveAgent::new(planner, solver)` |
| `LeastToMostAgent` | `LeastToMostAgent::new(agent, max_subproblems: usize)` |
