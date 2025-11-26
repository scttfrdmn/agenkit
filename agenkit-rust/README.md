# Agenkit Rust

Minimal, composable interfaces for AI agents in Rust.

## Features

- **Simple**: Minimal `Agent` trait with only 2 required methods
- **Composable**: Easy to wrap and extend agents
- **Type-safe**: Full Rust type safety with async/await
- **Performance**: Built on Tokio for high-performance async I/O
- **Production-ready**: HTTP transport with timeouts, error handling, and tracing

## Quick Start

Add to your `Cargo.toml`:

```toml
[dependencies]
agenkit = "0.1"
tokio = { version = "1.35", features = ["full"] }
async-trait = "0.1"
```

## Core Concepts

### Message

Universal message format for agent communication:

```rust
use agenkit::core::Message;
use serde_json::json;

let msg = Message::with_text("user", "Hello, agent!");
let msg_with_metadata = msg.with_metadata("session_id", json!("abc123"));
```

### Agent

Core trait that all agents must implement:

```rust
use agenkit::core::{Agent, Message, AgentError};
use async_trait::async_trait;

struct EchoAgent;

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        "echo"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        Ok(Message::with_text("assistant", message.content_as_str().unwrap_or("")))
    }
}
```

### HTTP Transport

Expose agents over HTTP or connect to remote agents:

```rust
use agenkit::transports::{HttpServer, HttpAgent, HttpTransportConfig};

// Server
let server = HttpServer::new(agent, "127.0.0.1:8080");
server.serve().await?;

// Client
let config = HttpTransportConfig {
    base_url: "http://localhost:8080".to_string(),
    timeout_secs: 30,
    api_key: None,
};
let client = HttpAgent::new("remote", config);
```

### Agent Patterns

Reusable patterns for composing and orchestrating agents:

**Reflection Pattern** - Iterative self-critique and refinement:

```rust
use agenkit::patterns::{ReflectionAgent, ReflectionConfig, CritiqueFormat};

let config = ReflectionConfig {
    generator,
    critic,
    max_iterations: 5,
    quality_threshold: 0.9,
    improvement_threshold: 0.05,
    critique_format: CritiqueFormat::Structured,
    verbose: false,
};

let agent = ReflectionAgent::new(config)?;
let result = agent.process(message).await?;
```

**Agents-as-Tools Pattern** - Hierarchical agent delegation:

```rust
use agenkit::patterns::agent_as_tool;

// Wrap specialist agents as tools
let code_tool = agent_as_tool(
    code_specialist,
    "code_expert",
    "Expert programmer for code-related tasks",
)?;

// Use with supervisor agents that support tools
```

**Orchestration Patterns** - Sequential and parallel composition:

```rust
use agenkit::patterns::{SequentialPattern, ParallelPattern};

// Sequential: agent1 → agent2 → agent3
let pipeline = SequentialPattern::new(vec![agent1, agent2, agent3])?;

// Parallel: all agents receive same input, results aggregated
let parallel = ParallelPattern::new(vec![agent_a, agent_b, agent_c])?;
```

## Examples

Run the included examples:

```bash
# Echo agent - simple agent that echoes input
cargo run --example echo_agent

# HTTP transport - client/server communication
cargo run --example http_transport

# Reflection pattern - iterative self-critique
cargo run --example reflection_pattern

# Agents as tools - hierarchical delegation
cargo run --example agents_as_tools

# Orchestration - sequential and parallel composition
cargo run --example orchestration
```

## Testing

Run all tests:

```bash
cargo test
```

## Architecture

Agenkit follows a layered architecture:

1. **Core** (`core/`): Message types and Agent trait
2. **Adapters** (`adapters/`): Local agent implementations
3. **Transports** (`transports/`): HTTP, WebSocket, gRPC
4. **Patterns** (`patterns/`): Reflection, Agents-as-Tools, Orchestration
5. **Evaluation** (future): Benchmarking and testing frameworks

## Current Status

✅ **v0.25.0 - Critical Patterns Complete**

**Infrastructure (~982 LOC, 25 tests)**
- Core Agent trait and Message types
- HTTP transport (client and server)
- Full documentation

**Patterns (~1,300 LOC, 19 tests)**
- Reflection: Iterative self-critique with configurable stopping conditions
- Agents-as-Tools: Hierarchical delegation through tool wrapping
- Sequential Orchestration: Pipeline composition
- Parallel Orchestration: Concurrent execution with aggregation

**Examples (5 working examples)**
- Echo agent, HTTP transport
- Reflection pattern
- Agents-as-tools delegation
- Orchestration (sequential and parallel)

**Total**: ~2,282 LOC, 44 tests (100% passing)

**Next Steps:**
- v0.26.0: More patterns (ReAct, Planning, Conversational, Task)
- v0.27.0: Complete pattern parity (Multiagent, Autonomous, Memory, Reasoning)
- v0.28.0: WASM support + Evaluation frameworks

## Performance

Rust implementation goals:
- **20x faster** than Python (expected)
- **Low memory footprint**: ~8 MB per agent
- **WASM support**: Browser deployment with minimal bundle size
- **Zero-copy serialization** where possible

## License

MIT

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
