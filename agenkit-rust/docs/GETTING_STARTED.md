# Getting Started with Agenkit-Rust

A practical guide to building AI agents with Rust and Agenkit.

## Table of Contents

- [Installation](#installation)
- [Your First Agent](#your-first-agent)
- [Understanding Messages](#understanding-messages)
- [Async/Await with Tokio](#asyncawait-with-tokio)
- [Error Handling](#error-handling)
- [Ownership Patterns in Agents](#ownership-patterns-in-agents)
- [Adding Middleware](#adding-middleware)
- [Using LLM Adapters](#using-llm-adapters)
- [Common Patterns](#common-patterns)
- [Testing Your Agent](#testing-your-agent)
- [Next Steps](#next-steps)

---

## Installation

### Prerequisites

You need Rust 1.75 or later and Cargo. Check your version:

```bash
rustc --version
# Should output: rustc 1.75.0 or higher

cargo --version
# Should output: cargo 1.75.0 or higher
```

If you don't have Rust installed, use `rustup`:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Adding Agenkit to Your Project

**Option 1: cargo add (Recommended)**

```bash
cargo add agenkit
cargo add tokio --features full
cargo add async-trait
cargo add serde --features derive
cargo add serde_json
```

**Option 2: Edit Cargo.toml directly**

```toml
[dependencies]
agenkit = "0.75"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Optional: for LLM providers
reqwest = { version = "0.11", features = ["json"] }

# Optional: for observability
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
opentelemetry = "0.21"
```

### Building Your Project

```bash
cargo build
```

Cargo resolves all dependencies automatically. For a release build:

```bash
cargo build --release
```

### Building from Source

Clone the repository and link locally:

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-rust
cargo build
cargo test  # Verify everything works
```

To use the local version in your project, add to `Cargo.toml`:

```toml
[dependencies]
agenkit = { path = "../agenkit/agenkit-rust" }
```

---

## Your First Agent

Let's build a simple echo agent that responds to messages.

### Step 1: Create the Project

```bash
cargo new my-first-agent
cd my-first-agent
cargo add agenkit tokio async-trait
```

Edit `Cargo.toml` to add the tokio features:

```toml
[dependencies]
agenkit = "0.75"
tokio = { version = "1", features = ["full"] }
async-trait = "0.1"
```

### Step 2: Write the Agent

Replace `src/main.rs` with:

```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

// Define your agent struct
struct EchoAgent {
    name: String,
}

impl EchoAgent {
    fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

// Implement the Agent trait
#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let user_text = message.content_as_str().unwrap_or("(empty)");
        let response_text = format!("Echo: {}", user_text);

        Ok(Message::with_text("assistant", &response_text))
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let agent = EchoAgent::new("echo-agent");

    // Create a user message
    let message = Message::with_text("user", "Hello, agent!");

    println!("User: {}", message.content_as_str().unwrap_or(""));

    // Process the message
    let response = agent.process(message).await?;
    println!("Agent: {}", response.content_as_str().unwrap_or(""));
    // Output: Agent: Echo: Hello, agent!

    Ok(())
}
```

### Step 3: Run It

```bash
cargo run
```

Expected output:
```
User: Hello, agent!
Agent: Echo: Hello, agent!
```

---

## Understanding Messages

`Message` is the fundamental unit of communication in Agenkit. Every interaction between agents, users, and tools goes through `Message` values.

### Message Structure

```rust
use agenkit::core::Message;
use serde_json::json;

// Text messages
let user_msg = Message::with_text("user", "What is the weather?");
let assistant_msg = Message::with_text("assistant", "I need to check that.");
let system_msg = Message::with_text("system", "You are a helpful assistant.");

// Messages with metadata
let tracked_msg = Message::with_text("user", "Hello!")
    .with_metadata("session_id", json!("abc-123"))
    .with_metadata("user_id", json!(42))
    .with_metadata("timestamp", json!(1710000000));
```

### Roles

The `role` field identifies who sent the message:

| Role | Purpose |
|------|---------|
| `"user"` | Messages from the human user |
| `"assistant"` | Messages from the AI agent |
| `"system"` | System instructions/context |
| `"tool"` | Results from tool executions |

### Convenience Constructors

```rust
// These all create the same structure with different roles
let user = Message::user("Hello");
let assistant = Message::assistant("Hi there!");
let system = Message::system("You are helpful.");
```

### Accessing Content

```rust
let msg = Message::with_text("user", "Some content");

// Safe access returns Option<&str>
if let Some(text) = msg.content_as_str() {
    println!("Content: {}", text);
}

// With a default
let text = msg.content_as_str().unwrap_or("(no content)");

// Accessing metadata
if let Some(session) = msg.get_metadata("session_id") {
    println!("Session: {}", session);
}
```

### Structured Content

For tool calls and complex data:

```rust
use agenkit::core::Message;
use serde_json::json;

let tool_result = Message::with_structured(
    "tool",
    json!({
        "tool_name": "search",
        "result": "Paris weather: 15°C, partly cloudy",
        "success": true
    }),
);
```

### Message Immutability

`Message` values in Rust are immutable by default. Use `with_*` builder methods to create modified copies:

```rust
let base = Message::with_text("user", "Hello");

// Create a new message with added metadata (base is unchanged)
let with_session = base.with_metadata("session_id", json!("xyz-789"));
```

---

## Async/Await with Tokio

Agenkit is built on Tokio, Rust's async runtime. Understanding async patterns is essential.

### The `#[async_trait]` Macro

Rust's trait system doesn't natively support async methods. The `async_trait` crate provides this:

```rust
use async_trait::async_trait;
use agenkit::core::{Agent, AgentError, Message};

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"
    }

    // The async keyword works here thanks to #[async_trait]
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // await async operations
        let result = some_async_operation().await?;
        Ok(Message::with_text("assistant", &result))
    }
}
```

### Tokio Runtime Setup

Every async program needs a Tokio runtime entry point:

```rust
// Standard setup for binary applications
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Your async code here
    Ok(())
}

// For tests
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_agent_processes_message() {
        let agent = MyAgent::new();
        let msg = Message::with_text("user", "test");
        let result = agent.process(msg).await;
        assert!(result.is_ok());
    }
}
```

### Concurrent Operations

Use `tokio::join!` for running multiple agents concurrently:

```rust
use tokio;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_a = MyAgent::new("a");
    let agent_b = MyAgent::new("b");
    let message = Message::with_text("user", "Hello");

    // Run both agents concurrently
    let (result_a, result_b) = tokio::join!(
        agent_a.process(message.clone()),
        agent_b.process(message.clone()),
    );

    println!("A: {:?}", result_a?);
    println!("B: {:?}", result_b?);

    Ok(())
}
```

For a dynamic number of tasks:

```rust
use futures::future::join_all;

async fn run_all_agents(
    agents: Vec<Box<dyn Agent>>,
    message: Message,
) -> Vec<Result<Message, AgentError>> {
    let futures: Vec<_> = agents
        .iter()
        .map(|agent| agent.process(message.clone()))
        .collect();

    join_all(futures).await
}
```

### Timeouts

Use `tokio::time::timeout` to enforce time limits:

```rust
use tokio::time::{timeout, Duration};
use agenkit::core::AgentError;

async fn process_with_timeout(
    agent: &impl Agent,
    message: Message,
    secs: u64,
) -> Result<Message, AgentError> {
    timeout(Duration::from_secs(secs), agent.process(message))
        .await
        .map_err(|_| AgentError::Timeout)?
}
```

---

## Error Handling

Agenkit uses `AgentError` for all agent-level errors. Rust's `Result<T, E>` type makes error handling explicit and safe.

### AgentError Variants

```rust
use agenkit::core::AgentError;

// All error variants you may encounter
match agent.process(msg).await {
    Ok(response) => println!("Success: {:?}", response),
    Err(AgentError::ProcessingFailed(msg)) => eprintln!("Processing error: {}", msg),
    Err(AgentError::InvalidInput(msg)) => eprintln!("Bad input: {}", msg),
    Err(AgentError::Timeout) => eprintln!("Operation timed out"),
    Err(AgentError::RateLimited) => eprintln!("Rate limit exceeded"),
    Err(AgentError::ToolNotFound(name)) => eprintln!("Tool not found: {}", name),
    Err(AgentError::NetworkError(msg)) => eprintln!("Network error: {}", msg),
    Err(AgentError::SerializationError(msg)) => eprintln!("Serialization error: {}", msg),
    Err(e) => eprintln!("Unknown error: {}", e),
}
```

### The `?` Operator

Propagate errors up the call stack cleanly:

```rust
#[async_trait]
impl Agent for PipelineAgent {
    fn name(&self) -> &str { "pipeline" }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Each ? propagates the error if it occurs
        let validated = self.validator.process(message).await?;
        let enriched = self.enricher.process(validated).await?;
        let formatted = self.formatter.process(enriched).await?;
        Ok(formatted)
    }
}
```

### Creating Custom Errors

Convert from other error types using `From`:

```rust
use agenkit::core::AgentError;

impl From<reqwest::Error> for AgentError {
    fn from(e: reqwest::Error) -> Self {
        AgentError::NetworkError(e.to_string())
    }
}

impl From<serde_json::Error> for AgentError {
    fn from(e: serde_json::Error) -> Self {
        AgentError::SerializationError(e.to_string())
    }
}

// Now you can use ? with these error types
async fn fetch_and_parse(url: &str) -> Result<serde_json::Value, AgentError> {
    let body = reqwest::get(url).await?.text().await?;  // reqwest::Error -> AgentError
    let json: serde_json::Value = serde_json::from_str(&body)?;  // serde_json::Error -> AgentError
    Ok(json)
}
```

### Error Context with `map_err`

Add context to errors:

```rust
async fn process(&self, message: Message) -> Result<Message, AgentError> {
    let text = message
        .content_as_str()
        .ok_or_else(|| AgentError::InvalidInput("message has no text content".to_string()))?;

    let result = self.llm.complete(text).await
        .map_err(|e| AgentError::ProcessingFailed(format!("LLM call failed: {}", e)))?;

    Ok(Message::with_text("assistant", &result))
}
```

---

## Ownership Patterns in Agents

Rust's ownership system shapes how you design agents. These patterns will appear throughout the codebase.

### Owned vs. Borrowed Data

Agents typically own their dependencies:

```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

// Agents own their internal state
struct SummarizationAgent {
    model_name: String,       // Owned String
    max_tokens: usize,        // Copied primitive
    system_prompt: String,    // Owned String
}

impl SummarizationAgent {
    fn new(model_name: impl Into<String>) -> Self {
        Self {
            model_name: model_name.into(),
            max_tokens: 1024,
            system_prompt: "Summarize the following text concisely.".to_string(),
        }
    }
}

#[async_trait]
impl Agent for SummarizationAgent {
    fn name(&self) -> &str {
        &self.model_name  // Borrow from self
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // message is owned by this function frame
        let text = message.content_as_str().unwrap_or("").to_string();
        let prompt = format!("{}\n\n{}", self.system_prompt, text);
        // process prompt...
        Ok(Message::with_text("assistant", &prompt))
    }
}
```

### Sharing Agents with Arc

When you need to share an agent across async tasks:

```rust
use std::sync::Arc;
use tokio;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Wrap in Arc for shared ownership
    let agent = Arc::new(MyAgent::new());

    // Clone the Arc (cheap — just increments reference count)
    let agent_clone = Arc::clone(&agent);

    // Spawn a task that uses the agent
    let handle = tokio::spawn(async move {
        let msg = Message::with_text("user", "Hello from task");
        agent_clone.process(msg).await
    });

    // Use original in main task
    let msg = Message::with_text("user", "Hello from main");
    let result = agent.process(msg).await?;
    let task_result = handle.await??;

    println!("Main: {:?}", result);
    println!("Task: {:?}", task_result);

    Ok(())
}
```

### Mutable State in Agents

For agents with mutable state (counters, caches), use `tokio::sync::Mutex` or `RwLock`:

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

struct StatefulAgent {
    name: String,
    call_count: Arc<Mutex<u64>>,
    cache: Arc<Mutex<std::collections::HashMap<String, String>>>,
}

impl StatefulAgent {
    fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            call_count: Arc::new(Mutex::new(0)),
            cache: Arc::new(Mutex::new(std::collections::HashMap::new())),
        }
    }
}

#[async_trait]
impl Agent for StatefulAgent {
    fn name(&self) -> &str { &self.name }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Increment counter
        {
            let mut count = self.call_count.lock().await;
            *count += 1;
        }

        let text = message.content_as_str().unwrap_or("").to_string();

        // Check cache
        {
            let cache = self.cache.lock().await;
            if let Some(cached) = cache.get(&text) {
                return Ok(Message::with_text("assistant", cached));
            }
        }

        // Compute result
        let result = format!("Response to: {}", text);

        // Store in cache
        {
            let mut cache = self.cache.lock().await;
            cache.insert(text, result.clone());
        }

        Ok(Message::with_text("assistant", &result))
    }
}
```

### Trait Objects for Dynamic Dispatch

When you need to store different agent types in a collection:

```rust
use std::sync::Arc;
use agenkit::core::Agent;

struct AgentRegistry {
    agents: Vec<Arc<dyn Agent + Send + Sync>>,
}

impl AgentRegistry {
    fn new() -> Self {
        Self { agents: Vec::new() }
    }

    fn register(&mut self, agent: Arc<dyn Agent + Send + Sync>) {
        self.agents.push(agent);
    }

    async fn dispatch(&self, message: Message, agent_name: &str) -> Option<Result<Message, AgentError>> {
        for agent in &self.agents {
            if agent.name() == agent_name {
                return Some(agent.process(message).await);
            }
        }
        None
    }
}
```

---

## Adding Middleware

Middleware wraps agents to add cross-cutting concerns like retry logic, timeouts, and circuit breakers.

### Retry Decorator

Automatically retry failed requests:

```rust
use agenkit::middleware::RetryDecorator;
use std::time::Duration;

let base_agent = MyAgent::new();

let agent = RetryDecorator::new(
    base_agent,
    3,                               // max_attempts
    Duration::from_millis(100),      // initial_delay (doubles each attempt)
);

// The agent will now retry up to 3 times on failure
let response = agent.process(message).await?;
```

### Timeout Decorator

Enforce a maximum processing time:

```rust
use agenkit::middleware::TimeoutDecorator;
use std::time::Duration;

let agent = TimeoutDecorator::new(
    base_agent,
    Duration::from_secs(10),  // timeout
);
```

### Circuit Breaker

Stop calling a failing service automatically:

```rust
use agenkit::middleware::CircuitBreakerDecorator;
use std::time::Duration;

let agent = CircuitBreakerDecorator::new(
    base_agent,
    5,                           // failure_threshold
    Duration::from_secs(30),     // recovery_timeout
);
```

### Composing Middleware

Layer middleware using wrapping:

```rust
use agenkit::middleware::{RetryDecorator, CircuitBreakerDecorator, TimeoutDecorator};
use agenkit::observability::{TracingMiddleware, MetricsMiddleware};
use std::time::Duration;

// Build from innermost to outermost
let agent = MyAgent::new();

// Add retry logic
let agent = RetryDecorator::new(agent, 3, Duration::from_millis(100));

// Add circuit breaker
let agent = CircuitBreakerDecorator::new(agent, 5, Duration::from_secs(30));

// Add timeout
let agent = TimeoutDecorator::new(agent, Duration::from_secs(10));

// Add observability (outermost — traces everything)
let agent = TracingMiddleware::new(agent, None);
let agent = MetricsMiddleware::new(agent);

// Now all calls go through the full stack
let response = agent.process(message).await?;
```

The middleware stack (outermost first):
```
MetricsMiddleware
  └─ TracingMiddleware
       └─ TimeoutDecorator
            └─ CircuitBreakerDecorator
                 └─ RetryDecorator
                      └─ MyAgent
```

---

## Using LLM Adapters

Agenkit provides adapters for popular LLM providers. Each adapter implements the `Agent` trait.

### OpenAI

```rust
use agenkit::adapters::OpenAIAgent;
use agenkit::core::{Agent, Message};
use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent = OpenAIAgent::new(
        env::var("OPENAI_API_KEY")?,
        "gpt-4-turbo",
    )
    .with_temperature(0.7)?
    .with_max_tokens(1024)?;

    let message = Message::with_text("user", "Explain Rust ownership in 3 sentences.");
    let response = agent.process(message).await?;
    println!("{}", response.content_as_str().unwrap_or(""));

    Ok(())
}
```

### Anthropic

```rust
use agenkit::adapters::AnthropicAgent;

let agent = AnthropicAgent::new(
    env::var("ANTHROPIC_API_KEY")?,
    "claude-3-5-sonnet-20241022",
)
.with_temperature(1.0)?
.with_max_tokens(4096)?;
```

### OpenAI-Compatible (vLLM, llama.cpp, etc.)

```rust
use agenkit::adapters::openai_compatible::{providers, OpenAICompatibleAgent};

// Local vLLM deployment
let config = providers::vllm("meta-llama/Llama-2-7b-chat-hf");
let agent = OpenAICompatibleAgent::new(config);

// llama.cpp server
let config = providers::llamacpp("llama-2-7b-chat");
let agent = OpenAICompatibleAgent::new(config);

// Generic OpenAI-compatible endpoint
let config = providers::custom("http://localhost:8080", "my-model");
let agent = OpenAICompatibleAgent::new(config);
```

Supported providers: vLLM, llama.cpp, SGLang, TensorRT-LLM, OpenLLM, MLC LLM, TGI, Inferflow

### Ollama (Local Models)

```rust
use agenkit::adapters::OllamaAgent;

let agent = OllamaAgent::new("llama3", "http://localhost:11434");

let message = Message::with_text("user", "Hello from Ollama!");
let response = agent.process(message).await?;
```

---

## Common Patterns

Agenkit provides 11 production-ready patterns. Here are three to get started.

### Sequential Pattern

Process messages through multiple agents in order:

```rust
use agenkit::patterns::SequentialPattern;

let pipeline = SequentialPattern::new(vec![
    Box::new(ResearchAgent::new()),
    Box::new(AnalysisAgent::new()),
    Box::new(FormatterAgent::new()),
])?;

let message = Message::with_text("user", "Analyze the impact of LLMs on software development");
let result = pipeline.process(message).await?;
// Result has passed through all three agents
```

### Reflection Pattern

Self-improving iterative refinement:

```rust
use agenkit::patterns::{ReflectionAgent, ReflectionConfig, CritiqueFormat};

let config = ReflectionConfig {
    generator: Box::new(DraftAgent::new()),
    critic: Box::new(CritiqueAgent::new()),
    max_iterations: 3,
    quality_threshold: 0.9,
    improvement_threshold: 0.05,
    critique_format: CritiqueFormat::Structured,
    verbose: false,
};

let agent = ReflectionAgent::new(config)?;
let message = Message::with_text("user", "Write a blog post about async Rust");
let refined = agent.process(message).await?;
```

### ReAct Pattern

Reasoning with tool use:

```rust
use agenkit::patterns::ReActAgent;
use agenkit::core::Tool;

let tools: Vec<Box<dyn Tool>> = vec![
    Box::new(SearchTool::new()),
    Box::new(CalculatorTool::new()),
];

let agent = ReActAgent::new(llm, tools).with_max_iterations(5);

let message = Message::with_text("user", "What is 15% of the GDP of France?");
let response = agent.process(message).await?;
```

See [PATTERNS.md](PATTERNS.md) for all 11 patterns with full examples and trade-off analysis.

---

## Testing Your Agent

### Unit Tests

Test individual agents with `#[tokio::test]`:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use agenkit::core::{Agent, Message};

    #[tokio::test]
    async fn test_echo_agent_returns_input() {
        let agent = EchoAgent::new("test-echo");
        let message = Message::with_text("user", "Hello!");
        let response = agent.process(message).await.expect("should succeed");

        assert_eq!(
            response.content_as_str().unwrap_or(""),
            "Echo: Hello!"
        );
        assert_eq!(response.role, "assistant");
    }

    #[tokio::test]
    async fn test_echo_agent_handles_empty_input() {
        let agent = EchoAgent::new("test-echo");
        let message = Message::with_text("user", "");
        let response = agent.process(message).await.expect("should succeed");

        assert!(response.content_as_str().is_some());
    }
}
```

### Mock Agents for Integration Tests

Use a mock agent to test patterns without real LLM calls:

```rust
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

struct MockAgent {
    responses: Vec<String>,
    call_index: std::sync::atomic::AtomicUsize,
}

impl MockAgent {
    fn new(responses: Vec<&str>) -> Self {
        Self {
            responses: responses.iter().map(|s| s.to_string()).collect(),
            call_index: std::sync::atomic::AtomicUsize::new(0),
        }
    }
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str { "mock" }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let idx = self.call_index.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        let response = &self.responses[idx % self.responses.len()];
        Ok(Message::with_text("assistant", response))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use agenkit::patterns::SequentialPattern;

    #[tokio::test]
    async fn test_sequential_pattern_chains_agents() {
        let agent_a = MockAgent::new(vec!["Step 1 complete"]);
        let agent_b = MockAgent::new(vec!["Step 2 complete"]);

        let pipeline = SequentialPattern::new(vec![
            Box::new(agent_a),
            Box::new(agent_b),
        ]).expect("pipeline should construct");

        let message = Message::with_text("user", "Start pipeline");
        let result = pipeline.process(message).await.expect("should succeed");

        assert_eq!(result.content_as_str().unwrap_or(""), "Step 2 complete");
    }
}
```

### Running Tests

```bash
# Run all tests
cargo test

# Run tests in a specific file
cargo test --test my_agent_test

# Run a specific test
cargo test test_echo_agent_returns_input

# Run with output visible
cargo test -- --nocapture

# Run tests in release mode (faster)
cargo test --release
```

---

## Next Steps

1. **Explore Patterns**: Read [PATTERNS.md](PATTERNS.md) for all 11 patterns with Rust examples
2. **API Reference**: See [API.md](API.md) for complete type and trait documentation
3. **Observability**: Read [OBSERVABILITY.md](OBSERVABILITY.md) for tracing and metrics setup
4. **Testing**: Read [TESTING_FRAMEWORK.md](TESTING_FRAMEWORK.md) for test utilities and patterns
5. **Migration**: Coming from another language? See [MIGRATION.md](MIGRATION.md)
6. **Safety**: Read [rust_safety.md](rust_safety.md) for the security middleware guide
7. **Examples**: Run the examples in `agenkit-rust/examples/`

```bash
# Try the examples
cargo run --example echo_agent
cargo run --example reflection_pattern
cargo run --example react_pattern
cargo run --example observability_basic
```

---

## Quick Reference

```rust
// Core imports
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

// Middleware
use agenkit::middleware::{
    RetryDecorator,
    TimeoutDecorator,
    CircuitBreakerDecorator,
    RateLimiterDecorator,
};

// LLM adapters
use agenkit::adapters::{OpenAIAgent, AnthropicAgent, OllamaAgent};
use agenkit::adapters::openai_compatible::{providers, OpenAICompatibleAgent};

// Patterns
use agenkit::patterns::{
    SequentialPattern,
    ParallelPattern,
    ReflectionAgent,
    ReActAgent,
    PlanningAgent,
    ConversationalAgent,
    TaskAgent,
    AutonomousAgent,
    MultiagentOrchestrator,
    MemoryHierarchyAgent,
    AgentsAsToolsPattern,
};

// Observability
use agenkit::observability::{TracingMiddleware, MetricsMiddleware, init_tracing};

// Safety
use agenkit::safety::{InputValidationMiddleware, OutputValidationMiddleware, PermissionMiddleware};

// Memory
use agenkit::memory::{MemoryHierarchy, WorkingMemory, LongTermMemory};
```

---

**Version**: v0.75.0
**Last Updated**: March 17, 2026
**Rust Edition**: 2021 (Rust 1.75+)

For help: Open an issue at https://github.com/scttfrdmn/agenkit/issues
