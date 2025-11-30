# Agenkit Rust Examples

Comprehensive examples demonstrating all Agenkit patterns and features in Rust.

## Directory Structure

Rust uses Cargo's flat example structure:

```
examples/
├── reflection-pattern.rs
├── react-pattern.rs
├── planning-pattern.rs
├── ... (11 pattern examples)
├── openai-basic.rs
├── anthropic-basic.rs
├── ollama-basic.rs
├── echo_agent.rs
├── http_transport.rs
└── README.md (this file)
```

**Note:** Cargo requires examples to be in a flat directory structure. All examples are in `examples/` with descriptive names.

## Pattern Examples

All pattern examples use **mock agents** (no API keys required) to demonstrate the pattern mechanics in isolation. This makes them:
- ✅ Runnable without any external dependencies
- ✅ Fast and deterministic for learning
- ✅ Adapter-agnostic (work with any LLM provider)
- ✅ Perfect for understanding pattern behavior

| Pattern | File | Command |
|---------|------|---------|
| **Reflection** | [reflection-pattern.rs](reflection-pattern.rs) | `cargo run --example reflection-pattern` |
| **ReAct** | [react-pattern.rs](react-pattern.rs) | `cargo run --example react-pattern` |
| **Planning** | [planning-pattern.rs](planning-pattern.rs) | `cargo run --example planning-pattern` |
| **Task** | [task-pattern.rs](task-pattern.rs) | `cargo run --example task-pattern` |
| **Multiagent** | [multiagent-pattern.rs](multiagent-pattern.rs) | `cargo run --example multiagent-pattern` |
| **Orchestration** | [orchestration-pattern.rs](orchestration-pattern.rs) | `cargo run --example orchestration-pattern` |
| **Conversational** | [conversational-pattern.rs](conversational-pattern.rs) | `cargo run --example conversational-pattern` |
| **Memory Hierarchy** | [memory-hierarchy-pattern.rs](memory-hierarchy-pattern.rs) | `cargo run --example memory-hierarchy-pattern` |
| **Agents as Tools** | [agents-as-tools-pattern.rs](agents-as-tools-pattern.rs) | `cargo run --example agents-as-tools-pattern` |
| **Reasoning with Tools** | [reasoning-with-tools-pattern.rs](reasoning-with-tools-pattern.rs) | `cargo run --example reasoning-with-tools-pattern` |
| **Autonomous** | [autonomous-pattern.rs](autonomous-pattern.rs) | `cargo run --example autonomous-pattern` |

## Adapter Examples

Real LLM provider integrations for production use:

| Adapter | File | Command |
|---------|------|---------|
| **OpenAI** | [openai-basic.rs](openai-basic.rs) | `cargo run --example openai-basic` |
| **Anthropic** | [anthropic-basic.rs](anthropic-basic.rs) | `cargo run --example anthropic-basic` |
| **Ollama** | [ollama-basic.rs](ollama-basic.rs) | `cargo run --example ollama-basic` |

## Other Examples

| Category | File | Command |
|----------|------|---------|
| **Echo Agent** | [echo_agent.rs](echo_agent.rs) | `cargo run --example echo_agent` |
| **HTTP Transport** | [http_transport.rs](http_transport.rs) | `cargo run --example http_transport` |

## Getting Started

### Prerequisites

