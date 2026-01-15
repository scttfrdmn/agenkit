# Getting Started with Agenkit - Rust

**Complete guide to building high-performance, memory-safe AI agents with Agenkit in Rust**

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

- Rust 1.70 or higher (install via [rustup](https://rustup.rs/))
- Cargo (comes with Rust)

### Create New Project

```bash
cargo new my-agent
cd my-agent
```

### Add Agenkit Dependency

Edit `Cargo.toml`:

```toml
[package]
name = "my-agent"
version = "0.1.0"
edition = "2021"

[dependencies]
agenkit = "0.46"
tokio = { version = "1.35", features = ["full"] }
```

### Verify Installation

```bash
cargo build
# Should compile successfully
```

---

## Your First Agent

Let's create a simple agent that processes messages:

### Step 1: Create Your Agent

Create `src/agent.rs`:

```rust
use agenkit::core::{Agent, Message};
use async_trait::async_trait;
use std::error::Error;

/// A simple agent that greets users
pub struct GreetingAgent;

#[async_trait]
impl Agent for GreetingAgent {
    fn name(&self) -> &str {
        "greeting-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        let user_message = message.content.to_string();

        Ok(Message {
            role: "assistant".to_string(),
            content: format!("Hello! You said: '{}'. How can I help you today?", user_message),
            ..Default::default()
        })
    }
}
```

### Step 2: Use Your Agent

Edit `src/main.rs`:

```rust
mod agent;

use agenkit::core::{Agent, Message};
use agent::GreetingAgent;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Create agent instance
    let agent = GreetingAgent;

    // Create a user message
    let user_msg = Message {
        role: "user".to_string(),
        content: "Hi there!".into(),
        ..Default::default()
    };

    // Process the message
    let response = agent.process(user_msg).await?;

    // Print the response
    println!("{}: {}", agent.name(), response.content);

    Ok(())
}
```

### Step 3: Run It

```bash
cargo run
# Output: greeting-agent: Hello! You said: 'Hi there!'. How can I help you today?
```

**🎉 Congratulations!** You've created your first Agenkit agent in Rust.

---

## Core Concepts

### The Agent Trait

Every agent in Agenkit implements the `Agent` trait:

```rust
use async_trait::async_trait;

#[async_trait]
pub trait Agent: Send + Sync {
    fn name(&self) -> &str;
    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>>;
}
```

**Key points**:
- `#[async_trait]` macro enables async trait methods
- `Send + Sync` allows agents to be used across threads
- Return `Result` for explicit error handling

### Messages

Messages are the unit of communication:

```rust
use agenkit::core::Message;
use serde_json::json;

// Create a message
let msg = Message {
    role: "user".to_string(),
    content: json!("Hello!"),
    metadata: Some(json!({
        "source": "web"
    })),
    ..Default::default()
};

// Access message properties
println!("Role: {}", msg.role);
println!("Content: {}", msg.content);
if let Some(metadata) = msg.metadata {
    println!("Metadata: {}", metadata);
}
```

### Ownership and Borrowing

Rust's ownership system ensures memory safety:

```rust
use agenkit::core::{Agent, Message};

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"  // String literal has 'static lifetime
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        // message is owned by this function
        let content = message.content.clone();  // Clone if you need to keep original

        // Transform the message
        let response = self.generate_response(&content).await?;

        // Return new message (original message is moved/consumed)
        Ok(Message {
            role: "assistant".to_string(),
            content: response.into(),
            ..Default::default()
        })
    }
}
```

### Error Handling with Result

Rust uses `Result` for error handling:

```rust
use std::error::Error;
use std::fmt;

#[derive(Debug)]
struct ProcessingError {
    message: String,
}

impl fmt::Display for ProcessingError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "Processing error: {}", self.message)
    }
}

impl Error for ProcessingError {}

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        // Validate input
        if message.content.to_string().is_empty() {
            return Err(Box::new(ProcessingError {
                message: "Empty message content".to_string(),
            }));
        }

        // Process with ? operator for error propagation
        let result = self.process_internal(&message).await?;

        Ok(result)
    }
}
```

### Tools

Tools let agents take actions:

```rust
use agenkit::core::{Tool, ToolResult};
use async_trait::async_trait;
use serde_json::{json, Value};

pub struct CalculatorTool;

#[async_trait]
impl Tool for CalculatorTool {
    fn name(&self) -> &str {
        "calculator"
    }

    fn description(&self) -> &str {
        "Performs basic arithmetic operations"
    }

    async fn execute(&self, params: Value) -> Result<ToolResult, Box<dyn Error + Send + Sync>> {
        let operation = params["operation"].as_str()
            .ok_or("Missing operation")?;
        let a = params["a"].as_f64()
            .ok_or("Missing parameter a")?;
        let b = params["b"].as_f64()
            .ok_or("Missing parameter b")?;

        let result = match operation {
            "add" => a + b,
            "multiply" => a * b,
            _ => return Err(format!("Unknown operation: {}", operation).into()),
        };

        Ok(ToolResult {
            output: Some(json!(result)),
            error: None,
        })
    }
}
```

---

## Using Patterns

Agenkit includes 18 pre-built patterns for common agent architectures.

### Reflection Pattern

Iteratively improve outputs through self-critique:

```rust
use agenkit::patterns::{ReflectionAgent, ReflectionConfig};
use std::sync::Arc;

// Configure reflection
let config = ReflectionConfig {
    max_iterations: 3,
    quality_threshold: Some(0.8),
    stop_on_repeat: true,
    ..Default::default()
};

// Create reflection agent
let generator = Arc::new(GeneratorAgent::new());
let critic = Arc::new(CriticAgent::new());

let agent = ReflectionAgent::new(generator, critic, config);

// Use it
let response = agent.process(Message {
    role: "user".to_string(),
    content: "Write a haiku about coding".into(),
    ..Default::default()
}).await?;

// Response includes iteration metadata
if let Some(metadata) = response.metadata {
    println!("Iterations: {}", metadata["iterations"]);
    println!("Quality: {}", metadata["final_quality_score"]);
}
```

### Sequential Pattern

Chain multiple agents in sequence:

```rust
use agenkit::patterns::SequentialPattern;
use std::sync::Arc;

// Create a pipeline: research → summarize → format
let pipeline = SequentialPattern::new(vec![
    Arc::new(ResearchAgent::new()),
    Arc::new(SummaryAgent::new()),
    Arc::new(FormatterAgent::new()),
]);

// Input flows through each agent in order
let response = pipeline.process(Message {
    role: "user".to_string(),
    content: "Research quantum computing".into(),
    ..Default::default()
}).await?;
```

### Parallel Pattern

Run multiple agents concurrently and aggregate results:

```rust
use agenkit::patterns::{ParallelPattern, ParallelConfig, AggregationStrategy};
use std::sync::Arc;

// Configure parallel execution
let config = ParallelConfig {
    agents: vec![
        Arc::new(TechnicalAgent::new()),
        Arc::new(BusinessAgent::new()),
        Arc::new(UserAgent::new()),
    ],
    aggregation: AggregationStrategy::Merge,
    ..Default::default()
};

// Create parallel pattern
let parallel = ParallelPattern::new(config)?;

// All agents process simultaneously (tokio::join!)
let response = parallel.process(Message {
    role: "user".to_string(),
    content: "Analyze this product idea".into(),
    ..Default::default()
}).await?;
```

### ReAct Pattern

Reasoning + Acting with tool use:

```rust
use agenkit::patterns::{ReActAgent, ReActConfig};
use std::sync::Arc;

// Configure ReAct
let config = ReActConfig {
    max_steps: 5,
    tools: vec![
        Arc::new(SearchTool::new()),
        Arc::new(CalculatorTool::new()),
    ],
    ..Default::default()
};

// Create ReAct agent
let agent = ReActAgent::new(
    Arc::new(ReasoningAgent::new()),
    config,
)?;

// Agent will alternate between thinking and acting
let response = agent.process(Message {
    role: "user".to_string(),
    content: "What's the population of Tokyo divided by the population of NYC?".into(),
    ..Default::default()
}).await?;

// Response includes reasoning trace
if let Some(metadata) = response.metadata {
    println!("Steps: {:?}", metadata["steps"]);
    println!("Tool calls: {:?}", metadata["tool_calls"]);
}
```

---

## Adding Middleware

Middleware adds production features without changing your agent code.

### Retry Logic

Automatically retry failed operations:

```rust
use agenkit::middleware::{RetryMiddleware, RetryConfig};
use std::sync::Arc;
use std::time::Duration;

// Configure retries
let config = RetryConfig {
    max_attempts: 3,
    backoff_factor: 2.0,
    initial_delay: Duration::from_secs(1),
    max_delay: Duration::from_secs(30),
    ..Default::default()
};

// Wrap your agent
let resilient_agent = RetryMiddleware::new(
    Arc::new(my_agent),
    config,
);

// Now handles transient failures automatically
let response = resilient_agent.process(message).await?;
```

### Circuit Breaker

Prevent cascading failures:

```rust
use agenkit::middleware::{CircuitBreakerMiddleware, CircuitBreakerConfig};
use std::time::Duration;

// Configure circuit breaker
let config = CircuitBreakerConfig {
    failure_threshold: 5,
    timeout: Duration::from_secs(60),
    success_threshold: 2,
    ..Default::default()
};

// Wrap your agent
let protected_agent = CircuitBreakerMiddleware::new(
    Arc::new(my_agent),
    config,
);

// Fails fast when circuit is open
match protected_agent.process(message).await {
    Ok(response) => println!("Success: {}", response.content),
    Err(e) if e.to_string().contains("Circuit breaker") => {
        println!("Circuit is open - service unavailable");
    }
    Err(e) => return Err(e),
}
```

### Timeout

Set maximum execution time:

```rust
use agenkit::middleware::{TimeoutMiddleware, TimeoutConfig};
use std::time::Duration;

// Configure timeout
let config = TimeoutConfig {
    timeout: Duration::from_secs(30),
    grace_period: Some(Duration::from_secs(5)),
};

// Wrap your agent
let timed_agent = TimeoutMiddleware::new(
    Arc::new(my_agent),
    config,
);

// Will cancel after 30 seconds
match timed_agent.process(message).await {
    Ok(response) => println!("Success: {}", response.content),
    Err(e) if e.to_string().contains("timeout") => {
        println!("Agent took too long to respond");
    }
    Err(e) => return Err(e),
}
```

### Stacking Middleware

Combine multiple middleware layers:

```rust
use agenkit::middleware::*;
use std::sync::Arc;
use std::time::Duration;

// Stack middleware (innermost to outermost)
let agent: Arc<dyn Agent> = Arc::new(my_agent);

let agent = TimeoutMiddleware::new(agent, TimeoutConfig {
    timeout: Duration::from_secs(30),
    ..Default::default()
});

let agent = CircuitBreakerMiddleware::new(Arc::new(agent), CircuitBreakerConfig {
    failure_threshold: 5,
    ..Default::default()
});

let agent = RetryMiddleware::new(Arc::new(agent), RetryConfig {
    max_attempts: 3,
    ..Default::default()
});

// Now has full production resilience
let response = agent.process(message).await?;
```

---

## Working with LLMs

### OpenAI Integration

```rust
use agenkit::adapters::{OpenAIAdapter, OpenAIConfig};
use std::env;

// Create OpenAI agent
let config = OpenAIConfig {
    model: "gpt-4".to_string(),
    api_key: env::var("OPENAI_API_KEY")?,
    ..Default::default()
};

let agent = OpenAIAdapter::new(config)?;

// Use it like any agent
let response = agent.process(Message {
    role: "user".to_string(),
    content: "Explain quantum computing".into(),
    ..Default::default()
}).await?;

println!("{}", response.content);
```

### Anthropic (Claude) Integration

```rust
use agenkit::adapters::{AnthropicAdapter, AnthropicConfig};

// Create Claude agent
let config = AnthropicConfig {
    model: "claude-3-opus-20240229".to_string(),
    api_key: env::var("ANTHROPIC_API_KEY")?,
    ..Default::default()
};

let agent = AnthropicAdapter::new(config)?;

let response = agent.process(Message {
    role: "user".to_string(),
    content: "Write a function to calculate Fibonacci numbers".into(),
    ..Default::default()
}).await?;
```

### Custom LLM Integration

```rust
use agenkit::core::{Agent, Message};
use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;

pub struct CustomLLMAgent {
    api_url: String,
    api_key: String,
    client: Client,
}

impl CustomLLMAgent {
    pub fn new(api_url: String, api_key: String) -> Self {
        Self {
            api_url,
            api_key,
            client: Client::new(),
        }
    }
}

#[async_trait]
impl Agent for CustomLLMAgent {
    fn name(&self) -> &str {
        "custom-llm"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        // Call your LLM API
        let response = self.client
            .post(&self.api_url)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&json!({
                "prompt": message.content
            }))
            .send()
            .await?;

        let result: serde_json::Value = response.json().await?;

        Ok(Message {
            role: "assistant".to_string(),
            content: result["completion"].clone(),
            ..Default::default()
        })
    }
}
```

---

## Testing Your Agents

### Unit Testing

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use agenkit::core::{Agent, Message};

    #[tokio::test]
    async fn test_greeting_agent() {
        let agent = GreetingAgent;

        let response = agent.process(Message {
            role: "user".to_string(),
            content: "Hello".into(),
            ..Default::default()
        }).await.unwrap();

        assert_eq!(response.role, "assistant");
        assert!(response.content.to_string().contains("Hello"));
    }

    #[test]
    fn test_agent_name() {
        let agent = GreetingAgent;
        assert_eq!(agent.name(), "greeting-agent");
    }
}
```

### Integration Testing with Mocks

```rust
use agenkit::core::{Agent, Message};
use async_trait::async_trait;

struct MockAgent {
    response: String,
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str {
        "mock-agent"
    }

    async fn process(&self, _message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        Ok(Message {
            role: "assistant".to_string(),
            content: self.response.clone().into(),
            ..Default::default()
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use agenkit::patterns::SequentialPattern;
    use std::sync::Arc;

    #[tokio::test]
    async fn test_sequential_pattern() {
        let pipeline = SequentialPattern::new(vec![
            Arc::new(MockAgent { response: "Step 1 complete".to_string() }),
            Arc::new(MockAgent { response: "Step 2 complete".to_string() }),
            Arc::new(MockAgent { response: "Step 3 complete".to_string() }),
        ]);

        let response = pipeline.process(Message {
            role: "user".to_string(),
            content: "Start pipeline".into(),
            ..Default::default()
        }).await.unwrap();

        assert!(response.content.to_string().contains("Step 3 complete"));
    }
}
```

### Benchmarking with Criterion

Add to `Cargo.toml`:

```toml
[dev-dependencies]
criterion = { version = "0.5", features = ["async_tokio"] }

[[bench]]
name = "agent_benchmark"
harness = false
```

Create `benches/agent_benchmark.rs`:

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use agenkit::core::{Agent, Message};
use my_agent::GreetingAgent;

fn benchmark_agent(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let agent = GreetingAgent;
    let message = Message {
        role: "user".to_string(),
        content: "Hello".into(),
        ..Default::default()
    };

    c.bench_function("greeting_agent", |b| {
        b.to_async(&rt).iter(|| async {
            agent.process(black_box(message.clone())).await.unwrap()
        });
    });
}

criterion_group!(benches, benchmark_agent);
criterion_main!(benches);
```

Run benchmarks:
```bash
cargo bench
```

---

## Next Steps

### Learn More

- **[Pattern Guide](../patterns/README.md)** - Detailed guide to all 18 patterns
- **[API Reference](https://docs.rs/agenkit)** - Complete API documentation on docs.rs
- **[Best Practices](../best-practices/RUST.md)** - Production deployment tips
- **[Examples](../../agenkit-rust/examples/)** - Working examples

### Performance Optimization

- **[Zero-Copy Patterns](../performance/RUST_ZERO_COPY.md)** - Minimize allocations
- **[Async Best Practices](../performance/RUST_ASYNC.md)** - Tokio optimization
- **[Memory Management](../performance/RUST_MEMORY.md)** - Smart pointers and lifetimes
- **[Profiling Guide](../performance/RUST_PROFILING.md)** - Profile your agents

### Deploy to Production

- **[Docker Deployment](../deployment/DOCKER.md)** - Containerize your agents
- **[Kubernetes Guide](../deployment/KUBERNETES.md)** - Scale with K8s
- **[AWS Lambda](../deployment/AWS_LAMBDA.md)** - Serverless Rust agents
- **[Monitoring & Observability](../observability/README.md)** - Track agent performance

### Migrate from Other Languages

Coming from Python or another language?

- **[Python → Rust Migration](../migration/PYTHON_TO_RUST.md)** - Migrate from Python
- **[Go → Rust Migration](../migration/GO_TO_RUST.md)** - Migrate from Go

---

## Quick Reference

### Installation
```bash
cargo add agenkit tokio --features tokio/full
```

### Minimal Agent
```rust
use agenkit::core::{Agent, Message};
use async_trait::async_trait;

pub struct MyAgent;

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "my-agent"
    }

    async fn process(&self, message: Message) -> Result<Message, Box<dyn Error + Send + Sync>> {
        Ok(Message {
            role: "assistant".to_string(),
            content: "Response".into(),
            ..Default::default()
        })
    }
}
```

### Common Imports
```rust
// Core
use agenkit::core::{Agent, Message, Tool, ToolResult};
use async_trait::async_trait;

// Patterns
use agenkit::patterns::{
    ReflectionAgent, ReActAgent, SequentialPattern,
    ParallelPattern, ConversationalAgent
};

// Middleware
use agenkit::middleware::{
    RetryMiddleware, CircuitBreakerMiddleware,
    TimeoutMiddleware, RateLimiterMiddleware
};

// Adapters
use agenkit::adapters::{OpenAIAdapter, AnthropicAdapter};
```

---

**Ready to build?** Check out the [examples](../../agenkit-rust/examples/) for working code you can run right now.

**Performance tip:** Rust's zero-cost abstractions and ownership system provide maximum performance with memory safety - perfect for production AI agents!
