# Getting Started with Agenkit (Rust)

**Target audience**: Rust developers new to Agenkit
**Time to first agent**: 15-30 minutes
**Prerequisites**: Rust 1.75+

---

## Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
agenkit = "0.50"
tokio = { version = "1", features = ["full"] }

# Optional LLM providers
reqwest = { version = "0.11", features = ["json"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

---

## Your First Agent

Let's create a simple greeting agent:

```rust
use agenkit::{Agent, Message, AgentError};
use async_trait::async_trait;

struct GreetingAgent;

#[async_trait]
impl Agent for GreetingAgent {
    fn name(&self) -> &str {
        "greeting-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let user_content = &message.content;
        let greeting = format!("Hello! You said: {}", user_content);

        let mut metadata = std::collections::HashMap::new();
        metadata.insert("processed_by".to_string(), serde_json::json!(self.name()));

        Ok(Message {
            role: "assistant".to_string(),
            content: greeting,
            metadata,
        })
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let agent = GreetingAgent;

    let message = Message {
        role: "user".to_string(),
        content: "Hi there!".to_string(),
        metadata: std::collections::HashMap::new(),
    };

    let response = agent.process(message).await?;
    println!("Agent: {}", response.content);
    // Output: Agent: Hello! You said: Hi there!

    Ok(())
}
```

Run it:
```bash
cargo run
```

---

## Production-Ready Agent with Middleware

Add resilience with retry, circuit breaker, and timeout middleware:

```rust
use agenkit::{Agent, Message, AgentError};
use agenkit::middleware::{RetryDecorator, CircuitBreakerDecorator, TimeoutDecorator};
use async_trait::async_trait;
use std::time::Duration;
use tokio::time::sleep;

struct ProductionAgent;

#[async_trait]
impl Agent for ProductionAgent {
    fn name(&self) -> &str {
        "production-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulate some processing
        sleep(Duration::from_millis(100)).await;

        let mut metadata = std::collections::HashMap::new();
        metadata.insert("agent".to_string(), serde_json::json!(self.name()));

        Ok(Message {
            role: "assistant".to_string(),
            content: format!("Processed: {}", message.content),
            metadata,
        })
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let base_agent = ProductionAgent;

    // Wrap with middleware (v0.50.0 uses Duration - idiomatic Rust)
    let agent = RetryDecorator::new(
        base_agent,
        3,  // max_attempts
        Duration::from_millis(100),  // initial_delay
    );

    let agent = CircuitBreakerDecorator::new(
        agent,
        5,  // failure_threshold
        Duration::from_secs(30),  // recovery_timeout
    );

    let agent = TimeoutDecorator::new(
        agent,
        Duration::from_secs(5),  // timeout
    );

    let message = Message {
        role: "user".to_string(),
        content: "Hello production!".to_string(),
        metadata: std::collections::HashMap::new(),
    };

    let response = agent.process(message).await?;
    println!("{}", response.content);

    Ok(())
}
```

**Note**: Rust uses `Duration` (idiomatic) instead of milliseconds.

---

## Using LLM Adapters

### OpenAI Example

```rust
use agenkit::{Message, AgentError};
use agenkit::adapters::OpenAILLM;
use std::env;

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // Initialize LLM (validates parameters at construction)
    let llm = OpenAILLM::new(
        env::var("OPENAI_API_KEY").expect("OPENAI_API_KEY not set"),
        "gpt-4-turbo".to_string(),
    )
    .with_temperature(0.7)?    // Validated: 0-2
    .with_max_tokens(1024)?;   // Validated: >0

    // Create conversation
    let messages = vec![
        Message::system("You are a helpful assistant."),
        Message::user("What is Agenkit?"),
    ];

    // Get completion
    let response = llm.complete(&messages).await?;
    println!("{}", response.content);

    // Stream response
    let mut stream = llm.stream(&messages).await?;
    while let Some(result) = stream.next().await {
        match result {
            Ok(chunk) => print!("{}", chunk.content),
            Err(e) => eprintln!("Error: {}", e),
        }
    }

    Ok(())
}
```

### Anthropic Example

```rust
use agenkit::adapters::AnthropicLLM;

let llm = AnthropicLLM::new(
    env::var("ANTHROPIC_API_KEY").expect("ANTHROPIC_API_KEY not set"),
    "claude-3-5-sonnet-20241022".to_string(),
)
.with_temperature(1.0)?
.with_max_tokens(4096)?;
```

**Parameter Validation** (v0.50.0):
- `temperature`: 0.0 - 2.0 (validated via builder pattern)
- `max_tokens`: > 0 (validated via builder pattern)
- `top_p`: 0.0 - 1.0 (validated via builder pattern)

Invalid values return `Result::Err` immediately.

---

## Common Patterns

Agenkit provides **18 core patterns** for building AI agents (see the [Agent Patterns Book](../../agent-patterns-book) for comprehensive details). Here are three essential patterns to get started:

### 1. Reflection Pattern

**One-line**: Iterative self-improvement through draft-critique-refine loop

```rust
use agenkit::{Message, AgentError};
use agenkit::patterns::ReflectionAgent;
use agenkit::adapters::OpenAILLM;

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let llm = OpenAILLM::new(
        env::var("OPENAI_API_KEY")?,
        "gpt-4-turbo".to_string(),
    );

    let agent = ReflectionAgent::new(llm)
        .with_max_iterations(3)
        .with_reflection_prompt("Review and improve this response:");

    let message = Message::user("Explain Rust ownership");
    let response = agent.process(message).await?;
    println!("{}", response.content);

    Ok(())
}
```

### 2. ReAct Pattern

**One-line**: Reasoning + Acting with explicit thought-action-observation loop

```rust
use agenkit::{Message, Tool, ToolResult, AgentError};
use agenkit::patterns::ReActAgent;
use agenkit::adapters::OpenAILLM;
use async_trait::async_trait;
use std::collections::HashMap;

struct SearchTool;

#[async_trait]
impl Tool for SearchTool {
    fn name(&self) -> &str {
        "search"
    }

    fn description(&self) -> &str {
        "Search for information"
    }

    fn parameters(&self) -> HashMap<String, serde_json::Value> {
        let mut params = HashMap::new();
        params.insert(
            "query".to_string(),
            serde_json::json!({
                "type": "string",
                "description": "Search query"
            }),
        );
        params
    }

    async fn execute(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> Result<ToolResult, AgentError> {
        let query = params.get("query")
            .and_then(|v| v.as_str())
            .ok_or(AgentError::InvalidParameters)?;

        // Simulate search
        Ok(ToolResult {
            success: true,
            result: format!("Search results for: {}", query),
        })
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let llm = OpenAILLM::new(
        env::var("OPENAI_API_KEY")?,
        "gpt-4-turbo".to_string(),
    );

    let tools: Vec<Box<dyn Tool>> = vec![Box::new(SearchTool)];

    let agent = ReActAgent::new(llm, tools)
        .with_max_iterations(5);

    let message = Message::user("What's the weather in Paris?");
    let response = agent.process(message).await?;
    println!("{}", response.content);

    Ok(())
}
```

**Note**: Tool signatures use explicit `params: HashMap<String, Value>` (v0.50.0+).

### 3. Sequential Pattern

**One-line**: Execute agents in order, passing outputs between stages

```rust
use agenkit::{Message, AgentError};
use agenkit::patterns::SequentialAgent;

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    // Create agent pipeline
    let agent = SequentialAgent::new(vec![
        Box::new(ResearchAgent),
        Box::new(SummarizerAgent),
        Box::new(EditorAgent),
    ]);

    let message = Message::user("Research AI safety");
    let final_response = agent.process(message).await?;
    println!("{}", final_response.content);

    Ok(())
}
```

**See all 18 patterns**: Refer to the [Agent Patterns Book](../../agent-patterns-book) for complete pattern descriptions, trade-offs, and when to use each pattern.

---

## Observability

### Basic Tracing with OpenTelemetry

```rust
use agenkit::observability::configure_observability;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Configure OpenTelemetry
    let _guard = configure_observability(
        "my-agent-service",
        "jaeger",
        "http://localhost:14268/api/traces",
    )?;

    // Your agent automatically gets:
    // - Span creation for each process() call
    // - W3C Trace Context propagation
    // - LLM call tracing
    // - Error tracking

    Ok(())
}
```

---

## Advanced Features

### 1. Memory Hierarchy

```rust
use agenkit::memory::{MemoryHierarchy, WorkingMemory, LongTermMemory};

let memory = MemoryHierarchy::new(
    WorkingMemory::with_capacity(10),
    LongTermMemory::with_path("./memory.db"),
);

let agent = ConversationalAgent::new(llm).with_memory(memory);
```

### 2. Budget Tracking

```rust
use agenkit::budget::BudgetTracker;

let tracker = BudgetTracker::new(10.0); // $10 USD
let agent = BudgetAwareAgent::new(llm).with_tracker(tracker);
```

### 3. Safety Framework

```rust
use agenkit::safety::{ContentFilter, RateLimiter};
use std::time::Duration;

let agent = SafeAgent::new(llm)
    .with_content_filter(ContentFilter::block_pii())
    .with_rate_limiter(RateLimiter::new(10, Duration::from_secs(30)));
```

---

## Common Pitfalls

### 1. Error Handling

```rust
// Use Result types throughout
async fn process(&self, message: Message) -> Result<Message, AgentError> {
    // Always propagate errors with ?
    let response = llm.complete(&messages).await?;
    Ok(response)
}
```

### 2. Lifetime Management

```rust
// Agent implementations typically don't need lifetimes
#[async_trait]
impl Agent for MyAgent {
    // Borrow when possible
    fn name(&self) -> &str {
        "my-agent"
    }
}
```

### 3. Type Safety

```rust
// Use type-safe enums instead of strings where possible
pub enum Role {
    User,
    Assistant,
    System,
}
```

---

## Next Steps

1. **Explore Patterns**: See the [Agent Patterns Book](../../agent-patterns-book) for all 18 patterns
2. **Read Architecture**: `ARCHITECTURE.md` explains design principles
3. **Check Examples**: `examples/rust/` has production examples
4. **API Reference**: Coming soon in `docs/api-reference/rust/`
5. **Migration Guide**: See `docs/MIGRATION_v0.50.0.md` for breaking changes

---

## Quick Reference

```rust
// Core imports
use agenkit::{Agent, Message, Tool, ToolResult, AgentError};
use async_trait::async_trait;

// Middleware
use agenkit::middleware::{
    RetryDecorator,
    TimeoutDecorator,
    CircuitBreakerDecorator,
    RateLimiterDecorator,
};

// LLM adapters
use agenkit::adapters::{OpenAILLM, AnthropicLLM, OllamaLLM};

// Patterns
use agenkit::patterns::{
    ReflectionAgent,
    ReActAgent,
    SequentialAgent,
    ParallelAgent,
};

// Observability
use agenkit::observability::configure_observability;

// Memory & Safety
use agenkit::memory::MemoryHierarchy;
use agenkit::safety::{ContentFilter, RateLimiter};
```

---

**Version**: v0.50.0
**Last Updated**: January 28, 2026

For help: Open an issue at https://github.com/yourusername/agenkit/issues