- Rust 1.70 or later (install from [rustup.rs](https://rustup.rs/))
- Cargo (comes with Rust)
- For adapter examples: API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY) or Ollama installation
- For pattern examples: **No API keys required!** Uses mock agents

### Installation

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Clone and build
git clone https://github.com/agenkit/agenkit.git
cd agenkit/agenkit-rust

# Build all examples
cargo build --examples --release
```

### Running Examples

Cargo makes running examples simple with the `--example` flag:

```bash
# Pattern examples (no API keys needed)
cargo run --example reflection-pattern
cargo run --example react-pattern
cargo run --example planning-pattern
cargo run --example multiagent-pattern

# Adapter examples (requires API keys or Ollama)
# OpenAI
export OPENAI_API_KEY="sk-..."
cargo run --example openai-basic

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
cargo run --example anthropic-basic

# Ollama (local, free)
# Install from https://ollama.ai then:
ollama pull llama2
cargo run --example ollama-basic

# Other examples
cargo run --example echo_agent
cargo run --example http_transport
```

### Release Mode

For better performance, use release mode:
```bash
cargo run --example reflection-pattern --release
```

## Key Principles

### Pattern Examples Use Mock Agents

All pattern examples use **mock agents** that simulate LLM behavior:

```rust
/// Mock agent - no API calls
struct SimpleGenerator;

#[async_trait]
impl Agent for SimpleGenerator {
    fn name(&self) -> &str {
        "SimpleGenerator"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simulated behavior for demonstration
        let response = generate_mock_response(&message);
        Ok(Message::with_text("assistant", response))
    }
}
```

**Why mock agents?**
- ✅ Learn pattern mechanics without API costs
- ✅ Fast, deterministic, reproducible
- ✅ No external dependencies or API keys
- ✅ Focus on pattern logic, not LLM responses

### Swapping Mock Agents for Real LLMs

Once you understand a pattern, swap the mock agent for a real LLM:

```rust
// Development: Mock agent (from pattern example)
let generator = Arc::new(MockCodeGenerator::new());

// Production: Real LLM (Ollama - free, local)
let generator = Arc::new(OllamaAgent::new(OllamaConfig {
    model: "llama2".to_string(),
    base_url: "http://localhost:11434".to_string(),
    ..Default::default()
}));

// Production: Real LLM (OpenAI - paid, cloud)
let generator = Arc::new(OpenAIAgent::new(OpenAIConfig {
    model: "gpt-4".to_string(),
    api_key: std::env::var("OPENAI_API_KEY").unwrap(),
    ..Default::default()
}));

// Pattern works identically with all agents!
let reflection = ReflectionAgent::new(generator, critic, config);
```

The pattern orchestration remains **identical** - only the agents change.

## Learning Path

We recommend following this progression:

### 1. Start with Patterns (Mock Agents)
Learn pattern mechanics without external dependencies:
```bash
cargo run --example reflection-pattern      # Iterative improvement
cargo run --example react-pattern           # Reasoning + Acting
cargo run --example planning-pattern        # Task decomposition
cargo run --example multiagent-pattern      # Agent coordination
```

### 2. Explore Adapters (Real LLMs)

#### Local Development (Free)
Start with Ollama for local, free LLM access:
```bash
# Install Ollama: https://ollama.ai
ollama pull llama2

# Run Ollama example
cargo run --example ollama-basic
```

**Ollama advantages:**
- ✅ Completely free
- ✅ Runs locally (no internet required)
- ✅ Fast for development
- ✅ Privacy-preserving
- ✅ Multiple models available (Llama 2, Mistral, CodeLlama, etc.)

#### Cloud Providers (Paid)
Move to cloud providers when ready:
```bash
# OpenAI (GPT-4)
export OPENAI_API_KEY="sk-..."
cargo run --example openai-basic

# Anthropic (Claude 3.5 Sonnet)
export ANTHROPIC_API_KEY="sk-ant-..."
cargo run --example anthropic-basic
```

### 3. Production Features
Add resilience and observability:
```bash
cargo run --example http_transport         # HTTP communication
# More middleware examples coming soon!
```

### 4. Advanced Patterns
Explore composition and specialized patterns:
```bash
cargo run --example autonomous-pattern
cargo run --example memory-hierarchy-pattern
cargo run --example orchestration-pattern
```

## Best Practices

### Async/Await with Tokio

All agent operations are async with Tokio runtime:
```rust
use tokio;

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    let agent = MyAgent::new();
    let result = agent.process(message).await?;
    println!("Success: {}", result.content_as_str()?);
    Ok(())
}
```

### Error Handling with Result

Use Rust's Result type for robust error handling:
```rust
match agent.process(message).await {
    Ok(response) => {
        println!("Success: {}", response.content_as_str()?);
    }
    Err(e) => {
        eprintln!("Error: {}", e);
    }
}

// Or use the ? operator
let result = agent.process(message).await?;
```

### Type Safety

Rust provides compile-time safety:
```rust
use agenkit::core::{Agent, Message, AgentError};
use async_trait::async_trait;

struct MyAgent;

#[async_trait]
impl Agent for MyAgent {
    fn name(&self) -> &str {
        "MyAgent"
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Type-safe implementation
        Ok(Message::with_text("assistant", "Response"))
    }
}
```

### Ownership and Borrowing

Use Arc for shared ownership of agents:
```rust
use std::sync::Arc;

let agent = Arc::new(MyAgent::new());

