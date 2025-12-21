# Rust API Reference

Complete API documentation for Agenkit Rust implementation.

## Official Documentation

The Rust implementation maintains complete API documentation using rustdoc, Rust's native documentation tool. Documentation is automatically published to docs.rs with each release.

[📚 View Rust API Documentation on docs.rs](https://docs.rs/agenkit){ .md-button .md-button--primary }

---

## Quick Navigation

### Core Module

[**agenkit::core**](https://docs.rs/agenkit/latest/agenkit/core/index.html) - Core types and traits
```rust
use agenkit::core::{Agent, Message, AgentError};
```

Key types:
- `Agent` - Core trait that all agents implement
- `Message` - Universal message format
- `AgentError` - Error type for agent operations
- `Tool` - Tool trait for agent capabilities
- `IntrospectionResult` - Agent metadata

### Patterns

[**agenkit::patterns**](https://docs.rs/agenkit/latest/agenkit/patterns/index.html) - Agent patterns
```rust
use agenkit::patterns::*;
```

Available patterns:
- `SequentialAgent` - Sequential pipeline
- `ParallelAgent` - Concurrent execution
- `ConditionalAgent` - Conditional routing
- `ReflectionAgent` - Self-critique loop
- `AgentsAsToolsAgent` - Hierarchical delegation
- `OrchestrationAgent` - Complex workflows
- `ReActAgent` - Reasoning + Acting
- `ConversationalAgent` - Multi-turn conversations
- `TaskAgent` - Task decomposition
- `PlanningAgent` - Goal-driven planning
- `AutonomousAgent` - Self-directed behavior
- `MultiagentAgent` - Multi-agent coordination
- `MemoryHierarchyAgent` - Memory management
- `ReasoningWithToolsAgent` - Advanced tool usage

### Reasoning Techniques

[**agenkit::techniques::reasoning**](https://docs.rs/agenkit/latest/agenkit/techniques/reasoning/index.html) - Advanced reasoning
```rust
use agenkit::techniques::reasoning::*;
```

Available techniques:
- `ChainOfThought` - Step-by-step reasoning
- `TreeOfThought` - Multi-path exploration
- `GraphOfThought` - Graph-based reasoning
- `SelfConsistency` - Voting strategy

### LLM Adapters

[**agenkit::adapters**](https://docs.rs/agenkit/latest/agenkit/adapters/index.html) - LLM provider adapters
```rust
use agenkit::adapters::*;
```

Available adapters:
- `OpenAIAdapter` - OpenAI API
- `AnthropicAdapter` - Claude API
- `BedrockAdapter` - AWS Bedrock
- `GeminiAdapter` - Google Gemini
- `OllamaAdapter` - Ollama (local models)

### Transport

[**agenkit::transports**](https://docs.rs/agenkit/latest/agenkit/transports/index.html) - HTTP/WebSocket
```rust
use agenkit::transports::*;
```

Features:
- `HttpServer` - Serve agents over HTTP
- `HttpAgent` - Connect to remote agents
- `HttpTransportConfig` - Configuration

### Evaluation

[**agenkit::evaluation**](https://docs.rs/agenkit/latest/agenkit/evaluation/index.html) - Testing and optimization
```rust
use agenkit::evaluation::*;
```

Features:
- `Recorder` - Session recording
- `BenchmarkRunner` - Performance benchmarks
- `BayesianOptimizer` - Hyperparameter optimization
- `PromptOptimizer` - Prompt optimization
- `ABTesting` - A/B testing framework

---

## Getting Started with Rust

### Installation

```bash
# Add to Cargo.toml
[dependencies]
agenkit = "0.1"

# Or via cargo add
cargo add agenkit
```

### Basic Example

```rust
use agenkit::core::{Agent, Message, AgentError};
use async_trait::async_trait;

struct EchoAgent;

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        "echo-agent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string(), "simple".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");
        Ok(Message::with_text("assistant", format!("Echo: {}", content)))
    }

    fn introspect(&self) -> agenkit::core::IntrospectionResult {
        agenkit::core::IntrospectionResult::default()
            .with_name(self.name())
            .with_capabilities(self.capabilities())
    }
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let agent = EchoAgent;

    let message = Message::with_text("user", "Hello!");
    let response = agent.process(message).await?;

    println!("{}", response.content_as_str().unwrap()); // "Echo: Hello!"
    Ok(())
}
```

---

## Rust-Specific Features

### Async/Await

Rust agents use async/await with tokio runtime:

```rust
use tokio;
use agenkit::core::{Agent, Message};

#[tokio::main]
async fn main() {
    let agent = MyAgent::new();
    let result = agent.process(message).await;
}
```

### Error Handling

Rust uses `Result<T, E>` for explicit error handling:

```rust
use agenkit::core::{Agent, Message, AgentError};

async fn process_with_recovery(
    agent: &impl Agent,
    message: Message
) -> Result<Message, AgentError> {
    match agent.process(message).await {
        Ok(response) => Ok(response),
        Err(e) => {
            eprintln!("Agent failed: {}", e);
            Err(e)
        }
    }
}
```

### Type Safety

Rust's type system prevents common bugs at compile time:

```rust
// This won't compile if types don't match
let message: Message = Message::with_text("user", "Hello");
let response: Result<Message, AgentError> = agent.process(message).await;

// Compiler ensures all error cases are handled
match response {
    Ok(msg) => println!("{}", msg.content_as_str().unwrap()),
    Err(e) => eprintln!("Error: {}", e),
}
```

### Performance

Rust provides exceptional performance with memory safety:

- **Zero-cost abstractions** - No runtime overhead
- **Memory safety** - No garbage collection
- **Fearless concurrency** - Thread-safe by default
- **Compiled binary** - Single executable deployment

---

## Features

Agenkit Rust supports two feature flags:

### Native (Default)

Full-featured build with tokio and HTTP support:

```toml
[dependencies]
agenkit = { version = "0.1", features = ["native"] }
```

Includes:
- tokio async runtime
- reqwest HTTP client
- axum HTTP server
- AWS Bedrock adapter
- All middleware and observability

### WASM

Browser-compatible WebAssembly build:

```toml
[dependencies]
agenkit = { version = "0.1", features = ["wasm"] }
```

Includes:
- wasm-bindgen support
- Browser-compatible async
- Console logging
- Reduced dependencies for smaller bundle size

---

## Documentation Standards

All Rust code follows rustdoc conventions:

### Module Documentation

Every module has a module-level doc comment:

```rust
//! Core interfaces for AI agents.
//!
//! This module provides the fundamental building blocks for creating
//! AI agent systems with a focus on simplicity and composability.

pub mod agent;
pub mod message;
```

### Type Documentation

Every public type is documented:

```rust
/// The core trait that all agents must implement.
///
/// Agents process messages and return responses. They can be composed
/// using patterns for complex behaviors.
///
/// # Example
///
/// ```
/// use agenkit::core::{Agent, Message};
/// use async_trait::async_trait;
///
/// struct EchoAgent;
///
/// #[async_trait]
/// impl Agent for EchoAgent {
///     fn name(&self) -> &str { "echo" }
///
///     async fn process(&self, message: Message) -> Result<Message, AgentError> {
///         Ok(message) // Echo back
///     }
/// }
/// ```
#[async_trait]
pub trait Agent: Send + Sync {
    /// Returns the agent's identifier.
    fn name(&self) -> &str;

    /// Processes a message and returns a response.
    async fn process(&self, message: Message) -> Result<Message, AgentError>;
}
```

---

## Examples

Comprehensive examples are available in the [Rust examples directory](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-rust/examples):

### Basic Examples
- Echo agent
- HTTP transport
- Sequential pipeline
- Parallel execution

### Pattern Examples
- Reflection loop
- Agents-as-Tools
- Orchestration
- ReAct with tools
- Planning agent
- Conversational agent
- Task agent
- Multiagent coordination
- Autonomous behavior
- Memory hierarchy
- Reasoning with tools

### LLM Examples
- OpenAI integration
- Anthropic/Claude integration
- AWS Bedrock integration
- Google Gemini integration
- Ollama (local models)

---

## Testing

Run tests for the Rust implementation:

```bash
cd agenkit-rust

# Run all tests
cargo test

# Run specific test
cargo test test_echo_agent

# Run with output
cargo test -- --nocapture

# Run benchmarks
cargo bench
```

---

## Building Documentation Locally

Generate rustdoc documentation locally:

```bash
cd agenkit-rust

# Generate docs
cargo doc --no-deps

# Generate and open in browser
cargo doc --no-deps --open

# Generate with all features
cargo doc --no-deps --features native

# Generate with private items (for development)
cargo doc --no-deps --document-private-items
```

Documentation will be generated in `target/doc/agenkit/`.

---

## IDE Integration

### RustRover / IntelliJ IDEA + Rust Plugin

Full inline documentation support:

1. Hover over any type/function for documentation
2. Press `Ctrl+Q` (Windows/Linux) or `F1` (Mac) for quick documentation
3. Press `Ctrl+B` to jump to definition
4. View rendered rustdoc in quick documentation popup

### VS Code

Install the rust-analyzer extension:

```bash
code --install-extension rust-lang.rust-analyzer
```

Features:
- Hover for documentation
- Inline type hints
- Auto-completion with docs
- Jump to definition

### vim/neovim

Use rust-analyzer with your LSP client:

```vim
" For vim-lsp
Plug 'prabirshrestha/vim-lsp'
Plug 'mattn/vim-lsp-settings'

" For coc.nvim
Plug 'neoclide/coc.nvim', {'branch': 'release'}
" :CocInstall coc-rust-analyzer
```

---

## Cross-Language Compatibility

Rust agents can communicate with Python, Go, TypeScript, and other language implementations via HTTP:

### Call Python Agent from Rust

```rust
use agenkit::transports::{HttpAgent, HttpTransportConfig};

let config = HttpTransportConfig {
    base_url: "http://localhost:8000".to_string(),
    timeout_secs: 30,
    api_key: None,
};

let python_agent = HttpAgent::new("python-agent", config);
let response = python_agent.process(message).await?;
```

### Expose Rust Agent to Python

```rust
use agenkit::transports::HttpServer;
use agenkit::core::Agent;

let agent = MyAgent::new();
let server = HttpServer::new(agent, "127.0.0.1:8080");

// Serve the agent
server.serve().await?;
```

Python can now call this agent:
```python
from agenkit.transports import HTTPClient

rust_agent = HTTPClient("http://127.0.0.1:8080")
response = await rust_agent.process(message)
```

---

## Contributing

Help improve Rust implementation:

1. **Report issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Improve docs**: Add rustdoc comments to code
3. **Add examples**: [Submit PR](https://github.com/scttfrdmn/agenkit/pulls)

---

## See Also

- **[Python API Reference](python.md)**: Python implementation
- **[Go API Reference](go.md)**: Go implementation
- **[TypeScript API Reference](typescript.md)**: TypeScript implementation
- **[Cross-Language Guide](../guides/cross-language.md)**: Language interop
- **[Rust README](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-rust/README.md)**: Rust-specific features

---

**Last Updated**: December 2025
**Rust Version**: 1.70+
**Agenkit Version**: 0.1.0+
