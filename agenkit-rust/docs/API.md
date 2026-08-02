# Agenkit Rust API Reference

Complete API documentation for Agenkit-Rust v0.75.0.

## Table of Contents

- [Core Types](#core-types)
  - [Message](#message)
  - [Agent Trait](#agent-trait)
  - [AgentError](#agenterror)
  - [Tool Trait](#tool-trait)
  - [ToolResult](#toolresult)
- [Middleware](#middleware)
  - [RetryDecorator](#retrydecorator)
  - [TimeoutDecorator](#timeoutdecorator)
  - [CircuitBreakerDecorator](#circuitbreakerdecorator)
  - [RateLimiterDecorator](#ratelimiterdecorator)
  - [CachingDecorator](#cachingdecorator)
  - [LoggingDecorator](#loggingdecorator)
- [Patterns](#patterns)
  - [SequentialPattern](#sequentialpattern)
  - [ParallelPattern](#parallelpattern)
  - [ReflectionAgent](#reflectionagent)
  - [ReActAgent](#reactagent)
  - [PlanningAgent](#planningagent)
  - [TaskAgent](#taskagent)
  - [ConversationalAgent](#conversationalagent)
  - [AgentsAsToolsPattern](#agentsastoolspattern)
  - [AutonomousAgent](#autonomousagent)
  - [MultiagentOrchestrator](#multiagentorchestrator)
  - [MemoryHierarchyAgent](#memoryhierarchyagent)
- [Observability](#observability)
  - [TracingMiddleware](#tracingmiddleware)
  - [MetricsMiddleware](#metricsmiddleware)
  - [MetricsCollector](#metricscollector)
  - [AuditLogger](#auditlogger)
- [Adapters](#adapters)
  - [OpenAIAgent](#openaiagent)
  - [AnthropicAgent](#anthropicagent)
  - [OllamaAgent](#ollamaagent)
  - [OpenAICompatibleAgent](#openaicompatibleagent)
- [Memory](#memory)
- [Safety](#safety)
- [Evaluation](#evaluation)

---

## Core Types

### Message

The fundamental unit of communication between agents, users, and tools.

```rust
// In agenkit::core
pub struct Message {
    pub role: String,
    pub content: MessageContent,
    pub metadata: HashMap<String, serde_json::Value>,
}
```

**Fields:**
- `role`: Who sent the message (`"user"`, `"assistant"`, `"system"`, `"tool"`)
- `content`: The message content (text or structured data)
- `metadata`: Key-value pairs for tracing, sessions, etc.

**Constructors:**

```rust
impl Message {
    // Create text message with explicit role
    pub fn with_text(role: &str, content: &str) -> Message;

    // Create message with structured JSON content
    pub fn with_structured(role: &str, content: serde_json::Value) -> Message;

    // Role-specific constructors (convenience)
    pub fn user(content: &str) -> Message;
    pub fn assistant(content: &str) -> Message;
    pub fn system(content: &str) -> Message;
    pub fn tool_result(content: &str) -> Message;
}
```

**Builder methods (return new Message, `self` is unchanged):**

```rust
impl Message {
    pub fn with_metadata(self, key: &str, value: serde_json::Value) -> Message;
    pub fn with_role(self, role: &str) -> Message;
}
```

**Accessor methods:**

```rust
impl Message {
    // Get content as string, returns None if content is structured
    pub fn content_as_str(&self) -> Option<&str>;

    // Get metadata value by key
    pub fn get_metadata(&self, key: &str) -> Option<&serde_json::Value>;

    // Check if this is a specific role
    pub fn is_user(&self) -> bool;
    pub fn is_assistant(&self) -> bool;
    pub fn is_system(&self) -> bool;
    pub fn is_tool(&self) -> bool;
}
```

**Trait implementations:**
- `Clone` — messages can be cloned for concurrent use
- `Debug` — formatted debug output
- `Serialize`, `Deserialize` — JSON serialization via serde

**Example:**

```rust
use agenkit::core::Message;
use serde_json::json;

// Text message
let msg = Message::with_text("user", "Hello!");

// With metadata
let tracked = Message::user("Search for Rust tutorials")
    .with_metadata("session_id", json!("abc-123"))
    .with_metadata("priority", json!("high"));

// Accessing content
if let Some(text) = tracked.content_as_str() {
    println!("User said: {}", text);
}

// Structured content for tool results
let result = Message::with_structured("tool", json!({
    "tool_name": "web_search",
    "results": ["https://doc.rust-lang.org", "https://rust-by-example.com"],
    "count": 2,
}));
```

---

### Agent Trait

The core interface that all agents must implement.

```rust
// In agenkit::core
#[async_trait]
pub trait Agent: Send + Sync {
    /// Return the agent's name (used in logging, tracing, and tool wrapping)
    fn name(&self) -> &str;

    /// Process an incoming message and return a response
    async fn process(&self, message: Message) -> Result<Message, AgentError>;

    /// Optional: return agent capabilities (used by orchestrators)
    fn capabilities(&self) -> Vec<String> {
        vec![]
    }

    /// Optional: return a description of what this agent does
    fn description(&self) -> &str {
        ""
    }
}
```

**Bounds:**
- `Send + Sync`: Required for safe use across async tasks and threads
- `#[async_trait]`: Required macro for async methods in traits (from the `async_trait` crate)

**Implementation pattern:**

```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

pub struct MyAgent {
    name: String,
}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let input = message
            .content_as_str()
            .ok_or_else(|| AgentError::InvalidInput("expected text content".to_string()))?;

        let response = format!("Processed: {}", input);
        Ok(Message::assistant(&response))
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text-processing".to_string(), "summarization".to_string()]
    }

    fn description(&self) -> &str {
        "Processes and summarizes text input"
    }
}
```

**Using trait objects:**

```rust
// Dynamic dispatch: store agents of different concrete types
let agents: Vec<Box<dyn Agent>> = vec![
    Box::new(MyAgent::new()),
    Box::new(AnotherAgent::new()),
];

// Shared ownership across async tasks
let shared: Arc<dyn Agent + Send + Sync> = Arc::new(MyAgent::new());
let clone = Arc::clone(&shared);
tokio::spawn(async move { clone.process(msg).await });
```

---

### AgentError

The error type for all agent operations.

```rust
// In agenkit::core
#[derive(Debug, thiserror::Error)]
pub enum AgentError {
    #[error("processing failed: {0}")]
    ProcessingFailed(String),

    #[error("invalid input: {0}")]
    InvalidInput(String),

    #[error("invalid parameters: {0}")]
    InvalidParameters(String),

    #[error("operation timed out")]
    Timeout,

    #[error("rate limit exceeded")]
    RateLimited,

    #[error("circuit breaker open")]
    CircuitBreakerOpen,

    #[error("tool not found: {0}")]
    ToolNotFound(String),

    #[error("tool execution failed: {0}")]
    ToolExecutionFailed(String),

    #[error("network error: {0}")]
    NetworkError(String),

    #[error("serialization error: {0}")]
    SerializationError(String),

    #[error("permission denied: {0}")]
    PermissionDenied(String),

    #[error("content filtered: {0}")]
    ContentFiltered(String),

    #[error("budget exceeded")]
    BudgetExceeded,

    #[error("max iterations reached")]
    MaxIterationsReached,

    #[error("agent not found: {0}")]
    AgentNotFound(String),

    #[error("initialization failed: {0}")]
    InitializationFailed(String),
}
```

**Usage patterns:**

```rust
use agenkit::core::AgentError;

// Creating errors
let err = AgentError::ProcessingFailed("LLM returned empty response".to_string());
let err = AgentError::InvalidInput("message must have text content".to_string());
let err = AgentError::Timeout;

// Matching errors
match result {
    Ok(msg) => handle_success(msg),
    Err(AgentError::Timeout) => retry_or_fail(),
    Err(AgentError::RateLimited) => back_off_and_retry(),
    Err(AgentError::CircuitBreakerOpen) => use_fallback(),
    Err(e) => log_and_propagate(e),
}

// Converting from other errors
impl From<reqwest::Error> for AgentError {
    fn from(e: reqwest::Error) -> Self {
        AgentError::NetworkError(e.to_string())
    }
}
```

---

### Tool Trait

Interface for tools that agents can call.

```rust
// In agenkit::core
#[async_trait]
pub trait Tool: Send + Sync {
    /// The tool's name (used to route tool calls)
    fn name(&self) -> &str;

    /// Human-readable description of what this tool does
    fn description(&self) -> &str;

    /// JSON Schema defining the tool's parameters
    fn parameters(&self) -> HashMap<String, serde_json::Value>;

    /// Execute the tool with the given parameters
    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError>;
}
```

**Example implementation:**

```rust
use agenkit::core::{Tool, ToolResult, AgentError};
use async_trait::async_trait;
use std::collections::HashMap;
use serde_json::json;

pub struct WebSearchTool {
    api_key: String,
}

#[async_trait]
impl Tool for WebSearchTool {
    fn name(&self) -> &str {
        "web_search"
    }

    fn description(&self) -> &str {
        "Search the web for current information"
    }

    fn parameters(&self) -> HashMap<String, serde_json::Value> {
        let mut params = HashMap::new();
        params.insert("query".to_string(), json!({
            "type": "string",
            "description": "The search query",
        }));
        params.insert("num_results".to_string(), json!({
            "type": "integer",
            "description": "Number of results to return (default: 5)",
            "default": 5,
        }));
        params
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let query = params
            .get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| AgentError::InvalidParameters("query is required".to_string()))?;

        let num_results = params
            .get("num_results")
            .and_then(|v| v.as_u64())
            .unwrap_or(5) as usize;

        // Perform search...
        let results = vec![format!("Result for: {}", query)];

        Ok(ToolResult {
            success: true,
            result: results.join("\n"),
            metadata: HashMap::new(),
        })
    }
}
```

---

### ToolResult

The return type from tool execution.

```rust
// In agenkit::core
pub struct ToolResult {
    pub success: bool,
    pub result: String,
    pub metadata: HashMap<String, serde_json::Value>,
}
```

---

## Middleware

Middleware wraps agents to add cross-cutting behavior. All middleware types implement `Agent`.

### RetryDecorator

Retries failed agent calls with exponential backoff.

```rust
// In agenkit::middleware
pub struct RetryDecorator<A: Agent> {
    // ...
}

impl<A: Agent> RetryDecorator<A> {
    /// Create a new retry decorator.
    ///
    /// # Arguments
    /// * `agent` - The inner agent to wrap
    /// * `max_attempts` - Maximum number of total attempts (including the first)
    /// * `initial_delay` - Delay before the first retry (doubles each attempt)
    pub fn new(agent: A, max_attempts: u32, initial_delay: Duration) -> Self;

    /// Set the maximum delay between retries (caps the exponential growth)
    pub fn with_max_delay(self, max_delay: Duration) -> Self;

    /// Only retry specific error variants
    pub fn with_retry_on(self, predicate: impl Fn(&AgentError) -> bool + Send + Sync + 'static) -> Self;
}
```

**Example:**

```rust
use agenkit::middleware::RetryDecorator;
use std::time::Duration;

// Retry up to 3 times with 100ms initial delay (doubles: 100ms, 200ms)
let agent = RetryDecorator::new(base_agent, 3, Duration::from_millis(100));

// With maximum delay cap
let agent = RetryDecorator::new(base_agent, 5, Duration::from_millis(100))
    .with_max_delay(Duration::from_secs(10));

// Only retry on network errors
let agent = RetryDecorator::new(base_agent, 3, Duration::from_millis(100))
    .with_retry_on(|e| matches!(e, AgentError::NetworkError(_)));
```

---

### TimeoutDecorator

Enforces a maximum duration on agent calls.

```rust
// In agenkit::middleware
pub struct TimeoutDecorator<A: Agent> {
    // ...
}

impl<A: Agent> TimeoutDecorator<A> {
    /// Wrap an agent with a timeout.
    ///
    /// Returns AgentError::Timeout if the inner agent doesn't respond in time.
    pub fn new(agent: A, timeout: Duration) -> Self;
}
```

---

### CircuitBreakerDecorator

Opens the circuit when failure rate exceeds threshold, blocking calls until recovery.

```rust
// In agenkit::middleware
pub struct CircuitBreakerDecorator<A: Agent> {
    // ...
}

impl<A: Agent> CircuitBreakerDecorator<A> {
    /// Create a circuit breaker.
    ///
    /// # Arguments
    /// * `agent` - The inner agent
    /// * `failure_threshold` - Number of consecutive failures before opening
    /// * `recovery_timeout` - How long to wait before attempting recovery
    pub fn new(agent: A, failure_threshold: u32, recovery_timeout: Duration) -> Self;

    /// Check the current circuit state
    pub fn state(&self) -> CircuitState;
}

pub enum CircuitState {
    /// Circuit is closed, all calls proceed normally
    Closed,
    /// Circuit is open, calls return CircuitBreakerOpen error immediately
    Open,
    /// Circuit is half-open, one test call is allowed through
    HalfOpen,
}
```

---

### RateLimiterDecorator

Limits the rate of calls to the inner agent.

```rust
// In agenkit::middleware
impl<A: Agent> RateLimiterDecorator<A> {
    /// Limit calls to `max_calls` per `window`.
    pub fn new(agent: A, max_calls: u32, window: Duration) -> Self;
}
```

---

### CachingDecorator

Caches responses to avoid redundant calls for identical inputs.

```rust
// In agenkit::middleware
impl<A: Agent> CachingDecorator<A> {
    /// Cache responses with a TTL.
    pub fn new(agent: A, ttl: Duration) -> Self;

    /// Set maximum cache size (number of entries)
    pub fn with_max_size(self, max_size: usize) -> Self;
}
```

---

### LoggingDecorator

Logs all requests and responses.

```rust
// In agenkit::middleware
impl<A: Agent> LoggingDecorator<A> {
    pub fn new(agent: A) -> Self;
    pub fn with_log_level(self, level: tracing::Level) -> Self;
    pub fn with_include_content(self, include: bool) -> Self;
}
```

---

## Patterns

### SequentialPattern

Process messages through multiple agents in order. Each agent's output becomes the next agent's input.

```rust
// In agenkit::patterns
pub struct SequentialPattern {
    // ...
}

impl SequentialPattern {
    /// Create a sequential pipeline.
    ///
    /// # Errors
    /// Returns an error if the agents list is empty.
    pub fn new(agents: Vec<Box<dyn Agent>>) -> Result<Self, AgentError>;

    /// Add an agent to the end of the pipeline.
    pub fn add_agent(&mut self, agent: Box<dyn Agent>);
}
```

**Data flow:**
```
Input Message → Agent[0] → Agent[1] → ... → Agent[n-1] → Output Message
```

**Example:**

```rust
use agenkit::patterns::SequentialPattern;

let pipeline = SequentialPattern::new(vec![
    Box::new(ExtractAgent::new()),    // Extract key information
    Box::new(AnalyzeAgent::new()),    // Analyze extracted data
    Box::new(FormatAgent::new()),     // Format for output
])?;

let result = pipeline.process(message).await?;
```

---

### ParallelPattern

Send the same message to multiple agents concurrently and aggregate the results.

```rust
// In agenkit::patterns
pub struct ParallelPattern {
    // ...
}

impl ParallelPattern {
    /// Create a parallel executor.
    ///
    /// # Errors
    /// Returns an error if the agents list is empty.
    pub fn new(agents: Vec<Box<dyn Agent>>) -> Result<Self, AgentError>;

    /// Set the aggregation strategy
    pub fn with_aggregator(self, aggregator: Box<dyn Aggregator>) -> Self;
}

pub trait Aggregator: Send + Sync {
    fn aggregate(&self, results: Vec<Message>) -> Result<Message, AgentError>;
}
```

**Data flow:**
```
                 ┌─── Agent[0] ───┐
Input Message ───┤─── Agent[1] ───┼─── Aggregator ─── Output
                 └─── Agent[2] ───┘
```

**Example:**

```rust
use agenkit::patterns::ParallelPattern;

let parallel = ParallelPattern::new(vec![
    Box::new(PerspectiveAgent::new("optimistic")),
    Box::new(PerspectiveAgent::new("pessimistic")),
    Box::new(PerspectiveAgent::new("neutral")),
])?;

let result = parallel.process(message).await?;
// result.content contains all three perspectives aggregated
```

---

### ReflectionAgent

Iterative self-improvement through draft-critique-refine loop.

```rust
// In agenkit::patterns
pub struct ReflectionConfig {
    pub generator: Box<dyn Agent>,
    pub critic: Box<dyn Agent>,
    pub max_iterations: u32,
    pub quality_threshold: f64,       // Stop early if score >= threshold
    pub improvement_threshold: f64,   // Stop if improvement < threshold
    pub critique_format: CritiqueFormat,
    pub verbose: bool,
}

pub enum CritiqueFormat {
    Structured,  // "SCORE: 8/10\nWEAKNESSES: ...\nIMPROVEMENTS: ..."
    Freeform,    // Natural language critique
}

pub struct ReflectionAgent {
    // ...
}

impl ReflectionAgent {
    pub fn new(config: ReflectionConfig) -> Result<Self, AgentError>;
}
```

**Data flow:**
```
Input → Generator → Draft
                       ↓
                    Critic → Critique
                       ↓
                    Generator → Refined Draft
                       ↓
                    (repeat up to max_iterations)
                       ↓
                    Output (best draft)
```

---

### ReActAgent

Reasoning + Acting with explicit thought-action-observation loop.

```rust
// In agenkit::patterns
pub struct ReActAgent {
    // ...
}

impl ReActAgent {
    pub fn new(llm: Box<dyn Agent>, tools: Vec<Box<dyn Tool>>) -> Self;

    /// Set maximum number of think-act-observe cycles
    pub fn with_max_iterations(self, max: u32) -> Self;

    /// Set the system prompt template
    pub fn with_system_prompt(self, prompt: &str) -> Self;
}
```

**Data flow:**
```
Input → Thought → Action → Observation → Thought → ...→ Final Answer
```

---

### PlanningAgent

Decompose complex tasks into steps and execute them.

```rust
// In agenkit::patterns
pub struct PlanningAgent {
    // ...
}

impl PlanningAgent {
    pub fn new(planner: Box<dyn Agent>, executor: Box<dyn Agent>) -> Self;
    pub fn with_max_plan_steps(self, max: u32) -> Self;
    pub fn with_replan_on_failure(self, replan: bool) -> Self;
}
```

---

### TaskAgent

One-shot task execution with full lifecycle management.

```rust
// In agenkit::patterns
pub struct TaskConfig {
    pub description: String,
    pub success_criteria: Vec<String>,
    pub timeout: Duration,
    pub retry_on_failure: bool,
}

pub struct TaskAgent {
    // ...
}

impl TaskAgent {
    pub fn new(inner: Box<dyn Agent>, config: TaskConfig) -> Self;
}
```

---

### ConversationalAgent

Multi-turn dialogue with conversation history management.

```rust
// In agenkit::patterns
pub struct ConversationalAgent {
    // ...
}

impl ConversationalAgent {
    pub fn new(llm: Box<dyn Agent>) -> Self;

    /// Maximum number of past messages to retain
    pub fn with_history_limit(self, limit: usize) -> Self;

    /// Initial system prompt for the conversation
    pub fn with_system_prompt(self, prompt: &str) -> Self;

    /// Attach memory hierarchy for long-term context
    pub fn with_memory(self, memory: MemoryHierarchy) -> Self;

    /// Clear conversation history
    pub fn clear_history(&mut self);

    /// Get current conversation history
    pub fn history(&self) -> &[Message];
}
```

---

### AgentsAsToolsPattern

Wrap specialist agents as tools for a supervisor agent.

```rust
// In agenkit::patterns
pub fn agent_as_tool(
    agent: Box<dyn Agent>,
    tool_name: &str,
    description: &str,
) -> Result<Box<dyn Tool>, AgentError>;

pub struct AgentsAsToolsPattern {
    // ...
}

impl AgentsAsToolsPattern {
    pub fn new(supervisor: Box<dyn Agent>) -> Self;
    pub fn with_specialist(self, agent: Box<dyn Agent>, description: &str) -> Self;
}
```

---

### AutonomousAgent

Goal-directed agent that runs iteratively until the goal is achieved.

```rust
// In agenkit::patterns
pub struct AutonomousAgent {
    // ...
}

impl AutonomousAgent {
    pub fn new(llm: Box<dyn Agent>, tools: Vec<Box<dyn Tool>>) -> Self;
    pub fn with_goal(self, goal: &str) -> Self;
    pub fn with_max_iterations(self, max: u32) -> Self;
    pub fn with_completion_signal(self, signal: &str) -> Self;
}
```

---

### MultiagentOrchestrator

Coordinate multiple specialist agents toward a shared goal.

```rust
// In agenkit::patterns
pub struct MultiagentOrchestrator {
    // ...
}

impl MultiagentOrchestrator {
    pub fn new(coordinator: Box<dyn Agent>) -> Self;
    pub fn with_worker(self, agent: Box<dyn Agent>) -> Self;
    pub fn with_consensus_threshold(self, threshold: f64) -> Self;
    pub fn with_max_rounds(self, max: u32) -> Self;
}
```

---

### MemoryHierarchyAgent

Agent with three-tier memory: working, episodic, and semantic.

```rust
// In agenkit::patterns
pub struct MemoryHierarchyAgent {
    // ...
}

impl MemoryHierarchyAgent {
    pub fn new(llm: Box<dyn Agent>, memory: MemoryHierarchy) -> Self;
}
```

---

## Observability

### TracingMiddleware

Adds OpenTelemetry distributed tracing to any agent.

```rust
// In agenkit::observability
pub struct TracingMiddleware<A: Agent> {
    // ...
}

impl<A: Agent> TracingMiddleware<A> {
    /// Wrap an agent with tracing.
    ///
    /// `service_name` defaults to the agent's name if None.
    pub fn new(agent: A, service_name: Option<&str>) -> Self;

    /// Add custom attributes to all spans
    pub fn with_attribute(self, key: &str, value: &str) -> Self;

    /// Control whether message content is included in spans
    pub fn with_include_content(self, include: bool) -> Self;
}
```

---

### MetricsMiddleware

Collects request counts, durations, and error rates.

```rust
// In agenkit::observability
impl<A: Agent> MetricsMiddleware<A> {
    pub fn new(agent: A) -> Self;
    pub fn with_collector(self, collector: Arc<MetricsCollector>) -> Self;
}
```

---

### MetricsCollector

Accumulates and exports agent metrics.

```rust
// In agenkit::observability
pub struct MetricsCollector {
    // ...
}

impl MetricsCollector {
    pub fn new() -> Self;

    // Counters
    pub fn increment_requests(&self);
    pub fn increment_errors(&self);
    pub fn increment_timeouts(&self);

    // Histograms
    pub fn record_duration(&self, duration: Duration);
    pub fn record_token_count(&self, tokens: u64);

    // Snapshots
    pub fn snapshot(&self) -> MetricsSnapshot;
}

pub struct MetricsSnapshot {
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub total_duration_ms: u64,
    pub avg_duration_ms: f64,
    pub p95_duration_ms: u64,
    pub p99_duration_ms: u64,
}
```

---

### AuditLogger

Compliance-ready audit logging with query API.

```rust
// In agenkit::observability
pub struct AuditLogger {
    // ...
}

impl AuditLogger {
    pub fn new(config: AuditLoggerConfig) -> Result<Self, std::io::Error>;

    pub fn log(&self, event: &AuditEvent) -> Result<(), std::io::Error>;

    pub fn query(&self, filter: AuditFilter) -> Vec<AuditEvent>;
}

pub struct AuditEvent {
    pub event_type: AuditEventType,
    pub severity: AuditSeverity,
    pub message: String,
    pub agent_name: Option<String>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub details: HashMap<String, serde_json::Value>,
}

pub enum AuditEventType {
    AgentStarted,
    AgentCompleted,
    AgentError,
    ToolCalled,
    ToolCompleted,
    RateLimitExceeded,
    SecurityViolation,
}
```

**Initializing the full observability stack:**

```rust
use agenkit::observability::{init_tracing, init_metrics, configure_logging};

// Initialize once at startup
init_tracing("otlp", Some("http://localhost:4317"))?;
init_metrics("otlp", Some("http://localhost:4317"))?;
configure_logging("json", "info")?;
```

---

## Adapters

### OpenAIAgent

```rust
// In agenkit::adapters
impl OpenAIAgent {
    pub fn new(api_key: impl Into<String>, model: &str) -> Self;

    // Builder methods — return Result because values are validated
    pub fn with_temperature(self, temp: f64) -> Result<Self, AgentError>;  // 0.0 - 2.0
    pub fn with_max_tokens(self, tokens: u32) -> Result<Self, AgentError>; // > 0
    pub fn with_top_p(self, top_p: f64) -> Result<Self, AgentError>;       // 0.0 - 1.0
    pub fn with_system_prompt(self, prompt: &str) -> Self;
    pub fn with_base_url(self, url: &str) -> Self;  // For custom endpoints
}
```

---

### AnthropicAgent

```rust
impl AnthropicAgent {
    pub fn new(api_key: impl Into<String>, model: &str) -> Self;

    pub fn with_temperature(self, temp: f64) -> Result<Self, AgentError>;  // 0.0 - 1.0
    pub fn with_max_tokens(self, tokens: u32) -> Result<Self, AgentError>; // > 0
    pub fn with_system_prompt(self, prompt: &str) -> Self;
}
```

---

### OllamaAgent

```rust
impl OllamaAgent {
    /// Create an Ollama agent.
    ///
    /// # Arguments
    /// * `model` - Model name (e.g., "llama3", "mistral", "codellama")
    /// * `base_url` - Ollama server URL (default: "http://localhost:11434")
    pub fn new(model: &str, base_url: &str) -> Self;
    pub fn with_temperature(self, temp: f64) -> Self;
}
```

---

### OpenAICompatibleAgent

For vLLM, llama.cpp, SGLang, and other OpenAI API-compatible servers:

```rust
pub mod providers {
    pub fn vllm(model: &str) -> OpenAICompatibleConfig;
    pub fn llamacpp(model: &str) -> OpenAICompatibleConfig;
    pub fn sglang(model: &str) -> OpenAICompatibleConfig;
    pub fn tensorrt_llm(model: &str) -> OpenAICompatibleConfig;
    pub fn custom(base_url: &str, model: &str) -> OpenAICompatibleConfig;
}

impl OpenAICompatibleAgent {
    pub fn new(config: OpenAICompatibleConfig) -> Self;
}
```

---

## Memory

```rust
// In agenkit::memory
pub struct MemoryHierarchy {
    // ...
}

impl MemoryHierarchy {
    pub fn new(working: WorkingMemory, long_term: LongTermMemory) -> Self;

    pub async fn store(&self, key: &str, value: &str) -> Result<(), AgentError>;
    pub async fn retrieve(&self, key: &str) -> Option<String>;
    pub async fn search(&self, query: &str, limit: usize) -> Vec<MemoryEntry>;
    pub async fn clear_working(&mut self);
}

pub struct WorkingMemory {
    // ...
}

impl WorkingMemory {
    /// Create working memory with a fixed capacity (oldest entries evicted first)
    pub fn with_capacity(capacity: usize) -> Self;
}

pub struct LongTermMemory {
    // ...
}

impl LongTermMemory {
    /// Persistent memory backed by SQLite
    pub fn with_path(path: impl Into<std::path::PathBuf>) -> Self;

    /// In-memory (non-persistent) long-term storage
    pub fn in_memory() -> Self;
}
```

---

## Safety

See [rust_safety.md](rust_safety.md) for the complete safety module documentation.

Quick reference:

```rust
use agenkit::safety::{
    // Middleware types
    InputValidationMiddleware,
    OutputValidationMiddleware,
    PermissionMiddleware,
    AnomalyDetectionMiddleware,

    // Configuration
    ContentFilterConfig,
    PromptInjectionConfig,
    SchemaValidatorConfig,
    Sandbox,

    // Roles
    Role,                          // Admin, User, ReadOnly, Restricted

    // Audit
    SecurityAuditLogger,
    SecurityAuditLoggerConfig,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
};
```

---

## Evaluation

```rust
// In agenkit::evaluation
pub struct MetricsCollector {
    // ...
}

impl MetricsCollector {
    pub fn new() -> Self;
    pub fn record_session(&mut self, session: EvaluationSession);
    pub fn accuracy(&self) -> f64;
    pub fn precision(&self) -> f64;
    pub fn recall(&self) -> f64;
    pub fn f1_score(&self) -> f64;
    pub fn report(&self) -> EvaluationReport;
}

pub struct BenchmarkSuite {
    // ...
}

impl BenchmarkSuite {
    pub fn new(agent: Box<dyn Agent>) -> Self;
    pub fn add_scenario(self, scenario: BenchmarkScenario) -> Self;
    pub async fn run(&self) -> BenchmarkResults;
}
```

---

**Version**: v0.75.0
**Last Updated**: March 17, 2026

For the complete source: `agenkit-rust/src/`
For examples: `agenkit-rust/examples/`
