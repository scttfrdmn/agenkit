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
agenkit = "0.27"
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
# Infrastructure Examples
cargo run --example echo_agent          # Simple echo agent
cargo run --example http_transport      # Client/server communication

# Pattern Examples (All 11 Patterns)
cargo run --example reflection_pattern            # Iterative self-critique
cargo run --example agents_as_tools               # Hierarchical delegation
cargo run --example orchestration                 # Sequential & parallel
cargo run --example react_pattern                 # Reasoning-Acting cycles
cargo run --example planning_pattern              # Task decomposition
cargo run --example conversational_pattern        # Multi-turn dialogue
cargo run --example task_pattern                  # One-shot execution
cargo run --example multiagent_pattern            # Multi-agent collaboration
cargo run --example autonomous_pattern            # Goal-directed agents
cargo run --example memory_hierarchy_pattern      # Three-tier memory
cargo run --example reasoning_with_tools_pattern  # Interleaved reasoning
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

✅ **v0.27.0 - Four-Language Pattern Parity Achieved!** 🎉

**Infrastructure (~982 LOC, 25 tests)**
- Core Agent trait with async support
- HTTP transport (client and server)
- Message and ToolResult types
- Comprehensive error handling

**Patterns (~5,318 LOC, 79 tests) - 11/11 Complete**
1. **Reflection** - Iterative self-critique and refinement
2. **Agents-as-Tools** - Hierarchical delegation through tool wrapping
3. **Orchestration** - Sequential and parallel composition
4. **ReAct** - Reasoning-Acting cycles with tool integration
5. **Planning** - Task decomposition and execution
6. **Conversational** - Multi-turn dialogue management
7. **Task** - One-shot task execution with lifecycle
8. **Multiagent** - Multi-agent orchestration and consensus
9. **Autonomous** - Goal-directed self-organizing agents
10. **Memory Hierarchy** - Three-tier memory system
11. **Reasoning with Tools** - Interleaved reasoning and tool usage

**Examples (13 working examples)**
- Infrastructure: echo_agent, http_transport
- All 11 patterns with comprehensive demonstrations

**Total**: ~6,300 LOC, 104 tests (100% passing)

**Achievement**: First AI agent toolkit with 100% pattern parity across Python, TypeScript, Go, and Rust!

**Next Steps:**
- v0.28.0: WASM support + Evaluation frameworks (Target: March 2026)

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
