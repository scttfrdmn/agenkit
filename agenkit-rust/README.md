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

## Examples

Run the included examples:

```bash
# Echo agent - simple agent that echoes input
cargo run --example echo_agent

# HTTP transport - client/server communication
cargo run --example http_transport
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
3. **Transports** (`transports/`): HTTP, WebSocket, gRPC (HTTP implemented)
4. **Patterns** (future): ReAct, Reflection, Planning, etc.
5. **Evaluation** (future): Benchmarking and testing frameworks

## Current Status

✅ **v0.1.0 - Infrastructure Complete**

- Core Agent trait and Message types (~350 LOC)
- HTTP transport (client and server) (~200 LOC)
- 17 unit tests + 8 doc tests (100% passing)
- 2 working examples
- Full documentation

**Next Steps:**
- v0.2.0: Critical patterns (Reflection, Agents-as-Tools)
- v0.3.0: More patterns (ReAct, Planning, Orchestration)
- v0.4.0: WASM support
- v0.5.0: Evaluation frameworks

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