// Share across threads/tasks
let agent_clone = Arc::clone(&agent);
tokio::spawn(async move {
    let result = agent_clone.process(message).await;
});
```

### Pattern Matching

Use Rust's powerful pattern matching:
```rust
let content = match message.content {
    MessageContent::Text(text) => text,
    MessageContent::ToolUse(tool) => tool.name,
    MessageContent::ToolResult(result) => result.output,
};
```

## Pattern Achievements (v0.31.0)

Agenkit Rust now has **full pattern parity** across all 4 languages (Python, Go, TypeScript, C++):

✅ **11/11 patterns implemented**
- All patterns use consistent APIs
- Mock agents for demonstration
- Production-ready implementations
- Comprehensive documentation
- Zero-cost abstractions
- Memory-safe by design

## Examples Statistics

- **Pattern Examples**: 11 (all use mock agents)
- **Adapter Examples**: 3 (OpenAI, Anthropic, Ollama)
- **Other Examples**: 2 (echo agent, HTTP transport)
- **Total**: 16 comprehensive examples

## Documentation Links

- **Main README**: [/README.md](../../README.md) - Project overview
- **API Documentation**: [/docs/API.md](../../docs/API.md) - Detailed API reference
- **Architecture**: [/ARCHITECTURE.md](../../ARCHITECTURE.md) - Design principles
- **Roadmap**: [/ROADMAP.md](../../ROADMAP.md) - Development status and plans
- **Python Examples**: [/examples/README.md](../../examples/README.md) - Python reference implementation
- **Cargo Docs**: Run `cargo doc --open` for generated documentation

## Cross-Language Compatibility

All Rust examples are designed for cross-language interoperability:
- **HTTP Transport**: RESTful API for cross-language communication
- **gRPC Transport**: High-performance binary protocol (coming soon)
- **WebSocket Transport**: Real-time bidirectional messaging (coming soon)
- **Consistent APIs**: Same patterns work across all languages

Example: Rust agent ↔ Python agent via HTTP:
```bash
# Terminal 1: Start Python agent server
python examples/transport/http_example.py

# Terminal 2: Connect with Rust client
cargo run --example http_transport
```

## Why Rust?

Rust brings several advantages to Agenkit:
- **Memory Safety**: No null pointer dereferences, no data races
- **Performance**: Native code execution, zero-cost abstractions
- **Concurrency**: Fearless concurrent programming with async/await
- **Type Safety**: Compile-time guarantees prevent many bugs
- **Ecosystem**: Growing ecosystem with Cargo package manager
- **WebAssembly**: Compile to WASM for browser/edge deployment
- **Reliability**: Used in production by Discord, Cloudflare, AWS, Microsoft

## Testing

Run the test suite:
```bash
cargo test
```

All examples are production-ready and well-tested. See [tests/](../../tests/) for additional patterns.

## Cargo Features

Customize the build with Cargo features:
```bash
# Build with OpenAI support only
cargo build --features openai

# Build with all adapters
cargo build --features "openai anthropic ollama"

# Build with full feature set
cargo build --all-features
```

## WebAssembly Support

Compile Rust agents to WebAssembly:
```bash
# Add wasm32 target
rustup target add wasm32-unknown-unknown

# Build for WASM
cargo build --target wasm32-unknown-unknown --release

# See wasm_browser_agent.html for browser example
```

## Platform Support

| Platform | Architecture | Status |
|----------|-------------|---------|
| Linux | x86_64, ARM64 | ✅ Fully supported |
| macOS | x86_64, ARM64 (Apple Silicon) | ✅ Fully supported |
| Windows | x86_64 | ✅ Fully supported |
| WebAssembly | wasm32 | ✅ Supported (see examples) |
| iOS/Android | ARM64 | 🚧 Experimental |

## Rust Version Policy

Agenkit Rust follows a conservative Minimum Supported Rust Version (MSRV) policy:
- **Current MSRV**: 1.70
- **Policy**: MSRV bumps require minor version bump
- **Testing**: CI tests against MSRV and stable

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/agenkit/agenkit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/agenkit/agenkit/discussions)
- **Documentation**: [/docs](../../docs/)
- **Cargo Docs**: `cargo doc --open`
- **Tests**: [/tests](../../tests/) - 137+ test examples
- **Rust Discord**: #agenkit on Rust Discord (coming soon)

## Contributing

We welcome contributions! To add a new example:

1. Create `examples/my-example.rs`
2. Add documentation comments at the top
3. Use mock agents for pattern examples
4. Test with `cargo run --example my-example`
5. Submit a PR

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## Next Steps

1. **Install Rust**: Visit [rustup.rs](https://rustup.rs/)
2. **Run a pattern example**: Start with `cargo run --example reflection-pattern`
3. **Understand the pattern**: Read the code comments and output
4. **Try Ollama**: Free, local LLM (`cargo run --example ollama-basic`)
5. **Add a cloud provider**: OpenAI or Anthropic when ready
6. **Build something**: Combine patterns for your use case
7. **Compile to WASM**: Deploy agents to the browser/edge

Happy building! 🚀🦀
